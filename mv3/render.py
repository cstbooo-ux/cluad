#!/usr/bin/env python3
"""《我不知道》PV —— 孔版印刷纸面风格，问号小人当主角。

52 s / 1920x1080 / 30 fps，歌词时间来自 lyrics.srt。
用法：
  python3 render.py stills 5.0 12.3 ...   # 静帧到 stills/
  python3 render.py video out.mp4         # 成片（音频来自 $MV_AUDIO）
"""
import math
import os
import re
import subprocess
import sys

import cv2
import numpy as np
from PIL import Image

from engine import (BEAT, CX, CY, FPS, H, HT, PH, TEX, V0, W, Canvas, Sub, View, beat_n, beat_u, bird, bmax, bpulse, c01,
                    cam, card_flip, ch_at, disc, ei, eio, ell, eo, eob, f32, finish, halftone, hsh, lerp, line_xs, over_masked,
                    pline, poly, pop, rect, ring, slide, ss, ssv, sub_path, ui, warp_canvas, wind_anim, wind_curl, _gx, _gy)

D = os.path.dirname(os.path.abspath(__file__))
AUDIO = os.environ.get("MV_AUDIO", "/root/.claude/uploads/e5f3b459-77d3-5ac0-ba91-983fc9f5c975/71d3e341-_____.wav")
DUR = 51.85
NF = int(DUR * FPS)
CREDIT = "vo. 洛天依"


# ------------------------------------------------------------------ lyrics
def _srt(path):
    out = []
    for blk in re.split(r"\n\s*\n", open(path, encoding="utf-8-sig").read().strip()):
        ln = blk.strip().splitlines()
        m = re.match(r"(\d+):(\d+):(\d+)[,.](\d+)\s*-->\s*(\d+):(\d+):(\d+)[,.](\d+)", ln[1])
        g = [int(x) for x in m.groups()]
        out.append((g[0] * 3600 + g[1] * 60 + g[2] + g[3] / 1000, g[4] * 3600 + g[5] * 60 + g[6] + g[7] / 1000, "".join(ln[2:]).strip()))
    return out


LY = _srt(os.path.join(D, "lyrics.srt"))


def syl(i):
    """per-character onset times of lyric line i (spaces = short pauses). Returns (text_without_spaces, times)."""
    a, b, text = LY[i]
    units = sum(1.6 if c == " " else 1.0 for c in text)
    d = min(0.29, (b - a) * 0.8 / max(units - 1, 1))
    chars, times, u = [], [], 0.0
    for c in text:
        if c == " ":
            u += 1.6
            continue
        chars.append(c)
        times.append(a + u * d)
        u += 1.0
    return "".join(chars), times


def part(i, k):
    """k-th space-separated phrase of line i with its char times."""
    text, times = syl(i)
    words = LY[i][2].split(" ")
    o = sum(len(w) for w in words[:k])
    return words[k], times[o:o + len(words[k])]


def word(cv, v, text, times, cx, cy, fk, size, col, t, track=0.04, amt=0.4, drop=0.0, shadow=None, sh=0.05,
         rot=0.0, a=1.0, wipe=None, jitter=0.0, buf=None):
    xs, _ = line_xs(text, fk, size, track)
    for i, c in enumerate(text):
        if t < times[i]:
            continue
        sc, al = pop(t, times[i], amt=amt)
        dy = -drop * (1 - eob((t - times[i]) / 0.24)) if drop else 0.0
        jx = jy = 0.0
        if jitter:
            n = beat_n(t)
            jx, jy = (hsh(i, n, 1) - 0.5) * jitter, (hsh(i, n, 2) - 0.5) * jitter
        w_ = None if wipe is None else (t - times[i]) / wipe
        if shadow:
            ch_at(cv, v, fk, size, c, cx + xs[i] + size * sh + jx, cy + dy + size * sh + jy, shadow, sc, rot, al * a, wipe=w_)
        ch_at(cv, v, fk, size, c, cx + xs[i] + jx, cy + dy + jy, col, sc, rot, al * a, wipe=w_, buf=buf)


# ------------------------------------------------------------------ the question-mark mascot
def mascot(cv, v, x, y, s, t, col="pink", rot=0.0, sx=1.0, sy=1.0, eyes="open", arms=0.0, mouth=None, flip=1.0,
           a=1.0, ph=0.0, blush=True):
    """(x, y) = head centre, s ≈ total height. The dot of the '?' is the head, the curl is a cowlick."""
    cr, sr = math.cos(math.radians(rot)), math.sin(math.radians(rot))

    def T(P):
        P = np.asarray(P, np.float64) * s
        px = P[:, 0] * sx * flip
        py = (P[:, 1] - 0.22 * s) * sy + 0.22 * s
        return np.stack([x + cr * px - sr * py, y + sr * px + cr * py], 1)

    sw = 0.09 * math.sin(t * 3.3 + ph)
    th = np.linspace(math.pi + 0.35, 2 * math.pi + 0.75, 28)
    arc = np.stack([0.22 * np.cos(th) + sw * (np.sin(th) + 1), -0.62 + 0.22 * np.sin(th)], 1)
    hook = np.vstack([arc, [(0.03, -0.31)]])
    pline(cv, v, T(hook), 0.12 * s, col, a)
    if arms:
        for sgn in (-1, 1):
            P = T([(0.2 * sgn, 0.04), (0.36 * sgn, 0.04 - 0.2 * arms), (0.42 * sgn, -0.02 - 0.3 * arms)])
            pline(cv, v, P, 0.06 * s, col, a)
    poly(cv, v, T(ell(0, 0, 0.25, 0.23, 44)), col, a)
    if blush:
        for sgn in (-1, 1):
            poly(cv, v, T(ell(0.15 * sgn, 0.07, 0.05, 0.03, 16)), "yellow", a * 0.9, mode="print")
    blink = ((t + ph) % 3.1) < 0.12
    for sgn in (-1, 1):
        ex, ey = 0.085 * sgn, -0.02
        if eyes == "closed" or (eyes == "open" and blink):
            pline(cv, v, T([(ex - 0.04, ey), (ex - 0.015, ey + 0.025), (ex + 0.015, ey + 0.025), (ex + 0.04, ey)]), 0.025 * s, "dark", a)
        elif eyes == "tired":
            poly(cv, v, T(ell(ex, ey + 0.012, 0.035, 0.022, 16)), "dark", a)
            pline(cv, v, T([(ex - 0.05, ey - 0.008), (ex + 0.05, ey - 0.008)]), 0.02 * s, "dark", a)
        elif eyes == "dizzy":
            pline(cv, v, T([(ex - 0.03, ey - 0.03), (ex + 0.03, ey + 0.03)]), 0.022 * s, "dark", a)
            pline(cv, v, T([(ex - 0.03, ey + 0.03), (ex + 0.03, ey - 0.03)]), 0.022 * s, "dark", a)
        else:
            poly(cv, v, T(ell(ex, ey, 0.034, 0.052, 18)), "dark", a)
            poly(cv, v, T(ell(ex + 0.012, ey - 0.02, 0.011, 0.014, 10)), "paper", a)
    if mouth == "o":
        poly(cv, v, T(ell(0, 0.1, 0.035, 0.045, 16)), "dark", a)
    elif mouth == "smile":
        pline(cv, v, T([(-0.04, 0.08), (0, 0.11), (0.04, 0.08)]), 0.022 * s, "dark", a)
    elif mouth == "flat":
        pline(cv, v, T([(-0.035, 0.1), (0.035, 0.1)]), 0.022 * s, "dark", a)


def mascot_buf(buf, v, x, y, s, t, ph=0.0, arms=0.0, sy=1.0, rot=0.0):
    """Silhouette only, into a mask buffer (for crowds)."""
    cr, sr = math.cos(math.radians(rot)), math.sin(math.radians(rot))

    def T(P):
        P = np.asarray(P, np.float64) * s
        py = (P[:, 1] - 0.22 * s) * sy + 0.22 * s
        return np.stack([x + cr * P[:, 0] - sr * py, y + sr * P[:, 0] + cr * py], 1)

    sw = 0.09 * math.sin(t * 3.3 + ph)
    th = np.linspace(math.pi + 0.35, 2 * math.pi + 0.75, 16)
    arc = np.stack([0.22 * np.cos(th) + sw * (np.sin(th) + 1), -0.62 + 0.22 * np.sin(th)], 1)
    pline(None, v, T(np.vstack([arc, [(0.03, -0.31)]])), 0.12 * s, "pink", buf=buf)
    poly(None, v, T(ell(0, 0, 0.25, 0.23, 20)), "pink", buf=buf)
    if arms:
        for sgn in (-1, 1):
            pline(None, v, T([(0.2 * sgn, 0.04), (0.36 * sgn, 0.04 - 0.2 * arms), (0.42 * sgn, -0.02 - 0.3 * arms)]), 0.06 * s, "pink", buf=buf)


