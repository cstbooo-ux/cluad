#!/usr/bin/env python3
"""他叫我随便做 — 9:16 pixel short, rendered entirely from code.
Canvas 360x640, upscaled 3x (nearest) to 1080x1920. Audio is synthesised chiptune.
usage: make.py [out.mp4] [--preview t1,t2,...]
"""
import math, random, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H, FPS, DUR = 360, 640, 20, 62.0
FONT = ImageFont.truetype('/usr/share/fonts/opentype/unifont/unifont.otf', 16)

INK = (62, 40, 74); WHITE = (255, 255, 255); CREAM = (255, 244, 214)
PINK = (255, 176, 205); HOT = (255, 120, 170); MINT = (168, 230, 207)
SKY = (150, 215, 255); YEL = (255, 224, 102); ORANGE = (255, 170, 90)
RED = (255, 107, 107); GREEN = (96, 192, 112); BROWN = (160, 108, 76)
LAV = (225, 214, 255); NIGHT = (43, 45, 91); PEACH = (255, 218, 190)


# ---------------------------------------------------------------- helpers
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def lerp(a, b, t): return a + (b - a) * t
def lerpc(c1, c2, t): return tuple(int(lerp(a, b, t)) for a, b in zip(c1, c2))
def ease_out(t): t = clamp(t); return 1 - (1 - t) ** 3


def bounce(t):
    t = clamp(t)
    if t < 1 / 2.75: return 7.5625 * t * t
    if t < 2 / 2.75: t -= 1.5 / 2.75; return 7.5625 * t * t + .75
    if t < 2.5 / 2.75: t -= 2.25 / 2.75; return 7.5625 * t * t + .9375
    t -= 2.625 / 2.75; return 7.5625 * t * t + .984375


def fall(t, te, dist=120, dur=0.5):
    """vertical offset (<=0, above rest) of an object dropped at te; None before."""
    if t < te: return None
    return -dist * (1 - bounce((t - te) / dur))


def text_img(s, col, shadow=None):
    w = int(FONT.getlength(s)) + 2
    im = Image.new('RGBA', (w, 19), (0, 0, 0, 0)); d = ImageDraw.Draw(im); d.fontmode = '1'
    if shadow: d.text((1, 1), s, font=FONT, fill=shadow)
    d.text((0, 0), s, font=FONT, fill=col)
    return im


def put(img, s, x, y, col=INK, scale=1, anchor='l', shadow=None):
    im = text_img(s, col, shadow)
    if scale != 1: im = im.resize((int(im.width * scale), int(im.height * scale)), Image.NEAREST)
    if anchor == 'm': x -= im.width // 2
    img.paste(im, (int(x), int(y)), im)


def box(d, b, fill=WHITE, r=5, w=2, sh=True):
    x0, y0, x1, y1 = b
    if sh: d.rounded_rectangle((x0 + 3, y0 + 3, x1 + 3, y1 + 3), radius=r, fill=(0, 0, 0, 40))
    d.rounded_rectangle(b, radius=r, fill=fill, outline=INK, width=w)


def chip(img, d, s, x, y, fill=YEL, scale=1):
    wd = int(FONT.getlength(s) * scale) + 14
    box(d, (x, y, x + wd, y + int(19 * scale) + 8), fill=fill)
    put(img, s, x + 7, y + 4, INK, scale)


def sparkle(d, x, y, r, col=YEL):
    d.line((x - r, y, x + r, y), fill=col, width=1); d.line((x, y - r, x, y + r), fill=col, width=1)
    d.rectangle((x - 1, y - 1, x + 1, y + 1), fill=WHITE)


def heart(d, x, y, s=3, col=HOT):
    for dx in (-s, s):
        d.ellipse((x + dx - s, y - s, x + dx + s, y + s), fill=col)
    d.polygon([(x - 2 * s, y + 1), (x + 2 * s, y + 1), (x, y + 3 * s)], fill=col)


def star5(d, x, y, r, col=YEL):
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5; rr = r if i % 2 == 0 else r * 0.45
        pts.append((x + rr * math.cos(a), y + rr * math.sin(a)))
    d.polygon(pts, fill=col, outline=INK)


