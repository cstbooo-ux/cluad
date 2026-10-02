#!/usr/bin/env python3
"""复印机 / 碳粉风格的逐帧渲染引擎（mv4 用，派生自 mv3/engine.py）。

画布是三种油墨的覆盖率，最后叠印到纸色上，带网点、纸纹、套色错位和线条抖动；
场景元素按景深分层，由虚拟摄像机投影得到视差。
"""
import math
import os
import subprocess
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

D = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(D, "fonts")
W, H, FPS = 1920, 1080, 30
CX, CY = W / 2, H / 2
BPM, PH = 112.0, 0.025
BEAT = 60.0 / BPM
f32 = np.float32

# ------------------------------------------------------------------ inks
PAPER = np.array([0.835, 0.815, 0.760], f32)
INK = np.array([[0.17, 0.16, 0.15],    # toner black
                [0.60, 0.20, 0.18],    # dull red (dried ink / stamp pad)
                [0.80, 0.79, 0.76]],   # light toner grey
               f32)
# ink combinations; older names kept as aliases for the shared motifs
COL = {"paper": (0, 0, 0), "black": (1, 0, 0), "red": (0, 1, 0), "grey": (0, 0, 1), "redgrey": (0, 1, 1),
       "dark": (1, 0, 0), "blue": (1, 0, 0), "teal": (1, 0, 0), "pink": (0, 1, 0), "yellow": (0, 0, 1), "orange": (0, 1, 1)}


# ------------------------------------------------------------------ easing
def c01(x):
    return 0.0 if x < 0 else (1.0 if x > 1 else x)


def ss(a, b, x):
    x = c01((x - a) / (b - a))
    return x * x * (3 - 2 * x)


def eo(x):
    x = c01(x)
    return 1 - (1 - x) ** 3


def ei(x):
    x = c01(x)
    return x ** 3


def eio(x):
    x = c01(x)
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def eob(x, k=1.70158):
    x = c01(x)
    return 1 + (k + 1) * (x - 1) ** 3 + k * (x - 1) ** 2


def lerp(a, b, u):
    return a + (b - a) * u


def hsh(*a):
    h = 2166136261
    for v in a:
        h = ((h ^ (int(v) & 0xFFFFFFFF)) * 16777619) & 0xFFFFFFFF
    h ^= h >> 13
    h = (h * 0x5BD1E995) & 0xFFFFFFFF
    h ^= h >> 15
    return (h & 0xFFFFFF) / float(0x1000000)


def beat_n(t):
    return math.floor((t - PH) / BEAT)


def beat_u(t):
    return ((t - PH) / BEAT) % 1.0


def bpulse(t, k=7.0):
    return math.exp(-beat_u(t) * BEAT * k)


def pop(t, ti, dur=0.18, amt=0.35):
    """scale, alpha of a pop-in that starts at ti."""
    if t < ti:
        return 0.0, 0.0
    return 1 + amt * (1 - eob((t - ti) / dur)), c01((t - ti + 0.017) / 0.05)


# ------------------------------------------------------------------ canvas
class Canvas:
    """Premultiplied ink coverage. L[0..2] = blue / red / yellow, L[3] = opacity (0 → bare paper)."""

    def __init__(s):
        s.L = np.zeros((4, H, W), f32)

    def fill(s, col, a=1.0):
        c = COL[col]
        for k in range(3):
            s.L[k] *= 1 - a
            if c[k]:
                s.L[k] += a
        s.L[3] *= 1 - a
        s.L[3] += a

    def paint(s, m, x0, y0, col, a=1.0, mode="over"):
        h, w = m.shape
        xa, ya, xb, yb = max(x0, 0), max(y0, 0), min(x0 + w, W), min(y0 + h, H)
        if xb <= xa or yb <= ya:
            return
        mm = m[ya - y0:yb - y0, xa - x0:xb - x0]
        if a != 1.0:
            mm = mm * a
        c = COL[col]
        for k in range(3):
            r = s.L[k, ya:yb, xa:xb]
            if c[k]:
                r += (1 - r) * mm
            elif mode == "over":
                r -= r * mm
        r = s.L[3, ya:yb, xa:xb]
        r += (1 - r) * mm

    def over(s, o, dx=0, dy=0):
        dx, dy = int(round(dx)), int(round(dy))
        xa, ya, xb, yb = max(dx, 0), max(dy, 0), min(W + dx, W), min(H + dy, H)
        if xb <= xa or yb <= ya:
            return
        src = o.L[:, ya - dy:yb - dy, xa - dx:xb - dx]
        dst = s.L[:, ya:yb, xa:xb]
        dst *= 1 - src[3:4]
        dst += src