def heart(cx, cy, s, n=80):
    th = np.linspace(0, 2 * math.pi, n)
    x = 16 * np.sin(th) ** 3
    y = -(13 * np.cos(th) - 5 * np.cos(2 * th) - 2 * np.cos(3 * th) - np.cos(4 * th))
    return np.stack([cx + x * s / 32, cy + y * s / 32], 1)


def rrect(x0, y0, x1, y1, r, n=8):
    P = []
    for (cx_, cy_, a0) in ((x1 - r, y0 + r, -math.pi / 2), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, math.pi / 2), (x0 + r, y0 + r, math.pi)):
        for k in range(n + 1):
            a = a0 + k * (math.pi / 2) / n
            P.append((cx_ + r * math.cos(a), cy_ + r * math.sin(a)))
    return np.array(P)


def print_lines(cv, v, x0, y0, x1, rows, gap, col="teal", a=1.0, seed=0, th=10):
    for r_ in range(rows):
        y = y0 + r_ * gap
        x = x0
        k = 0
        while x < x1 - 30:
            w = 40 + 120 * hsh(seed, r_, k)
            w = min(w, x1 - x)
            pline(cv, v, [(x, y), (x + w, y)], th, col, a)
            x += w + 16
            k += 1


def beat_t(k):
    return PH + k * BEAT


def hb(t):
    """time since the most recent beat."""
    return beat_u(t) * BEAT


# ================================================================== scenes
# ------------------------------------------------------------------ 00 intro: textbook, a ? is doodled and comes alive
def s_intro(cv, t, st):
    st["no"] = 0
    cv.fill("teal")
    z = lerp(-160, 60, eio(t / 4.2))
    vm = cam(0, 0, z, lerp(-4, -1, t / 4.2))
    # book
    poly(cv, vm, rrect(150, 40, 1770, 1040, 26), "dark")
    rect(cv, vm, 180, 60, 955, 1020, "paper")
    rect(cv, vm, 965, 60, 1740, 1020, "paper")
    pline(cv, vm, [(960, 60), (960, 1020)], 6, "dark", 0.5)
    buf = np.zeros((H, W), f32)
    rect(cv, vm, 250, 140, 880, 470, "pink", buf=buf)
    cv.paint(buf * HT(0.35, 12, 30), 0, 0, "pink")
    ring(cv, vm, 560, 300, 90, 8, "teal")
    print_lines(cv, vm, 250, 540, 880, 9, 52, "dark", 0.75, seed=1)
    print_lines(cv, vm, 1040, 150, 1670, 5, 52, "dark", 0.75, seed=2)
    print_lines(cv, vm, 1040, 760, 1670, 4, 52, "dark", 0.75, seed=3)
    ch_at(cv, vm, "smiley", 40, "4", 230, 990, "dark", a=0.8)
    ch_at(cv, vm, "smiley", 40, "5", 1690, 990, "dark", a=0.8)
    # the doodle
    MX, MY, MS = 1360, 560, 300
    u = c01((t - 0.8) / 1.5)
    alive = ss(2.45, 2.6, t)
    if u > 0 and alive < 1:
        th = np.linspace(math.pi + 0.35, 2 * math.pi + 0.75, 40)
        hook = np.vstack([np.stack([0.22 * np.cos(th), -0.62 + 0.22 * np.sin(th)], 1), [(0.03, -0.31)]])
        circ = ell(0, 0, 0.25, 0.23, 40)
        path = np.vstack([hook, circ]) * MS + (MX, MY)
        sp = sub_path(path, 0, u)
        pline(cv, vm, sp, 6, "dark", 1 - alive)
        tip = sp[-1]
        # pencil
        if u < 1:
            ang = 0.6
            d = np.array([math.cos(ang), -math.sin(ang)])
            P0 = tip
            P1 = tip + d * 40
            P2 = tip + d * 420
            n = np.array([-d[1], d[0]]) * 24
            poly(cv, vm, [P0, P1 + n, P1 - n], "paper")
            poly(cv, vm, [P0, P0 + d * 14 + n * 0.35, P0 + d * 14 - n * 0.35], "dark")
            poly(cv, vm, [P1 + n, P2 + n, P2 - n, P1 - n], "yellow")
            poly(cv, vm, [P2 + n, P2 + d * 60 + n, P2 + d * 60 - n, P2 - n], "pink")
    if alive > 0:
        hop = 0.0
        for k in (6, 7):
            dt = t - beat_t(k)
            if 0 <= dt < 0.45:
                hop = max(hop, 4 * dt / 0.45 * (1 - dt / 0.45))
        sq = 1 + 0.25 * math.exp(-max(0, t - 2.45) * 9)
        mascot(cv, vm, MX, MY - 160 * hop, MS * (1 + 0.15 * (1 - eob((t - 2.45) / 0.3))), t, sx=sq, sy=1 / sq, a=alive,
               eyes="closed" if t < 2.9 else "open", mouth="smile" if t > 3.2 else None)


# ------------------------------------------------------------------ 01 老师又在问 答案多少 (blackboard)
def s_board(cv, t, st):
    st["no"] = 1
    cv.fill("yellow")
    x = 60 * eio((t - 4.3) / 2.4)
    vm = cam(x, 0, 40 + 60 * (t - 4.3) / 2.4, 0)
    vn = cam(x, 0, 40 + 60 * (t - 4.3) / 2.4, 0, 700)
    buf = np.zeros((H, W), f32)
    rect(cv, vm, -400, -200, 2400, 1400, "yellow", buf=buf)
    cv.paint(buf * HT(0.3, 14, 45), 0, 0, "orange", mode="print")
    rect(cv, vm, 170, 90, 1750, 820, "orange")
    rect(cv, vm, 200, 120, 1720, 790, "green")
    rect(cv, vm, 150, 820, 1770, 850, "dark")
    # chalk
    text, times = part(0, 0)
    word(cv, vm, text, times, 560, 260, "kai", 120, "paper", t, wipe=0.18)
    text, times = part(0, 1)
    word(cv, vm, text, times, 900, 520, "kai", 190, "paper", t, wipe=0.2)
    if t > times[-1] + 0.2:
        ch_at(cv, vm, "kai", 220, "?", 1440, 520, "yellow", 1.0, 10, wipe=(t - times[-1] - 0.2) / 0.2)
    ur = eo((t - 5.95) / 0.25)
    if ur > 0:
        P = ell(900, 520, 430 * 1.0, 150, 90, -2.2, -2.2 + 2.25 * math.pi * ur)
        pline(cv, vm, P, 9, "pink")
    # pointer from the off-screen teacher, tapping on beats
    tap = math.exp(-hb(t) * 10)
    tx, ty = 1180 + 60 * math.sin(t * 1.3), 600 - 40 * tap
    pline(cv, vm, [(2100, 1150), (tx, ty)], 16, "orange")
    disc(cv, vm, tx, ty, 10, "dark")
    # mascot in the foreground, sweating
    mascot(cv, vn, 1500, 960, 330, t, rot=-8 + 6 * math.sin(t * 2), eyes="open", mouth="flat")
    if t > 5.9:
        u = c01((t - 5.9) / 0.6)
        poly(cv, vn, ell(1640, 800 + 70 * u, 14, 22, 20), "teal", 1 - u * 0.5)


# ------------------------------------------------------------------ 02 我只看见 窗外飞鸟 (window, the characters fly away like birds)
CLOUD2 = [(520, 320, 60), (590, 300, 75), (670, 325, 55), (1250, 260, 50), (1310, 240, 66), (1380, 262, 48)]