def bg_dots(d, base, dot, t, sp=10, step=18):
    d.rectangle((0, 0, W, H), fill=base)
    o = int(t * sp) % step
    for y in range(-step, H + step, step):
        for x in range(-step, W + step, step):
            xx, yy = x + o + (step // 2 if (y // step) % 2 else 0), y + o
            d.rectangle((xx, yy, xx + 2, yy + 2), fill=dot)


def vgrad(d, c1, c2, y0=0, y1=H, band=6):
    for y in range(y0, y1, band):
        d.rectangle((0, y, W, y + band), fill=lerpc(c1, c2, (y - y0) / max(1, y1 - y0)))


# ---------------------------------------------------------------- characters
def mochi(d, cx, by, face='n', sq=0.0, arms=0.0, k=1.0, hat=None, t=0, tilt=0):
    w = int(48 * k * (1 + .18 * sq)); h = int(40 * k * (1 - .22 * sq))
    cx += tilt
    d.ellipse((cx - w // 2 - 3, by - 3, cx + w // 2 + 3, by + 4), fill=(0, 0, 0, 45))
    for fx in (-9, 9):
        d.ellipse((cx + int(fx * k) - 5, by - 5, cx + int(fx * k) + 5, by + 2), fill=PINK, outline=INK)
    ay = by - h * .45
    for sgn in (-1, 1):
        d.ellipse((cx + sgn * (w // 2 - 1) - 4, ay - arms * 14 - 4, cx + sgn * (w // 2 - 1) + 4, ay - arms * 14 + 4),
                  fill=WHITE, outline=INK)
    d.ellipse((cx - w // 2, by - h, cx + w // 2, by), fill=WHITE, outline=INK, width=2)
    # leaf
    d.ellipse((cx - 2, by - h - 9, cx + 8, by - h + 1), fill=GREEN, outline=INK)
    d.line((cx, by - h + 1, cx, by - h - 3), fill=INK)
    cy = int(by - h * .45); ex = int(10 * k)
    d.ellipse((cx - ex - 12, cy + 1, cx - ex - 4, cy + 8), fill=PINK)
    d.ellipse((cx + ex + 4, cy + 1, cx + ex + 12, cy + 8), fill=PINK)
    blink = (t % 3.2) < 0.12
    if face in ('n', 'think') and blink: face = 'sleep'
    for sgn in (-1, 1):
        ex_ = cx + sgn * ex
        if face == 'n':
            d.rectangle((ex_ - 1, cy - 4, ex_ + 1, cy + 2), fill=INK)
            d.point((ex_ + 1, cy - 4), fill=WHITE)
        elif face == 'think':
            d.rectangle((ex_ - 1, cy - 6, ex_ + 1, cy - 3), fill=INK)
        elif face == 'panic':
            for i in range(4):
                d.point((ex_ - sgn * (3 - i) if True else 0, cy - 4 + i if sgn < 0 else cy - 4 + i), fill=INK)
            d.line((ex_ - sgn * 4, cy - 5, ex_ + sgn * 1, cy - 2), fill=INK)
            d.line((ex_ - sgn * 4, cy + 1, ex_ + sgn * 1, cy - 2), fill=INK)
        elif face == 'happy':
            d.line((ex_ - 3, cy, ex_, cy - 4), fill=INK); d.line((ex_, cy - 4, ex_ + 3, cy), fill=INK)
        elif face == 'sleep':
            d.line((ex_ - 3, cy - 1, ex_ + 3, cy - 1), fill=INK)
        elif face == 'wow':
            d.ellipse((ex_ - 4, cy - 6, ex_ + 4, cy + 2), fill=INK); d.rectangle((ex_ - 2, cy - 5, ex_, cy - 3), fill=WHITE)
    my = cy + 6
    if face in ('n', 'think'):
        d.line((cx - 2, my, cx, my + 1), fill=INK); d.line((cx, my + 1, cx + 2, my), fill=INK)
    elif face == 'panic':
        d.ellipse((cx - 3, my - 1, cx + 3, my + 7), fill=INK); d.rectangle((cx - 1, my + 4, cx + 1, my + 6), fill=HOT)
        d.ellipse((cx + w // 2 - 6, by - h - 2, cx + w // 2, by - h + 8), fill=SKY, outline=INK)
    elif face == 'happy':
        d.pieslice((cx - 5, my - 4, cx + 5, my + 6), 0, 180, fill=INK)
        d.rectangle((cx - 2, my + 2, cx + 2, my + 3), fill=HOT)
    elif face == 'sleep':
        d.line((cx - 2, my, cx + 2, my), fill=INK)
    elif face == 'wow':
        d.ellipse((cx - 3, my - 1, cx + 3, my + 5), fill=INK)
    if hat == 'chef':
        hy = by - h + 2
        d.rectangle((cx - 13, hy - 8, cx + 13, hy + 2), fill=WHITE, outline=INK)
        for hx in (-12, 0, 12):
            d.ellipse((cx + hx - 9, hy - 24, cx + hx + 9, hy - 6), fill=WHITE, outline=INK)
        d.rectangle((cx - 12, hy - 8, cx + 12, hy - 2), fill=WHITE)
    elif hat == 'cap':
        hy = by - h + 3
        d.pieslice((cx - 20, hy - 22, cx + 20, hy + 10), 180, 360, fill=SKY, outline=INK)
        d.rectangle((cx - 22, hy - 2, cx + 22, hy + 2), fill=SKY, outline=INK)
    elif hat == 'night':
        hy = by - h + 4
        d.polygon([(cx - 18, hy), (cx + 18, hy), (cx + 24, hy - 28)], fill=LAV, outline=INK)
        d.ellipse((cx + 20, hy - 34, cx + 30, hy - 24), fill=WHITE, outline=INK)


def cat(d, cx, by, pose='sit', eyes='o', k=1.0, tail=0.0, ground=True):
    O = (255, 176, 96); Dk = (226, 128, 60); L = (255, 238, 205)
    S = lambda v: int(v * k)
    if ground:
        d.ellipse((cx - S(34), by - 3, cx + S(34), by + 5), fill=(0, 0, 0, 45))
    if pose == 'sit':
        tx = cx + S(18); ty = by - S(8)
        pts = [(tx, ty), (tx + S(14), ty - S(6) - tail * S(8)), (tx + S(18), ty - S(24) - tail * S(10)), (tx + S(10), ty - S(34))]
        d.line(pts, fill=INK, width=S(7), joint='curve'); d.line(pts, fill=O, width=S(4), joint='curve')
        d.ellipse((cx - S(20), by - S(36), cx + S(20), by), fill=O, outline=INK, width=2)
        d.ellipse((cx - S(11), by - S(28), cx + S(11), by - S(2)), fill=L)
        for sx in (-8, 8):
            d.ellipse((cx + S(sx) - S(6), by - S(7), cx + S(sx) + S(6), by + 1), fill=L, outline=INK)
        hy = by - S(50)
    else:  # loaf
        d.ellipse((cx - S(36), by - S(30), cx + S(36), by), fill=O, outline=INK, width=2)
        for sx in (8, 18, 28):
            d.line((cx + S(sx), by - S(29), cx + S(sx - 2), by - S(21)), fill=Dk, width=2)
        pts = [(cx + S(32), by - S(8)), (cx + S(12), by - S(2)), (cx - S(14), by - S(3))]
        d.line(pts, fill=INK, width=S(7), joint='curve'); d.line(pts, fill=O, width=S(4), joint='curve')
        hy = by - S(22); cx = cx - S(8)
    # head
    hw, hh = S(27), S(21)
    for sgn in (-1, 1):
        d.polygon([(cx + sgn * S(24), hy - S(8)), (cx + sgn * S(23), hy - hh - S(14)), (cx + sgn * S(7), hy - hh + S(2))], fill=O, outline=INK)
        d.polygon([(cx + sgn * S(21), hy - S(12)), (cx + sgn * S(21), hy - hh - S(7)), (cx + sgn * S(11), hy - hh + S(1))], fill=PINK)
    d.ellipse((cx - hw, hy - hh, cx + hw, hy + hh), fill=O, outline=INK, width=2)
    for sx in (-5, 0, 5):
        d.line((cx + S(sx), hy - hh + 2, cx + S(sx), hy - hh + S(8)), fill=Dk, width=2 if sx == 0 else 1)
    for sgn in (-1, 1):
        ex = cx + sgn * S(12); ey = hy + S(2)
        if eyes == 'o':
            d.rectangle((ex - 2, ey - 4, ex + 2, ey + 3), fill=INK); d.rectangle((ex, ey - 4, ex + 1, ey - 2), fill=WHITE)
        elif eyes == 'c':
            d.arc((ex - 4, ey - 4, ex + 4, ey + 3), 20, 160, fill=INK, width=2)
        elif eyes == 'h':
            d.line((ex - 4, ey + 1, ex, ey - 3), fill=INK, width=2); d.line((ex, ey - 3, ex + 4, ey + 1), fill=INK, width=2)
        elif eyes == 'w':
            d.ellipse((ex - 4, ey - 5, ex + 4, ey + 4), fill=WHITE, outline=INK); d.ellipse((ex - 1, ey - 2, ex + 1, ey + 1), fill=INK)
        d.ellipse((cx + sgn * S(19) - 4, hy + S(8) - 2, cx + sgn * S(19) + 4, hy + S(8) + 3), fill=PINK)
        for wy in (-2, 3):
            d.line((cx + sgn * S(22), hy + S(6) + wy, cx + sgn * S(36), hy + S(4) + wy * 2), fill=INK)
    d.polygon([(cx - 3, hy + S(7)), (cx + 3, hy + S(7)), (cx, hy + S(11))], fill=HOT, outline=INK)
    d.arc((cx - 6, hy + S(9), cx, hy + S(16)), 0, 180, fill=INK); d.arc((cx, hy + S(9), cx + 6, hy + S(16)), 0, 180, fill=INK)


def bowl(d, cx, base, T, k=1.0):
    """T: dict of drop offsets for parts (None = hidden)."""
    S = lambda v: int(v * k)
    by = base - S(44); yr = by - S(12)
    o = T.get('bowl')
    if o is None: return
    by += int(o); yr += int(o)
    d.ellipse((cx - S(46), base - 4, cx + S(46), base + 4), fill=(0, 0, 0, 45))
    d.rectangle((cx - S(22), by + S(34), cx + S(22), by + S(44)), fill=RED, outline=INK)
    d.pieslice((cx - S(50), by - S(62), cx + S(50), by + S(38)), 0, 180, fill=WHITE, outline=INK, width=2)
    d.pieslice((cx - S(50), by - S(62), cx + S(50), by + S(38)), 25, 155, fill=(255, 235, 235))
    d.pieslice((cx - S(50), by - S(62), cx + S(50), by + S(38)), 0, 180, outline=INK, width=2)
    for i in range(-3, 4):  # dots
        d.ellipse((cx + i * S(11) - 2, by + S(9) + (i % 2) * S(7), cx + i * S(11) + 2, by + S(13) + (i % 2) * S(7)), fill=RED)
    d.ellipse((cx - S(50), yr - S(9), cx + S(50), yr + S(9)), fill=CREAM, outline=INK, width=2)
    if T.get('soup') is not None:
        r = clamp(T['soup'])
        d.ellipse((cx - S(46 * r), yr - S(7 * r), cx + S(46 * r), yr + S(7 * r)), fill=(214, 150, 80))
        d.arc((cx - S(30), yr - S(4), cx - S(8), yr + S(4)), 0, 180, fill=(240, 190, 110))
    o = T.get('noodle')
    if o is not None:
        o = int(o); nx0, nx1 = cx - S(34), cx + S(34)
        d.ellipse((nx0, yr - S(26) + o, nx1, yr + S(6) + o), fill=YEL, outline=INK, width=2)
        for i in range(5):
            yy = yr - S(20) + i * S(5) + o
            d.arc((nx0 + 3, yy - 4, nx1 - 3, yy + 8), 200 + (i % 2) * 20, 340, fill=(214, 170, 60))
    o = T.get('naruto')
    if o is not None:
        x, y = cx - S(22), yr - S(8) + int(o)
        d.ellipse((x - S(12), y - S(8), x + S(12), y + S(8)), fill=WHITE, outline=INK)
        d.arc((x - S(7), y - S(5), x + S(7), y + S(5)), 30, 300, fill=HOT, width=2)
        d.ellipse((x - 2, y - 2, x + 2, y + 2), fill=HOT)
    o = T.get('egg')
    if o is not None:
        x, y = cx + S(20), yr - S(6) + int(o)
        d.ellipse((x - S(15), y - S(10), x + S(15), y + S(10)), fill=WHITE, outline=INK)
        d.ellipse((x - S(6), y - S(5), x + S(6), y + S(5)), fill=ORANGE, outline=INK)
        d.rectangle((x - 3, y - 3, x - 2, y - 2), fill=YEL)
    o = T.get('nori')
    if o is not None:
        x, y = cx + S(34), yr - S(22) + int(o)
        d.polygon([(x - S(6), y + S(20)), (x + S(8), y + S(18)), (x + S(10), y - S(8)), (x - S(4), y - S(10))], fill=(40, 70, 56), outline=INK)
    for i, (dx, dy) in enumerate([(-8, -14), (4, -10), (14, -16), (-18, -4), (24, -6), (-2, -2)]):
        o = T.get(f'sc{i}')
        if o is not None:
            x, y = cx + S(dx), yr + S(dy) + int(o)
            d.rectangle((x - 2, y - 1, x + 2, y + 1), fill=GREEN, outline=INK)


def flower_plant(d, cx, ptop, grow, bloom, t=0, k=1.0, face=True):
    """grow 0..1 stem, bloom 0..1 petals."""
    S = lambda v: int(v * k)
    if grow <= 0: return
    hgt = int(S(150) * grow)
    sway = int(math.sin(t * 2) * 2 * grow)
    top = (cx + sway, ptop - hgt)
    d.line([(cx, ptop), (cx + sway // 2, ptop - hgt // 2), top], fill=INK, width=7)
    d.line([(cx, ptop), (cx + sway // 2, ptop - hgt // 2), top], fill=GREEN, width=4)
    for frac, side in ((0.35, -1), (0.6, 1)):
        if grow > frac:
            g = clamp((grow - frac) * 4)
            lx, ly = cx + sway // 2, ptop - int(hgt * frac)
            L = int(S(22) * g)
            d.ellipse((lx + (0 if side > 0 else -L), ly - S(7) * g, lx + (L if side > 0 else 0), ly + S(7) * g), fill=GREEN, outline=INK)
    if bloom <= 0 and grow >= 0.98:
        d.ellipse((top[0] - 6, top[1] - 8, top[0] + 6, top[1] + 6), fill=PINK, outline=INK)
        d.polygon([(top[0] - 6, top[1] + 4), (top[0], top[1] + 10), (top[0] + 6, top[1] + 4)], fill=GREEN, outline=INK)
    if bloom > 0:
        R = int(S(17) * bloom); pr = int(S(11) * bloom)
        for i in range(8):
            a = i * math.pi / 4 + t * .3
            px, py = top[0] + math.cos(a) * R, top[1] + math.sin(a) * R
            d.ellipse((px - pr, py - pr, px + pr, py + pr), fill=PINK if i % 2 == 0 else (255, 150, 190), outline=INK)
        cr = int(S(12) * bloom)
        d.ellipse((top[0] - cr, top[1] - cr, top[0] + cr, top[1] + cr), fill=YEL, outline=INK, width=2)
        if face and bloom > .6:
            for sx in (-4, 4): d.rectangle((top[0] + sx - 1, top[1] - 3, top[0] + sx, top[1]), fill=INK)
            d.arc((top[0] - 4, top[1] - 1, top[0] + 4, top[1] + 5), 10, 170, fill=INK)
            for sx in (-8, 8): d.ellipse((top[0] + sx - 2, top[1] + 1, top[0] + sx + 2, top[1] + 4), fill=PINK)
    return top


def pot(d, cx, top, k=1.0):
    S = lambda v: int(v * k)
    d.ellipse((cx - S(40), top + S(54), cx + S(40), top + S(62)), fill=(0, 0, 0, 40))
    d.polygon([(cx - S(34), top), (cx + S(34), top), (cx + S(26), top + S(58)), (cx - S(26), top + S(58))], fill=(236, 130, 100), outline=INK)
    d.rectangle((cx - S(38), top - S(8), cx + S(38), top + S(4)), fill=(250, 150, 118), outline=INK, width=2)
    d.rectangle((cx - S(30), top - S(5), cx + S(30), top - S(3)), fill=(120, 80, 60))
    for sx in (-14, 0, 14):
        d.rectangle((cx + S(sx) - 1, top + S(20), cx + S(sx) + 1, top + S(22)), fill=(255, 190, 160))


def rocket(d, cx, by, k=1.0, flame=0.0, win=None, t=0):
    S = lambda v: int(v * k)
    right = []
    for i in range(9):
        a = i * (math.pi / 2) / 8
        right.append((S(22) * math.sin(a), -S(124) + S(52) * (1 - math.cos(a))))
    pts = [(cx + x, by + y) for x, y in right] + [(cx + S(22), by - S(14))] + [(cx - S(22), by - S(14))] + [(cx - x, by + y) for x, y in reversed(right)]
    # fins
    for sgn in (-1, 1):
        d.polygon([(cx + sgn * S(21), by - S(52)), (cx + sgn * S(42), by - S(8)), (cx + sgn * S(21), by - S(18))], fill=RED, outline=INK)
    # flame
    if flame > 0:
        f = flame * (1 + .25 * math.sin(t * 40))
        d.polygon([(cx - S(15), by - S(14)), (cx + S(15), by - S(14)), (cx + S(6), by + S(30 * f)), (cx, by + S(60 * f)), (cx - S(6), by + S(30 * f))], fill=ORANGE, outline=INK)
        d.polygon([(cx - S(9), by - S(14)), (cx + S(9), by - S(14)), (cx, by + S(38 * f))], fill=YEL)
        d.polygon([(cx - S(4), by - S(14)), (cx + S(4), by - S(14)), (cx, by + S(18 * f))], fill=WHITE)
    d.polygon(pts, fill=WHITE, outline=INK)
    d.line(pts + [pts[0]], fill=INK, width=2)
    cap = [(cx + x, by + y) for x, y in right if y < -S(98)]
    cap = cap + [(cx - (x - cx), y) for x, y in reversed(cap)]
    d.polygon(cap, fill=RED, outline=INK)
    d.rectangle((cx - S(21), by - S(38), cx + S(21), by - S(30)), fill=RED, outline=INK)
    d.rectangle((cx - S(21), by - S(30), cx + S(21), by - S(24)), fill=(230, 230, 245))
    wy = by - S(74)
    d.ellipse((cx - S(14), wy - S(14), cx + S(14), wy + S(14)), fill=(120, 200, 255), outline=INK, width=2)
    if win: win(cx, wy)
    d.rectangle((cx - S(10), wy - S(10), cx - S(8), wy - S(6)), fill=WHITE)


# ---------------------------------------------------------------- script data
SUBS = [
    (4.5, 6.0, ["一分钟小视频，开始~", "(๑>◡<๑)"]),
    (6.4, 8.4, ["「随便」到底是什么？", "(;°Д°)"]),
    (8.6, 10.0, ["想不出来……", "交给骰子吧！"]),
    (11.9, 12.95, ["掷出了 4 ！", "那就做 4 个随便~"]),
    (13.4, 15.0, ["随便 #1：一碗面", "(๑´▽`๑)"]),
    (15.2, 17.6, ["先来点汤 再下面条~"]),
    (17.7, 20.2, ["加蛋 加鱼板 加葱花", "(｡･ω･｡)"]),
    (20.5, 22.9, ["好香呀！做好啦~", "\\(◕ᴗ◕✿)/"]),
    (23.4, 25.2, ["随便 #2：一朵花", "(◕‿◕✿)"]),
    (25.4, 27.4, ["浇点水 然后……", "等一等~"]),
    (27.8, 30.0, ["日升日落 一天又一天", "( ˘ω˘ )zzZ"]),
    (30.6, 33.0, ["开花啦！！", "\\(✿^▽^)/"]),
    (33.4, 35.2, ["随便 #3：一只猫", "(=^･ω･^=)"]),
    (36.0, 38.0, ["咦 箱子里有东西……", "(´･ω･`)?"]),
    (38.6, 41.0, ["喵~ 追毛线球！", "ε=ε=┌(=^･ω･^=)┘"]),
    (41.4, 43.0, ["玩累了 呼噜噜", "(=-ω-=)zzZ"]),
    (43.4, 45.4, ["随便 #4：去太空", "(๑•̀ㅂ•́)و✧"]),
    (45.6, 47.2, ["猫：？？？", "我为什么在这里"]),
    (49.2, 51.5, ["出发咯~ \\(◕ᴗ◕)/", "目标：随便哪颗星星"]),
    (51.8, 53.0, ["猫：喵？", "(´･_･`)"]),
    (54.4, 56.8, ["你说随便……", "我就真的随便做啦~"]),
    (57.1, 59.5, ["下次想看什么？", "继续叫我随便做吧 (๑>◡<๑)"]),
]
CPS = 14
BOUNDS = [6.0, 13.0, 23.0, 33.0, 43.0, 53.0]

SF = []  # (time, kind, *args)
def sfx(t, kind, *a): SF.append((t, kind) + a)

for t0, t1, lines in SUBS:
    n = 0
    for ch in "".join(lines):
        if ch.strip():
            sfx(t0 + n / CPS, 'blip', 880 if n % 2 else 988, 0.05)
        n += 1
for b in BOUNDS: sfx(b - 0.25, 'whoosh', 0.5)


def tween_sub(t):
    for t0, t1, lines in SUBS:
        if t0 <= t < t1: return t0, lines
    return None


# ---- scene event timings (global time)
# S0
CH1, CH2, TITLE = 0.5, 2.2, 3.7
sfx(0.5, 'pop', 600); sfx(2.2, 'pop', 700); sfx(3.7, 'thump'); sfx(3.75, 'sparkle')
for i in range(10): sfx(0.9 + i * .1, 'blip', 700 + i * 20, .04)
for i in range(10): sfx(2.6 + i * .1, 'blip', 760 + i * 20, .04)
# S1
sfx(6.5, 'pop', 400); sfx(7.3, 'pop', 500); sfx(8.2, 'pop', 300)
for i in range(17): sfx(9.9 + i * .1, 'rattle')
sfx(11.8, 'ding'); sfx(11.85, 'sparkle')
# S2 noodles
N0 = 13.0
for te, f in ((14.0, 330), (15.4, 300), (16.2, 380), (17.0, 340), (17.5, 400), (18.0, 360)): sfx(te, 'plop', f)
sfx(14.9, 'splash')
for i in range(6): sfx(18.5 + i * .12, 'blip', 1400 + i * 100, .04)
sfx(20.6, 'twinkle'); sfx(21.0, 'ding')
# S3 flower
sfx(24.3, 'plop', 420)
for i in range(8): sfx(25.0 + i * .18, 'drip')
sfx(26.5, 'twinkle')
sfx(30.9, 'twinkle'); sfx(31.1, 'ding'); sfx(31.6, 'pop', 900); sfx(32.0, 'pop', 1000)
# S4 cat
sfx(34.0, 'plop', 200); sfx(35.0, 'rattle'); sfx(35.15, 'rattle'); sfx(35.3, 'rattle')
sfx(36.6, 'pop', 500); sfx(37.4, 'pop', 700); sfx(37.9, 'boing')
sfx(38.7, 'plop', 500); sfx(39.6, 'boing'); sfx(40.2, 'boing'); sfx(40.8, 'meow')
sfx(41.5, 'yawn')
# S5 space
for tt, f in ((45.8, 520), (46.8, 520), (47.8, 520)): sfx(tt, 'beep', f)
sfx(48.8, 'beep', 1040, .5); sfx(48.8, 'rumble', 3.0); sfx(51.5, 'twinkle')
# S6
for i, te in enumerate((53.4, 54.0, 54.6, 55.2)): sfx(te, 'pop', 600 + i * 120)
sfx(56.0, 'ding'); sfx(56.05, 'sparkle'); sfx(59.6, 'twinkle')


# ---------------------------------------------------------------- scenes
def scene0(img, d, t):
    bg_dots(d, CREAM, PINK, t)
    # avatar + chat bubbles
    def chat(y, s, t0):
        if t < t0: return
        p = bounce((t - t0) / .35)
        n = int((t - t0 - .3) * 10) if t - t0 > .3 else 0
        wd = int(FONT.getlength(s)) + 22
        yy = int(y - (1 - p) * 24)
        box(d, (62, yy, 62 + wd, yy + 36), fill=WHITE)
        d.polygon([(62, yy + 10), (52, yy + 17), (62, yy + 22)], fill=WHITE)
        d.line([(62, yy + 11), (52, yy + 17), (62, yy + 22)], fill=INK, width=2)
        d.rectangle((63, yy + 11, 65, yy + 21), fill=WHITE)
        put(img, s[:max(0, n)], 73, yy + 9, INK)
        # avatar
        ax, ay = 14, yy + 2
        d.rectangle((ax, ay, ax + 34, ay + 34), fill=SKY, outline=INK, width=2)
        d.rectangle((ax + 9, ay + 12, ax + 11, ay + 17), fill=INK); d.rectangle((ax + 22, ay + 12, ax + 24, ay + 17), fill=INK)
        d.line((ax + 11, ay + 24, ax + 22, ay + 24), fill=INK)
    chat(70, "你随便做个小视频吧~", CH1)
    chat(130, "什么都行 随便！", CH2)
    mt = t
    face = 'n' if t < 2.4 else ('wow' if t < TITLE else 'happy')
    jump = abs(math.sin(t * 5)) * 6 if t > TITLE else 0
    if 2.2 < t < 2.7: jump = 8 * math.sin((t - 2.2) / .5 * math.pi)
    mochi(d, 180, 505 - int(jump), face, sq=(0.4 if jump < 1 and t > TITLE else 0), arms=(1 if t > TITLE else 0), t=t)
    if 2.3 < t < 3.2: put(img, "!", 215, 440 - int((t - 2.3) * 15), RED, 3)
    if t > TITLE:
        p = bounce((t - TITLE) / .5)
        y = int(260 - (1 - p) * 220)
        flash = t < TITLE + .12
        if flash: d.rectangle((0, 0, W, H), fill=WHITE)
        put(img, "他叫我随便做", 180 + 4, y + 4, HOT, 3, 'm')
        put(img, "他叫我随便做", 180, y, INK, 3, 'm')
        if t > TITLE + .5:
            for i, (sx, sy) in enumerate([(40, 250), (320, 280), (60, 340), (300, 220)]):
                if int(t * 6 + i) % 3 == 0: sparkle(d, sx, sy, 6)
            put(img, "- 随便做的小视频 -", 180, y + 62, INK, 1, 'm')


def scene1(img, d, t):  # t local 0..7
    g = t + 6
    bg_dots(d, LAV, (200, 185, 245), g, 6)
    shake = int(math.sin(g * 40) * 3) if 0.4 < t < 3.6 else 0
    face = 'panic' if t < 3.7 else ('think' if t < 5.8 else 'happy')
    mochi(d, 180, 505, face, sq=0.2 * math.sin(g * 14) if t < 3.7 else 0, arms=(1 if t < 3.5 else 0), t=g, tilt=shake)
    # thought cloud
    if g > 6.4:
        p = bounce((g - 6.4) / .4)
        cy = 160
        for cx_, cy_, r in ((130, cy, 34), (180, cy - 18, 42), (232, cy, 34), (180, cy + 12, 38)):
            d.ellipse((cx_ - r * p, cy_ - r * p, cx_ + r * p, cy_ + r * p), fill=WHITE, outline=INK, width=2)
        for cx_, cy_, r in ((130, cy, 34), (180, cy - 18, 42), (232, cy, 34), (180, cy + 12, 38)):
            d.ellipse((cx_ - r * p + 2, cy_ - r * p + 2, cx_ + r * p - 2, cy_ + r * p - 2), fill=WHITE)
        for (px, py, r) in ((170, 480, 4), (155, 505, 6)):
            pass
        d.ellipse((168, 232, 176, 240), fill=WHITE, outline=INK); d.ellipse((160, 252, 172, 264), fill=WHITE, outline=INK)
        put(img, "随便？", 180, 140, INK, 2, 'm')
    if 0.8 < t < 4.0:
        for i in range(6):
            a = g * 3 + i * math.pi / 3
            x = 180 + math.cos(a) * 110; y = 330 + math.sin(a) * 40 + math.sin(g * 5 + i) * 6
            put(img, "?", x - 8, y - 16, (HOT, SKY, YEL, MINT, ORANGE, RED)[i], 2)
    if 3.9 < t < 7:  # dice
        dd = fall(g, 9.9, 260, .6)
        if dd is not None:
            lt = g - 9.9
            if g < 11.8:
                val = 1 + int(g * 14) % 6
                rot = (math.sin(g * 30) * 4, math.cos(g * 26) * 4)
            else:
                val = 4; rot = (0, 0)
            cx, cy = 180 + int(rot[0]), 330 + int(dd) + int(rot[1])
            s = 38
            d.rectangle((cx - s + 4, cy - s + 4, cx + s + 4, cy + s + 4), fill=(0, 0, 0, 50))
            d.rounded_rectangle((cx - s, cy - s, cx + s, cy + s), radius=10, fill=WHITE, outline=INK, width=3)
            pips = {1: [(0, 0)], 2: [(-1, -1), (1, 1)], 3: [(-1, -1), (0, 0), (1, 1)], 4: [(-1, -1), (1, -1), (-1, 1), (1, 1)],
                    5: [(-1, -1), (1, -1), (0, 0), (-1, 1), (1, 1)], 6: [(-1, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (1, 1)]}[val]
            for px, py in pips:
                d.ellipse((cx + px * 20 - 7, cy + py * 20 - 7, cx + px * 20 + 7, cy + py * 20 + 7), fill=RED if val == 1 or val == 4 else INK, outline=INK)
        if g > 11.8:
            p = bounce((g - 11.8) / .4)
            put(img, "x4", 180 + 3, 400 + 3 - int((1 - p) * 40), HOT, 4, 'm')
            put(img, "x4", 180, 400 - int((1 - p) * 40), INK, 4, 'm')
            for i in range(8):
                a = i * math.pi / 4 + g
                r = 70 + (g - 11.8) * 30
                if r < 140: sparkle(d, int(180 + math.cos(a) * r), int(330 + math.sin(a) * r), 4, (YEL, PINK, MINT, SKY)[i % 4])


def kitchen(d, t):
    d.rectangle((0, 0, W, H), fill=PEACH)
    for y in range(0, 420, 24):
        for x in range(0, W, 24):
            d.rectangle((x, y, x + 22, y + 22), fill=(255, 226, 202) if (x // 24 + y // 24) % 2 == 0 else (255, 214, 186))
    # window
    d.rectangle((40, 70, 150, 160), fill=SKY, outline=INK, width=3)
    d.line((95, 70, 95, 160), fill=INK, width=2); d.line((40, 115, 150, 115), fill=INK, width=2)
    d.ellipse((60, 84, 80, 102), fill=WHITE); d.ellipse((72, 80, 96, 100), fill=WHITE)
    # shelf with pots
    d.rectangle((200, 130, 330, 138), fill=BROWN, outline=INK)
    for i, c in enumerate((RED, MINT, YEL)):
        x = 215 + i * 38
        d.rectangle((x, 100, x + 26, 130), fill=c, outline=INK, width=2); d.rectangle((x - 2, 96, x + 28, 102), fill=WHITE, outline=INK)
    # hanging ladle etc
    for i in range(3):
        x = 215 + i * 45
        d.line((x, 30, x, 60 + i * 6), fill=INK, width=2); d.ellipse((x - 9, 60 + i * 6, x + 9, 78 + i * 6), fill=(200, 200, 215), outline=INK, width=2)
    d.rectangle((0, 470, W, 640), fill=(190, 130, 96)); d.rectangle((0, 470, W, 480), fill=(220, 160, 120), outline=INK)
    for x in range(0, W, 40): d.line((x, 480, x - 10, 640), fill=(160, 106, 76), width=2)


def scene2(img, d, t):  # local 0..10
    g = t + 13
    kitchen(d, g)
    base = 474
    chef_face = 'happy' if g > 18.4 else ('n' if g < 15.0 else 'wow')
    hop = abs(math.sin(g * 6)) * 5 if g > 18.4 else 0
    mochi(d, 300, base - 44 - int(hop), chef_face, sq=0.25 if hop < 1 else 0, arms=(1 if g > 18.4 else 0), hat='chef', t=g)
    T = {}
    T['bowl'] = fall(g, 14.0, 200, .7)
    T['soup'] = clamp((g - 14.9) / 0.6) if g > 14.9 else None
    for name, te in (('noodle', 15.4), ('naruto', 16.2), ('egg', 17.0), ('nori', 17.5)):
        o = fall(g, te, 110, .55)
        T[name] = o
    for i in range(6):
        T[f'sc{i}'] = fall(g, 18.0 + i * .12, 90, .45)
    wig = int(math.sin(g * 18) * 2) if g > 18.7 else 0
    bowl(d, 150 + wig, base, T, k=1.35)
    if g > 19.2:  # steam
        for i in range(5):
            ph = (g * 1.2 + i * .37) % 1
            x = 100 + i * 24 + math.sin(ph * 8 + i) * 5; y = 330 - ph * 120
            a = int(200 * (1 - ph))
            d.ellipse((x - 5, y - 5, x + 5, y + 5), fill=(255, 255, 255, a))
    if 20.3 < g < 22.8:
        for i in range(6):
            a = i * math.pi / 3 + g * 2; r = 90 + math.sin(g * 4 + i) * 6
            sparkle(d, int(150 + math.cos(a) * r), int(340 + math.sin(a) * r * .8), 4 + (i % 2) * 2, (YEL, PINK, WHITE)[i % 3])
    chip(img, d, "随便 #1  一碗面", 18, 14, YEL)
    if g > 21.2:
        p = bounce((g - 21.2) / .4)
        put(img, "好吃!", 150, 190 - int((1 - p) * 30), RED, 3, 'm', shadow=WHITE)


SKYKEYS = [(0, (150, 215, 255)), (3, (255, 205, 160)), (4.4, (60, 60, 120)), (6.4, (60, 60, 120)), (7.6, (255, 222, 195)), (8.8, (170, 225, 255)), (10, (170, 225, 255))]


def skycol(t):
    for (a, ca), (b, cb) in zip(SKYKEYS, SKYKEYS[1:]):
        if a <= t <= b: return lerpc(ca, cb, (t - a) / (b - a))
    return SKYKEYS[-1][1]


def scene3(img, d, t):  # local 0..10
    g = t + 23
    c = skycol(t); vgrad(d, c, lerpc(c, (255, 255, 255), .35), 0, 470)
    night = clamp(1 - abs(t - 5.4) / 1.6)
    if night > 0:
        rnd = random.Random(3)
        for i in range(36):
            x, y = rnd.randint(0, W), rnd.randint(0, 340)
            if int(g * 3 + i) % 4: d.rectangle((x, y, x + 1, y + 1), fill=(255, 255, 255, int(255 * night)))
        mx, my = lerp(300, 60, clamp((t - 3.8) / 4)), 150 - math.sin(clamp((t - 3.8) / 4) * math.pi) * 80
        d.ellipse((mx - 18, my - 18, mx + 18, my + 18), fill=(255, 245, 200), outline=INK, width=2)
        d.ellipse((mx - 4, my - 14, mx + 12, my + 2), fill=(255, 245, 200))
        d.ellipse((mx - 12, my - 12, mx + 8, my + 12), fill=c)
        d.ellipse((mx - 18, my - 18, mx + 18, my + 18), outline=INK, width=2)
    # sun: day 0..4 and 6.8..10
    for a, b in ((0, 4.4), (6.6, 10)):
        if a <= t <= b:
            p = (t - a) / (b - a)
            sx, sy = lerp(40, 320, p), 360 - math.sin(p * math.pi) * 280
            d.ellipse((sx - 20, sy - 20, sx + 20, sy + 20), fill=YEL, outline=INK, width=2)
            for i in range(8):
                ang = i * math.pi / 4 + g * 1.2
                d.line((sx + math.cos(ang) * 26, sy + math.sin(ang) * 26, sx + math.cos(ang) * 34, sy + math.sin(ang) * 34), fill=YEL, width=3)
            for ex in (-6, 6): d.rectangle((sx + ex - 1, sy - 3, sx + ex, sy + 1), fill=INK)
            d.arc((sx - 5, sy - 1, sx + 5, sy + 7), 10, 170, fill=INK)
    # clouds
    for i, (cx0, cy0) in enumerate(((60, 90), (250, 190), (120, 280))):
        x = (cx0 + g * (6 + i * 3)) % 440 - 40
        d.ellipse((x - 20, cy0 - 8, x + 20, cy0 + 12), fill=(255, 255, 255, 210)); d.ellipse((x - 4, cy0 - 18, x + 26, cy0 + 8), fill=(255, 255, 255, 210))
    # ground
    d.rectangle((0, 470, W, 640), fill=(120, 200, 120)); d.rectangle((0, 470, W, 480), fill=(150, 220, 130), outline=INK)
    for x in range(10, W, 28):
        d.line((x, 482, x - 3, 476), fill=INK); d.line((x, 482, x + 3, 477), fill=INK)
    ptop = 440
    pot(d, 180, ptop)
    # seed
    sd = fall(g, 24.3, 160, .5)
    if sd is not None and g < 26.2: d.ellipse((176, ptop - 6 + sd, 184, ptop + 2 + sd), fill=BROWN, outline=INK)
    grow = clamp((t - 3.0) / 4.4); grow = grow ** .8 if grow > 0 else 0
    bloom = clamp((t - 7.8) / .8)
    top = flower_plant(d, 180, ptop - 6, grow if t > 3.0 else 0, bloom, t=g)
    # watering can + mochi
    pouring = 1.7 < t < 3.0
    sleeping = 4.2 < t < 7.4
    face = 'happy' if bloom > 0 else ('sleep' if sleeping else ('n'))
    if 7.4 <= t < 7.9: face = 'wow'
    hat = 'night' if sleeping else None
    mochi(d, 70, 510, face, sq=(0.3 * math.sin(g * 12) if t > 8.5 else 0), arms=(1 if bloom > 0 else 0), hat=hat, t=g)
    if pouring:
        cx = 120; cy = 420
        d.polygon([(cx - 14, cy), (cx + 14, cy), (cx + 12, cy + 24), (cx - 12, cy + 24)], fill=(120, 170, 255), outline=INK)
        d.line((cx - 14, cy + 4, cx - 24, cy - 6, cx - 14, cy - 6), fill=INK, width=2)
        d.polygon([(cx + 14, cy + 4), (cx + 32, cy + 16), (cx + 32, cy + 22), (cx + 12, cy + 20)], fill=(120, 170, 255), outline=INK)
        for i in range(8):
            ph = ((g * 2.2 + i * .13) % 1)
            d.rectangle((cx + 32 + ph * 20 - 1, cy + 22 + ph * ph * 90, cx + 32 + ph * 20 + 1, cy + 24 + ph * ph * 90), fill=(90, 160, 255), outline=None)
    if sleeping:
        for i in range(3):
            ph = (g * .8 + i / 3) % 1
            put(img, "z", 96 + ph * 24, 480 - ph * 60 - i * 6, WHITE if night > .3 else INK, 1 + (i % 2), shadow=None)
    if t > 8.9:
        for i in range(2):  # bees
            a = g * 3 + i * math.pi
            bx, by_ = top[0] + math.cos(a) * 46, top[1] + math.sin(a * 1.3) * 22 - 10
            d.ellipse((bx - 6, by_ - 4, bx + 6, by_ + 4), fill=YEL, outline=INK)
            d.line((bx - 2, by_ - 4, bx - 2, by_ + 4), fill=INK, width=2); d.line((bx + 2, by_ - 4, bx + 2, by_ + 4), fill=INK, width=2)
            d.ellipse((bx - 5, by_ - 11 - int(abs(math.sin(g * 40)) * 3), bx, by_ - 4), fill=(255, 255, 255, 200), outline=INK)
        for i in range(3):
            ph = (g * 1.0 + i / 3) % 1
            heart(d, int(top[0] + 40 + i * 12 - ph * 6), int(top[1] - 20 - ph * 40), 3)
    chip(img, d, "随便 #2  一朵花", 18, 14, MINT)


def scene4(img, d, t):  # local 0..10
    g = t + 33
    d.rectangle((0, 0, W, H), fill=(255, 205, 224))
    for x in range(0, W, 30): d.rectangle((x, 0, x + 14, 480), fill=(255, 214, 230))
    # window
    d.rectangle((210, 60, 320, 190), fill=NIGHT, outline=INK, width=4)
    d.line((265, 60, 265, 190), fill=INK, width=3); d.line((210, 125, 320, 125), fill=INK, width=3)
    for (sx, sy) in ((230, 80), (290, 100), (240, 160), (300, 170)):
        if int(g * 2 + sx) % 3: sparkle(d, sx, sy, 3, WHITE)
    d.ellipse((276, 70, 304, 98), fill=(255, 245, 200)); d.ellipse((284, 66, 306, 92), fill=NIGHT)
    # frames
    for fx, fy, c in ((36, 90, MINT), (90, 120, YEL)):
        d.rectangle((fx, fy, fx + 44, fy + 52), fill=c, outline=INK, width=3)
        d.ellipse((fx + 14, fy + 14, fx + 30, fy + 32), fill=WHITE, outline=INK)
    d.rectangle((0, 470, W, 640), fill=(210, 160, 110)); d.rectangle((0, 470, W, 480), fill=(236, 190, 140), outline=INK)
    for x in range(0, W, 60): d.line((x, 480, x, 640), fill=(180, 132, 90), width=2)
    d.ellipse((50, 520, 310, 610), fill=MINT, outline=INK, width=3); d.ellipse((90, 535, 270, 595), outline=WHITE, width=2)
    # state
    bx = 180
    boxdrop = fall(g, 34.0, 260, .6)
    cat_out = g > 37.8
    shaking = 35.0 < g < 35.6
    sh = int(math.sin(g * 50) * 3) if shaking else 0
    mface = 'n' if g < 36.5 else ('wow' if g < 38 else ('happy' if g < 41.4 else 'sleep'))
    mochi(d, 50, 510, mface, hat='cap' if g > 38 else None, sq=0, arms=(1 if 37.8 < g < 38.6 else 0), t=g)
    # cat peeking inside box before leaving
    def draw_box(front=True):
        o = boxdrop if boxdrop is not None else None
        if o is None: return
        x0, x1 = bx - 52 + sh, bx + 52 + sh; y1 = 472 + int(o); y0 = y1 - 62
        d.polygon([(x0, y0), (x1, y0), (x1 + 6, y0 - 10), (x0 - 6, y0 - 10)], fill=(214, 160, 110), outline=INK) if not front else None
        if front:
            d.rectangle((x0, y0, x1, y1), fill=(226, 172, 118), outline=INK, width=3)
            d.rectangle((bx - 14 + sh, y0 + 10, bx + 14 + sh, y0 + 38), fill=(246, 214, 168), outline=INK)
            d.line((x0 + 6, y0 + 8, x1 - 6, y0 + 8), fill=(190, 138, 92), width=3)
            # flaps
            d.polygon([(x0, y0), (x0 - 14, y0 - 12), (bx - 6, y0 - 6), (bx, y0)], fill=(236, 186, 132), outline=INK)
            d.polygon([(x1, y0), (x1 + 14, y0 - 12), (bx + 6, y0 - 6), (bx, y0)], fill=(236, 186, 132), outline=INK)
    if boxdrop is not None and not cat_out:
        # peek rising
        rise = clamp((g - 36.8) / .7)
        if g > 36.4:
            cy = 472 - 40 - int(rise * 34)
            if g < 37.8:
                cat(d, bx, 472 - 8 + int(36 * (1 - rise)) if False else 472 - 14 + int((1 - rise) * 60), 'sit', 'o', 1.0, ground=False)
        draw_box(True)
        if 36.0 < g < 36.8:
            put(img, "?", bx - 8, 330 - int((g - 36) * 10), RED, 3)
        if g < 36.4 and not shaking:
            pass
    elif cat_out:
        draw_box(True)
    # cat after exit
    if cat_out:
        lt = g - 37.8
        if lt < .8:  # jump arc
            p = lt / .8; x = lerp(bx, 170, p); y = 472 - math.sin(p * math.pi) * 90
            cat(d, int(x), int(y + (100 if False else 0)), 'sit', 'h', 1.0, tail=1, ground=False)
        else:
            ballx = 330 - (g - 38.6) * 20 if g < 39.6 else 330 - 1.0 * 20 - 0
            # ball rolls from right to center-left
            if g < 40.6:
                ballx = lerp(340, 130, clamp((g - 38.4) / 2.2))
            else:
                ballx = 130
            catx = lerp(170, 140, clamp((g - 38.8) / 1.8))
            hopy = abs(math.sin((g - 38.8) * 5)) * 18 if 38.8 < g < 40.8 else 0
            if g < 41.5:
                pounce = clamp((g - 40.4) / .3) * (1 - clamp((g - 40.8) / .3))
                eyes = 'w' if g < 40.8 else 'h'
                cat(d, int(catx), int(472 - hopy - pounce * 10), 'sit', eyes, 1.0, tail=math.sin(g * 8))
                # yarn ball
                bry = 470
                d.ellipse((ballx - 11, bry - 22, ballx + 11, bry), fill=RED, outline=INK, width=2)
                for i in range(3): d.arc((ballx - 9, bry - 20 + i * 3, ballx + 9, bry - 2 - i * 2), 200 + i * 30, 340, fill=(255, 190, 190))
                d.line((ballx + 8, bry - 4, ballx + 30 + int(math.sin(g * 6) * 4), bry + 6), fill=RED, width=2)
            else:
                lt2 = g - 41.5
                yawn = 41.5 < g < 42.2
                cat(d, 285, 505, 'loaf' if lt2 > .9 else 'sit', 'c' if lt2 > .9 else 'w', 1.0)
                if lt2 > .9:
                    for i in range(3):
                        ph = (g * .7 + i / 3) % 1
                        put(img, "zZ"[i % 2], 290 + ph * 30, 440 - ph * 50, INK, 1 + (i % 2))
    if 40.6 < g < 41.5:
        for i in range(3): heart(d, 150 + i * 14, 400 - int((g - 40.6) * 40) - i * 6, 3)
    chip(img, d, "随便 #3  一只猫", 18, 14, PINK)


def scene5(img, d, t):  # local 0..10 -> global 43..53
    g = t + 43
    launch = 48.8
    lt = g - launch
    spacey = clamp((lt - 1.4) / 1.0)
    # sky
    vgrad(d, lerpc((90, 120, 200), NIGHT, spacey) if False else NIGHT, lerpc(NIGHT, (110, 90, 170), 1 - spacey * .6), 0, H)
    rnd = random.Random(8)
    off = max(0, lt) ** 2 * 60 if lt > 0 else 0
    sp = 260 if lt > 1.6 else (lt * 160 if lt > 0 else 0)
    for i in range(70):
        x, y0 = rnd.randint(0, W), rnd.randint(0, H * 2)
        y = (y0 + (g - 43) * 4 + (off if lt < 1.6 else 0) + max(0, lt - 1.6) * 0 + 0)
        if lt > 1.6: y = (y0 + off * 0 + (g - launch - 1.6) * 260 * (0.6 + (i % 3) * .5) + 400) % H
        else: y = y0 % H + (off if lt > 0 else 0)
        y = y % H
        L = 1 + int(sp / 60 * (0.5 + (i % 3) * .5)) if lt > 0 else 1
        if lt > 0 or int(g * 3 + i) % 4:
            d.line((x, y, x, y + L), fill=WHITE, width=1 if i % 3 else 2)
    # moon on horizon at start
    ground_off = int(max(0, lt) ** 2 * 120) if lt > 0 else 0
    if ground_off < 700:
        d.ellipse((260, 90 + ground_off // 3, 330, 160 + ground_off // 3), fill=(255, 245, 200), outline=INK, width=2)
        for (cx, cy, r) in ((282, 112, 7), (306, 130, 5), (292, 140, 4)):
            d.ellipse((cx - r, cy - r + ground_off // 3, cx + r, cy + r + ground_off // 3), fill=(236, 226, 176))
        d.rectangle((0, 470 + ground_off, W, 640 + ground_off), fill=(86, 70, 130)); d.rectangle((0, 470 + ground_off, W, 480 + ground_off), fill=(130, 110, 180), outline=INK)
        # launch pad
        d.rectangle((120, 466 + ground_off, 240, 476 + ground_off), fill=(190, 190, 205), outline=INK, width=2)
        d.rectangle((250, 400 + ground_off, 262, 470 + ground_off), fill=(190, 190, 205), outline=INK)
        d.line((262, 410 + ground_off, 232, 410 + ground_off), fill=INK, width=3)
        mochi(d, 60, 510 + ground_off, 'happy' if lt > -1 else 'n', arms=(1 if int(g * 3) % 2 else .3), hat='cap', t=g)
    # planets scrolling after liftoff
    if lt > 1.6:
        pl = lt - 1.6
        py = -80 + pl * 150
        d.ellipse((230, py - 50, 330, py + 50), fill=(255, 150, 120), outline=INK, width=3)
        d.ellipse((240, py - 40, 270, py - 10), fill=(255, 190, 150))
        d.arc((200, py - 22, 360, py + 22), 0, 180, fill=(255, 220, 150), width=4)
        d.arc((200, py - 22, 360, py + 22), 180, 360, fill=(255, 220, 150), width=4)
        py2 = -420 + pl * 150
        d.ellipse((30, py2 - 30, 100, py2 + 30), fill=MINT, outline=INK, width=3)
        for ex in (-12, 12): d.rectangle((65 + ex - 1, py2 - 6, 65 + ex + 1, py2 - 1), fill=INK)
        d.arc((58, py2 - 4, 72, py2 + 8), 10, 170, fill=INK)
        py3 = -820 + pl * 150
        d.ellipse((260, py3 - 22, 304, py3 + 22), fill=(255, 245, 200), outline=INK, width=2)
        # shooting star
    if g > 51.3 and g < 52.4:
        p = (g - 51.3) / 1.1
        x, y = lerp(360, 60, p), lerp(60, 330, p)
        d.line((x, y, x + 50, y - 30), fill=(255, 255, 255, 140), width=3); star5(d, int(x), int(y), 9)
    # rocket
    shake = int(math.sin(g * 60) * 2) if lt > -0.2 and lt < 1.6 else 0
    if lt < 0: ry = 466
    elif lt < 1.6: ry = 466 - int((lt ** 2) * 80) if lt < 1.6 else 466
    else: ry = 466 - int(1.6 ** 2 * 80)
    if lt >= 1.6:
        ry = int(lerp(466 - 205, 520, 0)) if False else 466 - 205 + int(math.sin(g * 3) * 6)
    cattime = g

    def win(cx, wy):
        eyes = 'w' if lt < 0 else 'c'
        face = 'w' if (45.6 < g < 49.3 or 51.8 < g < 53) else 'o'
        d.ellipse((cx - 11, wy - 11, cx + 11, wy + 11), fill=(130, 170, 255))
        d.ellipse((cx - 9, wy - 8, cx + 9, wy + 10), fill=ORANGE, outline=INK)
        d.polygon([(cx - 9, wy - 6), (cx - 8, wy - 14), (cx - 3, wy - 8)], fill=ORANGE, outline=INK); d.polygon([(cx + 9, wy - 6), (cx + 8, wy - 14), (cx + 3, wy - 8)], fill=ORANGE, outline=INK)
        for sx in (-4, 4):
            d.ellipse((cx + sx - 2, wy - 3, cx + sx + 2, wy + 2), fill=WHITE if face == 'w' else INK, outline=INK)
            if face == 'w': d.rectangle((cx + sx - 1, wy - 1, cx + sx, wy), fill=INK)
        d.arc((cx - 3, wy + 1, cx + 3, wy + 6), 190, 350 if face == 'o' else 350, fill=INK)
    flame = 0 if lt < 0 else clamp(.3 + lt * 1.2, 0, 1.5)
    rocket(d, 180 + shake, ry, 1.3 if False else 1.0, flame, win, g)
    if 45.6 < g < 47.4 or 51.8 < g < 53: put(img, "?!", 214 + shake, ry - 120 + int(math.sin(g * 8) * 2), RED, 2)
    # countdown
    for tt, s in ((45.8, "3"), (46.8, "2"), (47.8, "1"), (48.8, "GO!")):
        if tt <= g < tt + .85:
            p = bounce((g - tt) / .3)
            sc = 3 + p * 3 if s != "GO!" else 4 + p * 2
            put(img, s, 180 + 3, 200 + 3, INK, sc, 'm'); put(img, s, 180, 200, YEL if s == "GO!" else WHITE, sc, 'm')
    if lt > 0 and lt < 1.6:  # smoke
        for i in range(8):
            ph = (g * 3 + i * .3) % 1
            x = 180 + (i - 4) * 12 + math.sin(i + g * 5) * 5; y = 470 + ph * 18 + ground_off
            r = 8 + ph * 10
            d.ellipse((x - r, y - r, x + r, y + r), fill=(240, 240, 250, int(180 * (1 - ph))))
    chip(img, d, "随便 #4  去太空", 18, 14, SKY)


def confetti(d, t, n=40, seed=4):
    rnd = random.Random(seed)
    cols = (PINK, YEL, MINT, SKY, ORANGE, HOT)
    for i in range(n):
        x0 = rnd.randint(0, W); sp = rnd.uniform(40, 110); ph = rnd.uniform(0, 600)
        y = (ph + t * sp) % (H + 20) - 10; x = x0 + math.sin(t * 2 + i) * 8
        d.rectangle((x, y, x + 4, y + 4), fill=cols[i % 6], outline=INK)


def scene6(img, d, t):  # local 0..9 -> 53..62
    g = t + 53
    bg_dots(d, (255, 238, 246), PINK, g, 8)
    cards = [(16, 60, "一碗面", YEL), (186, 60, "一朵花", MINT), (16, 250, "一只猫", PINK), (186, 250, "去太空", SKY)]
    for i, (x, y, lab, col) in enumerate(cards):
        te = 53.4 + i * .6
        o = fall(g, te, 300, .6)
        if o is None: continue
        y = y + int(o)
        box(d, (x, y, x + 158, y + 168), fill=col)
        d.rectangle((x + 8, y + 8, x + 150, y + 140), fill=(255, 255, 255, 120))
        cx = x + 79
        if i == 0:
            T = {'bowl': 0, 'soup': 1, 'noodle': 0, 'naruto': 0, 'egg': 0, 'nori': 0}
            for j in range(6): T[f'sc{j}'] = 0
            bowl(d, cx, y + 124, T, k=0.9)
            if g > 56:
                for j in range(3):
                    ph = (g * 1.2 + j * .3) % 1; d.ellipse((cx - 20 + j * 20 - 3, y + 50 - ph * 30, cx - 20 + j * 20 + 3, y + 56 - ph * 30), fill=(255, 255, 255, int(200 * (1 - ph))))
        elif i == 1:
            pot(d, cx, y + 100, 0.6); flower_plant(d, cx, y + 100, 1.0, 1.0, t=g, k=.62)
        elif i == 2:
            cat(d, cx, y + 118, 'sit', 'h' if int(g * 2) % 2 else 'o', 1.0, tail=math.sin(g * 6))
        else:
            rocket(d, cx, y + 124, .85, 0.9, None, g)
        chip(img, d, lab, x + 79 - int(FONT.getlength(lab) / 2) - 7, y + 140, WHITE)
    confetti(d, g, 36)
    jump = abs(math.sin(g * 5)) * 14 if g > 53.6 else 0
    mochi(d, 180, 524 - int(jump), 'happy', sq=(.4 if jump < 1 else 0), arms=1, hat='cap', k=1.0, t=g)
    if g > 56:
        p = bounce((g - 56) / .5)
        put(img, "做完啦!", 180 + 2, 428 + 2 - int((1 - p) * 40), INK, 2, 'm'); put(img, "做完啦!", 180, 428 - int((1 - p) * 40), HOT, 2, 'm')
    # blink END
    if g > 59.6:
        put(img, "~ END ~", 180, 40, INK, 2, 'm')


SCENES = [(0, scene0), (6, scene1), (13, scene2), (23, scene3), (33, scene4), (43, scene5), (53, scene6)]


def render(t):
    img = Image.new('RGB', (W, H), CREAM)
    d = ImageDraw.Draw(img, 'RGBA')
    d.fontmode = '1'
    for i in range(len(SCENES) - 1, -1, -1):
        if t >= SCENES[i][0]:
            s0, fn = SCENES[i]
            if fn in (scene1,): fn(img, d, t - s0)
            elif fn in (scene2, scene3, scene4, scene5, scene6): fn(img, d, t - s0)
            else: fn(img, d, t)
            break
    # subtitle
    sub = tween_sub(t)
    if sub:
        t0, lines = sub
        n = int((t - t0) * CPS)
        bh = 18 + 24 * len(lines)
        y0 = 640 - 30 - bh - 6
        box(d, (14, y0, 346, y0 + bh), fill=WHITE)
        yy = y0 + 9
        for ln in lines:
            put(img, ln[:max(0, n)], 180, yy, INK, 1, 'm') if False else None
            wdt = int(FONT.getlength(ln))
            put(img, ln[:max(0, n)], 180 - wdt // 2, yy, INK, 1)
            n -= len(ln); yy += 24
    # transition
    for b in BOUNDS:
        p = 1 - abs(t - b) / .35
        if p > 0:
            rnd = random.Random(int(b * 10))
            cols = 15; rows = 27
            for r in range(rows):
                for c in range(cols):
                    thr = (r / rows) * .45 + rnd.random() * .5
                    if p >= thr:
                        x, y = c * 24, r * 24
                        d.rectangle((x, y, x + 23, y + 23), fill=HOT if (r + c) % 2 else PINK)
                        if (r + c) % 4 == 0: d.rectangle((x + 9, y + 9, x + 14, y + 14), fill=WHITE)
    # progress bar
    pw = int((W - 28) * clamp(t / DUR))
    d.rectangle((14, 626, W - 14, 634), fill=(255, 255, 255, 170), outline=INK)
    if pw > 0: d.rectangle((15, 627, 14 + pw, 633), fill=HOT)
    star5(d, 14 + pw, 630, 7)
    # fade out
    if t > DUR - .7:
        a = int(255 * clamp((t - (DUR - .7)) / .7)); d.rectangle((0, 0, W, H), fill=(0, 0, 0, a))
    return img


# ---------------------------------------------------------------- audio
SR = 44100


def mid2f(m): return 440 * 2 ** ((m - 69) / 12)


def synth():
    n = int(DUR * SR); out = np.zeros(n, np.float32); rng = np.random.default_rng(1)

    def add(t0, sig, vol=1.0):
        i0 = int(t0 * SR)
        if i0 >= n or i0 < 0: return
        sig = sig[:n - i0]; out[i0:i0 + len(sig)] += sig * vol

    def tone(f, dur, wave='sq', duty=.5, vol=.3, a=.005, rel=.05, glide=None, vib=0):
        m = int(dur * SR); tt = np.arange(m) / SR
        fr = f if glide is None else np.linspace(f, glide, m)
        if vib: fr = fr * (1 + .02 * np.sin(2 * np.pi * 6 * tt))
        ph = np.cumsum(np.broadcast_to(fr, m)) / SR
        if wave == 'sq': s = np.where((ph % 1) < duty, 1., -1.)
        elif wave == 'tri': s = 2 * np.abs(2 * ((ph % 1) - .5)) - 1
        else: s = np.sin(2 * np.pi * ph)
        env = np.minimum(1, tt / a) * np.minimum(1, np.maximum(0, (dur - tt) / rel))
        return (s * env * vol).astype(np.float32)

    def noise(dur, vol=.3, dec=20, lp=0):
        m = int(dur * SR); tt = np.arange(m) / SR
        s = rng.uniform(-1, 1, m)
        if lp:
            for _ in range(lp): s = (s + np.roll(s, 1)) / 2
        return (s * np.exp(-tt * dec) * vol).astype(np.float32)

    # music
    beat = .5; step = beat / 2
    chords = [(48, 52, 55), (45, 48, 52), (53, 57, 60), (55, 59, 62)]
    roots = [48, 45, 41, 43]
    mel = [
        [76, 79, 76, 72, 74, 76, 0, 72],
        [69, 72, 76, 72, 69, 72, 74, 0],
        [77, 81, 77, 72, 74, 77, 0, 72],
        [74, 79, 83, 79, 74, 76, 74, 0],
    ]
    mel_b = [
        [79, 0, 76, 79, 84, 79, 76, 72],
        [76, 0, 72, 76, 81, 76, 72, 69],
        [77, 0, 81, 84, 81, 77, 72, 77],
        [79, 83, 86, 83, 79, 74, 79, 0],
    ]
    for bar in range(int(DUR / (step * 8)) + 1):
        tb = bar * step * 8
        if tb >= DUR - .5: break
        ci = bar % 4
        ten = 0 if tb < 3.7 else (1 if tb < 6 else 2)
        loud = 1.0 if tb < 53 else 1.15
        use_b = (bar // 4) % 2 == 1 and tb > 23
        for s in range(8):
            t0 = tb + s * step
            nt = (mel_b if use_b else mel)[ci][s]
            if nt and t0 < DUR - 1.5:
                add(t0, tone(mid2f(nt), step * .9, 'sq', .25, .17 * loud, rel=.04), 1)
            if tb < 3.7 and s % 2 == 0:
                pass
            if ten >= 1:
                r = roots[ci]
                if s in (0, 3, 4, 6): add(t0, tone(mid2f(r if s != 4 else r + 7), step * .9, 'tri', vol=.34, rel=.03), 1)
            if ten >= 2 or tb > 3.7:
                c = chords[ci]
                add(t0, tone(mid2f(c[s % 3] + 12), step * .8, 'sq', .125, .06, rel=.05), 1)
            if tb >= 6 and s in (0, 4):  # kick
                add(t0, tone(140, .12, 'sin', vol=.45, glide=45, rel=.02), 1)
            if tb >= 6 and s in (2, 6):  # snare
                add(t0, noise(.1, .22, 30), 1)
            if tb >= 6 and s % 2 == 1:
                add(t0, noise(.04, .1, 80), 1)
    # outro chord
    for m_ in (60, 64, 67, 72): add(59.4, tone(mid2f(m_), 2.2, 'sq', .25, .1, rel=1.0, a=.01), 1)
    # sfx
    for ev in SF:
        t, k, *a = ev
        if k == 'blip': add(t, tone(a[0], a[1], 'sq', .5, .1, a=.002, rel=.015))
        elif k == 'pop': add(t, tone(a[0], .12, 'sin', vol=.3, glide=a[0] * 1.8, rel=.03))
        elif k == 'thump': add(t, tone(110, .35, 'sin', vol=.6, glide=35, rel=.05)); add(t, noise(.2, .3, 15, 2))
        elif k == 'sparkle':
            for i in range(6): add(t + i * .05, tone(mid2f(84 + i * 3), .1, 'sq', .25, .1, rel=.05))
        elif k == 'whoosh':
            m = int(a[0] * SR); tt = np.arange(m) / SR
            s = noise(a[0], .5, 0, 3) * np.sin(np.pi * tt / a[0]); add(t, s, 1)
        elif k == 'rattle': add(t, noise(.05, .35, 40, 1))
        elif k == 'ding': add(t, tone(988, .12, 'sq', .5, .17, rel=.03)); add(t + .1, tone(1318, .5, 'sq', .5, .17, rel=.4))
        elif k == 'plop': add(t, tone(a[0] * 1.5, .12, 'sin', vol=.5, glide=a[0] * .5, rel=.03))
        elif k == 'splash': add(t, noise(.35, .5, 8, 2))
        elif k == 'twinkle':
            for i, m_ in enumerate((79, 84, 88, 91, 96)): add(t + i * .07, tone(mid2f(m_), .15, 'sq', .25, .1, rel=.07))
        elif k == 'drip': add(t, tone(1400, .06, 'sin', vol=.2, glide=700, rel=.02))
        elif k == 'boing': add(t, tone(220, .25, 'sq', .5, .2, glide=720, rel=.1, vib=1))
        elif k == 'meow': add(t, tone(600, .5, 'sq', .35, .2, glide=900, rel=.2, vib=1)); add(t + .25, tone(900, .25, 'sq', .35, .15, glide=500, rel=.1))
        elif k == 'yawn': add(t, tone(400, 1.0, 'sin', vol=.25, glide=200, rel=.5, vib=1))
        elif k == 'beep':
            d_ = a[1] if len(a) > 1 else .18; add(t, tone(a[0], d_, 'sq', .5, .22, rel=.04))
        elif k == 'rumble':
            m = int(a[0] * SR); tt = np.arange(m) / SR
            r = noise(a[0], .5, 0, 6) * np.minimum(1, tt) * .9 + 0 ; add(t, r * 1.5, 1)
    out = np.tanh(out * 1.4) * .85
    # fade out
    fo = int(1.0 * SR); out[-fo:] *= np.linspace(1, 0, fo)
    return out


def write_wav(path, x):
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype('<i2').tobytes())


if __name__ == '__main__':
    args = sys.argv[1:]
    if '--preview' in args:
        i = args.index('--preview'); ts = [float(v) for v in args[i + 1].split(',')]
        ims = [render(t).resize((W // 2, H // 2), Image.NEAREST) if '--small' in args else render(t) for t in ts]
        sheet = Image.new('RGB', (ims[0].width * len(ims), ims[0].height))
        for k_, im in enumerate(ims): sheet.paste(im, (k_ * ims[0].width, 0))
        sheet.save(args[0] if not args[0].startswith('--') else '/tmp/preview.png'); sys.exit()
    out = args[0] if args else 'suibian.mp4'
    wav = out + '.wav'; write_wav(wav, synth())
    p = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-framerate', str(FPS),
                          '-i', '-', '-i', wav, '-vf', 'scale=1080:1920:flags=neighbor,format=yuv420p', '-r', '30', '-c:v', 'libx264', '-crf', '17',
                          '-preset', 'medium', '-c:a', 'aac', '-b:a', '160k', '-shortest', '-movflags', '+faststart', out], stdin=subprocess.PIPE)
    for i in range(int(DUR * FPS)):
        p.stdin.write(render(i / FPS).tobytes())
    p.stdin.close(); p.wait()
    print('done', out)
