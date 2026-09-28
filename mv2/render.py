#!/usr/bin/env python3
"""风筝 MV v2 —— 孔版印刷（Risograph）纸面风格的动态字 MV 渲染器。

30 s / 1920x1080 / 30 fps。所有画面都由代码逐帧生成：
  * 画布是三种油墨（蓝 / 红 / 黄）的覆盖率，最后叠印到纸色上，带网点、纸纹、套色错位和线条抖动；
  * 场景里的元素按景深分层，由虚拟摄像机（平移 / 推拉 / 旋转）投影，得到视差；
  * 歌词逐字动画，时间在各场景函数里。

用法：
  python3 render.py stills 2.0 7.5 ...   # 渲染静帧到 stills/
  python3 render.py video out.mp4        # 渲染成片（音频来自 $MV_AUDIO）
"""
import math
import os
import subprocess
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

D = os.path.dirname(os.path.abspath(__file__))
AUDIO = os.environ.get("MV_AUDIO", "/root/.claude/uploads/e5f3b459-77d3-5ac0-ba91-983fc9f5c975/574890a3-__.wav")
FONT_DIR = os.path.join(D, "fonts")
W, H, FPS, DUR = 1920, 1080, 30, 30.0
NF = int(DUR * FPS)
CX, CY = W / 2, H / 2
BPM, PH = 147.0, 0.03
BEAT = 60.0 / BPM
f32 = np.float32

# ------------------------------------------------------------------ inks
PAPER = np.array([0.953, 0.929, 0.878], f32)
INK = np.array([[0.20, 0.34, 0.67],    # blue
                [0.96, 0.32, 0.38],    # red
                [1.00, 0.77, 0.13]],   # yellow
               f32)
COL = {"paper": (0, 0, 0), "blue": (1, 0, 0), "red": (0, 1, 0), "yellow": (0, 0, 1),
       "dark": (1, 1, 0), "orange": (0, 1, 1)}


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


# ================================================================== scenes
# ------------------------------------------------------------------ 01  前奏 / 吹散了天 / 吹乱了地 / 吹远了 / 哦~哦
CLOUDS = [((330, 210), [(-95, 12, 56), (-35, -24, 76), (48, -10, 68), (112, 16, 50), (8, 26, 56)]),
          ((905, 120), [(-70, 6, 44), (-12, -20, 62), (58, 0, 50), (2, 18, 44)]),
          ((1490, 235), [(-112, 12, 58), (-42, -30, 82), (46, -14, 72), (122, 14, 52), (2, 24, 60)]),
          ((1830, 95), [(-40, 4, 36), (8, -12, 46), (48, 6, 34)])]
_r = np.random.default_rng(5)
GRASS = [(float(x), float(_r.uniform(90, 200)), i) for i, x in enumerate(np.linspace(-500, 2420, 46) + _r.uniform(-20, 20, 46))]
W01 = [(1.00, 1.0, wind_curl(140, 640, 760, 24, 62), 11, "blue"),
       (1.25, 0.9, wind_curl(430, 880, 560, 16, 44, down=True), 9, "red"),
       (2.40, 0.8, wind_curl(150, 150, 950, 30, 70), 11, "red"),
       (2.60, 0.8, wind_curl(1150, 560, 600, 18, 46, down=True), 9, "blue"),
       (3.30, 0.8, wind_curl(640, 990, 760, 20, 52, down=True), 10, "blue"),
       (3.95, 0.9, wind_curl(260, 400, 820, 26, 60), 10, "red")]
SAN_V = [(-220, -380), (-70, -520), (110, -470), (280, -560)]
SAN_R = [-80, 45, -40, 90]


def cam01(t):
    u = eo((t - 0.05) / 1.6)
    z, roll, x, y = lerp(560, 0, u), lerp(-7, 0, u), 0.0, 0.0
    y += -130 * eio((t - 1.75) / 0.45) + 130 * eio((t - 2.5) / 0.3)
    y += 150 * eio((t - 2.55) / 0.3) - 150 * eio((t - 3.42) / 0.3)
    roll += 3.5 * eio((t - 2.6) / 0.3) - 3.5 * eio((t - 3.42) / 0.3)
    z += 150 * eio((t - 3.45) / 0.55) - 150 * eio((t - 4.05) / 0.5)
    x += 190 * eio((t - 4.0) / 1.3)
    return x, y, z, roll