def s_window(cv, t, st):
    st["no"] = 2
    cv.fill("pink")
    x = 80 * eio((t - 6.7) / 2.1)
    vm = cam(x, 0, 30, 0)
    vf = cam(x, 0, 30, 0, 3000)
    vn = cam(x, 0, 30, 0, 700)
    buf = np.zeros((H, W), f32)
    rect(cv, vm, -400, -200, 2400, 1400, "pink", buf=buf)
    for k in range(-6, 30):
        pline(cv, vm, [(k * 90, -200), (k * 90, 1400)], 26, "pink", buf=buf)
    cv.paint(buf * HT(0.25, 12, 0), 0, 0, "orange", mode="print")
    # window opening
    sky = Canvas()
    sky.fill("paper")
    sb = np.zeros((H, W), f32)
    rect(sky, V0, 0, 0, W, H, "teal", buf=sb)
    sky.paint(sb * halftone(0.65 * np.clip(1 - _gy / 900, 0.15, 1), 16, 20), 0, 0, "teal")
    for (cx_, cy_, r) in CLOUD2:
        disc(sky, vf, cx_ + 40 * (t - 6.7), cy_, r, "paper")
    for i, (bx, by) in enumerate(((300, 420), (420, 380), (1500, 300))):
        bird(sky, vf, bx + 260 * (t - 6.7), by + 10 * math.sin(t * 2 + i), 22, t, i * 1.7)
    # 窗外飞鸟: each character flies off with little wings
    text, times = part(1, 1)
    for i, c in enumerate(text):
        dt = t - times[i]
        if dt < 0:
            continue
        px = 470 + i * 250 + 260 * dt + 80 * dt * dt
        py = 560 - 150 * dt - (i % 2) * 70 + 30 * math.sin(dt * 7 + i)
        sc, al = pop(t, times[i], amt=0.5)
        f = math.sin(t * 18 + i)
        for sgn in (-1, 1):
            poly(sky, vm, [(px + 30 * sgn, py - 20), (px + 120 * sgn, py - 70 - 50 * f), (px + 70 * sgn, py + 5)], "paper", al)
        ch_at(sky, vm, "heavy", 150, c, px, py, "dark", sc, 8 * math.sin(dt * 6 + i), al)
    win = np.zeros((H, W), f32)
    rect(None, vm, 360, 130, 1560, 760, "paper", buf=win)
    over_masked(cv, sky, win)
    pline(cv, vm, [(360, 130), (1560, 130), (1560, 760), (360, 760)], 34, "dark", closed=True)
    pline(cv, vm, [(960, 130), (960, 760)], 22, "dark")
    pline(cv, vm, [(360, 445), (1560, 445)], 22, "dark")
    rect(cv, vm, 300, 760, 1620, 820, "paper")
    rect(cv, vm, 300, 812, 1620, 828, "dark")
    # 我只看见 on the wall
    text, times = part(1, 0)
    word(cv, vm, text, times, 960, 930, "heavy", 120, "dark", t, track=0.12, shadow="paper", sh=0.06)
    # mascot on the sill, head following the birds
    look = 1.0 if t < 7.6 else -1.0
    mascot(cv, vn, 1450, 625, 260, t, flip=-look, rot=10 * math.sin(t * 2.5), eyes="open", mouth="o" if t > 7.9 else None)


# ------------------------------------------------------------------ 03 你问啥我也不知道 (exam sheet)
def s_exam(cv, t, st, line=2, no=3):
    st["no"] = no
    cv.fill("teal")
    z = 30 + 70 * eio((t - LY[line][0]) / 1.7)
    vm = cam(-40, 0, z, -2.5)
    sv = Sub(vm, 960, 540, 1.5)
    rect(cv, sv, 260, 60, 1660, 1060, "paper")
    rect(cv, sv, 260, 60, 1660, 150, "pink")
    for q in range(4):
        y = 300 + q * 190
        ch_at(cv, sv, "smiley", 56, f"{q + 1}.", 340, y - 40, "dark")
        pline(cv, sv, [(420, y), (1200, y)], 4, "dark", 0.7)
        rect(cv, sv, 1280, y - 80, 1460, y + 20, "dark", 0.25)
    text, times = syl(line)
    xs, _ = line_xs(text, "heavy", 140, 0.02)
    for i, c in enumerate(text):
        if t < times[i]:
            continue
        sc, al = pop(t, times[i], amt=0.5)
        dy = -160 * (1 - eob((t - times[i]) / 0.24))
        big = c in "不知道"
        col = "pink" if big else "dark"
        ch_at(cv, sv, "heavy", 170 if big else 140, c, 940 + xs[i] * (1.05 if big else 1), 560 + dy, "dark" if big else "paper",
              sc, 0, al * (1 if big else 0))
        ch_at(cv, sv, "heavy", 170 if big else 140, c, 940 + xs[i] * (1.05 if big else 1) - 6, 554 + dy, col, sc, 0, al)
    # ?-marks scribbled into the answer boxes on beats
    for q in range(4):
        tb = beat_t(beat_n(LY[line][0]) + 1 + q)
        if t >= tb:
            ch_at(cv, sv, "heavy", 90, "?", 1370, 250 + q * 190, "pink", pop(t, tb, amt=0.6)[0], 12)
    k = 0
    for i, ti in enumerate(times):
        if t >= ti:
            k = i
    mascot(cv, vm, 1640, 860, 280, t, rot=(-14 if k % 2 else 14) * (1 if t > times[0] else 0), eyes="open", mouth="o")


# ------------------------------------------------------------------ 04 碳酸饮料也要喝到饱 (soda bubbles)
_r = np.random.default_rng(7)
FIZZ = [(float(_r.uniform(-500, 500)), float(_r.uniform(0, 1)), float(_r.uniform(8, 30)), i) for i in range(70)]


def can(cv, v, x, y, s, t, col="teal"):
    w, h = 0.36 * s, 0.62 * s
    poly(cv, v, rrect(x - w, y - h, x + w, y + h, 0.08 * s), col)
    rect(cv, v, x - w, y - 0.12 * s, x + w, y + 0.2 * s, "pink")
    ch_at(cv, v, "heavy", 0.3 * s, "?", x, y + 0.04 * s, "paper", 1.0, -8)
    poly(cv, v, ell(x, y - h, w, 0.07 * s, 40), "paper")
    pline(cv, v, ell(x, y - h, w, 0.07 * s, 40), 4, "dark", closed=True)
    disc(cv, v, x + 0.1 * s, y - h, 0.05 * s, "dark")


def s_soda(cv, t, st):
    st["no"] = 4
    a0 = LY[3][0]
    cv.fill("yellow")
    vm = cam(0, -60 * eio((t - a0) / 2.0), 40, 2 * math.sin(t * 1.5))
    buf = np.zeros((H, W), f32)
    for k in range(14):
        a = k * math.pi / 7 + t * 0.4
        poly(None, vm, [(960, 900), (960 + 2600 * math.cos(a), 900 + 2600 * math.sin(a)),
                        (960 + 2600 * math.cos(a + 0.22), 900 + 2600 * math.sin(a + 0.22))], "pink", buf=buf)
    cv.paint(buf, 0, 0, "orange", 0.6, mode="print")
    pt = t - a0
    can(cv, vm, 960, 900 + 30 * math.exp(-max(pt, 0) * 8) * (pt > 0), 520, t)
    if 0 <= pt < 0.5:
        for k in range(12):
            a = -math.pi / 2 + (k - 5.5) * 0.17
            r0, r1 = 40 + 400 * pt, 120 + 700 * pt
            pline(cv, vm, [(960 + r0 * math.cos(a), 578 + r0 * math.sin(a)), (960 + r1 * math.cos(a), 578 + r1 * math.sin(a))], 10, "dark", 1 - pt * 2)
    # fizz
    for (dx, ph, r, i) in FIZZ:
        if pt < 0:
            break
        yy = 560 - ((pt * 420 + ph * 1400) % 1400)
        ring(cv, vm, 960 + dx * min(1, pt * 3) + 18 * math.sin(t * 4 + i), yy, r, 4, "paper")
    # characters in bubbles
    text, times = syl(3)
    for i, c in enumerate(text):
        dt = t - times[i]
        if dt < 0:
            continue
        big = c in "喝到饱"
        r = 115 if big else 88
        bx = 960 + (-1) ** i * (140 + 90 * (i % 3)) + 40 * math.sin(dt * 3 + i)
        by = 560 - 420 * dt - 30 * dt * dt + (200 if big else 0) * (1 - eo(dt / 0.4))
        sc, al = pop(t, times[i], amt=0.6)
        disc(cv, vm, bx, by, r * sc, "paper")
        ring(cv, vm, bx, by, r * sc, 7, "teal")
        pline(cv, vm, ell(bx, by, r * 0.7 * sc, r * 0.7 * sc, 12, -2.6, -1.8), 8, "teal", 0.7)
        ch_at(cv, vm, "heavy", 112 if big else 92, c, bx, by + 4, "pink" if big else "dark", sc)
    # bubbles swallow the screen → next scene
    u = (t - 12.45) / 0.4
    if u > 0:
        for k in range(9):
            ang = k * 2.4
            disc(cv, V0, 960 + 700 * math.cos(ang) * (k / 9), 540 + 420 * math.sin(ang) * (k / 9), 1400 * eio(u - k * 0.04), "paper")
            ring(cv, V0, 960 + 700 * math.cos(ang) * (k / 9), 540 + 420 * math.sin(ang) * (k / 9), 1400 * eio(u - k * 0.04), 10, "teal")


# ------------------------------------------------------------------ 05 爸妈又在问 以后咋搞 (speech bubbles squeeze the mascot)
def bubble(cv, v, cx, cy, w, h, tx, ty, col, tail=1.0):
    P = rrect(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2, min(w, h) * 0.45)
    poly(cv, v, P, col)
    if tail > 0:
        ex, ey = lerp(cx, tx, tail), lerp(cy + h / 2, ty, tail)
        poly(cv, v, [(cx - 60, cy + h / 2 - 20), (cx + 60, cy + h / 2 - 20), (ex, ey)], col)


