#!/usr/bin/env python3
"""《我不知道》PV（暗版）—— 复印机 / 碳粉风格，头被问号盖住的学生剪影。

同样的歌词，读成麻木和逃避：灰黄旧纸、黑色碳粉、一点暗红；
每重复一次「我不知道」，画面就像又被复印一遍（更糊、更脏、对比更硬）；
结尾闹钟响起，复印机再次扫过，回到开头——循环。

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

from engine import (BEAT, CX, CY, FPS, H, HT, PH, TEX, V0, W, Canvas, Sub, View, beat_n, beat_u, bird, c01, cam, ch_at,
                    disc, ei, eio, ell, eo, eob, f32, finish, hsh, lerp, line_xs, pline, poly, rect, ring, ss, ui,
                    warp_canvas, _gx, _gy)

D = os.path.dirname(os.path.abspath(__file__))
AUDIO = os.environ.get("MV_AUDIO", "/root/.claude/uploads/e5f3b459-77d3-5ac0-ba91-983fc9f5c975/71d3e341-_____.wav")
DUR = 51.85
NF = int(DUR * FPS)
CREDIT = "vo. 洛天依"
ANIM_FPS = 12          # the animation itself moves on twos-and-a-half: cold, slightly choppy


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


def type_line(cv, v, i, x, y, size, col="dark", t=0.0, fk="bold", track=0.12, a=1.0, keep_space=True, caret=True, rot=0.0):
    """Typewriter subtitle of lyric line i: characters appear instantly, no bounce."""
    a0, a1, raw = LY[i]
    text, times = syl(i)
    full = raw if keep_space else text
    xs, _ = line_xs(full, fk, size, track)
    k = 0
    last = None
    for j, c in enumerate(full):
        if c == " ":
            continue
        if t >= times[k]:
            ch_at(cv, v, fk, size, c, x + xs[j], y, col, 1.0, rot, a)
            last = j
        k += 1
    if caret and last is not None and t < a1 + 0.3 and (t * 2.5) % 1 < 0.6:
        cx_ = x + xs[last] + size * 0.62
        rect(cv, v, cx_ - size * 0.04, y - size * 0.45, cx_ + size * 0.04, y + size * 0.45, "red", a)


def rrect(x0, y0, x1, y1, r, n=8):
    P = []
    for (cx_, cy_, a0) in ((x1 - r, y0 + r, -math.pi / 2), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, math.pi / 2), (x0 + r, y0 + r, math.pi)):
        for k in range(n + 1):
            a = a0 + k * (math.pi / 2) / n
            P.append((cx_ + r * math.cos(a), cy_ + r * math.sin(a)))
    return np.array(P)


def heart(cx, cy, s, n=80):
    th = np.linspace(0, 2 * math.pi, n)
    x = 16 * np.sin(th) ** 3
    y = -(13 * np.cos(th) - 5 * np.cos(2 * th) - 2 * np.cos(3 * th) - np.cos(4 * th))
    return np.stack([cx + x * s / 32, cy + y * s / 32], 1)


def beat_t(k):
    return PH + k * BEAT


# ------------------------------------------------------------------ the student
def student(cv, v, x, y, s, t, shrug=0.0, col="dark", head="dark", arms="desk", a=1.0, tilt=0.0, buf=None):
    """Front/back silhouette; (x, y) = base of the neck, s = shoulder width. The head is a '?'."""
    def T(P):
        P = np.asarray(P, np.float64) * s
        return P + (x, y)

    sh = -0.13 * shrug
    poly(cv, v, T([(-0.09, -0.06), (0.09, -0.06), (0.1, 0.08), (-0.1, 0.08)]), col, a, buf=buf)
    poly(cv, v, T([(-0.16, 0.02 + sh), (0.16, 0.02 + sh), (0.5, 0.12 + sh), (0.58, 0.32), (0.56, 1.2), (-0.56, 1.2), (-0.58, 0.32), (-0.5, 0.12 + sh)]),
         col, a, buf=buf)
    if arms == "desk":
        for sg in (-1, 1):
            pline(cv, v, T([(0.52 * sg, 0.3), (0.62 * sg, 0.72), (0.2 * sg, 0.86)]), 0.17 * s, col, a, buf=buf)
    elif arms == "shrug":
        for sg in (-1, 1):
            pline(cv, v, T([(0.52 * sg, 0.3), (0.74 * sg, 0.62 - 0.25 * shrug), (1.0 * sg, 0.5 - 0.45 * shrug)]), 0.15 * s, col, a, buf=buf)
            poly(cv, v, T(ell(1.04 * sg, 0.46 - 0.45 * shrug, 0.09, 0.05, 14)), col, a, buf=buf)
    hx, hy = x, y - 0.26 * s + sh * s * 0.5
    poly(cv, v, T(ell(0, -0.26 + sh * 0.5, 0.24, 0.27, 40)), col, a, buf=buf)
    # a sheet of paper with a printed '?' taped over the face
    sv = Sub(v, hx, hy, -7 + tilt)
    if buf is None:
        rect(cv, sv, hx - 0.27 * s, hy - 0.3 * s, hx + 0.27 * s, hy + 0.3 * s, "paper", a)
        rect(cv, sv, hx - 0.27 * s, hy - 0.3 * s, hx + 0.27 * s, hy + 0.3 * s, "grey", 0.35 * a)
        rect(cv, sv, hx - 0.12 * s, hy - 0.34 * s, hx + 0.12 * s, hy - 0.26 * s, "grey", 0.8 * a)
        ch_at(cv, sv, "heavy", 0.6 * s, "?", hx, hy + 0.02 * s, head, 1.0, 0, a)
    else:
        rect(None, sv, hx - 0.27 * s, hy - 0.3 * s, hx + 0.27 * s, hy + 0.3 * s, "dark", buf=buf)


def desk(cv, v, y, col="dark", x0=-400, x1=2320):
    rect(cv, v, x0, y, x1, y + 34, col)
    rect(cv, v, x0, y + 34, x1, 1500, "grey")


# ------------------------------------------------------------------ photocopy degradation
_r = np.random.default_rng(13)
_sn = cv2.GaussianBlur(_r.random((H, W)).astype(f32), (0, 0), 1.1)
SPECK = ((_sn - _sn.mean()) / _sn.std()).astype(f32)
STREAK_X = _r.integers(0, W, 40)


def degrade(img, g, gen):
    """img: float RGB 0..1. g = how many generations of copying (0..1)."""
    if g <= 0.01:
        return img
    img = cv2.GaussianBlur(img, (0, 0), 0.3 + 1.6 * g)
    lum = img.mean(2, keepdims=True)
    k = 1 + 1.8 * g
    img = np.clip(lum + (img - lum) * (1 - 0.6 * g), 0, 1)
    img = np.clip(0.55 + (img - 0.55) * k, 0, 1)
    sp = np.clip((SPECK - (3.4 - 1.6 * g)) / 0.5, 0, 1)
    img *= (1 - 0.85 * sp)[..., None]
    for j in range(int(3 + 16 * g)):
        x = int(STREAK_X[(j + gen * 7) % len(STREAK_X)])
        w = 1 + int(3 * hsh(j, gen))
        img[:, x:x + w] *= 1 - (0.15 + 0.3 * g) * hsh(j, gen, 2)
    if g > 0.35:
        dy = int(6 * g * math.sin(gen * 2.1))
        img = np.roll(img, dy, 0)
    return img


# ================================================================== scenes
def tq(t):
    """quantise animation time."""
    return math.floor(t * ANIM_FPS) / ANIM_FPS


def exam_sheet(cv, v, blank=True):
    rect(cv, v, 360, 40, 1560, 1120, "paper")
    rect(cv, v, 360, 40, 1560, 1120, "grey", 0.25)
    rect(cv, v, 360, 40, 1560, 1120, "paper", 0.8)
    pline(cv, v, [(420, 150), (1500, 150)], 3, "dark", 0.6)
    for q in range(5):
        yy = 290 + q * 170
        ch_at(cv, v, "bold", 44, f"{q + 1}.", 450, yy - 34, "dark", a=0.8)
        pline(cv, v, [(510, yy), (1300, yy)], 3, "dark", 0.55)
        rect(cv, v, 1350, yy - 70, 1480, yy + 10, "dark", 0.18)


# ------------------------------------------------------------------ 00 intro: the copier light sweeps, a blank exam sheet comes out
def s_intro(cv, t, st, end_loop=False):
    st["no"] = 0
    cv.fill("dark")
    u = c01((t - 0.6) / 2.4) if not end_loop else c01((t - 49.4) / 1.6)
    sheet = Canvas()
    exam_sheet(sheet, cam(0, 0, 40, 0))
    # revealed above the light bar
    yb = lerp(-60, H + 60, eio(u))
    m = np.zeros((H, W), f32)
    m[:max(0, int(yb))] = 1
    sheet.L *= m[None]
    cv.over(sheet)
    if 0 < u < 1:
        band = np.exp(-((_gy - yb) / 26) ** 2).astype(f32)
        cv.paint(band, 0, 0, "paper")
        glow = np.exp(-((_gy - yb) / 160) ** 2).astype(f32) * 0.5
        cv.paint(glow, 0, 0, "paper", 0.6)
    if not end_loop and t > 3.4:
        st["hold"] = True


# ------------------------------------------------------------------ 01 老师又在问 答案多少: red pen circles until the sheet is full
CIRCLES = [(float(_r.uniform(480, 1440)), float(_r.uniform(180, 1000)), float(_r.uniform(50, 180)), float(_r.uniform(0, 6))) for _ in range(46)]


def s_teacher(cv, t, st):
    st["no"] = 1
    cv.fill("dark")
    vm = cam(0, 0, 40 + 40 * (t - LY[0][0]) / 2.4, 0)
    exam_sheet(cv, vm)
    k = int((t - LY[0][0]) / (BEAT / 2)) + 1
    for j, (x, y, r, ph) in enumerate(CIRCLES[:max(0, min(len(CIRCLES), k * k // 2 + 1))]):
        if j % 3 == 2:
            pline(cv, vm, [(x - r * 0.6, y - r * 0.6), (x + r * 0.6, y + r * 0.6)], 9, "red", 0.9)
            pline(cv, vm, [(x + r * 0.6, y - r * 0.6), (x - r * 0.6, y + r * 0.6)], 9, "red", 0.9)
        else:
            th = np.linspace(ph, ph + 2.2 * math.pi, 50)
            rr = r * (1 + 0.08 * np.sin(th * 3))
            pline(cv, vm, np.stack([x + rr * np.cos(th), y + 0.7 * rr * np.sin(th)], 1), 8, "red", 0.9)
    rect(cv, V0, 0, 900, W, 1080, "dark", 0.85)
    type_line(cv, V0, 0, 960, 985, 70, "paper", t)


# ------------------------------------------------------------------ 02 我只看见 窗外飞鸟: back view at a barred window
def s_window(cv, t, st):
    st["no"] = 2
    cv.fill("grey")
    ta = tq(t)
    vm = cam(0, 0, 30 + 50 * (t - LY[1][0]) / 2.1, 0)
    rect(cv, vm, 500, 90, 1420, 700, "paper")
    for k in range(7):
        x = 560 + k * 135
        pline(cv, vm, [(x, 90), (x, 700)], 16, "dark")
    pline(cv, vm, [(500, 90), (1420, 90), (1420, 700), (500, 700)], 26, "dark", closed=True)
    # bar shadows across the wall and desk
    for k in range(7):
        x = 560 + k * 135
        poly(cv, vm, [(x - 8, 700), (x + 8, 700), (x + 260, 1300), (x + 230, 1300)], "dark", 0.25)
    text, times = syl(1)
    for i, ti in enumerate(times[4:]):
        dt = ta - ti
        if dt > 0:
            bird(cv, vm, 520 + 380 * dt + i * 60, 300 - 60 * dt + 30 * i, 26, ta, i, "dark")
    student(cv, vm, 960, 690, 330, ta)
    desk(cv, vm, 860)
    rect(cv, V0, 0, 960, W, 1080, "dark", 0.85)
    type_line(cv, V0, 1, 960, 1020, 64, "paper", t)


# ------------------------------------------------------------------ 03 你问啥我也不知道: front view, static, slow push
def s_front(cv, t, st, i=2, g_head=0.0):
    st["no"] = 3
    cv.fill("grey")
    vm = cam(0, 0, 60 * (t - LY[i][0]) / 2.0, 0)
    pline(cv, vm, [(-200, 300), (2200, 300)], 3, "dark", 0.4)
    for k in range(9):
        rect(cv, vm, 120 + k * 200, 60, 200 + k * 200, 250, "dark", 0.12)
    tilt = 0.0
    if int(t * 30) % 23 == 0:
        tilt = 6.0
    student(cv, vm, 960, 450, 380, tq(t), tilt=tilt)
    desk(cv, vm, 820)
    rect(cv, V0, 0, 960, W, 1080, "dark", 0.85)
    type_line(cv, V0, i, 960, 1020, 64, "paper", t)


# ------------------------------------------------------------------ 04 碳酸饮料也要喝到饱: a wall of identical empty cans
def can(cv, v, x, y, s):
    poly(cv, v, rrect(x - 0.36 * s, y - 0.62 * s, x + 0.36 * s, y + 0.62 * s, 0.06 * s), "grey")
    rect(cv, v, x - 0.36 * s, y - 0.1 * s, x + 0.36 * s, y + 0.15 * s, "dark", 0.7)
    poly(cv, v, ell(x, y - 0.62 * s, 0.36 * s, 0.07 * s, 30), "paper")
    pline(cv, v, ell(x, y - 0.62 * s, 0.36 * s, 0.07 * s, 30), 3, "dark", closed=True)


def s_cans(cv, t, st):
    st["no"] = 4
    a0 = LY[3][0]
    cv.fill("paper")
    vm = cam(0, 0, -150 * eio((t - a0) / 2.3), 0)
    n = int((t - a0) / (BEAT / 2)) + 1
    k = 0
    for row in range(5):
        for col in range(11):
            if k >= n * 3:
                break
            x, y = 210 + col * 150, 880 - row * 200
            can(cv, vm, x, y, 150)
            k += 1
    rect(cv, V0, 0, 960, W, 1080, "dark", 0.85)
    type_line(cv, V0, 3, 960, 1020, 64, "paper", t)


# ------------------------------------------------------------------ 05 爸妈又在问 以后咋搞: dark room, light through the door
def s_door(cv, t, st):
    st["no"] = 5
    a0 = LY[4][0]
    cv.fill("dark")
    vm = cam(0, 0, 40 + 60 * (t - a0) / 2.4, 0)
    open_ = 0.6 + 0.4 * eio((t - a0) / 0.6)
    poly(cv, vm, [(1400, 120), (1400 + 120 * open_, 120), (1400 + 120 * open_, 820), (1400, 820)], "paper")
    poly(cv, vm, [(1400, 820), (1400 + 120 * open_, 820), (900 + 900 * open_, 1300), (-200, 1300)], "grey", 0.85)
    # muffled voices: unreadable scribbled bubbles behind the door
    for j, (bx, by, ti) in enumerate(((1640, 260, a0), (1700, 470, a0 + 1.1))):
        if t < ti:
            continue
        u = eo((t - ti) / 0.3)
        poly(cv, vm, rrect(bx - 190 * u, by - 80 * u, bx + 190 * u, by + 80 * u, 40 * u + 1), "grey" if j == 0 else "red", 0.85)
        for q in range(3):
            xs = np.linspace(bx - 150 * u, bx + 150 * u, 40)
            ys = by - 40 + q * 40 + 8 * np.sin(xs * 0.08 + q + tq(t) * 9)
            pline(cv, vm, np.stack([xs, ys], 1), 5, "dark", 0.7 * u)
    student(cv, vm, 640, 560, 360, tq(t), col="dark", head="dark")
    rect(cv, vm, 300, 900, 980, 960, "grey", 0.5)
    rect(cv, V0, 0, 960, W, 1080, "dark", 0.85)
    type_line(cv, V0, 4, 960, 1020, 64, "paper", t)


# ------------------------------------------------------------------ 06 我就假装 信号不好: a phone in the dark, then everything freezes
def s_phone(cv, t, st):
    st["no"] = 6
    a0 = LY[5][0]
    text, times = syl(5)
    fz = times[4]
    if t > fz:
        t_eff = fz + (math.floor((t - fz) * 3) / 3) * 0.08
        st["hold"] = True
    else:
        t_eff = t
    cv.fill("dark")
    vm = cam(0, 0, 60 + 60 * (t_eff - a0) / 2.2, 0)
    glow = np.exp(-(((_gx - 960) / 520) ** 2 + ((_gy - 560) / 420) ** 2)).astype(f32)
    cv.paint(glow, 0, 0, "grey", 0.5)
    student(cv, vm, 960, 470, 380, tq(t_eff), col="dark")
    poly(cv, vm, rrect(820, 760, 1100, 1260, 30), "dark")
    poly(cv, vm, rrect(840, 780, 1080, 1240, 22), "paper")
    nb = 4 - int(c01((t - fz) / 0.6) * 4.99) if t > fz else 4
    for k in range(4):
        rect(cv, vm, 1000 + k * 16, 820 - 10 - 7 * k, 1010 + k * 16, 820, "dark" if k < nb else "grey")
    if t > fz:
        for k in range(8):
            a = k * math.pi / 4
            disc(cv, vm, 960 + 40 * math.cos(a), 960 + 40 * math.sin(a), 5 + k, "dark", 0.7)
    rect(cv, V0, 0, 960, W, 1080, "dark", 0.85)
    type_line(cv, V0, 5, 960, 1020, 64, "paper", t, caret=t < fz)


# ------------------------------------------------------------------ 07 喜欢谁我也不知道: a red heart, scribbled out
def s_heart(cv, t, st):
    st["no"] = 7
    a0 = LY[6][0]
    cv.fill("paper")
    vm = cam(0, 0, 40, 0)
    rect(cv, vm, 300, 0, 1620, 1080, "grey", 0.3)
    pline(cv, vm, heart(960, 470, 560), 12, "red")
    text, times = syl(6)
    tq_ = times[3]
    if t > tq_:
        n = int((tq(t) - tq_) * 60)
        P = []
        for j in range(n):
            P.append((760 + 400 * hsh(j, 1), 260 + 420 * hsh(j, 2)))
        if len(P) > 1:
            pline(cv, vm, np.array(P), 7, "dark", 0.9)
    rect(cv, V0, 0, 960, W, 1080, "dark", 0.85)
    type_line(cv, V0, 6, 960, 1020, 64, "paper", t)


# ------------------------------------------------------------------ 08 通宵熬夜也要吃到饱: monitor glow, day and night flicker
def s_night(cv, t, st):
    st["no"] = 8
    a0 = LY[7][0]
    day = (beat_n(t) % 2) == 0
    cv.fill("dark")
    vm = cam(0, 0, 40 + 40 * (t - a0) / 2.3, 0)
    rect(cv, vm, 1280, 80, 1740, 520, "paper" if day else "dark")
    pline(cv, vm, [(1280, 80), (1740, 80), (1740, 520), (1280, 520)], 14, "grey", closed=True)
    pline(cv, vm, [(1510, 80), (1510, 520)], 10, "grey")
    disc(cv, vm, 420, 260, 100, "paper")
    ring(cv, vm, 420, 260, 100, 8, "grey")
    for (L_, sp, th) in ((55, 2.0, 9), (80, 18.0, 5)):
        a = (tq(t) - a0) * sp * 2 * math.pi - math.pi / 2
        pline(cv, vm, [(420, 260), (420 + L_ * math.cos(a), 260 + L_ * math.sin(a))], th, "dark")
    glow = np.exp(-(((_gx - 960) / 600) ** 2 + ((_gy - 700) / 300) ** 2)).astype(f32)
    cv.paint(glow, 0, 0, "grey", 0.6)
    student(cv, vm, 960, 470, 360, tq(t))
    poly(cv, vm, [(700, 760), (1220, 760), (1260, 1100), (660, 1100)], "dark")
    poly(cv, vm, [(720, 780), (1200, 780), (1230, 1060), (690, 1060)], "paper", 0.85)
    rect(cv, V0, 0, 960, W, 1080, "dark", 0.85)
    type_line(cv, V0, 7, 960, 1020, 64, "paper", t)


# ------------------------------------------------------------------ 09 问我一百遍 / 耸耸肩: copies pile up; the shrug is a production line
def s_hundred(cv, t, st):
    st["no"] = 9
    a0 = LY[8][0]
    cv.fill("dark")
    if t < LY[9][0]:
        n = min(100, 1 + int((t - a0) / (BEAT / 4)) * 3)
        for j in range(min(n, 40)):
            x = 960 + (hsh(j, 1) - 0.5) * 300
            y = 520 + (hsh(j, 2) - 0.5) * 160 - j * 4
            rot = (hsh(j, 3) - 0.5) * 18
            sv = Sub(V0, x, y, rot)
            rect(cv, sv, x - 330, y - 420, x + 330, y + 420, "paper")
            rect(cv, sv, x - 330, y - 420, x + 330, y + 420, "grey", 0.15 + 0.012 * j)
            ch_at(cv, sv, "heavy", 380, "?", x, y, "dark", a=0.4 + 0.6 * (j == min(n, 40) - 1))
        lab = "%03d" % n
        for q, c in enumerate(lab):
            ch_at(cv, V0, "bold", 110, c, 1610 + q * 72, 140, "red")
        type_line(cv, V0, 8, 960, 1020, 64, "paper", t)
    else:
        cv.fill("grey")
        shrug = 0.0
        for ts in (LY[9][0], LY[9][0] + BEAT, LY[9][0] + 2 * BEAT):
            if 0 <= t - ts < 0.45:
                shrug = max(shrug, math.sin(math.pi * (tq(t) - ts) / 0.45))
        buf = np.zeros((H, W), f32)
        for r_ in range(4):
            for c_ in range(9):
                student(None, V0, 120 + c_ * 210, 100 + r_ * 250, 120, t, shrug=shrug, arms="shrug", buf=buf)
        cv.paint(buf, 0, 0, "dark")
        rect(cv, V0, 0, 960, W, 1080, "dark", 0.85)
        type_line(cv, V0, 9, 960, 1020, 64, "paper", t)


# ------------------------------------------------------------------ 10 问我一万遍 / 还是那句: a dense grid of the same silhouette, then black
_SPR = {}


def sprite(cell):
    if cell not in _SPR:
        b = np.zeros((H, W), f32)
        student(None, V0, CX, CY - 0.1 * cell, cell * 0.55, 0.0, buf=b)
        _SPR[cell] = b[int(CY) - cell // 2:int(CY) + cell // 2, int(CX) - cell // 2:int(CX) + cell // 2].copy()
    return _SPR[cell]


def s_tenk(cv, t, st):
    st["no"] = 10
    a0, a1 = LY[10][0], LY[11][0]
    if t < a1:
        cv.fill("grey")
        u = (t - a0) / (a1 - a0)
        cell = int(lerp(120, 30, eio(u)))
        tile = np.tile(sprite(cell), (H // cell + 2, W // cell + 2))[:H, :W]
        cv.paint(tile, 0, 0, "dark")
        n = int(min(10000, 10 ** (2 + 2 * c01(u * 1.15))))
        lab = "%05d" % n
        rect(cv, V0, 1530, 70, 1890, 210, "paper")
        for q, c in enumerate(lab):
            ch_at(cv, V0, "bold", 100, c, 1590 + q * 62, 140, "red")
        rect(cv, V0, 0, 960, W, 1080, "dark", 0.85)
        type_line(cv, V0, 10, 960, 1020, 64, "paper", t)
    else:
        cv.fill("dark")
        type_line(cv, V0, 11, 960, 540, 64, "paper", t)


# ------------------------------------------------------------------ chorus: the same frame, copied again and again
CHORUS = {12: 0.18, 13: 0.32, 14: 0.46, 16: 0.6, 17: 0.74, 18: 0.9}


def s_chorus(cv, t, st, i):
    st["no"] = 11 + sorted(CHORUS).index(i)
    st["gen"] = (CHORUS[i], i)
    cv.fill("grey")
    sk = (hsh(i, 1) - 0.5) * 2.4 * CHORUS[i] * 3
    vm = cam((hsh(i, 2) - 0.5) * 40 * CHORUS[i], (hsh(i, 3) - 0.5) * 30 * CHORUS[i], 60 + 20 * (t - LY[i][0]), sk)
    student(cv, vm, 960, 450, 380, tq(t))
    desk(cv, vm, 820)
    text, times = syl(i)
    xs, _ = line_xs(text, "heavy", 160, 0.12)
    for j, c in enumerate(text):
        if t >= times[j]:
            ch_at(cv, V0, "heavy", 160, c, 960 + xs[j], 945, "red" if (i in (14, 18) and j == 0) else "dark")
    # 还是那句 overlaps the first chorus line
    if i == 12 and t < LY[11][1]:
        type_line(cv, V0, 11, 960, 120, 56, "paper", 99.0, caret=False, a=1 - ss(LY[11][1] - 0.2, LY[11][1], t))
    # tail of 明天再说就好 overlaps the fourth
    if i == 16 and t < LY[15][1]:
        type_line(cv, V0, 15, 960, 120, 48, "paper", 99.0, caret=False, a=1 - ss(LY[15][1] - 0.2, LY[15][1], t))


# ------------------------------------------------------------------ 15 想不通的事情明天再说就好: a tear-off calendar, always the same day
def s_calendar(cv, t, st):
    st["no"] = 14
    st["gen"] = (0.5, 15)
    a0 = LY[15][0]
    cv.fill("grey")
    vm = cam(0, 0, 40, 0)
    X0, Y0, X1, Y1 = 660, 110, 1260, 820
    rect(cv, vm, X0 + 12, Y0 + 12, X1 + 12, Y1 + 12, "dark", 0.6)
    rect(cv, vm, X0, Y0, X1, Y1, "paper")
    rect(cv, vm, X0, Y0, X1, Y0 + 110, "red")
    ch_at(cv, vm, "heavy", 420, "13", (X0 + X1) / 2, 480, "dark")
    nflip = int((t - a0) / BEAT)
    pt = t - (a0 + nflip * BEAT)
    if pt < 0.35:
        u = eo(pt / 0.35)
        card = Canvas()
        rect(card, V0, X0, Y0 + 110, X1, Y1, "paper")
        ch_at(card, V0, "heavy", 420, "13", (X0 + X1) / 2, 480, "dark")
        src = np.array([(X0, Y0 + 110), (X1, Y0 + 110), (X1, Y1), (X0, Y1)], f32)
        dst = np.array([(X0 + 600 * u, Y0 + 110 + 700 * u * u), (X1 + 640 * u, Y0 + 110 + 600 * u * u),
                        (X1 + 700 * u, Y1 + 400 * u * u), (X0 + 640 * u, Y1 + 520 * u * u)], f32)
        cv.over(warp_canvas(card, cv2.getPerspectiveTransform(np.array([vm.pt(*p) for p in src], f32), np.array([vm.pt(*p) for p in dst], f32))))
    rect(cv, V0, 0, 960, W, 1080, "dark", 0.85)
    type_line(cv, V0, 15, 960, 1020, 64, "paper", t)


# ------------------------------------------------------------------ 19 天塌下来也要先让我睡个饱: the ceiling caves in; under the covers
CRACK = []
for _k in range(9):
    P = [(960 + (_r.random() - 0.5) * 200, 40)]
    ang = _r.uniform(0.2, math.pi - 0.2)
    for _s in range(8):
        ang += _r.uniform(-0.5, 0.5)
        x, y = P[-1]
        P.append((x + 110 * math.cos(ang) * (1 if _k % 2 else -1), y + 50 * abs(math.sin(ang)) + 10))
    CRACK.append(np.array(P))
DEBRIS = [(float(_r.uniform(200, 1700)), float(_r.uniform(20, 120)), float(_r.uniform(20, 70)), i) for i in range(30)]


def s_ceiling(cv, t, st):
    st["no"] = 19
    st["gen"] = (0.55, 19)
    a0 = LY[19][0]
    cv.fill("grey")
    vm = cam(0, 0, 40 + 40 * (t - a0) / 2.7, 0)
    rect(cv, vm, -300, -300, 2300, 120, "paper", 0.7)
    u = c01((t - a0) / 1.0)
    for P in CRACK:
        n = max(2, int(len(P) * u))
        pline(cv, vm, P[:n], 6, "dark")
    for (x, y, s, i) in DEBRIS:
        d = tq(t) - (a0 + 0.4 + 0.05 * i)
        if d <= 0:
            continue
        yy = y + 1300 * d * d
        if yy > 1200:
            continue
        a = d * (3 + i % 4)
        P = np.array([(math.cos(a + k * 2.1) * s, math.sin(a + k * 2.1) * s * 0.8) for k in range(3)]) + (x, yy)
        poly(cv, vm, P, "dark")
    # bed, a lump under the blanket, the ? on the pillow
    rect(cv, vm, 360, 840, 1560, 900, "dark")
    poly(cv, vm, rrect(400, 700, 640, 800, 30), "paper")
    ch_at(cv, vm, "heavy", 240, "?", 520, 690, "dark", 1.0, -90)
    xs_ = np.linspace(600, 1560, 40)
    top = 760 - 60 * np.sin((xs_ - 600) / 960 * math.pi)
    poly(cv, vm, np.vstack([np.stack([xs_, top], 1), [(1560, 860), (600, 860)]]), "dark", 0.9)
    rect(cv, V0, 0, 960, W, 1080, "dark", 0.85)
    type_line(cv, V0, 19, 960, 1020, 60, "paper", t)


# ------------------------------------------------------------------ outro: the alarm rings; the copier sweeps again → loop
def s_outro(cv, t, st):
    st["no"] = 20
    if t < 49.4:
        cv.fill("dark")
        vm = cam(0, 0, 40 + 80 * (t - 47.14) / 2.3, 0)
        ring_on = t > 48.2
        shake = (5 * math.sin(t * 90)) if ring_on else 0.0
        disc(cv, vm, 960 + shake, 520, 170, "paper")
        ring(cv, vm, 960 + shake, 520, 170, 14, "grey")
        for sg in (-1, 1):
            disc(cv, vm, 960 + sg * 120 + shake, 360, 50, "grey")
        a = -math.pi / 2 + 0.5
        pline(cv, vm, [(960 + shake, 520), (960 + shake + 70 * math.cos(-math.pi / 2 - 1.0), 520 + 70 * math.sin(-math.pi / 2 - 1.0))], 10, "dark")
        pline(cv, vm, [(960 + shake, 520), (960 + shake + 120 * math.cos(a - 1.6), 520 + 120 * math.sin(a - 1.6))], 6, "dark")
        if ring_on and (t * 8) % 1 < 0.6:
            for k in range(5):
                an = -math.pi / 2 + (k - 2) * 0.4
                pline(cv, vm, [(960 + 230 * math.cos(an), 520 + 230 * math.sin(an)), (960 + 300 * math.cos(an), 520 + 300 * math.sin(an))], 10, "red")
        st["gen"] = (0.3, 20)
    else:
        s_intro(cv, t, st, end_loop=True)
        st["gen"] = (0.0, 20)
    st["fade"] = 1 - ss(51.35, 51.85, t)


# ================================================================== timeline
B = [LY[k][0] for k in range(len(LY))]
SCENES = [(0.0, s_intro), (B[0], s_teacher), (B[1], s_window), (B[2], s_front), (B[3], s_cans), (B[4], s_door),
          (B[5], s_phone), (B[6], s_heart), (B[7], s_night), (B[8], s_hundred), (B[10], s_tenk),
          (B[12], lambda c, t, s: s_chorus(c, t, s, 12)), (B[13], lambda c, t, s: s_chorus(c, t, s, 13)),
          (B[14], lambda c, t, s: s_chorus(c, t, s, 14)), (B[15], s_calendar),
          (B[16], lambda c, t, s: s_chorus(c, t, s, 16)), (B[17], lambda c, t, s: s_chorus(c, t, s, 17)),
          (B[18], lambda c, t, s: s_chorus(c, t, s, 18)), (B[19], s_ceiling), (LY[19][1], s_outro)]
HITS = [(B[k], 0.12) for k in (12, 13, 14, 16, 17, 18)] + [(LY[11][0], 0.08)]


def render(fidx):
    t = fidx / FPS
    st = {"no": 0}
    k = 0
    for i, (t0, _) in enumerate(SCENES):
        if t >= t0:
            k = i
    cv = Canvas()
    SCENES[k][1](cv, t, st)
    # a hard flicker on every scene change: one frame of black
    if 0 <= t - SCENES[k][0] < 1 / FPS and k > 0:
        cv.fill("dark", 0.85)
    ui(cv, t, st, CREDIT, a=ss(0.3, 0.8, t) * (1 - ss(51.3, 51.85, t)))
    st["mis"] = (-3, 2)
    img = finish(cv, fidx, t, st, HITS).astype(f32) / 255.0
    g, gen = st.get("gen", (0.08, 0))
    img = degrade(img, g + 0.04 * math.sin(t * 13) * (g > 0), gen)
    # scanner lines and a faint 50 Hz flicker over everything
    img *= 1 - 0.035 * (np.sin(_gy[..., None] * 0.9 + t * 40) > 0.97)
    img *= 1 - 0.03 * hsh(fidx, 77)
    return (np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)


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
               "-c:v", "libx264", "-preset", "slow", "-crf", "23", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
               "-c:a", "aac", "-b:a", "320k", out]
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        with Pool(4) as pool:
            for i, fr in enumerate(pool.imap(render, range(NF), chunksize=2)):
                p.stdin.write(fr.tobytes())
                if i % 120 == 0:
                    print("frame", i, flush=True)
        p.stdin.close()
        p.wait()
        print("done", out)