def s01(cv, t, st):
    st["no"] = 1
    cv.fill("paper")
    x, y, z, roll = cam01(t)
    vf, vm, vn = cam(x, y, z, roll, 2600), cam(x, y, z, roll), cam(x, y, z, roll, 650)
    push = ei((t - 4.95) / 0.5)

    # far: halftone clouds, torn apart on 吹散了天
    buf = np.zeros((H, W), f32)
    for ci, ((ccx, ccy), puffs) in enumerate(CLOUDS):
        d = t - (2.42 + ci * 0.05)
        for (dx, dy, r) in puffs:
            px, py, rr = ccx + dx + 14 * t + 900 * push, ccy + dy, r
            if d > 0:
                n = math.hypot(dx, dy) + 1e-3
                ux, uy = dx / n, dy / n
                px += (ux * 300 + 180) * d + (ux * 520 + 260) * d * d
                py += (uy * 300 - 240) * d + (uy * 520 - 380) * d * d
                rr *= max(0.0, 1 - 0.85 * d)
            if rr > 1:
                disc(cv, vf, px, py, rr, "blue", buf=buf)
    cv.paint(buf * HT(0.42, 12, 20), 0, 0, "blue", mode="print")

    ra = 1 - ss(0.9, 1.5, t)
    if ra > 0:
        target(cv, vm, 960, 540, 34, "dark", ra)

    for (t0, dur, P, th, col) in W01:
        wind_anim(cv, vm, t, t0, dur, P, th, col)

    # kite: pulled in during the intro, tossed around afterwards
    if t < 1.81:
        u = eo((t - 0.25) / 1.45)
        kx, ky, ks, kr = lerp(700, 1320, u), lerp(1300, 330, u), 105, -12 + 8 * math.sin(t * 2.4)
    else:
        u = eio((t - 1.81) / 0.8)
        kx = lerp(1320, 1560, u) + 30 * math.sin(t * 1.7)
        ky = lerp(330, 200, u) + 22 * math.sin(t * 2.9)
        ks, kr = lerp(105, 78, u), -10 + 20 * math.sin(t * 3.1) + 9 * math.sin(t * 5.3)
    kite(cv, vm, kx + 1500 * push, ky - 500 * push, ks, kr + 40 * push, t, anchor=(-160, 1260), sag=0.12)

    # near: grass
    hb2 = math.floor((t - PH) / (BEAT / 2))
    for (gx, gh, i) in GRASS:
        sway = 16 * math.sin(2.1 * t + gx * 0.012) + 14
        k = ss(2.62, 2.75, t) * (1 - ss(3.45, 3.62, t))
        if k > 0:
            sway += k * (hsh(i, hb2, 7) - 0.5) * 200
        if t > 2.45:
            sway += 70 * math.exp(-(t - 2.45) * 4)
        sway += 220 * ss(4.95, 5.3, t)
        tuft(cv, vn, gx, 1110, gh, t, sway, ("dark", "blue")[i % 2], i)

    # 吹散了天
    xs, _ = line_xs("吹散了天", "heavy", 205, 0.02)
    for i, c in enumerate("吹散了天"):
        sc, a = pop(t, (1.81, 2.02, 2.23, 2.44)[i])
        if a <= 0:
            continue
        px, py, rot = 760 + xs[i], 300, 0.0
        d = t - (2.60 + 0.035 * i)
        if d > 0:
            px += SAN_V[i][0] * d + 150 * d * d
            py += SAN_V[i][1] * d - 500 * d * d
            rot += SAN_R[i] * d
            a *= 1 - ss(0.3, 0.7, d)
        ch_at(cv, vm, "heavy", 205, c, px + 1800 * push, py, "blue", sc, rot, a)

    # 吹乱了地
    xs, _ = line_xs("吹乱了地", "heavy", 205, 0.02)
    hb = math.floor((t - PH) / (BEAT / 2))
    for i, c in enumerate("吹乱了地"):
        ti = (2.65, 2.86, 3.07, 3.28)[i]
        sc, a = pop(t, ti, amt=0.5)
        if a <= 0:
            continue
        k = ss(ti + 0.04, ti + 0.16, t)
        rot = k * (hsh(i, hb, 1) - 0.5) * 50
        px = 1180 + xs[i] + k * (hsh(i, hb, 2) - 0.5) * 50
        py = 720 + k * (hsh(i, hb, 3) - 0.5) * 90
        d = t - (3.52 + 0.05 * i)
        if d > 0:
            py += 2600 * d * d + 200 * d
            rot += (1 if i % 2 else -1) * 120 * d
        ch_at(cv, vm, "heavy", 205, c, px + 1800 * push, py, "red", sc, rot, a)

    # 吹远了 (recedes with echoes)
    xs, _ = line_xs("吹远了", "heavy", 250, 0.0)
    u = eio((t - 3.92) / 0.48)
    fade = 1 - ss(4.3, 4.6, t)
    for e in (2, 1, 0):
        ue = c01(u - 0.12 * e)
        if e and not (0 < u < 1 + 0.12 * e and ue < 1):
            continue
        Px, Py, s_ = lerp(960, 1500, ue), lerp(470, 330, ue), 1 - 0.9 * ue
        col, mode, aa = ("blue", "over", 1.0) if e == 0 else ("red", "print", 0.45)
        for i, c in enumerate("吹远了"):
            sc, a = pop(t, (3.50, 3.66, 3.82)[i])
            if a > 0:
                ch_at(cv, vm, "heavy", 250, c, Px + xs[i] * s_ + 1800 * push, Py, col, sc * s_, 0, a * aa * fade, mode)

    # 哦~哦 riding a wind line
    if t >= 4.0:
        head = eo((t - 4.0) / 0.5)
        xw = np.linspace(-150, -150 + 2400 * head, 120)
        yw = 870 + 44 * np.sin(0.0085 * xw - 5.5 * (t - 4.0))
        pline(cv, vm, np.stack([xw + 1800 * push, yw], 1), 12, "blue")
        for (c, ti, x0, sz) in (("哦", 4.00, 560, 180), ("~", 4.33, 760, 230), ("哦", 4.66, 960, 180)):
            sc, a = pop(t, ti, amt=0.5)
            if a <= 0:
                continue
            px = x0 + 150 * (t - ti)
            ph = 0.0085 * px - 5.5 * (t - 4.0)
            py = 870 + 44 * math.sin(ph) - 118
            rot = math.degrees(math.atan(44 * 0.0085 * math.cos(ph)))
            ch_at(cv, vm, "smiley", sz, c, px + 1800 * push, py, "red", sc, rot, a)

    # wind gust wipe → next scene
    if t > 4.9:
        for i in range(8):
            u = (t - 4.92 - 0.03 * i) / 0.5
            if u <= 0 or u >= 1.25:
                continue
            hx = -300 + 3100 * eio(u)
            xs_ = np.linspace(hx - 1300, hx, 60)
            ys_ = 90 + i * 128 + 26 * np.sin(xs_ * 0.005 + i * 1.3)
            pline(cv, V0, np.stack([xs_, ys_], 1), 30 + 16 * (i % 3), ("blue", "red", "dark")[i % 3])


# ------------------------------------------------------------------ 02  啊 / 有些话还没说出口  (desk, top-down)
SHEET = (240.0, 130.0, 1680.0, 950.0)
SHEET_C = ((SHEET[0] + SHEET[2]) / 2, (SHEET[1] + SHEET[3]) / 2)
GRID_X = [320 + 160 * k for k in range(9)]
GRID_Y = [220, 380, 540, 700, 860]
KF = 290.0  # size of the kite the sheet folds into


def cam2(t):
    z = lerp(40, 170, eio((t - 5.5) / 2.4)) - 430 * eio((t - 7.98) / 0.3)
    z += 90 * math.exp(-(t - 5.5) * 7)
    x = lerp(-110, 30, eio((t - 5.6) / 2.2))
    y = lerp(-10, 70, eio((t - 6.6) / 0.6))
    roll = lerp(-3.0, -1.2, c01((t - 5.5) / 2.9))
    return x, y, z, roll