def s_parents(cv, t, st):
    st["no"] = 5
    a0 = LY[4][0]
    cv.fill("paper")
    z = 120 * eio((t - a0) / 2.4) + 600 * ei((t - 15.05) / 0.22)
    vm = cam(0, 0, z, 0)
    buf = np.zeros((H, W), f32)
    for k in range(-8, 30):
        rect(None, vm, k * 120, -300, k * 120 + 60, 1400, "pink", buf=buf)
    cv.paint(buf * HT(0.35, 12, 45), 0, 0, "pink")
    rect(cv, vm, -400, 960, 2400, 1400, "teal")
    squeeze = eio((t - 13.4) / 1.4)
    text, times = part(4, 0)
    ul = eob((t - times[0] + 0.15) / 0.3)
    if ul > 0:
        g = 1 + 0.25 * squeeze + 0.04 * bpulse(t)
        bubble(cv, vm, lerp(-500, 470, ul) + 80 * squeeze, 330, 760 * g, 300 * g, 860, 640, "teal", c01(ul - 0.6) * 2.5)
        word(cv, vm, text, times, lerp(-500, 470, ul) + 80 * squeeze, 330, "heavy", 110 * g, "paper", t)
    text, times = part(4, 1)
    ur = eob((t - times[0] + 0.15) / 0.3)
    if ur > 0:
        g = 1 + 0.25 * squeeze + 0.04 * bpulse(t)
        bubble(cv, vm, lerp(2400, 1450, ur) - 80 * squeeze, 400, 680 * g, 300 * g, 1060, 660, "dark", c01(ur - 0.6) * 2.5)
        word(cv, vm, text, times, lerp(2400, 1450, ur) - 80 * squeeze, 400, "heavy", 110 * g, "yellow", t)
    sq = 1 + 0.3 * squeeze * (1 + 0.15 * math.sin(t * 20))
    mascot(cv, vm, 960, 820, 300, t, sx=1 / sq, sy=sq * 0.95, eyes="dizzy" if squeeze > 0.6 else "open", mouth="o")
    if t > 14.9:
        poly(cv, vm, rrect(1040, 760, 1120, 900, 12), "dark")
        rect(cv, vm, 1050, 772, 1110, 885, "yellow")


# ------------------------------------------------------------------ 06 我就假装 信号不好 (phone, glitch)
def s_phone(cv, t, st):
    st["no"] = 6
    a0 = LY[5][0]
    text2, times2 = part(5, 1)
    g = ss(times2[0] - 0.05, times2[0] + 0.1, t)
    if g > 0:
        t = math.floor(t * 10) / 10 + 0.02          # stutter
    cv.fill("dark")
    vm = cam(0, 0, lerp(-300, 0, eo((t - a0) / 0.35)), 3 * math.sin(t * 1.7))
    poly(cv, vm, rrect(560, 40, 1360, 1040, 70), "black")
    poly(cv, vm, rrect(590, 70, 1330, 1010, 50), "paper")
    poly(cv, vm, rrect(870, 85, 1050, 120, 18), "black")
    # signal bars dropping
    nb = 4 - int(c01((t - times2[0]) / 0.9) * 4.99)
    for k in range(4):
        h = 18 + 12 * k
        rect(cv, vm, 1200 + k * 22, 160 - h, 1214 + k * 22, 160, "dark" if k < nb else "pink", 1.0 if k < nb else 0.35)
    if nb == 0:
        ch_at(cv, vm, "heavy", 40, "×", 1300, 140, "pink")
    # video call: mascot face, frozen with a loading spinner when the signal dies
    buf = np.zeros((H, W), f32)
    rect(None, vm, 620, 190, 1300, 640, "teal", buf=buf)
    cv.paint(buf * HT(0.45, 14, 20), 0, 0, "teal")
    mascot(cv, vm, 960, 500, 330, t if g < 0.5 else math.floor(t * 2) / 2, eyes="closed" if g > 0.5 else "open", mouth="smile")
    if g > 0.5:
        for k in range(8):
            a = k * math.pi / 4 + math.floor(t * 8) * math.pi / 4
            disc(cv, vm, 960 + 70 * math.cos(a), 410 + 70 * math.sin(a), 6 + k * 1.2, "paper")
    text1, times1 = part(5, 0)
    word(cv, vm, text1, times1, 960, 740, "heavy", 105, "dark", t)
    word(cv, vm, text2, times2, 960, 900, "heavy", 125, "pink", t, jitter=50 * g, shadow="teal", sh=0.06)
    st["glitch"] = g
    st["mis"] = (int(30 * g * (hsh(int(t * 30), 3) - 0.3)), int(12 * g * (hsh(int(t * 30), 4) - 0.5)))


def glitch(cv, t, g):
    if g <= 0:
        return
    n = int(t * 30)
    for k in range(int(3 + 9 * g)):
        y0 = int(hsh(n, k, 1) * H)
        h = int(10 + 90 * hsh(n, k, 2))
        dx = int((hsh(n, k, 3) - 0.5) * 300 * g)
        cv.L[:, y0:y0 + h] = np.roll(cv.L[:, y0:y0 + h], dx, axis=2)
    for k in range(int(2 + 4 * g)):
        x0, y0 = int(hsh(n, k, 5) * (W - 200)), int(hsh(n, k, 6) * (H - 120))
        w, h = int(60 + 200 * hsh(n, k, 7)), int(30 + 90 * hsh(n, k, 8))
        blk = cv.L[:, y0:y0 + h, x0:x0 + w]
        m = blk[:, ::16, ::16]
        cv.L[:, y0:y0 + h, x0:x0 + w] = np.repeat(np.repeat(m, 16, 1), 16, 2)[:, :blk.shape[1], :blk.shape[2]]


# ------------------------------------------------------------------ 07 喜欢谁我也不知道 (heart → ?)
def s_heart(cv, t, st):
    st["no"] = 7
    a0 = LY[6][0]
    cv.fill("paper")
    vm = cam(0, 0, 60 * eio((t - a0) / 1.7), 3 * math.sin(t * 2.1))
    buf = np.zeros((H, W), f32)
    disc(None, vm, 960, 520, 480, "pink", buf=buf)
    cv.paint(buf * HT(0.4, 16, 45), 0, 0, "pink")
    text, times = syl(6)
    tq = times[5]                     # 也 → the poke
    morph = eio((t - tq - 0.1) / 0.3)
    pul = 1 + 0.08 * bpulse(t)
    if morph < 1:
        hs = 520 * pul * (1 - morph)
        poly(cv, vm, heart(960, 540, hs) + [10, 12], "dark")
        poly(cv, vm, heart(960, 540, hs), "pink")
        pline(cv, vm, heart(985, 520, hs * 0.6, 40)[3:14], 14, "paper", 0.8)
    if morph > 0:
        sc = morph * (1 + 0.3 * (1 - eob((t - tq - 0.1) / 0.4)))
        ch_at(cv, vm, "heavy", 560, "?", 972, 552, "dark", sc * pul)
        ch_at(cv, vm, "heavy", 560, "?", 960, 540, "pink", sc * pul)
    word(cv, vm, text[:3], times[:3], 460, 210, "heavy", 120, "dark", t, rot=-6)
    word(cv, vm, text[3:], times[3:], 1310, 900, "heavy", 120, "teal", t, rot=-6, shadow="dark", sh=0.05)
    poke = eo((t - tq + 0.25) / 0.25) * (1 - eo((t - tq - 0.25) / 0.3))
    mascot(cv, vm, lerp(240, 470, poke), 760, 280, t, arms=0.3 + poke, rot=20 * poke, eyes="open", mouth="o" if morph > 0.5 else "smile")
    # iris out to the night scene
    u = (t - 18.95) / 0.2
    if u > 0:
        m = np.clip((np.hypot(_gx - 960, _gy - 540) - 1200 * (1 - eio(u))) / 2, 0, 1).astype(f32)
        cv.paint(m, 0, 0, "dark")


# ------------------------------------------------------------------ 08 通宵熬夜也要吃到饱 (night desk, noodles, clock spinning)
STARS = [(float(_r.uniform(0, W)), float(_r.uniform(0, 500)), float(_r.uniform(2, 6)), i) for i in range(60)]