def warp_canvas(o, M):
    src = np.ascontiguousarray(o.L.transpose(1, 2, 0))
    out = cv2.warpPerspective(src, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    c = Canvas()
    c.L = np.ascontiguousarray(out.transpose(2, 0, 1))
    return c


def bmax(buf, m, x0, y0, a=1.0):
    h, w = m.shape
    xa, ya, xb, yb = max(x0, 0), max(y0, 0), min(x0 + w, W), min(y0 + h, H)
    if xb <= xa or yb <= ya:
        return
    src = m[ya - y0:yb - y0, xa - x0:xb - x0]
    reg = buf[ya:yb, xa:xb]
    np.maximum(reg, src * a if a != 1.0 else src, out=reg)


# ------------------------------------------------------------------ camera
class View:
    """authored point → screen: C + R(roll) · (s·(p − C) + t) + o."""

    def __init__(s, sc=1.0, rot=0.0, tx=0.0, ty=0.0, ox=0.0, oy=0.0):
        s.s, s.r, s.tx, s.ty, s.ox, s.oy = sc, rot, tx, ty, ox, oy
        a = math.radians(rot)
        s.cr, s.sr = math.cos(a), math.sin(a)

    def pt(s, x, y):
        qx = s.s * (x - CX) + s.tx
        qy = s.s * (y - CY) + s.ty
        return CX + s.cr * qx - s.sr * qy + s.ox, CY + s.sr * qx + s.cr * qy + s.oy

    def pts(s, P):
        P = np.asarray(P, np.float64)
        qx = s.s * (P[:, 0] - CX) + s.tx
        qy = s.s * (P[:, 1] - CY) + s.ty
        return np.stack([CX + s.cr * qx - s.sr * qy + s.ox, CY + s.sr * qx + s.cr * qy + s.oy], 1)


class Sub:
    """A view whose authored plane is additionally rotated by deg about (px, py)."""

    def __init__(s, v, px, py, deg):
        s.v, s.px, s.py = v, px, py
        a = math.radians(deg)
        s.c, s.sn = math.cos(a), math.sin(a)
        s.s, s.r = v.s, v.r + deg

    def _rot(s, x, y):
        dx, dy = x - s.px, y - s.py
        return s.px + s.c * dx - s.sn * dy, s.py + s.sn * dx + s.c * dy

    def pt(s, x, y):
        return s.v.pt(*s._rot(x, y))

    def pts(s, P):
        P = np.asarray(P, np.float64)
        x, y = s._rot(P[:, 0], P[:, 1])
        return s.v.pts(np.stack([x, y], 1))


V0 = View()


def cam(x=0.0, y=0.0, z=0.0, roll=0.0, depth=1000.0, ox=0.0, oy=0.0):
    """Pinhole camera at (x, y, z) looking at a layer `depth` away; depth 1000 is the main plane."""
    k = depth / (depth - z)
    return View(k, roll, -x * 1000.0 / (depth - z), -y * 1000.0 / (depth - z), ox, oy)


# ------------------------------------------------------------------ textures
_rng = np.random.default_rng(20260928)
_gy, _gx = np.mgrid[0:H, 0:W].astype(f32)


def _noise(sig):
    if sig > 6:
        n = _rng.standard_normal((H // 8 + 1, W // 8 + 1)).astype(f32)
        n = cv2.resize(cv2.GaussianBlur(n, (0, 0), sig / 8), (W, H), interpolation=cv2.INTER_CUBIC)
    else:
        n = _rng.standard_normal((H, W)).astype(f32)
        if sig > 0:
            n = cv2.GaussianBlur(n, (0, 0), sig)
    return n / (n.std() + 1e-6)


PAPER_IMG = (PAPER[None, None, :] * (1 + 0.012 * _noise(70) + 0.008 * _noise(9) + 0.010 * _noise(0.6))[..., None]).astype(f32)
TEX = []
for _ in range(3):
    _speck = np.clip((_noise(0.8) - 1.2) / 0.9, 0, 1)
    TEX.append(np.clip(1 - 0.36 * _speck - 0.035 * np.clip(_noise(4), 0, None), 0.3, 1).astype(f32))
MAPS = []
for _ in range(3):
    _d = []
    for __ in range(2):
        n = cv2.GaussianBlur(_rng.standard_normal((H // 8 + 1, W // 8 + 1)).astype(f32), (0, 0), 1.6)
        n = cv2.resize(n, (W, H), interpolation=cv2.INTER_CUBIC)
        _d.append(n * (1.15 / (n.std() + 1e-6)))
    MAPS.append(((_gx + _d[0]).astype(f32), (_gy + _d[1]).astype(f32)))
GRAIN = [(_rng.standard_normal((H, W)) * 0.007).astype(f32) for _ in range(4)]

_htg, _htc = {}, {}


def ht_grid(cell, ang):
    k = (cell, ang)
    if k not in _htg:
        a = math.radians(ang)
        u = (_gx * math.cos(a) + _gy * math.sin(a)) / cell
        v = (-_gx * math.sin(a) + _gy * math.cos(a)) / cell
        _htg[k] = np.sqrt((u - np.round(u)) ** 2 + (v - np.round(v)) ** 2).astype(f32)
    return _htg[k]


def halftone(val, cell=14, ang=20):
    r = 0.72 * np.sqrt(np.clip(val, 0, 1))
    return np.clip((r - ht_grid(cell, ang)) * (cell / 1.3) + 0.5, 0, 1).astype(f32)


def HT(val, cell=14, ang=20):
    k = (val, cell, ang)
    if k not in _htc:
        _htc[k] = halftone(val, cell, ang)
    return _htc[k]


def ssv(a, b, x):
    x = np.clip((x - a) / (b - a), 0, 1)
    return x * x * (3 - 2 * x)


# ------------------------------------------------------------------ type
FONT_FILES = {"heavy": "SourceHanSansSC-Heavy.otf", "bold": "SourceHanSansSC-Bold.otf",
              "smiley": "SmileySans-Oblique.ttf", "kai": "LXGWWenKai-Medium.ttf"}
_fonts, _glyphs, _adv = {}, {}, {}
_gbytes = [0]


def font(fk, size):
    k = (fk, size)
    if k not in _fonts:
        _fonts[k] = ImageFont.truetype(os.path.join(FONT_DIR, FONT_FILES[fk]), size)
    return _fonts[k]


def adv(fk, ch):
    k = (fk, ch)
    if k not in _adv:
        _adv[k] = font(fk, 500).getlength(ch) / 500.0
    return _adv[k]


def qsize(px):
    return max(4, int(round(2 ** (math.ceil(24 * math.log2(max(px, 4.0))) / 24))))


def glyph(fk, size, ch):
    k = (fk, size, ch)
    g = _glyphs.get(k)
    if g is None:
        if _gbytes[0] > 900e6:
            _glyphs.clear()
            _gbytes[0] = 0
        S = int(size * 1.5) + 8
        im = Image.new("L", (S, S), 0)
        ImageDraw.Draw(im).text((S / 2, S / 2), ch, font=font(fk, size), fill=255, anchor="mm")
        g = np.asarray(im, f32) * (1 / 255.0)
        _glyphs[k] = g
        _gbytes[0] += g.nbytes
    return g


def place(m, X, Y, sc, rot):
    """m (centered mask) scaled by sc, rotated rot° clockwise, centered at (X, Y). Returns patch, x0, y0."""
    h, w = m.shape
    if abs(rot) < 0.05 and abs(sc - 1) < 0.004:
        return m, int(round(X - w / 2)), int(round(Y - h / 2))
    a = math.radians(rot)
    ca, sa = abs(math.cos(a)), abs(math.sin(a))
    ow, oh = int((ca * w + sa * h) * sc) + 4, int((sa * w + ca * h) * sc) + 4
    x0, y0 = int(math.floor(X - ow / 2)), int(math.floor(Y - oh / 2))
    xa, ya, xb, yb = max(x0, 0), max(y0, 0), min(x0 + ow, W), min(y0 + oh, H)
    if xb <= xa or yb <= ya:
        return None, 0, 0
    M = cv2.getRotationMatrix2D((w / 2, h / 2), -rot, sc)
    M[0, 2] += (X - xa) - w / 2
    M[1, 2] += (Y - ya) - h / 2
    return cv2.warpAffine(m, M, (xb - xa, yb - ya), flags=cv2.INTER_LINEAR), xa, ya


def wipe_mask(m, gs, u):
    S = m.shape[1]
    soft = gs * 0.12
    left = S / 2 - gs * 0.52
    ramp = np.clip((left + u * (gs * 1.04 + soft) - np.arange(S, dtype=f32)) / soft, 0, 1).astype(f32)
    return m * ramp[None, :]


def ch_at(cv, v, fk, size, ch, x, y, col, sc=1.0, rot=0.0, a=1.0, mode="over", wipe=None, buf=None):
    if a <= 0.004 or sc <= 0.01:
        return
    X, Y = v.pt(x, y)
    ps = size * sc * v.s
    if ps < 2 or X < -ps or X > W + ps or Y < -ps or Y > H + ps:
        return
    gs = qsize(ps)
    m = glyph(fk, gs, ch)
    if wipe is not None:
        if wipe <= 0:
            return
        if wipe < 1:
            m = wipe_mask(m, gs, wipe)
    patch, x0, y0 = place(m, X, Y, ps / gs, rot + v.r)
    if patch is None:
        return
    if buf is not None:
        bmax(buf, patch, x0, y0, a)
    else:
        cv.paint(patch, x0, y0, col, a, mode)


def line_xs(text, fk, size, track=0.0):
    advs = [adv(fk, c) * size for c in text]
    tot = sum(advs) + track * size * (len(text) - 1)
    xs, x = [], -tot / 2
    for a_ in advs:
        xs.append(x + a_ / 2)
        x += a_ + track * size
    return xs, tot


# ------------------------------------------------------------------ shapes
def _bbox(S, pad):
    xa = max(int(math.floor(S[:, 0].min())) - pad, 0)
    ya = max(int(math.floor(S[:, 1].min())) - pad, 0)
    xb = min(int(math.ceil(S[:, 0].max())) + pad, W)
    yb = min(int(math.ceil(S[:, 1].max())) + pad, H)
    return (xa, ya, xb, yb) if xb > xa and yb > ya else None


def _emit(cv, patch, xa, ya, col, a, mode, buf):
    m = patch.astype(f32) * (1 / 255.0)
    if buf is not None:
        bmax(buf, m, xa, ya, a)
    else:
        cv.paint(m, xa, ya, col, a, mode)


def _ip(S, xa, ya):
    return np.round((S - (xa, ya)) * 16).clip(-2e8, 2e8).astype(np.int32)


def poly(cv, v, P, col, a=1.0, mode="over", buf=None):
    if a <= 0.004:
        return
    S = v.pts(P)
    bb = _bbox(S, 2)
    if bb is None:
        return
    xa, ya, xb, yb = bb
    patch = np.zeros((yb - ya, xb - xa), np.uint8)
    cv2.fillPoly(patch, [_ip(S, xa, ya)], 255, cv2.LINE_AA, 4)
    _emit(cv, patch, xa, ya, col, a, mode, buf)


def pline(cv, v, P, th, col, a=1.0, closed=False, mode="over", buf=None):
    if a <= 0.004 or len(P) < 2:
        return
    S = v.pts(P)
    tw = th * v.s
    if tw < 1:
        a *= tw
        tw = 1
    bb = _bbox(S, int(tw) + 3)
    if bb is None:
        return
    xa, ya, xb, yb = bb
    patch = np.zeros((yb - ya, xb - xa), np.uint8)
    cv2.polylines(patch, [_ip(S, xa, ya)], closed, 255, int(round(tw)), cv2.LINE_AA, 4)
    _emit(cv, patch, xa, ya, col, a, mode, buf)


def ell(cx, cy, rx, ry, n=72, a0=0.0, a1=2 * math.pi):
    th = np.linspace(a0, a1, n)
    return np.stack([cx + rx * np.cos(th), cy + ry * np.sin(th)], 1)


def disc(cv, v, cx, cy, r, col, a=1.0, mode="over", buf=None):
    poly(cv, v, ell(cx, cy, r, r, 24 + int(min(r * v.s, 400) / 4)), col, a, mode, buf)


def ring(cv, v, cx, cy, r, th, col, a=1.0, mode="over", buf=None):
    pline(cv, v, ell(cx, cy, r, r, 24 + int(min(r * v.s, 400) / 3)), th, col, a, True, mode, buf)


def rect(cv, v, x0, y0, x1, y1, col, a=1.0, mode="over", buf=None):
    poly(cv, v, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], col, a, mode, buf)


def target(cv, v, x, y, r, col, a=1.0):
    ring(cv, v, x, y, r, 3, col, a)
    pline(cv, v, [(x - 1.9 * r, y), (x + 1.9 * r, y)], 3, col, a)
    pline(cv, v, [(x, y - 1.9 * r), (x, y + 1.9 * r)], 3, col, a)


# ------------------------------------------------------------------ motifs
def wind_curl(x0, y0, length, amp=20.0, curl=60.0, turns=1.15, down=False):
    n = 70
    xs = np.linspace(0, length, n)
    ys = amp * np.sin(np.linspace(0, np.pi * 1.4, n))
    th = np.linspace(0, turns * 2 * np.pi, 80)[1:]
    r = curl * (1 - 0.6 * th / (turns * 2 * np.pi))
    cx, cy = length, ys[-1] - curl
    P = np.concatenate([np.stack([xs, ys], 1), np.stack([cx + r * np.sin(th), cy + r * np.cos(th)], 1)])
    if down:
        P[:, 1] = -P[:, 1]
    return P + (x0, y0)


def sub_path(P, a, b):
    d = np.hypot(*np.diff(P, axis=0).T)
    c = np.concatenate([[0], np.cumsum(d)])
    s0, s1 = a * c[-1], b * c[-1]
    idx = (c > s0) & (c < s1)
    p0 = [np.interp(s0, c, P[:, 0]), np.interp(s0, c, P[:, 1])]
    p1 = [np.interp(s1, c, P[:, 0]), np.interp(s1, c, P[:, 1])]
    return np.vstack([p0, P[idx], p1])


def wind_anim(cv, v, t, t0, dur, P, th, col, a=1.0):
    u = (t - t0) / dur
    if u <= 0 or u >= 1:
        return
    head, tail = eo(u / 0.6), ei((u - 0.25) / 0.75)
    if head - tail > 0.003:
        pline(cv, v, sub_path(P, tail, head), th, col, a)


KITE = np.array([(0, -1.0), (0.7, -0.32), (0, 1.25), (-0.7, -0.32)])


def kite_string(cv, v, bx, by, ax, ay, t, sag=0.1, vib=0.0, sw=3.0, col="dark", a=1.0):
    b, A = np.array([bx, by]), np.array([ax, ay], float)
    dv = A - b
    L = math.hypot(*dv) + 1e-6
    n = np.array([-dv[1], dv[0]]) / L
    if n[1] < 0:
        n = -n
    u = np.linspace(0, 1, 64)[:, None]
    ctrl = (A + b) / 2 + n * sag * L
    P = (1 - u) ** 2 * b + 2 * (1 - u) * u * ctrl + u ** 2 * A
    if vib:
        w = np.sin(np.pi * u) * (np.sin(t * 41.0 + u * 3) * 0.7 + np.sin(t * 67.0 - u * 7) * 0.3)
        P = P + n[None, :] * vib * w
    pline(cv, v, P, sw, col, a)


def kite(cv, v, x, y, s, rot, t, anchor=None, sag=0.1, vib=0.0, body=("red", "orange"), spar="dark",
         string="dark", sw=3.0, tail=True, wind=1.0, a=1.0):
    cr, sr = math.cos(math.radians(rot)), math.sin(math.radians(rot))

    def T(P):
        P = np.asarray(P, np.float64) * s
        return np.stack([x + cr * P[:, 0] - sr * P[:, 1], y + sr * P[:, 0] + cr * P[:, 1]], 1)

    if anchor is not None:
        b = T([(0, 0.12)])[0]
        kite_string(cv, v, b[0], b[1], anchor[0], anchor[1], t, sag, vib, sw, string, a)
    if tail:
        n = 40
        u = np.linspace(0, 1, n)
        P = T(np.stack([0.34 * np.sin(u * 7 - t * 7.5) * u * wind, 1.25 + 2.7 * u], 1))
        P[:, 0] -= s * 0.9 * u ** 1.5 * wind
        pline(cv, v, P, max(2.0, s * 0.03), "dark", a)
        for j, uu in enumerate((0.3, 0.62, 0.95)):
            cx_, cy_ = P[int(uu * (n - 1))]
            bw, bh = 0.17 * s, 0.13 * s
            c = ("blue", "red", "blue")[j]
            poly(cv, v, [(cx_ - bw, cy_ - bh), (cx_, cy_), (cx_ - bw, cy_ + bh)], c, a)
            poly(cv, v, [(cx_ + bw, cy_ - bh), (cx_, cy_), (cx_ + bw, cy_ + bh)], c, a)
    P = T(KITE)
    poly(cv, v, [P[0], P[2], P[3]], body[0], a)
    poly(cv, v, [P[0], P[1], P[2]], body[1], a)
    pline(cv, v, [P[0], P[2]], max(2.0, s * 0.035), spar, a)
    pline(cv, v, [P[3], P[1]], max(2.0, s * 0.035), spar, a)


def person(cv, v, x, y, sc, t, col="dark", scarf="red", a=1.0):
    """Flat silhouette seen from behind, right hand raised holding a kite line. (x, y) = feet."""
    def T(P):
        P = np.asarray(P, np.float64)
        return np.stack([x + P[:, 0] * sc, y + P[:, 1] * sc], 1)

    fl = 12 * math.sin(t * 9.0) + 7 * math.sin(t * 13.7)
    poly(cv, v, T([(-40, 30), (-14, 30), (-16, 205), (-40, 205)]), col, a)
    poly(cv, v, T([(14, 30), (40, 30), (40, 205), (16, 205)]), col, a)
    poly(cv, v, T([(-66, -272), (66, -272), (82, -130), (94 + fl * 0.5, 54), (-92 + fl * 0.3, 54), (-82, -130)]), col, a)
    pline(cv, v, T([(-60, -256), (-88, -160), (-84, -70)]), 26 * sc, col, a)
    pline(cv, v, T([(60, -256), (98, -335), (78, -425)]), 26 * sc, col, a)
    rect(cv, v, *T([(-16, -300)])[0], *T([(16, -262)])[0], col, a)
    disc(cv, v, *T([(0, -335)])[0], 50 * sc, col, a)
    poly(cv, v, T([(-30, -296), (26, -300), (170 + fl * 2.2, -318 + fl), (182 + fl * 2.6, -286 + fl * 1.2), (24, -270), (-30, -272)]), scarf, a)
    return T([(80, -432)])[0]


def bird(cv, v, x, y, s, t, ph, col="dark"):
    f = math.sin(t * 9 + ph)
    pline(cv, v, [(x - s, y - s * 0.5 * f), (x - s * 0.4, y - s * 0.25), (x, y), (x + s * 0.4, y - s * 0.25), (x + s, y - s * 0.5 * f)], 3, col)


def tuft(cv, v, x, y, h, t, sway, col, seed):
    for j in range(3):
        off = (j - 1) * h * 0.18
        hh = h * (0.75 + 0.35 * hsh(seed, j))
        sw_ = sway * (0.8 + 0.4 * hsh(seed, j, 3)) + 6 * math.sin(t * 3 + seed + j)
        poly(cv, v, [(x + off - 7, y), (x + off + sw_ * 0.35 - 3, y - hh * 0.55), (x + off + sw_, y - hh),
                     (x + off + sw_ * 0.35 + 3, y - hh * 0.55), (x + off + 7, y)], col)




def over_masked(dst, src, m):
    """Composite canvas src over dst through a (H, W) mask."""
    a = src.L[3] * m
    dst.L *= 1 - a[None]
    dst.L += src.L * m[None]


def slide(a, b, e, dx, dy):
    """Canvas a leaves by (dx, dy)·e while b enters from the opposite side."""
    out = Canvas()
    out.over(a, dx * e, dy * e)
    out.over(b, -dx * (1 - e), -dy * (1 - e))
    return out


def card_flip(src, th_deg, F=2600.0, k=0.92):
    a_ = math.radians(th_deg)
    corners = np.array([(0, 0), (W, 0), (W, H), (0, H)], np.float64)
    dst = []
    for (px, py) in corners:
        dxp = px - CX
        s = F / (F + dxp * math.sin(a_)) * k
        dst.append((CX + dxp * math.cos(a_) * s, CY + (py - CY) * s))
    M = cv2.getPerspectiveTransform(corners.astype(f32), np.array(dst, f32))
    return warp_canvas(src, M)


# ------------------------------------------------------------------ chrome / finish
def ui(cv, t, st, credit, a=1.0):
    if a <= 0:
        return

    def pick(x0, y0, x1, y1):
        return "paper" if cv.L[:3, y0:y1:3, x0:x1:3].max(0).mean() > 0.45 else "dark"

    m, l = 40, 46
    for (sx_, sy_) in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
        x0 = m if sx_ > 0 else W - m
        y0 = m if sy_ > 0 else H - m
        col = pick(min(x0, x0 + sx_ * l), min(y0, y0 + sy_ * l), max(x0, x0 + sx_ * l), max(y0, y0 + sy_ * l))
        pline(cv, V0, [(x0, y0 + sy_ * l), (x0, y0), (x0 + sx_ * l, y0)], 3, col, a)
    lab = "No.%02d" % st.get("no", 1)
    xs, tot = line_xs(lab, "smiley", 34)
    col = pick(m + 60, m, m + 60 + int(tot), m + 40)
    for i, c in enumerate(lab):
        ch_at(cv, V0, "smiley", 34, c, m + 64 + tot / 2 + xs[i], m + 18, col, a=a)
    xs, tot = line_xs(credit, "smiley", 34)
    col = pick(W - m - 64 - int(tot), H - m - 40, W - m - 64, H - m)
    for i, c in enumerate(credit):
        ch_at(cv, V0, "smiley", 34, c, W - m - 64 - tot / 2 + xs[i], H - m - 18, col, a=a)


def hit_env(hits, t, k):
    v = 0.0
    for (ti, s) in hits:
        if 0 <= t - ti < 1.5:
            v += s * math.exp(-(t - ti) * k)
    return v


def shifted(a, dx, dy):
    if dx == 0 and dy == 0:
        return a
    out = np.zeros_like(a)
    out[max(dy, 0):H + min(dy, 0), max(dx, 0):W + min(dx, 0)] = a[max(-dy, 0):H + min(-dy, 0), max(-dx, 0):W + min(-dx, 0)]
    return out


def finish(cv, fidx, t, st, hits):
    L = cv.L
    if st.get("blur"):
        bx, by = st["blur"]
        k = (max(1, int(bx)), max(1, int(by)))
        if k != (1, 1):
            for c in range(3):
                L[c] = cv2.blur(L[c], k)
    q = (fidx // 3) % 3
    mx, my = MAPS[q]
    ch = [cv2.remap(L[c], mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE) for c in range(3)]
    sh = hit_env(hits, t, 9.0) + st.get("shake", 0.0)
    mis = st.get("mis", (0, 0))
    ch[1] = shifted(ch[1], int(round(3 + 12 * min(sh, 1.6) + mis[0])), int(round(-2 + 7 * min(sh, 1.6) + mis[1])))
    fade = st.get("fade", 1.0)
    img = PAPER_IMG.copy()
    for c in range(3):
        ch[c] *= TEX[(q + c) % 3] * fade
        img *= 1 - ch[c][..., None] * (1 - INK[c])
    zoom = 1 + 0.035 * hit_env(hits, t, 12.0) + st.get("zoom", 0.0)
    dx = sh * 16 * math.sin(t * 83.0) + sh * 7 * math.sin(t * 51.0)
    dy = sh * 13 * math.cos(t * 71.0)
    rot = sh * 0.8 * math.sin(t * 37.0)
    if abs(zoom - 1) > 0.002 or abs(dx) + abs(dy) > 0.3:
        M = cv2.getRotationMatrix2D((CX, CY), rot, zoom)
        M[0, 2] += dx
        M[1, 2] += dy
        img = cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    img += GRAIN[fidx % 4][..., None]
    return (np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)