def s2(cv, t, st, draw_kite=True):
    st["no"] = 2
    cv.fill("dark")
    x, y, z, roll = cam2(t)
    vm = cam(x, y, z, roll)
    sv = Sub(vm, SHEET_C[0], SHEET_C[1], -2.0)
    fu = eio((t - 8.0) / 0.28)

    # pen on the desk
    pline(cv, vm, [(1560, 1050), (1930, 915)], 30, "blue")
    pline(cv, vm, [(1830, 951), (1930, 915)], 32, "red")
    poly(cv, vm, [(1560, 1050), (1528, 1072), (1566, 1066)], "paper")

    # the sheet (own card so it can be folded)
    card = Canvas()
    x0, y0, x1, y1 = SHEET
    rect(card, sv, x0, y0, x1, y1, "paper")
    for gx in GRID_X:
        pline(card, sv, [(gx, GRID_Y[0]), (gx, GRID_Y[-1])], 3, "red")
    for gy in GRID_Y:
        pline(card, sv, [(GRID_X[0], gy), (GRID_X[-1], gy)], 3, "red")
    pline(card, sv, [(GRID_X[0] - 16, GRID_Y[0] - 16), (GRID_X[-1] + 16, GRID_Y[0] - 16), (GRID_X[-1] + 16, GRID_Y[-1] + 16),
                     (GRID_X[0] - 16, GRID_Y[-1] + 16)], 6, "red", closed=True)

    # 啊 — a red seal slammed onto the sheet
    sc, a = pop(t, 5.50, dur=0.12, amt=0.7)
    if t >= 5.50:
        a = 1.0
        buf = np.zeros((H, W), f32)
        ring(card, sv, 1330, 540, 205 * sc, 18 * sc, "red", a, buf=buf)
        ch_at(card, sv, "heavy", 260, "啊", 1330, 548, "red", sc, -9, a, buf=buf)
        card.paint(buf * np.clip(TEX[1] * 1.25 - 0.2, 0, 1), 0, 0, "red")

    # typed into the cells
    cur = None
    for row, (text, times) in enumerate((("有些话还", (5.70, 5.95, 6.20, 6.45)), ("没说出口", (6.70, 7.00, 7.30, 7.60)))):
        cy_ = (GRID_Y[1] + GRID_Y[2]) / 2 if row == 0 else (GRID_Y[2] + GRID_Y[3]) / 2
        for i, c in enumerate(text):
            cx_ = (GRID_X[i] + GRID_X[i + 1]) / 2
            if t >= times[i]:
                sc, a = pop(t, times[i], dur=0.1, amt=0.2)
                ch_at(card, sv, "heavy", 118, c, cx_, cy_, "blue", sc, 0, a)
                cur = (GRID_X[i + 1] + 80, cy_)
    if cur is not None and t < 7.72 and (t * 4) % 2 < 1.2:
        rect(card, sv, cur[0] - 6, cur[1] - 60, cur[0] + 6, cur[1] + 60, "blue")

    # 没说出口 gets redacted
    cy_ = (GRID_Y[2] + GRID_Y[3]) / 2
    for i in range(4):
        w_ = 150 * eo((t - (7.72 + 0.07 * i)) / 0.1)
        if w_ > 1:
            rect(card, sv, GRID_X[i] + 5, cy_ - 66, GRID_X[i] + 5 + w_, cy_ + 66, "dark")

    Q = sv.pts([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
    C = Q.mean(0) + (0, -80 * fu)
    if fu < 1:
        if fu > 0:
            dia = KITE[[0, 1, 2, 3]] * KF + C
            dst = Q * (1 - fu) + dia * fu
            M = cv2.getPerspectiveTransform(Q.astype(f32), dst.astype(f32))
            card = warp_canvas(card, M)
        cv.over(card)
    ka = ss(0.55, 1.0, fu)
    if draw_kite and ka > 0:
        kite(cv, V0, C[0], C[1], KF, 0, t, a=ka, tail=fu >= 1)
    return C


# ------------------------------------------------------------------ 03  就随着晚风 / 飘呀×3 / 飘到远方  (dusk sky)
def _hill(base, a1, f1, p1, a2, f2, p2):
    xs = np.arange(-2600, 4600, 40, dtype=np.float64)
    ys = base + a1 * np.sin(xs * f1 + p1) + a2 * np.sin(xs * f2 + p2)
    return np.concatenate([np.stack([xs, ys], 1), [(4600, 3000), (-2600, 3000)]])


HILL_F = _hill(862, 34, 0.0031, 0.4, 14, 0.011, 1.0)
HILL_M = _hill(915, 28, 0.0042, 2.0, 12, 0.013, 0.2)
HILL_N = _hill(985, 24, 0.0036, 4.1, 10, 0.017, 2.2)
_SKY = {}


def sky_masks():
    if not _SKY:
        yy = _gy
        _SKY["sky"] = halftone(0.62 * np.clip(1 - yy / 640, 0, 1), 16, 20)
        _SKY["dusk"] = halftone(0.5 * ssv(430, 900, yy), 16, 70)
    return _SKY["sky"], _SKY["dusk"]


CONF = [(float(_r.uniform(-400, 2000)), float(_r.uniform(120, 820)), float(_r.uniform(0, 6.28)), i) for i in range(16)]
BIRDS = [(1560, 300, 0.0), (1640, 340, 1.3), (1720, 290, 2.1), (1500, 360, 3.3), (1790, 330, 4.2)]
W03 = [(8.55, 1.1, wind_curl(90, 390, 700, 22, 56), 10, "paper"),
       (9.25, 1.1, wind_curl(760, 700, 600, 18, 44, down=True), 9, "blue"),
       (10.05, 1.1, wind_curl(260, 250, 820, 24, 60), 10, "paper"),
       (10.85, 1.1, wind_curl(900, 640, 700, 20, 50, down=True), 9, "blue"),
       (11.65, 1.1, wind_curl(150, 470, 760, 22, 56), 10, "paper")]
PIAO_P = [(700, 770), (950, 690), (1200, 610)]
YUAN = [(380, 690, 250), (660, 600, 192), (885, 528, 146), (1062, 472, 110)]


def cam3(t):
    x = 260 * eio((t - 8.6) / 3.8)
    y = -110 * eio((t - 10.3) / 2.0)
    z = -240 * eio((t - 10.4) / 2.0) + 70 * (1 - eo((t - 8.3) / 0.9))
    return x, y, z, 1.6 * math.sin(0.9 * t)


def kite3(t):
    if t < 10.5:
        kx, ky, ks = 1180 + 26 * math.sin(1.3 * t), 300 + 18 * math.sin(2.1 * t), 95
    else:
        v = eio((t - 10.5) / 1.9)
        kx, ky, ks = lerp(1180, 1620, v) + 20 * math.sin(1.3 * t), lerp(300, 160, v) + 12 * math.sin(2.1 * t), lerp(95, 50, v)
    taut = ss(12.15, 12.35, t)
    vib = 12 * taut * (math.exp(-(t - 12.35) * 3) if t > 12.35 else 1)
    return kx, ky, ks, -8 + 13 * math.sin(2.6 * t) + 6 * math.sin(4.1 * t), 0.14 * (1 - taut), vib


def s3(cv, t, st, draw_kite=True):
    st["no"] = 3
    cv.fill("paper")
    x, y, z, roll = cam3(t)
    vm = cam(x, y, z, roll)
    sky, dusk = sky_masks()
    cv.paint(sky, 0, 0, "blue", mode="print")
    disc(cv, cam(x, y, z, roll, 6000), 1480, 760, 170, "yellow")
    cv.paint(dusk, 0, 0, "red", mode="print")
    vfar = cam(x, y, z, roll, 2400)
    for (bx, by, ph) in BIRDS:
        bird(cv, vfar, bx + 30 * (t - 8.4), by + 8 * math.sin(t * 1.5 + ph), 16, t, ph)
    buf = np.zeros((H, W), f32)
    poly(cv, vfar, HILL_F, "blue", buf=buf)
    cv.paint(buf * HT(0.55, 12, 45), 0, 0, "blue")
    poly(cv, cam(x, y, z, roll, 1600), HILL_M, "blue")
    poly(cv, cam(x, y, z, roll, 1150), HILL_N, "dark")

    for (t0, dur, P, th, col) in W03:
        wind_anim(cv, vm, t, t0, dur, P, th, col)

    # confetti drifting on the wind (飘)
    for (cx_, cy_, ph, i) in CONF:
        if t < 9.2 + 0.05 * i:
            continue
        px = (cx_ + 260 * (t - 8.4)) % 2600 - 400
        py = cy_ + 40 * math.sin(t * 1.7 + ph)
        r_ = math.radians(t * 220 + ph * 57)
        c_, s_ = math.cos(r_) * 16, math.sin(r_) * 16
        poly(cv, vm, [(px - c_ + s_ * 0.6, py - s_ - c_ * 0.6), (px + c_ + s_ * 0.6, py + s_ - c_ * 0.6),
                      (px + c_ - s_ * 0.6, py + s_ + c_ * 0.6), (px - c_ - s_ * 0.6, py - s_ + c_ * 0.6)],
             ("red", "yellow", "blue", "paper")[i % 4])

    kx, ky, ks, kr, sag, vib = kite3(t)
    if draw_kite:
        kite(cv, vm, kx, ky, ks, kr, t, anchor=(-200, 1250), sag=sag, vib=vib)

    # 就随着晚风 on a wave
    xs, _ = line_xs("就随着晚风", "heavy", 125, 0.1)
    for i, c in enumerate("就随着晚风"):
        ti = 8.40 + 0.2 * i
        if t < ti:
            continue
        u = eo((t - ti) / 0.3)
        px = 540 + xs[i] - 160 * (1 - u)
        py = 520 + 34 * math.sin(0.9 * i - 4 * t)
        rot, a = 8 * math.sin(0.9 * i - 4 * t + 1.2), u
        d = t - (10.42 + 0.04 * i)
        if d > 0:
            px += 900 * d + 1400 * d * d
            py -= 250 * d + 300 * d * d
            rot += 60 * d
            a *= 1 - ss(0.25, 0.6, d)
        ch_at(cv, vm, "heavy", 125, c, px, py, "blue", 1.0, rot, a)

    # 飘呀 ×3
    for i, ti in enumerate((9.40, 9.77, 10.13)):
        if t < ti:
            continue
        sc, a = pop(t, ti, amt=0.4)
        u = eo((t - ti) / 0.4)
        px = PIAO_P[i][0] - 60 * (1 - u)
        py = PIAO_P[i][1] + 60 * (1 - u) + 16 * math.sin(5 * t + i * 1.9)
        rot = 8 * math.sin(3 * t + i)
        d = t - (10.46 + 0.05 * i)
        if d > 0:
            px += 900 * d + 1400 * d * d
            py -= 300 * d + 300 * d * d
            rot += 80 * d
            a *= 1 - ss(0.25, 0.6, d)
        xs, _ = line_xs("飘呀", "smiley", 115)
        for j, c in enumerate("飘呀"):
            ch_at(cv, vm, "smiley", 115, c, px + xs[j] + 7, py + 10 * j + 6, "blue", sc, rot, a)
            ch_at(cv, vm, "smiley", 115, c, px + xs[j], py + 10 * j, "paper", sc, rot, a)

    # 飘到远方 receding toward the kite
    for i, c in enumerate("飘到远方"):
        ti = (10.50, 10.78, 11.06, 11.34)[i]
        sc, a = pop(t, ti, amt=0.4)
        if a <= 0:
            continue
        px, py, sz = YUAN[i]
        k = min(1.0, 0.07 * (t - ti))
        px, py = lerp(px, kx, k), lerp(py, ky, k)
        ch_at(cv, vm, "heavy", sz, c, px, py, "dark", sc * (1 - 0.06 * (t - ti)), 0, a)
    return vm.pt(kx, ky) + (ks * vm.s, kr)


# ------------------------------------------------------------------ 04  我却成了 / 阶下囚
BAR_STY = [("blue", "paper", "red", "dark", "red"), ("red", "paper", "blue", "dark", "orange"),
           ("dark", "red", "blue", "paper", "blue"), ("paper", "blue", "red", "dark", "red")]


def s4a(cv, t, st):
    st["no"] = 4
    cv.fill("paper")
    z = 30 + 90 * eio((t - 12.6) / 1.2)
    vm = cam(0, 0, z, 0.8 * math.sin(1.1 * t))
    poly(cv, cam(0, 0, z, 0, 1300), _hill(925, 10, 0.004, 1.0, 5, 0.02, 0.0), "dark")
    for i in range(9):
        gx = -160 + i * 280 + 40 * hsh(i, 4)
        tuft(cv, cam(0, 0, z, 0, 800), gx, 1010, 80 + 50 * hsh(i, 9), t, 14 * math.sin(2 * t + i), "blue", i)
    # paper scraps from the sky scene, now falling
    for (cx_, cy_, ph, i) in CONF:
        d = t - 12.45 + 0.06 * i
        px = cx_ * 0.8 + 60 + 50 * math.sin(t * 1.9 + ph)
        py = -80 + (cy_ * 0.3) + 260 * d + 60 * d * d
        r_ = math.radians(t * 160 + ph * 57)
        c_, s_ = math.cos(r_) * 15, math.sin(r_) * 15
        poly(cv, vm, [(px - c_ + s_ * 0.6, py - s_ - c_ * 0.6), (px + c_ + s_ * 0.6, py + s_ - c_ * 0.6),
                      (px + c_ - s_ * 0.6, py + s_ + c_ * 0.6), (px - c_ - s_ * 0.6, py - s_ + c_ * 0.6)],
             ("red", "yellow", "blue", "dark")[i % 4])
    vib = 5 + 3 * math.sin(t * 2)
    kite_string(cv, vm, 962, -120, 960, 905, t, 0.0, vib, 3.5)
    rect(cv, vm, 947, 885, 973, 965, "dark")
    disc(cv, vm, 960, 900, 15, "red")
    for i, c in enumerate("我却成了"):
        sc, a = pop(t, (12.80, 13.05, 13.30, 13.55)[i])
        if a > 0:
            ch_at(cv, vm, "heavy", 120, c, (600, 760, 1160, 1320)[i], 600, "blue", sc, 0, a)
    # foreshadow of the cage
    for i in range(11):
        u = eo((t - 13.52 - 0.015 * abs(i - 5)) / 0.25)
        if u > 0:
            bx = 960 + (i - 5) * 162
            pline(cv, vm, [(bx, -20), (bx, -20 + 1120 * u)], 3, "blue", 0.55)


def s4b(cv, t, st):
    st["no"] = 4
    k = 0 if t < 14.21 else 1 + int((t - 14.21) / (2 * BEAT))
    bg, txt, shc, barc, bbc = BAR_STY[k % 4]
    cv.fill(bg)
    du = eio((t - 14.3) / 2.5)
    sb, sf = 1 - 0.3 * du, 1 + 0.24 * du
    ex = ei((t - 16.72) / 0.25)
    # back bars
    for i in range(15):
        bx = 960 + (i - 7) * 118 * sb
        u = eo((t - 13.84 - 0.015 * abs(i - 7)) / 0.2)
        rect(cv, V0, bx - 7, -60 + (H + 300) * ex, bx + 7, lerp(-60, H + 60, u) + (H + 300) * ex, bbc)
    # the kite, caught inside
    kx = 960 + 60 * math.sin(t * 2.3) + 30 * math.sin(t * 5.1)
    kite(cv, V0, kx, 190 + 12 * math.sin(t * 3.3), 58, 14 * math.sin(t * 4.2), t, anchor=(kx + 5, H + 40), sag=0.0, vib=4)
    # 阶下囚
    xs, _ = line_xs("阶下囚", "heavy", 380, 0.04)
    pulse = 1 + 0.045 * bpulse(t) * (t > 14.2)
    for i, c in enumerate("阶下囚"):
        sc, a = pop(t, 13.80 + 0.07 * i, dur=0.14, amt=0.6)
        if a <= 0:
            continue
        sc *= pulse * (1 - 0.95 * ex)
        jx = (hsh(i, beat_n(t), 11) - 0.5) * 10 if i == 2 else 0
        px, py = 960 + xs[i] * (1 - 0.95 * ex) + jx, 560
        ch_at(cv, V0, "heavy", 380, c, px + 16, py + 14, shc, sc, 0, a)
        ch_at(cv, V0, "heavy", 380, c, px, py, txt, sc, 0, a)
    # front bars + cross bars
    for i in range(11):
        bx = 960 + (i - 5) * 162 * sf
        u = eob((t - 13.80 - 0.018 * abs(i - 5)) / 0.17)
        rect(cv, V0, bx - 17, -100 - (H + 300) * ex, bx + 17, lerp(-100, H + 100, u) - (H + 300) * ex, barc)
    for j, yb in enumerate((110, 985)):
        u = eo((t - 13.9 - 0.05 * j) / 0.18)
        sgn = 1 if j == 0 else -1
        off = sgn * (1 - u) * 2200 + sgn * ex * 2400
        rect(cv, V0, 60 + off, yb - 14, W - 60 + off, yb + 14, barc)


# ------------------------------------------------------------------ 05  可能是我 / 不懂  (quiet, handwriting)
def s5(cv, t, st):
    st["no"] = 5
    cv.fill("paper")
    x, y = 20 * math.sin(1.3 * t), 12 * math.sin(1.7 * t)
    vm = cam(x, y, 60 + 60 * (t - 17.0) / 1.8, 1.2 * math.sin(0.9 * t))
    for i in range(-2, 14):
        pline(cv, vm, [(-200, 90 * i + 40), (2120, 90 * i + 40)], 2, "blue", 0.35)
    pline(cv, vm, [(250, -200), (250, 1300)], 3, "red", 0.7)
    xs, _ = line_xs("可能是我", "kai", 135, 0.02)
    for i, c in enumerate("可能是我"):
        ti = (17.00, 17.22, 17.44, 17.66)[i]
        ch_at(cv, vm, "kai", 135, c, 720 + xs[i], 520, "blue", wipe=(t - ti) / 0.2)
    xs, _ = line_xs("不懂", "kai", 200, 0.02)
    for i, c in enumerate("不懂"):
        ti = (18.00, 18.22)[i]
        ch_at(cv, vm, "kai", 200, c, 1360 + xs[i], 540, "red", wipe=(t - ti) / 0.22)
    u = (t - 18.30) / 0.32
    if u > 0:
        n = 160
        th = np.linspace(0, 2.35 * math.pi, n) - 2.4
        rr = 1 + 0.07 * np.sin(3 * th + 1) + 0.04 * np.sin(7 * th) + 0.05 * th / (2.35 * math.pi)
        P = np.stack([1360 + 265 * rr * np.cos(th), 540 + 150 * rr * np.sin(th)], 1)
        pline(cv, vm, P[:max(2, int(n * eo(u)))], 7, "red")
    ch_at(cv, vm, "kai", 130, "?", 1665, 360, "red", 1.0, 12, wipe=(t - 18.55) / 0.18)


# ------------------------------------------------------------------ 06  可是我们 / 没什么 / 不同  (split screen)
def s6(cv, t, st):
    st["no"] = 6
    sx = int(round(lerp(W, CX, eo((t - 18.80) / 0.25))))
    sw = (math.floor((t - 20.60) / (BEAT / 2)) + 1) % 2 if t >= 20.60 else 0
    lbg, rbg = ("blue", "paper") if not sw else ("paper", "blue")
    vm = cam(0, 0, 50 * (t - 18.8) / 2.6, 0)
    cv.fill(rbg)
    rect(cv, V0, -10, -10, sx, H + 10, lbg)
    # mirrored kites = 我们
    kr = 10 * math.sin(t * 2.7)
    ky = 150 + 12 * math.sin(t * 2.2)
    kite(cv, vm, 470, ky, 52, kr, t, anchor=(470, 1300), sag=0.0, sw=2)
    kite(cv, vm, W - 470, ky, 52, -kr, t, anchor=(W - 470, 1300), sag=0.0, sw=2, wind=-1)
    TB = np.zeros((H, W), f32)
    rows = (("可是我们", "heavy", 150, 330, (18.80, 19.05, 19.30, 19.55), 0.1),
            ("没什么", "heavy", 135, 540, (20.00, 20.20, 20.40), 0.1),
            ("不同", "heavy", 330, 800, (20.60, 20.60), 0.12))
    for (text, fk, sz, yy, times, tr) in rows:
        xs, _ = line_xs(text, fk, sz, tr)
        for i, c in enumerate(text):
            sc, a = pop(t, times[i], amt=0.7 if sz > 200 else 0.35)
            if a > 0:
                ch_at(cv, vm, fk, sz, c, CX + xs[i], yy, "blue", sc, 0, a, buf=TB)
    L_, R_ = np.zeros_like(TB), np.zeros_like(TB)
    L_[:, :sx] = TB[:, :sx]
    R_[:, sx:] = TB[:, sx:]
    cv.paint(L_, 0, 0, rbg)
    cv.paint(R_, 0, 0, lbg)
    if sx < W:
        pline(cv, V0, [(sx, -10), (sx, H + 10)], 5, "red")


# ------------------------------------------------------------------ 07  故事 / 走呀×4 / 走到了尽头  (tracking shot)
EDGE = 2930.0
STEP_X0, STEP_W, STEP_H, GROUND = 700.0, 330.0, 60.0, 860.0


def cam7(t):
    x = -60.0
    for ti in (21.84, 22.25, 22.67, 23.08):
        x += 185 * eio((t - ti) / 0.28)
    x += 530 * eio((t - 23.50) / 1.1)
    x += 1500 * ei((t - 24.80) / 0.2)
    ph = 0.0
    for ti in (21.84, 22.25, 22.67, 23.08):
        if 0 <= t - ti < 0.4:
            ph = math.sin(math.pi * (t - ti) / 0.4)
    return x, -14 * ph, 0.0, 1.4 * ph


def s7(cv, t, st):
    st["no"] = 7
    cv.fill("paper")
    x, y, z, roll = cam7(t)
    vf, vm, vn = cam(x, y, z, roll, 2400), cam(x, y, z, roll), cam(x, y, z, roll, 700)
    # far: telegraph poles & wires
    pline(cv, vf, [(-3000, 905), (6000, 905)], 3, "blue")
    for k in range(-6, 16):
        px = -400 + 520 * k
        pline(cv, vf, [(px, 330), (px, 905)], 5, "blue")
        pline(cv, vf, [(px - 38, 365), (px + 38, 365)], 4, "blue")
        for dx in (-30, 30):
            u = np.linspace(0, 1, 24)
            P = np.stack([px + dx + 520 * u, 368 + 46 * 4 * u * (1 - u)], 1)
            pline(cv, vf, P, 2, "blue")
    # mid: ground, steps, plateau
    pline(cv, vm, [(-800, GROUND), (EDGE, GROUND)], 8, "blue")
    for i in range(4):
        rect(cv, vm, STEP_X0 + i * STEP_W, GROUND - (i + 1) * STEP_H, STEP_X0 + (i + 1) * STEP_W, GROUND, "red")
    rect(cv, vm, STEP_X0 + 4 * STEP_W, GROUND - 4 * STEP_H, EDGE, GROUND, "red")
    # 故事 — chapter label
    u = eo((t - 21.42) / 0.14)
    if u > 0:
        rect(cv, vm, 150, 300, 150 + 380 * u, 500, "dark")
        xs, _ = line_xs("故事", "heavy", 175, 0.04)
        for i, c in enumerate("故事"):
            sc, a = pop(t, (21.42, 21.62)[i])
            ch_at(cv, vm, "heavy", 175, c, 340 + xs[i], 400, "paper", sc, 0, a)
    # 走呀 ×4, landing on each step
    for i, ti in enumerate((21.84, 22.25, 22.67, 23.08)):
        if t < ti:
            continue
        top = GROUND - (i + 1) * STEP_H
        cx_ = STEP_X0 + i * STEP_W + STEP_W / 2
        u = (t - ti) / 0.2
        dy = -240 * (1 - eob(u)) if u < 1 else 0
        sq = 1 + 0.18 * math.exp(-max(0, t - ti - 0.12) * 14) * (t > ti + 0.12)
        xs, _ = line_xs("走呀", "smiley", 120)
        for j, c in enumerate("走呀"):
            ch_at(cv, vm, "smiley", 120, c, cx_ + xs[j], top - 72 + dy, "blue", sq, -6)
        for j in range(2):
            disc(cv, vm, cx_ - 40 + 70 * j, top - 6 + 3 * j, 9, "dark", c01((t - ti - 0.15) / 0.05))
    # 走到了尽头 — marching to the edge of the paper
    top = GROUND - 4 * STEP_H
    for j, c in enumerate("走到了尽头"):
        ti = (23.50, 23.76, 24.02, 24.28, 24.54)[j]
        if t < ti:
            continue
        u = eo((t - ti) / 0.22)
        sc, a = pop(t, ti, amt=0.3)
        ch_at(cv, vm, "heavy", 150, c, 2160 + j * 160 - 200 * (1 - u), top - 92, "dark", sc, 0, a)
    # near: fast foreground tufts
    for i in range(-2, 22):
        gx = i * 300 + 90 * hsh(i, 2)
        tuft(cv, vn, gx, 1110, 110 + 70 * hsh(i, 5), t, 10 * math.sin(2 * t + i), "dark", i + 50)
    # the end of the paper
    ex_, _ = vm.pt(EDGE, 0)
    if ex_ < W:
        rect(cv, V0, ex_, -10, W + 10, H + 10, "dark")
        pline(cv, V0, [(ex_ - 4, -10), (ex_ - 4, H + 10)], 6, "blue", 0.6)


# ------------------------------------------------------------------ 08  还有个人 / 却不肯 / 放手 / 结尾
def s8a(cv, t, st):
    st["no"] = 8
    cv.fill("paper")
    z = 150 * ei((t - 25.0) / 2.0)
    ox = 520 * (1 - eo((t - 25.0) / 0.16))
    vm = cam(0, 0, z, 0, ox=ox)
    wind_anim(cv, vm, t, 25.1, 1.0, wind_curl(150, 300, 520, 18, 44), 8, "blue", 0.8)
    wind_anim(cv, vm, t, 25.9, 1.0, wind_curl(1350, 820, 420, 16, 38, down=True), 8, "red", 0.8)
    hand = person(cv, vm, 960, 1100, 1.2, t)
    vib = lerp(2, 18, ei((t - 25.0) / 2.0))
    kite_string(cv, vm, hand[0], hand[1], hand[0] + 40, -200, t, 0.0, vib, 3.5)
    disc(cv, vm, hand[0], hand[1], 20, "red")
    for i, c in enumerate("还有个人"):
        ti = (25.00, 25.25, 25.50, 25.75)[i]
        if t >= ti:
            u = (t - ti) / 0.2
            ch_at(cv, vm, "heavy", 118, c, 660, 250 + 140 * i - 70 * (1 - eob(u)), "blue", 1.0, 0, c01(u * 4))
    for i, c in enumerate("却不肯"):
        ti = (26.00, 26.33, 26.66)[i]
        if t >= ti:
            u = (t - ti) / 0.2
            ch_at(cv, vm, "heavy", 118, c, 1290, 330 + 140 * i - 70 * (1 - eob(u)), "red", 1.0, 0, c01(u * 4))


DROP_T = 27.0
LOOKS = [("red", "paper", "blue", 3.0), ("blue", "red", "paper", -4.0), ("paper", "dark", "red", 2.5),
         ("dark", "red", "blue", -5.0), ("yellow", "red", "blue", 4.0)]


def s8b(cv, t, st):
    st["no"] = 8
    j = min(4, int((t - DROP_T) / BEAT))
    tb = t - (DROP_T + j * BEAT)
    bg, txt, shc, roll = LOOKS[j]
    cv.fill(bg)
    punch = 1 + 0.16 * (1 - eo(tb / 0.14))
    v = View(punch, roll * (1 - 0.5 * eo(tb / 0.3)))
    if j == 0:
        buf = np.zeros((H, W), f32)
        for k in range(12):
            a0 = k * math.pi / 6 + t * 0.8
            poly(cv, v, [(CX, CY), (CX + 2000 * math.cos(a0), CY + 2000 * math.sin(a0)),
                         (CX + 2000 * math.cos(a0 + 0.26), CY + 2000 * math.sin(a0 + 0.26))], "orange", buf=buf)
        cv.paint(buf, 0, 0, "yellow", mode="print")
    elif j == 1:
        for r_ in range(6):
            yy = 20 + r_ * 210
            off = ((t - DROP_T) * 900 * (1 if r_ % 2 else -1)) % 560
            for q in range(-1, 8):
                for m_, c in enumerate("放手"):
                    ch_at(cv, V0, "heavy", 150, c, q * 560 + m_ * 170 + off - 280, yy, "dark")
    elif j == 2:
        buf = np.zeros((H, W), f32)
        disc(cv, v, CX, CY, 480, "red", buf=buf)
        cv.paint(buf * HT(0.5, 18, 45), 0, 0, "red")
        hand = person(cv, v, 300, 1150, 0.9, t)
        kite_string(cv, v, hand[0], hand[1], 1800, -100, t, 0.08, 20, 3)
    elif j == 3:
        pass
    else:
        for k in range(40):
            a0 = k * math.pi / 20 + 0.3 * hsh(k, 3)
            r0 = 380 + 160 * hsh(k, 1)
            pline(cv, v, [(CX + r0 * math.cos(a0), CY + r0 * math.sin(a0)),
                          (CX + 1400 * math.cos(a0), CY + 1400 * math.sin(a0))], 4, "dark")
    if j != 2:
        kite_string(cv, v, CX + 20, -100, CX - 20, H + 100, t, 0.0, 40 * math.exp(-tb * 4) + 8, 4, "dark")
    if j == 3:
        ch_at(cv, v, "heavy", 720, "放", 640 + 18, 420 + 14, shc)
        ch_at(cv, v, "heavy", 720, "放", 640, 420, txt)
        ch_at(cv, v, "heavy", 820, "手", 1330 + 18, 660 + 14, shc)
        ch_at(cv, v, "heavy", 820, "手", 1330, 660, "paper")
    else:
        xs, _ = line_xs("放手", "heavy", 560, 0.06)
        for i, c in enumerate("放手"):
            ch_at(cv, v, "heavy", 560, c, CX + xs[i] + 18, CY + 14, shc)
            ch_at(cv, v, "heavy", 560, c, CX + xs[i], CY, txt)


def s8c(cv, t, st):
    st["no"] = 8
    cv.fill("paper")
    z = lerp(70, 0, eo((t - 29.04) / 0.9))
    vm = cam(0, 0, z, 0)
    buf = np.zeros((H, W), f32)
    poly(cv, cam(0, 0, z, 0, 1800), _hill(930, 30, 0.003, 0.5, 12, 0.012, 1.0), "blue", buf=buf)
    cv.paint(buf * HT(0.5, 12, 45), 0, 0, "blue")
    poly(cv, vm, np.array([(-300, 960), (200, 930), (560, 950), (900, 1010), (1200, 1100), (1200, 1400), (-300, 1400)]), "dark")
    hand = person(cv, vm, 420, 950, 0.42, t)
    kx, ky = 1420 + 30 * math.sin(1.4 * t), 260 + 20 * math.sin(2.2 * t)
    kite(cv, vm, kx, ky, 72, -8 + 12 * math.sin(2.7 * t), t, anchor=hand, sag=0.1, vib=10 * math.exp(-(t - 29.04) * 3))
    wind_anim(cv, vm, t, 29.1, 1.0, wind_curl(700, 520, 520, 16, 40), 8, "blue")
    st["fade"] = 1 - ss(29.72, 30.0, t)


# ------------------------------------------------------------------ frame chrome
def ui(cv, t, st):
    a = ss(0.3, 0.8, t)
    if a <= 0:
        return

    def pick(x0, y0, x1, y1):
        return "paper" if cv.L[:3, y0:y1:3, x0:x1:3].max(0).mean() > 0.45 else "blue"

    m, l = 40, 46
    for (sx_, sy_) in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
        x0 = m if sx_ > 0 else W - m
        y0 = m if sy_ > 0 else H - m
        col = pick(min(x0, x0 + sx_ * l), min(y0, y0 + sy_ * l), max(x0, x0 + sx_ * l), max(y0, y0 + sy_ * l))
        pline(cv, V0, [(x0, y0 + sy_ * l), (x0, y0), (x0 + sx_ * l, y0)], 3, col, a)
    lab = "No.%02d" % st["no"]
    xs, tot = line_xs(lab, "smiley", 34)
    col = pick(m + 60, m, m + 60 + int(tot), m + 40)
    for i, c in enumerate(lab):
        ch_at(cv, V0, "smiley", 34, c, m + 64 + tot / 2 + xs[i], m + 18, col, a=a)
    lab = "vo. 诗岸"
    xs, tot = line_xs(lab, "smiley", 34)
    col = pick(W - m - 64 - int(tot), H - m - 40, W - m - 64, H - m)
    for i, c in enumerate(lab):
        ch_at(cv, V0, "smiley", 34, c, W - m - 64 - tot / 2 + xs[i], H - m - 18, col, a=a)


# ------------------------------------------------------------------ hits / finish
HITS = [(1.81, .25), (2.65, .3), (3.50, .25), (5.50, .8), (7.72, .15), (10.50, .25), (13.80, 1.2), (18.00, .15),
        (20.60, .9), (21.84, .15), (22.25, .15), (22.67, .15), (23.08, .15), (24.54, .7), (25.0, .3)] + \
       [(DROP_T + j * BEAT, 1.5 if j == 0 else .8) for j in range(5)]


def hit_env(t, k):
    v = 0.0
    for (ti, s) in HITS:
        if t >= ti:
            v += s * math.exp(-(t - ti) * k)
    return v


def shifted(a, dx, dy):
    if dx == 0 and dy == 0:
        return a
    out = np.zeros_like(a)
    ys = slice(max(dy, 0), H + min(dy, 0))
    ysrc = slice(max(-dy, 0), H + min(-dy, 0))
    xs = slice(max(dx, 0), W + min(dx, 0))
    xsrc = slice(max(-dx, 0), W + min(-dx, 0))
    out[ys, xs] = a[ysrc, xsrc]
    return out


def finish(cv, fidx, t, st):
    L = cv.L
    if st.get("blur"):
        bx, by = st["blur"]
        k = (max(1, int(bx)), max(1, int(by)))
        if k != (1, 1):
            for c in range(3):
                L[c] = cv2.blur(L[c], k)
    q = (fidx // 3) % 3
    mx, my = MAPS[q]
    b = cv2.remap(L[0], mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    r = cv2.remap(L[1], mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    y = cv2.remap(L[2], mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    sh = hit_env(t, 9.0)
    r = shifted(r, int(round(3 + 12 * min(sh, 1.6))), int(round(-2 + 7 * min(sh, 1.6))))
    fade = st.get("fade", 1.0)
    b *= TEX[q] * fade
    r *= TEX[(q + 1) % 3] * fade
    y *= TEX[(q + 2) % 3] * fade
    img = PAPER_IMG * (1 - b[..., None] * (1 - INK[0])) * (1 - r[..., None] * (1 - INK[1])) * (1 - y[..., None] * (1 - INK[2]))
    zoom = 1 + 0.035 * hit_env(t, 12.0)
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


# ------------------------------------------------------------------ timeline
def render(fidx):
    t = fidx / FPS
    st = {"no": 1}
    cv = Canvas()
    if t < 5.5:
        s01(cv, t, st)
    elif t < 8.26:
        s2(cv, t, st)
    elif t < 8.62:
        e = eio((t - 8.26) / 0.36)
        a, b = Canvas(), Canvas()
        C = s2(a, t, st, draw_kite=False)
        kx, ky, ks, kr = s3(b, t, st, draw_kite=False)
        cv.over(a, 0, H * e)
        cv.over(b, 0, -H * (1 - e))
        w = eo((t - 8.26) / 0.4)
        kite(cv, V0, lerp(C[0], kx, w), lerp(C[1], ky, w), lerp(KF, ks, w), lerp(0, kr, w), t, anchor=(-200, 1250), sag=0.14)
        st["blur"] = (1, 1 + 60 * math.sin(math.pi * c01((t - 8.26) / 0.36)))
    elif t < 12.45:
        s3(cv, t, st)
    elif t < 12.83:
        e = eio((t - 12.45) / 0.38)
        a, b = Canvas(), Canvas()
        s3(a, t, st)
        s4a(b, t, st)
        cv.over(a, 0, -H * e)
        cv.over(b, 0, H * (1 - e))
        st["blur"] = (1, 1 + 60 * math.sin(math.pi * e))
    elif t < 13.8:
        s4a(cv, t, st)
    elif t < 17.0:
        s4b(cv, t, st)
    elif t < 18.8:
        s5(cv, t, st)
    elif t < 21.02:
        s6(cv, t, st)
    elif t < 21.42:
        u = (t - 21.02) / 0.4
        src = Canvas()
        if u < 0.5:
            s6(src, t, st)
            th = 90 * eio(u * 2) * 0.999
        else:
            s7(src, t, st)
            th = -90 * (1 - eio(u * 2 - 1)) * 0.999
        cv.fill("dark")
        a_ = math.radians(th)
        Fp = 2600.0
        corners = np.array([(0, 0), (W, 0), (W, H), (0, H)], np.float64)
        dst = []
        for (px, py) in corners:
            dxp = px - CX
            zz = dxp * math.sin(a_)
            k = Fp / (Fp + zz) * 0.92
            dst.append((CX + dxp * math.cos(a_) * k, CY + (py - CY) * k))
        M = cv2.getPerspectiveTransform(corners.astype(f32), np.array(dst, f32))
        cv.over(warp_canvas(src, M))
    elif t < 25.0:
        s7(cv, t, st)
        if t > 24.8:
            st["blur"] = (1 + 120 * ei((t - 24.8) / 0.2), 1)
    elif t < DROP_T:
        s8a(cv, t, st)
        if t < 25.16:
            st["blur"] = (1 + 100 * (1 - eo((t - 25.0) / 0.16)), 1)
    elif t < DROP_T + 5 * BEAT:
        s8b(cv, t, st)
    else:
        s8c(cv, t, st)
    ui(cv, t, st)
    return finish(cv, fidx, t, st)


if __name__ == "__main__":
    cv2.setNumThreads(1)
    if sys.argv[1] == "stills":
        out = os.path.join(D, "stills")
        os.makedirs(out, exist_ok=True)
        for tt in sys.argv[2:]:
            fr = render(int(round(float(tt) * FPS)))
            Image.fromarray(fr).save(os.path.join(out, f"{float(tt):05.2f}.jpg"), quality=90)
            print("still", tt, flush=True)
    elif sys.argv[1] == "video":
        from multiprocessing import Pool
        import imageio_ffmpeg
        ff = imageio_ffmpeg.get_ffmpeg_exe()
        out = sys.argv[2]
        cmd = [ff, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
               "-i", AUDIO, "-t", str(DUR), "-map", "0:v", "-map", "1:a", "-af", "afade=t=out:st=29.0:d=1.0",
               "-c:v", "libx264", "-preset", "slow", "-crf", "22", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
               "-c:a", "aac", "-b:a", "320k", out]
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        frames = range(NF) if len(sys.argv) < 4 else range(int(float(sys.argv[3]) * FPS), int(float(sys.argv[4]) * FPS))
        with Pool(4) as pool:
            for i, fr in enumerate(pool.imap(render, frames, chunksize=2)):
                p.stdin.write(fr.tobytes())
                if i % 60 == 0:
                    print("frame", i, flush=True)
        p.stdin.close()
        p.wait()
        print("done", out)