def s_night(cv, t, st, no=8):
    st["no"] = no
    a0 = LY[7][0]
    cv.fill("dark")
    vm = cam(80 * eio((t - a0) / 2.2), 0, 40, 0)
    vf = cam(80 * eio((t - a0) / 2.2), 0, 40, 0, 2500)
    for (x, y, r, i) in STARS:
        disc(cv, vf, x, y, r * (0.6 + 0.4 * math.sin(t * 4 + i)), "yellow")
    disc(cv, vf, 1500, 200, 110, "yellow")
    disc(cv, vf, 1550, 170, 100, "dark")
    rect(cv, vm, -400, 800, 2400, 1400, "teal")
    # lamp + light
    buf = np.zeros((H, W), f32)
    poly(None, vm, [(330, 420), (450, 420), (700, 820), (140, 820)], "yellow", buf=buf)
    cv.paint(buf * HT(0.3, 12, 20), 0, 0, "yellow")
    pline(cv, vm, [(250, 820), (250, 520), (380, 360)], 18, "paper")
    poly(cv, vm, [(300, 300), (480, 300), (540, 420), (240, 420)], "pink")
    # clock, hands spinning
    disc(cv, vm, 1520, 520, 150, "paper")
    ring(cv, vm, 1520, 520, 150, 12, "pink")
    for k in range(12):
        a = k * math.pi / 6
        pline(cv, vm, [(1520 + 120 * math.cos(a), 520 + 120 * math.sin(a)), (1520 + 136 * math.cos(a), 520 + 136 * math.sin(a))], 6, "dark")
    for (L, sp, th) in ((80, 1.5, 12), (115, 14.0, 7)):
        a = (t - a0) * sp * 2 * math.pi - math.pi / 2
        pline(cv, vm, [(1520, 520), (1520 + L * math.cos(a), 520 + L * math.sin(a))], th, "dark")
    # noodle cup + steam
    poly(cv, vm, [(860, 600), (1160, 600), (1120, 900), (900, 900)], "paper")
    rect(cv, vm, 875, 680, 1145, 760, "pink")
    poly(cv, vm, ell(1010, 600, 150, 30, 40), "yellow")
    for k in range(3):
        xs_ = 940 + k * 70 + 18 * np.sin(np.linspace(0, 6, 30) + t * 5 + k)
        ys_ = np.linspace(570, 300, 30)
        pline(cv, vm, np.stack([xs_, ys_], 1), 8, "paper", 0.7)
    ch_at(cv, vm, "heavy", 70, "?", 1010, 722, "paper")
    text, times = syl(7)
    word(cv, vm, text[:4], times[:4], 560, 150, "heavy", 135, "yellow", t, track=0.06, shadow="pink", sh=0.05)
    for i, c in enumerate(text[4:]):
        ti = times[4 + i]
        if t < ti:
            continue
        dt = t - ti
        big = c in "吃到饱"
        px = 760 + i * 135 + 18 * math.sin(dt * 5 + i)
        py = 560 - 260 * eo(dt / 0.6) - (40 if big else 0)
        ch_at(cv, vm, "heavy", 140 if big else 110, c, px, py, "paper" if not big else "yellow", pop(t, ti, amt=0.5)[0])
    mascot(cv, vm, 1270, 760, 260, t, eyes="tired", mouth="o", rot=6 * math.sin(t * 1.4))


# ------------------------------------------------------------------ 09 问我一百遍 / 耸耸肩 (? multiplies)
GRID = sorted([(gx, gy) for gx in range(-4, 16) for gy in range(-3, 10)], key=lambda p: (p[0] - 6) ** 2 + (p[1] - 3) ** 2)
GCOL = ("pink", "teal", "yellow", "orange")


def s_hundred(cv, t, st):
    st["no"] = 9
    a0 = LY[8][0]
    cv.fill("paper")
    z = -260 * eio((t - a0) / 4.0)
    vm = cam(0, 0, z, 2 * math.sin(t * 1.3))
    k = int((t - a0) / (BEAT / 2))
    n = min(len(GRID), 2 ** min(k, 12))
    count = min(100, 2 ** min(k, 12))
    sh_times = (LY[9][0], LY[9][0] + BEAT, LY[9][0] + 2 * BEAT)
    shrug = 0.0
    for ts in sh_times:
        if 0 <= t - ts < 0.45:
            shrug = max(shrug, math.sin(math.pi * (t - ts) / 0.45))
    bufs = [np.zeros((H, W), f32) for _ in range(4)]
    for j, (gx, gy) in enumerate(GRID[:n]):
        x, y = 150 + gx * 150, 120 + gy * 150
        pop_ = eob((t - (a0 + math.log2(j + 1) * BEAT / 2)) / 0.2)
        mascot_buf(bufs[j % 4], vm, x, y + 30, 120 * pop_, t, ph=j * 0.7, arms=shrug, sy=1 - 0.15 * shrug)
    for b, c in zip(bufs, GCOL):
        cv.paint(b, 0, 0, c)
    # label boxes with the lyrics
    if t < LY[9][0] + 0.15:
        text, times = syl(8)
        rect(cv, V0, 470, 400, 1450, 650, "dark", eo((t - a0) / 0.2))
        word(cv, V0, text, times, 960, 525, "heavy", 170, "paper", t, amt=0.5)
    else:
        text, times = syl(9)
        u = eo((t - LY[9][0]) / 0.15)
        rect(cv, V0, 640, 410, 1280, 640, "pink", u)
        for i, c in enumerate(text):
            if t >= times[i]:
                dy = -40 * shrug
                ch_at(cv, V0, "heavy", 180, c, 760 + i * 200, 525 + dy, "paper", pop(t, times[i], amt=0.5)[0], (-8, 8, -8)[i] * shrug)
    lab = "×%d" % count
    xs, tot = line_xs(lab, "smiley", 120)
    rect(cv, V0, 1890 - tot - 60, 110, 1890, 250, "yellow")
    for i, c in enumerate(lab):
        ch_at(cv, V0, "smiley", 120, c, 1860 - tot + tot / 2 + xs[i], 180, "dark")


# ------------------------------------------------------------------ 10 问我一万遍 / 还是那句 (a sea of ?, then silence)
_SPR = {}


def q_sprite(cell):
    if cell not in _SPR:
        b = np.zeros((H, W), f32)
        mascot_buf(b, V0, CX, CY + 0.05 * cell, cell * 0.8, 0.0)
        cx, cy = int(CX), int(CY)
        _SPR[cell] = b[cy - cell // 2:cy + cell // 2, cx - cell // 2:cx + cell // 2].copy()
    return _SPR[cell]


def s_tenk(cv, t, st):
    st["no"] = 10
    a0, a1 = LY[10][0], LY[11][0]
    if t < a1:
        cv.fill("teal")
        u = (t - a0) / (a1 - a0)
        cell = int(lerp(110, 46, eio(u)))
        spr = q_sprite(cell)
        tile = np.tile(spr, (H // cell + 3, W // cell + 3))
        ox, oy = int((t * 140) % cell), int((t * 90) % cell)
        m = tile[oy:oy + H, ox:ox + W]
        bands = ((_gx + _gy * 0.6 + t * 300) // 260 % 3).astype(np.int32)
        for k, c in enumerate(("paper", "pink", "yellow")):
            cv.paint(m * (bands == k), 0, 0, c)
        text, times = syl(10)
        rot = 6 * math.sin(t * 3)
        sv = Sub(V0, 960, 540, rot)
        rect(cv, sv, 360, 380, 1560, 700, "dark", eo((t - a0) / 0.2))
        word(cv, sv, text, times, 960, 540, "heavy", 210, "yellow", t, amt=0.5)
        count = int(min(10000, 10 ** (1 + 3 * c01(u * 1.2))))
        lab = "×%d" % count
        xs, tot = line_xs(lab, "smiley", 130)
        rect(cv, V0, 1890 - tot - 60, 100, 1890, 250, "pink")
        for i, c in enumerate(lab):
            ch_at(cv, V0, "smiley", 130, c, 1860 - tot + tot / 2 + xs[i], 175, "paper")
    else:
        cv.fill("paper")
        vm = cam(0, 0, 160 * eio((t - a1) / 1.6), 0)
        text, times = syl(11)
        word(cv, vm, text, times, 960, 480, "heavy", 110, "dark", t, track=0.2, amt=0.2)
        for k in range(6):
            tk = beat_t(beat_n(a1) + 2 + k * 0.5)
            if t >= tk:
                disc(cv, vm, 1210 + k * 34, 510, 9, "pink")
        mascot(cv, vm, 960, 760, 220, t, eyes="open", mouth="flat", rot=0)


# ------------------------------------------------------------------ chorus helpers
def chorus_text(i):
    return syl(i)


# C1 我不知道 — stamped onto the exam sheet
def s_c1(cv, t, st):
    st["no"] = 11
    a0 = LY[12][0]
    cv.fill("teal")
    vm = cam(0, 0, 40 + 60 * (t - a0) / 2.1, -3)
    rect(cv, vm, 300, 40, 1620, 1100, "paper")
    for q in range(5):
        pline(cv, vm, [(420, 220 + q * 170), (1500, 220 + q * 170)], 4, "dark", 0.5)
    # 还是那句 (overlaps the start of this line)
    text, times = syl(11)
    if t < LY[11][1] + 0.1:
        word(cv, vm, text, [a0 - 1] * 4, 960, 130, "heavy", 70, "dark", t, track=0.2, a=1 - ss(LY[11][1] - 0.2, LY[11][1] + 0.1, t))
    text, times = syl(12)
    sc = 1 + 0.9 * (1 - eo((t - a0) / 0.12))
    buf = np.zeros((H, W), f32)
    sv = Sub(vm, 960, 560, -8)
    pline(None, sv, (rrect(400, 380, 1520, 740, 30) - (960, 560)) * sc + (960, 560), 22 * sc, "pink", closed=True, buf=buf)
    xs, _ = line_xs(text, "heavy", 230, 0.05)
    for i, c in enumerate(text):
        if t >= times[i] - 0.001 or i == 0:
            ch_at(None, sv, "heavy", 230, c, 960 + xs[i] * sc, 560, "pink", sc if i == 0 else pop(t, times[i], amt=0.6)[0], buf=buf)
    cv.paint(buf * np.clip(TEX[1] * 1.25 - 0.2, 0, 1), 0, 0, "pink")
    for k in range(4):
        tb = beat_t(beat_n(a0) + 2 + k)
        if t >= tb:
            sp = pop(t, tb, amt=0.8)[0]
            x, y = (520, 1420, 600, 1360)[k], (220, 260, 900, 880)[k]
            ring(cv, vm, x, y, 70 * sp, 10, "pink")
            ch_at(cv, vm, "heavy", 100, "?", x, y, "pink", sp, 15 - 30 * (k % 2))


# C2 我不知道 — four flip tiles
def s_c2(cv, t, st):
    st["no"] = 12
    a0 = LY[13][0]
    cv.fill("pink")
    vm = cam(0, 0, 50, 2 * math.sin(t * 2))
    buf = np.zeros((H, W), f32)
    disc(None, vm, 960, 540, 700, "teal", buf=buf)
    cv.paint(buf * HT(0.5, 18, 45), 0, 0, "teal", mode="print")
    text, times = syl(13)
    cols = ("paper", "yellow", "teal", "paper")
    for i, c in enumerate(text):
        if t < times[i]:
            continue
        f = eob((t - times[i]) / 0.25)
        bounce = -40 * math.exp(-hb(t) * 9) * ((beat_n(t) + i) % 2)
        x, y = 960 + (i - 1.5) * 380, 540 + bounce
        w = 170 * max(f, 0.02)
        rect(cv, vm, x - w + 14, y - 170 + 14, x + w + 14, y + 170 + 14, "dark")
        rect(cv, vm, x - w, y - 170, x + w, y + 170, cols[i])
        if f > 0.3:
            ch_at(cv, vm, "heavy", 250, c, x, y, "dark" if cols[i] != "teal" else "paper", 1.0)


# C3 真不知道 — written on a blank sheet, crumpled, thrown in the bin
def s_c3(cv, t, st):
    st["no"] = 13
    a0 = LY[14][0]
    cv.fill("yellow")
    vm = cam(0, 0, 30, 0)
    bin_x, bin_y = 1620, 820
    poly(cv, vm, [(bin_x - 150, bin_y - 160), (bin_x + 150, bin_y - 160), (bin_x + 120, bin_y + 260), (bin_x - 120, bin_y + 260)], "teal")
    for k in range(5):
        pline(cv, vm, [(bin_x - 110 + k * 55, bin_y - 120), (bin_x - 90 + k * 45, bin_y + 230)], 6, "dark", 0.5)
    rect(cv, vm, bin_x - 165, bin_y - 175, bin_x + 165, bin_y - 145, "dark")
    text, times = syl(14)
    cr = eio((t - 34.75) / 0.3)
    if cr < 1:
        card = Canvas()
        rect(card, vm, 480, 180, 1240, 900, "paper")
        ch_at(card, vm, "smiley", 60, "0", 1150, 250, "pink")
        ring(card, vm, 1150, 250, 50, 6, "pink")
        for q in range(3):
            pline(card, vm, [(560, 720 + q * 60), (1160, 720 + q * 60)], 3, "dark", 0.4)
        word(card, vm, text, times, 860, 470, "kai", 170, "dark", t, wipe=0.2)
        if cr > 0:
            src = np.array([(480, 180), (1240, 180), (1240, 900), (480, 900)], f32)
            ctr = np.array([860, 540])
            ang = cr * 2.5
            dst = []
            for k, p in enumerate(src):
                d = (p - ctr) * (1 - 0.82 * cr)
                d = np.array([d[0] * math.cos(ang) - d[1] * math.sin(ang), d[0] * math.sin(ang) + d[1] * math.cos(ang)])
                dst.append(ctr + d + (hsh(k, 9) - 0.5) * 120 * cr)
            card = warp_canvas(card, cv2.getPerspectiveTransform(src, np.array(dst, f32)))
        cv.over(card)
    if cr > 0.6:
        u = c01((t - 35.05) / 0.5)
        bx = lerp(860, bin_x, u)
        by = lerp(540, bin_y - 170, u) - 520 * 4 * u * (1 - u)
        if u < 1:
            disc(cv, vm, bx, by, 95, "paper")
            for k in range(6):
                a = k * 1.1 + t * 9
                pline(cv, vm, [(bx + 30 * math.cos(a), by + 30 * math.sin(a)), (bx + 80 * math.cos(a + 0.5), by + 80 * math.sin(a + 0.5))], 4, "dark", 0.6)
        else:
            sw = eo((t - 35.55) / 0.3)
            for k in range(5):
                a = -math.pi / 2 + (k - 2) * 0.35
                pline(cv, vm, [(bin_x + 80 * math.cos(a), bin_y - 200 + 80 * math.sin(a)),
                               (bin_x + (80 + 120 * sw) * math.cos(a), bin_y - 200 + (80 + 120 * sw) * math.sin(a))], 10, "pink", 1 - sw)
    mascot(cv, vm, 300, 760, 300, t, eyes="open", mouth="smile" if t > 35.55 else "flat", arms=0.8 if t > 35.55 else 0.0)


# ------------------------------------------------------------------ 16 想不通的事情明天再说就好 (tear-off calendar)
def s_calendar(cv, t, st):
    st["no"] = 14
    a0 = LY[15][0]
    cv.fill("teal")
    vm = cam(0, 0, 40 + 50 * (t - a0) / 2.2, 0)
    buf = np.zeros((H, W), f32)
    for k in range(-5, 25):
        pline(None, vm, [(k * 110, -100), (k * 110 - 600, 1300)], 30, "teal", buf=buf)
    cv.paint(buf * HT(0.4, 12, 0), 0, 0, "green", mode="print")
    X0, Y0, X1, Y1 = 700, 90, 1220, 700
    nflip = max(0, int((t - a0) / BEAT) + 1)
    rect(cv, vm, X0 + 14, Y0 + 14, X1 + 14, Y1 + 14, "dark")
    rect(cv, vm, X0, Y0, X1, Y1, "paper")
    rect(cv, vm, X0, Y0, X1, Y0 + 110, "pink")
    for k in range(6):
        disc(cv, vm, X0 + 60 + k * 80, Y0 + 20, 12, "dark")
    ch_at(cv, vm, "heavy", 380, str(1 + nflip), (X0 + X1) / 2, 420, "dark")
    # the page currently tearing off
    pt = t - (a0 + (nflip - 1) * BEAT)
    if nflip >= 1 and pt < 0.4:
        card = Canvas()
        rect(card, V0, X0, Y0 + 110, X1, Y1, "paper")
        ch_at(card, V0, "heavy", 380, str(nflip), (X0 + X1) / 2, 420, "dark")
        u = eo(pt / 0.4)
        src = np.array([(X0, Y0 + 110), (X1, Y0 + 110), (X1, Y1), (X0, Y1)], f32)
        dx, dy = 700 * u, -300 * u + 900 * u * u
        dst = np.array([(X0 + dx, Y0 + 110 + dy), (X1 + dx + 60 * u, Y0 + 110 + dy - 100 * u),
                        (X1 + dx + 160 * u, Y1 + dy - 260 * u), (X0 + dx + 80 * u, Y1 + dy - 60 * u)], f32)
        dst_s = np.array([vm.pt(*p) for p in dst], f32)
        cv.over(warp_canvas(card, cv2.getPerspectiveTransform(np.array([V0.pt(*p) for p in src], f32), dst_s)))
    text, times = syl(15)
    word(cv, vm, text[:6], times[:6], 960, 845, "heavy", 105, "paper", t, shadow="dark", sh=0.06)
    word(cv, vm, text[6:], times[6:], 960, 960, "heavy", 105, "yellow", t, shadow="dark", sh=0.06)
    mascot(cv, vm, 1520, 560, 300, t, eyes="closed", mouth="o", rot=8 * math.sin(t * 3))
    for k in range(3):
        u = ((t - a0) * 0.8 + k / 3) % 1
        ch_at(cv, vm, "heavy", 70, "~", 1600 + 120 * u + 20 * math.sin(u * 9), 380 - 260 * u, "yellow", 1.0, 0, 1 - u)


# ------------------------------------------------------------------ C4 我不知道 — marquee rows
def s_c4(cv, t, st):
    st["no"] = 15
    a0 = LY[16][0]
    cv.fill("pink")
    for r_ in range(7):
        yy = 20 + r_ * 175
        off = ((t - a0) * 700 * (1 if r_ % 2 else -1)) % 640
        for q in range(-1, 5):
            for m_, c in enumerate("我不知道"):
                ch_at(cv, V0, "heavy", 130, c, q * 640 + m_ * 150 + off - 320, yy, "dark" if r_ % 2 else "orange", mode="print")
    text, times = syl(16)
    v = View(1 + 0.05 * bpulse(t), -4)
    rect(cv, v, 300, 380, 1620, 700, "paper", eo((t - a0) / 0.15))
    word(cv, v, text, times, 960, 540, "heavy", 250, "pink", t, amt=0.6, shadow="dark", sh=0.04)
    # tail of 明天再说就好 (overlap)
    if t < LY[15][1]:
        tx, tt = syl(15)
        word(cv, V0, tx[6:], [0] * 6, 960, 960, "heavy", 80, "paper", t, a=1 - ss(LY[15][1] - 0.15, LY[15][1], t))


# C5 我不知道 — characters sink into a pillow, mascot yawning
def s_c5(cv, t, st):
    st["no"] = 16
    a0 = LY[17][0]
    cv.fill("teal")
    vm = cam(0, 0, 40 + 50 * (t - a0) / 2.1, 1.5 * math.sin(t * 1.4))
    buf = np.zeros((H, W), f32)
    for k in range(40):
        disc(None, vm, (k * 263) % 2000, (k * 151) % 1100, 30, "paper", buf=buf)
    cv.paint(buf * HT(0.4, 10, 45), 0, 0, "paper")
    xs_ = np.linspace(260, 1660, 60)
    wob = 14 * np.sin(xs_ * 0.01 + t * 2)
    top = 560 + wob - 40 * np.sin((xs_ - 260) / 1400 * math.pi)
    bot = 900 + 30 * np.sin((xs_ - 260) / 1400 * math.pi)
    P = np.vstack([np.stack([xs_, top], 1), np.stack([xs_[::-1], bot[::-1]], 1)])
    poly(cv, vm, P + [16, 18], "dark")
    poly(cv, vm, P, "paper")
    pline(cv, vm, np.stack([xs_[5:-5], (top[5:-5] + bot[5:-5]) / 2], 1), 4, "pink", 0.6)
    text, times = syl(17)
    for i, c in enumerate(text):
        if t < times[i]:
            continue
        dt = t - times[i]
        x = 600 + i * 240
        land = eo(dt / 0.22)
        y = lerp(80, 470, land)
        sq = 1 + 0.3 * math.exp(-max(0, dt - 0.22) * 8) * (dt > 0.22)
        ch_at(cv, vm, "heavy", 210, c, x, y + 20 * (sq - 1) * 3, "pink", 1.0, (-5, 4, -3, 6)[i], 1.0)
    yawn = ss(41.0, 41.3, t) * (1 - ss(41.9, 42.2, t))
    mascot(cv, vm, 1620, 400, 260, t, eyes="closed" if yawn > 0.3 else "tired", mouth="o", sy=1 + 0.12 * yawn, rot=-10 * yawn)
    if yawn > 0.3:
        ch_at(cv, vm, "smiley", 90, "Z", 1760, 210 - 60 * yawn, "paper", 1.0, 10)


# C6 真不知道 — one composition per beat
C6_LOOKS = [("yellow", "pink", "dark", "row"), ("dark", "yellow", "pink", "grid"), ("pink", "paper", "teal", "col"),
            ("teal", "dark", "yellow", "diag"), ("yellow", "dark", "pink", "row")]


def s_c6(cv, t, st):
    st["no"] = 17
    a0 = LY[18][0]
    j = min(len(C6_LOOKS) - 1, int((t - a0) / BEAT))
    tb = t - (a0 + j * BEAT)
    bg, txt, shc, lay = C6_LOOKS[j]
    cv.fill(bg)
    v = View(1 + 0.14 * (1 - eo(tb / 0.14)), (3, -4, 2, -5, 3)[j])
    if j % 2 == 0:
        buf = np.zeros((H, W), f32)
        for k in range(16):
            a = k * math.pi / 8 + t * 0.5
            poly(None, v, [(CX, CY), (CX + 2200 * math.cos(a), CY + 2200 * math.sin(a)), (CX + 2200 * math.cos(a + 0.2), CY + 2200 * math.sin(a + 0.2))], "pink", buf=buf)
        cv.paint(buf, 0, 0, shc, 0.5, mode="print")
    else:
        buf = np.zeros((H, W), f32)
        disc(None, v, CX, CY, 520, "pink", buf=buf)
        cv.paint(buf * HT(0.5, 18, 45), 0, 0, shc)
    text, times = syl(18)
    pos = {"row": [(CX + (i - 1.5) * 330, CY, 330) for i in range(4)],
           "grid": [(CX + (i % 2 - 0.5) * 380, CY + (i // 2 - 0.5) * 380, 360) for i in range(4)],
           "col": [(CX - 300 + (i % 2) * 600, 160 + i * 250, 260) for i in range(4)],
           "diag": [(CX - 540 + i * 360, CY - 330 + i * 220, 330) for i in range(4)]}[lay]
    for i, c in enumerate(text):
        if t < times[i]:
            continue
        x, y, s = pos[i]
        ch_at(cv, v, "heavy", s, c, x + 16, y + 14, shc)
        ch_at(cv, v, "heavy", s, c, x, y, txt, pop(t, times[i], amt=0.4)[0])
    mascot(cv, v, 1700 if j % 2 else 220, 880, 220, t, arms=1.0 if tb < 0.25 else 0.4, eyes="open", mouth="o")


# ------------------------------------------------------------------ 20 天塌下来也要先让我睡个饱 (the sky collapses; asleep)
SKY_TILES = []
for _gyi in range(5):
    for _gxi in range(8):
        SKY_TILES.append((_gxi, _gyi, float(_r.uniform(-0.3, 0.3)), float(_r.uniform(-300, 300))))


def bed(cv, v, t, sleeper=True):
    rect(cv, v, 300, 820, 1620, 900, "orange")
    rect(cv, v, 300, 700, 340, 1000, "dark")
    rect(cv, v, 1580, 760, 1620, 1000, "dark")
    poly(cv, v, rrect(360, 700, 640, 800, 40), "paper")
    if sleeper:
        mascot(cv, v, 520, 680, 260, t, eyes="closed", rot=-90, mouth="o" if (t % 2.2) < 1.1 else "smile")
    breath = 8 * math.sin(t * 2.6)
    xs_ = np.linspace(560, 1600, 40)
    top = 700 - breath - 30 * np.sin((xs_ - 560) / 1040 * math.pi)
    P = np.vstack([np.stack([xs_, top], 1), [(1600, 860), (560, 860)]])
    poly(cv, v, P, "pink")
    buf = np.zeros((H, W), f32)
    poly(None, v, P, "pink", buf=buf)
    cv.paint(buf * HT(0.2, 30, 20), 0, 0, "yellow", mode="print")


def s_sky(cv, t, st):
    st["no"] = 18
    a0 = LY[19][0]
    cv.fill("dark")
    vm = cam(0, 0, 30, 0)
    for (x, y, r, i) in STARS:
        disc(cv, vm, x, y, r, "yellow", 0.7)
    text, times = syl(19)
    tw, th = 260, 160
    for (gx, gy, rv, vx) in SKY_TILES:
        d = t - (times[0] + 0.15 + 0.05 * gx + 0.07 * (4 - gy) + 0.1 * hsh(gx, gy))
        x0, y0 = -80 + gx * tw, -40 + gy * th
        cx_, cy_ = x0 + tw / 2, y0 + th / 2
        ang, dx, dy = 0.0, 0.0, 0.0
        if d > 0:
            dy = 1500 * d * d + 100 * d
            dx = vx * d
            ang = rv * d * 3
        if cy_ + dy > 1400:
            continue
        P = np.array([(x0, y0), (x0 + tw, y0), (x0 + tw, y0 + th), (x0, y0 + th)], np.float64) - (cx_, cy_)
        ca, sa = math.cos(ang), math.sin(ang)
        P = np.stack([P[:, 0] * ca - P[:, 1] * sa, P[:, 0] * sa + P[:, 1] * ca], 1) + (cx_ + dx, cy_ + dy)
        b = np.zeros((H, W), f32)
        poly(None, vm, P, "teal", buf=b)
        cv.paint(b * HT(0.6 - 0.08 * gy, 14, 20), 0, 0, "teal")
        cv.paint(b * (1 - HT(0.6 - 0.08 * gy, 14, 20)), 0, 0, "paper")
        pline(cv, vm, np.vstack([P, P[:1]]), 4, "dark")
    # 天塌下来: heavy characters crash down
    for i, c in enumerate(text[:4]):
        ti = times[i]
        if t < ti:
            continue
        u = eo((t - ti) / 0.2)
        ch_at(cv, vm, "heavy", 200, c, 480 + i * 320, lerp(-150, 330, u) + (0 if u < 1 else 0), "yellow", 1.0, (-6, 5, -4, 7)[i])
    bed(cv, vm, t)
    word(cv, vm, text[4:], times[4:], 1000, 975, "heavy", 98, "paper", t, amt=0.2, shadow="pink", sh=0.06)


# ------------------------------------------------------------------ outro: Zzz, pull back into the textbook, the book closes
def night_card(t):
    c = Canvas()
    c.fill("dark")
    vm = cam(0, 0, 30, 0)
    for (x, y, r, i) in STARS:
        disc(c, vm, x, y, r * (0.6 + 0.4 * math.sin(t * 3 + i)), "yellow")
    disc(c, vm, 1500, 220, 120, "yellow")
    disc(c, vm, 1555, 190, 110, "dark")
    bed(c, vm, t)
    for k in range(3):
        u = ((t - 47.1) * 0.5 + k / 3) % 1
        ch_at(c, vm, "smiley", 70 + 60 * u, "Z", 640 + 260 * u + 40 * math.sin(u * 8), 600 - 420 * u, "paper", 1.0, 10, min(1, 4 * (1 - u)))
    return c


def s_outro(cv, t, st):
    st["no"] = 19
    pb = eio((t - 48.6) / 1.4)
    if pb <= 0:
        cv.over(night_card(t))
        return
    cv.fill("teal")
    s = lerp(1.0, 0.36, pb)
    ox, oy = lerp(0, 380, pb), lerp(0, 20, pb)
    sq = eio((t - 50.95) / 0.4)
    vb = View(lerp(2.6, 1.0, pb), 0, lerp(-1030, 0, pb), lerp(-60, 0, pb), ox=-400 * sq)
    poly(cv, vb, rrect(lerp(150, 935, sq), 40, 1770, 1040, 26), "dark")
    if sq < 1:
        rect(cv, vb, lerp(180, 955, sq), 60, 955, 1020, "paper")
        if sq < 0.05:
            print_lines(cv, vb, 250, 160, 880, 15, 52, "dark", 0.75, seed=1)
    rect(cv, vb, 965, 60, 1740, 1020, "paper")
    nc = night_card(t)
    M = np.float32([[vb.s * 0.36, 0, 0], [0, vb.s * 0.36, 0], [0, 0, 1]])
    X0, Y0 = vb.pt(1352 - 0.36 * W / 2, 540 - 0.36 * H / 2)
    M[0, 2], M[1, 2] = X0, Y0
    cv.over(warp_canvas(nc, M))
    mascot(cv, vb, 1580, 920, 120, t, eyes="closed", mouth="o")
    # cover closes over the right page
    cl = eio((t - 50.2) / 0.7)
    if cl > 0:
        cover = Canvas()
        poly(cover, V0, rrect(965, 50, 1760, 1030, 20), "pink")
        ch_at(cover, V0, "heavy", 380, "?", 1362, 520, "paper")
        rect(cover, V0, 965, 50, 1010, 1030, "dark")
        th = math.radians(180 * (1 - cl))
        F = 2800.0
        src = np.array([(965, 50), (1760, 50), (1760, 1030), (965, 1030)], np.float64)
        dst = []
        for (px, py) in src:
            dxp = px - 960
            X, Z = dxp * math.cos(th), dxp * math.sin(th)
            k = F / (F + Z)
            dst.append((960 + X * k, 540 + (py - 540) * k))
        if cl > 0.02:
            if math.cos(th) < 0:
                cover2 = Canvas()
                poly(cover2, V0, rrect(965, 50, 1760, 1030, 20), "orange")
                cover = cover2
            Mv = cv2.getPerspectiveTransform(np.array([V0.pt(*p) for p in src], f32), np.array([vb.pt(*p) for p in dst], f32))
            cv.over(warp_canvas(cover, Mv))
    st["fade"] = 1 - ss(51.3, 51.85, t)


# ================================================================== timeline
B = [4.286, 6.696, 8.839, 10.58, 12.857, 15.268, 17.411, 19.152, 21.429, 25.714, 29.464, 31.607, 33.75, 35.893, 38.036,
     40.179, 42.321, 44.464, 47.143]
SCENES = [(0.0, s_intro), (B[0], s_board), (B[1], s_window), (B[2], s_exam), (B[3], s_soda), (B[4], s_parents),
          (B[5], s_phone), (B[6], s_heart), (B[7], s_night), (B[8], s_hundred), (B[9], s_tenk), (B[10], s_c1),
          (B[11], s_c2), (B[12], s_c3), (B[13], s_calendar), (B[14], s_c4), (B[15], s_c5), (B[16], s_c6),
          (B[17], s_sky), (B[18], s_outro)]
HITS = [(b, 0.25) for b in B] + [(B[10], 1.2), (B[12], 0.4), (B[14], 0.8), (B[16], 0.6), (34.75, 0.3), (35.55, 0.3)] + \
       [(B[16] + j * BEAT, 0.6) for j in range(1, 4)] + [(B[17] + 0.4, 0.6), (B[17] + 0.65, 0.5), (B[17] + 0.9, 0.5), (B[17] + 1.15, 0.5)]
WHIPS = {1: (-1, 0), 2: (-1, 0), 3: (1, 0), 9: (0, 1), 13: (-1, 0), 18: (0, -1)}   # scene index → direction of the incoming whip


def scene_at(t):
    k = 0
    for i, (t0, _) in enumerate(SCENES):
        if t >= t0:
            k = i
    return k


def draw_scene(k, t, st):
    c = Canvas()
    SCENES[k][1](c, t, st)
    return c


def render(fidx):
    t = fidx / FPS
    st = {"no": 0}
    k = scene_at(t)
    cv = draw_scene(k, t, st)
    # whip transitions: the last 0.12 s of the previous scene slides out, the new one slides in
    if k in WHIPS:
        t0 = SCENES[k][0]
        dx, dy = WHIPS[k]
        if t0 - 0.0 <= t < t0 + 0.14:
            e = 0.5 + 0.5 * eo((t - t0) / 0.14)
            prev = draw_scene(k - 1, t, {"no": 0})
            cv = slide(prev, cv, e, dx * W, dy * H)
            st["blur"] = (1 + 140 * abs(dx) * (1 - e) * 2, 1 + 140 * abs(dy) * (1 - e) * 2)
    if k + 1 < len(SCENES) and (k + 1) in WHIPS:
        t1 = SCENES[k + 1][0]
        if t1 - 0.12 <= t < t1:
            dx, dy = WHIPS[k + 1]
            e = 0.5 * ei((t - (t1 - 0.12)) / 0.12)
            cv = slide(cv, draw_scene(k + 1, t1, {"no": 0}), e, dx * W, dy * H)
            st["blur"] = (1 + 140 * abs(dx) * e * 2, 1 + 140 * abs(dy) * e * 2)
    glitch(cv, t, st.get("glitch", 0.0))
    ui(cv, t, st, CREDIT, a=ss(0.3, 0.8, t))
    return finish(cv, fidx, t, st, HITS)


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
               "-i", AUDIO, "-t", str(DUR), "-map", "0:v", "-map", "1:a", "-af", f"afade=t=out:st={DUR - 0.8}:d=0.8",
               "-c:v", "libx264", "-preset", "slow", "-crf", "22", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
               "-c:a", "aac", "-b:a", "320k", out]
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        frames = range(NF) if len(sys.argv) < 4 else range(int(float(sys.argv[3]) * FPS), int(float(sys.argv[4]) * FPS))
        with Pool(4) as pool:
            for i, fr in enumerate(pool.imap(render, frames, chunksize=2)):
                p.stdin.write(fr.tobytes())
                if i % 120 == 0:
                    print("frame", i, flush=True)
        p.stdin.close()
        p.wait()
        print("done", out)
