"""Frame-by-frame renderer for the combinatorics video.

    python3 render.py still <t> out.png      # one frame, for checking
    python3 render.py video out.mp4 music.wav
"""
import functools, io, itertools, math, os, subprocess, sys
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
import matplotlib
matplotlib.use("Agg")
from matplotlib import mathtext
from matplotlib.font_manager import FontProperties
from timeline import *

W, H, FPS = 1920, 1080, 30
NF = int(TOTAL * FPS)
D = os.path.dirname(os.path.abspath(__file__))
FONT = {k: os.path.join(D, "fonts", v) for k, v in
        {"serif": "SerifBlack.ttf", "serifb": "SerifBold.ttf",
         "sans": "SansLight.ttf", "sansb": "SansBold.ttf"}.items()}
CX, CY = W // 2, H // 2
SH = 4                      # cv2 sub-pixel shift bits
S16 = 1 << SH

# ---------------------------------------------------------------- easing
def clamp(x, a=0.0, b=1.0): return min(max(x, a), b)
def ss(a, b, x):
    x = clamp((x - a) / (b - a)); return x * x * (3 - 2 * x)
def eo(x): x = clamp(x); return 1 - (1 - x) ** 3
def eio(x): x = clamp(x); return 4 * x ** 3 if x < .5 else 1 - (-2 * x + 2) ** 3 / 2
def pop(x):
    x = clamp(x); c = 2.2; return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2
def win(t, a, b, fi=.35, fo=.45):
    """1 inside [a, b], with fades at both ends."""
    return ss(a, a + fi, t) * (1 - ss(b - fo, b, t))

KICKS = np.array(kick_times())
def kick_env(t):
    i = np.searchsorted(KICKS, t, side="right") - 1
    return 0.0 if i < 0 else math.exp(-(t - KICKS[i]) * 9)
def hit_env(t, rate=6.0):
    return sum(s * math.exp(-(t - h) * rate) for h, s in HITS if 0 <= t - h < 3)

# ---------------------------------------------------------------- colours
def mix(c1, c2, u): return tuple(a + (b - a) * u for a, b in zip(c1, c2))
def sc(c, a): return tuple(int(clamp(v * a, 0, 255)) for v in c)
WHITE = (255, 255, 255)
ICE, CYAN, VIOLET = (175, 220, 255), (110, 215, 255), (185, 160, 255)
GOLD, TEAL, MAGENTA = (255, 196, 105), (80, 235, 205), (255, 85, 170)
INDIGO, RED, BLUE = (140, 130, 255), (255, 55, 60), (70, 140, 255)
ACCENT = {"intro": ICE, "mult": CYAN, "perm": VIOLET, "comb": GOLD, "incl": TEAL,
          "catalan": INDIGO, "genf": GOLD, "ramsey": RED, "outro": WHITE}

def accent(t):
    name, a, b = section_at(t)
    c = ACCENT[name]
    if t < a + .8:
        prev = [s for s in SECTIONS if s[2] == a]
        if prev:
            c = mix(ACCENT[prev[0][0]], c, ss(a - .01, a + .8, t))
    return c

# ---------------------------------------------------------------- sprites
@functools.lru_cache(maxsize=1024)
def text_mask(s, font, size, spacing=0):
    f = ImageFont.truetype(FONT[font], size)
    if spacing:
        widths = [f.getlength(ch) for ch in s]
        tw = int(sum(widths) + spacing * (len(s) - 1))
    else:
        tw = int(f.getlength(s))
    asc, desc = f.getmetrics()
    pad = size // 4
    im = Image.new("L", (tw + 2 * pad, asc + desc + 2 * pad))
    d = ImageDraw.Draw(im)
    if spacing:
        x = pad
        for ch, w in zip(s, widths):
            d.text((x, pad), ch, font=f, fill=255); x += w + spacing
    else:
        d.text((pad, pad), s, font=f, fill=255)
    a = np.asarray(im)
    ys = np.where(a.max(1) > 0)[0]
    if len(ys):                                      # trim vertical padding
        a = a[max(0, ys[0] - 4):ys[-1] + 5]
    return a

@functools.lru_cache(maxsize=512)
def math_mask(tex, px):
    buf = io.BytesIO()
    mathtext.math_to_image("$" + tex + "$", buf, dpi=100, format="png",
                           prop=FontProperties(size=px * 72 / 100, math_fontfamily="cm"))
    a = np.asarray(Image.open(io.BytesIO(buf.getvalue())).convert("L"))
    return np.ascontiguousarray(255 - a)


class Canvas:
    def __init__(self):
        self.bg = np.zeros((H, W, 3), np.uint8)    # graphics (strong bloom)
        self.fg = np.zeros((H, W, 3), np.uint8)    # text (soft bloom)
        self.dims = []

    def blit(self, m, x, y, color, alpha=1.0, anchor="c", scale=1.0, layer="fg", wipe=1.0):
        if alpha <= 0.003 or m is None:
            return
        if scale != 1.0:
            m = cv2.resize(m, None, fx=scale, fy=scale,
                           interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_LINEAR)
        h, w = m.shape
        if wipe < 1.0:
            ramp = np.clip((wipe * (w + 80) - np.arange(w)) / 80, 0, 1)
            m = (m * ramp[None]).astype(np.uint8)
        x0 = int(round(x - (w / 2 if anchor == "c" else (w if anchor == "r" else 0))))
        y0 = int(round(y - h / 2))
        ax0, ay0 = max(x0, 0), max(y0, 0)
        ax1, ay1 = min(x0 + w, W), min(y0 + h, H)
        if ax1 <= ax0 or ay1 <= ay0:
            return
        sub = m[ay0 - y0:ay1 - y0, ax0 - x0:ax1 - x0]
        col = np.array(color, np.float32) * (alpha / 255.0)
        src = (sub[..., None] * col).astype(np.uint8)
        dst = (self.fg if layer == "fg" else self.bg)[ay0:ay1, ax0:ax1]
        np.maximum(dst, src, out=dst)
        return w, h

    def text(self, s, x, y, size, font="sans", color=WHITE, alpha=1.0, spacing=0, **kw):
        return self.blit(text_mask(s, font, size, spacing), x, y, color, alpha, **kw)

    def math(self, tex, x, y, px, color=WHITE, alpha=1.0, **kw):
        return self.blit(math_mask(tex, px), x, y, color, alpha, **kw)

    def dim(self, x0, y0, x1, y1, a):
        self.dims.append((x0, y0, x1, y1, a))


def P(x, y): return (int(round(x * S16)), int(round(y * S16)))
def line(img, p, q, c, th=1): cv2.line(img, P(*p), P(*q), c, th, cv2.LINE_AA, SH)
def circle(img, p, r, c, th=1): cv2.circle(img, P(*p), int(round(r * S16)), c, th, cv2.LINE_AA, SH)
def polys(img, pts, c, th=1, closed=False):
    if len(pts):
        cv2.polylines(img, [np.round(np.asarray(p) * S16).astype(np.int32) for p in pts],
                      closed, c, th, cv2.LINE_AA, SH)
def dots(img, xy, c, r=1):
    xy = np.round(xy).astype(int)
    for dx in range(-r + 1, r):
        for dy in range(-r + 1, r):
            x, y = xy[:, 0] + dx, xy[:, 1] + dy
            ok = (x >= 0) & (x < W) & (y >= 0) & (y < H)
            img[y[ok], x[ok]] = np.maximum(img[y[ok], x[ok]], c)

# ---------------------------------------------------------------- global layers
rng0 = np.random.default_rng(3)
def _fog():
    f = np.zeros((600, 1000), np.float32)
    for s, a in [(80, 1), (35, .6), (14, .35)]:
        f += cv2.GaussianBlur(rng0.standard_normal((600, 1000)).astype(np.float32), (0, 0), s) * a * s / 10
    f = (f - f.min()) / (f.max() - f.min())
    return f ** 2.2
FOG = _fog()
GRAIN = [cv2.resize(rng0.standard_normal((H // 2, W // 2)).astype(np.float32), (W, H))
         for _ in range(8)]
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
RAD = np.sqrt(((xx - CX) / (W * .62)) ** 2 + ((yy - CY) / (H * .62)) ** 2)
del yy, xx
DUST = rng0.random((260, 3)) * [W, H, 1]

CHAPTERS = [("壹", "乘法原理", 10), ("贰", "排列", 26), ("叁", "组合", 42), ("肆", "容斥原理", 60),
            ("伍", "卡特兰数", 76), ("陆", "生成函数", 94), ("柒", "拉姆齐数", 108)]


def ambient(cv, t):
    """Drifting fog + dust in the section colour."""
    if t >= CUT and t < FINAL:
        return None
    c = np.array(accent(t), np.float32) / 255
    ox = int(250 + 200 * math.sin(t * .05)); oy = int(150 + 120 * math.cos(t * .037))
    f = FOG[oy:oy + 270, ox:ox + 480]
    press = ss(90, 125, t)
    lvl = .07 + .06 * press + .05 * kick_env(t) * (t > 42)
    if t >= FINAL:
        lvl = .05
    fog = cv2.resize(f, (W, H), interpolation=cv2.INTER_LINEAR)[..., None] * c * lvl
    # dust
    z = DUST[:, 2]
    x = (DUST[:, 0] + t * (8 + 30 * z) * (1 + 3 * press)) % W
    y = (DUST[:, 1] - t * (4 + 10 * z)) % H
    dots(cv.bg, np.stack([x, y], 1)[z > .5], sc(accent(t), .5), 2)
    dots(cv.bg, np.stack([x, y], 1)[z <= .5], sc(accent(t), .3), 1)
    return fog


def chapter_card(cv, t, idx):
    num, title, t0 = CHAPTERS[idx]
    subs = ["每一次选择，都让世界分裂", "顺序，就是一切", "不问顺序，只问选谁",
            "多算的减掉，多减的加回", "同一串数字，藏在无数问题里",
            "把无穷数列，装进一个函数", "完全的无序，是不可能的"]
    u = t - t0
    if not (0 <= u < 3.3):
        return
    a = 1 - ss(2.8, 3.3, u)
    col = RED if idx == 6 else accent(t)
    cv.text(num, CX, CY - 20, 560, "serif", col, .13 * a * ss(0, .3, u), scale=1.12 - .12 * eo(u / 3), layer="bg")
    s = 1.35 - .35 * eo(u / .35)
    cv.text(title, CX, CY - 40 - 20 * ss(2.8, 3.3, u), 150, "serif", WHITE, a * ss(0, .12, u), spacing=18, scale=s)
    wline = 700 * eo((u - .15) / .8)
    if wline > 1:
        line(cv.bg, (CX - wline / 2, CY + 60), (CX + wline / 2, CY + 60), sc(col, a), 2)
    cv.text(subs[idx], CX, CY + 125, 46, "sans", mix(WHITE, col, .3), a, spacing=6,
            wipe=eo((u - .5) / 1.1))


def hud(cv, t):
    if not (13 <= t < CUT):
        return
    idx = max(i for i, c in enumerate(CHAPTERS) if c[2] <= t)
    num, title, t0 = CHAPTERS[idx]
    a = ss(t0 + 3.0, t0 + 3.6, t) * .75
    cv.text(f"{num} · {title}", 70, 62, 30, "sansb", accent(t), a, anchor="l", spacing=4)
    for i in range(7):
        x = CX + (i - 3) * 34
        on = i <= idx
        circle(cv.fg, (x, H - 46), 4 if i == idx else 3, sc(accent(t) if on else WHITE, .9 if on else .25),
               -1 if on else 1)


# ================================================================ scenes
def intro(cv, t):
    # a point that keeps splitting
    lvl = sum(1 for s in SPLITS if t >= s)
    if t >= SPLITS[0]:
        blow = 1 + 2.8 * eo((t - 6) / 2.5) if t >= 6 else 1
        fade = 1 - ss(7.2, 9.0, t)
        r = np.random.default_rng(11)
        angs = [r.random(2 ** k) * 2 * np.pi for k in range(len(SPLITS))]
        levels = [np.zeros((1, 2))]
        for k in range(1, lvl):
            u = eo((t - SPLITS[k]) / .45)
            ids = np.arange(2 ** k)
            sgn = np.where(ids & 1, 1, -1) * 330 * .74 ** k * u
            vec = np.stack([np.cos(angs[k][ids >> 1]), np.sin(angs[k][ids >> 1])], 1) * sgn[:, None]
            levels.append(levels[-1][ids >> 1] + vec)
        org = np.array([CX, CY - 30])
        L = [p * blow + org for p in levels]
        for k in range(1, len(L)):
            par = L[k - 1][np.arange(len(L[k])) >> 1]
            polys(cv.bg, list(np.stack([par, L[k]], 1)), sc(mix(ICE, WHITE, k / 8), (.25 + .35 * k / 8) * fade), 1)
            dots(cv.bg, L[k - 1], sc(ICE, .45 * fade), 2)
        pos = L[-1]; n = len(pos)
        pulse = math.exp(-(t - SPLITS[lvl - 1]) * 6)
        dots(cv.bg, pos, sc(WHITE, fade), 4 if n < 32 else 3)
        for p in pos[:16]:
            circle(cv.bg, p, 8 + 26 * (1 - pulse), sc(ICE, .7 * pulse * fade), 2)
        if t < 6:
            cv.text(f"{n}", CX, H - 170, 72, "serifb", ICE, .8 * ss(2.1, 2.4, t),
                    scale=1 + .2 * pulse, layer="fg")
    # title
    if t >= 6:
        u = t - 6
        a = 1 - ss(8.9, 9.8, t)
        cv.text("组合数学", CX, CY - 40, 210, "serif", WHITE, a, spacing=40, scale=1.3 - .3 * eo(u / .4))
        cv.text("COMBINATORICS", CX, CY + 110, 34, "sans", ICE, .8 * a, spacing=22, wipe=eo((u - .3) / 1.2))
        cv.text("数清楚，是一门艺术", CX, CY + 185, 42, "sans", WHITE, .85 * a * ss(7.0, 7.6, t), spacing=8)


def mult(cv, t):
    chapter_card(cv, t, 0)
    # --- 3 x 4 outfit grid
    if 12.8 <= t < 18.2:
        a = win(t, 12.8, 18.0)
        shirts = [(255, 110, 110), (110, 220, 190), (255, 205, 110)]
        pants = [(120, 160, 255), (200, 140, 255), (240, 240, 240), (120, 230, 255)]
        gx0, gy0, dx, dy = 800, 390, 150, 150
        cv.text("上衣 ×3", 600, 280, 34, "sansb", WHITE, .8 * a)
        cv.text("裤子 ×4", 1260, 250, 34, "sansb", WHITE, .8 * a, anchor="l")
        for i, c in enumerate(shirts):
            circle(cv.bg, (600, gy0 + i * dy), 30 * eo((t - 12.8 - i * .1) / .3), sc(c, a), -1)
        for j, c in enumerate(pants):
            h = 56 * eo((t - 13 - j * .1) / .3)
            cv2.rectangle(cv.bg, P(gx0 + j * dx - 14, 300 - h / 2), P(gx0 + j * dx + 14, 300 + h / 2), sc(c, a), -1, cv2.LINE_AA, SH)
        k_now = int((t - GRID_T0) / GRID_DT) + 1 if t >= GRID_T0 else 0
        for k in range(min(k_now, 12)):
            i, j = divmod(k, 4)
            u = (t - GRID_T0 - k * GRID_DT)
            s = pop(u / .3)
            x, y = gx0 + j * dx, gy0 + i * dy
            circle(cv.bg, (x, y - 18 * s), 17 * s, sc(shirts[i], a), -1)
            cv2.rectangle(cv.bg, P(x - 9 * s, y + 2), P(x + 9 * s, y + 40 * s), sc(pants[j], a), -1, cv2.LINE_AA, SH)
            ring = math.exp(-u * 5)
            circle(cv.bg, (x, y + 5), 30 + 50 * (1 - ring), sc(WHITE, .6 * ring * a), 2)
        cnt = min(k_now, 12)
        if cnt:
            cv.text(str(cnt), 1560, 540, 200, "serif", CYAN, a, scale=1 + .15 * math.exp(-(t - GRID_T0 - (cnt - 1) * GRID_DT) * 8))
        cv.math(r"3 \times 4 = 12", CX, 900, 90, WHITE, a * ss(16.0, 16.4, t))
    # --- radial binary tree 2^n
    if 17.8 <= t < 26:
        a = win(t, 17.8, 25.9, .3, .5)
        rot = (t - 18) * .06
        L = int((t - TREE_T0) / TREE_DT) if t >= TREE_T0 else -1
        L = min(L, TREE_N - 1)
        cxy = np.array([CX - 180, CY + 20])
        Rmax = 470
        def pos(l, i):
            ang = (i + .5) / 2 ** l * 2 * np.pi + rot
            r = Rmax * (l / (TREE_N - 1)) ** .8
            return cxy + np.stack([np.cos(ang), np.sin(ang)], -1) * r[..., None] if np.ndim(r) else \
                cxy + np.stack([np.cos(ang), np.sin(ang)], -1) * r
        for l in range(1, L + 1):
            u = eo((t - TREE_T0 - l * TREE_DT) / .35)
            i = np.arange(2 ** l)
            p0 = pos(l - 1, i >> 1); p1 = pos(l, i)
            p1 = p0 + (p1 - p0) * u
            col = mix(CYAN, WHITE, l / TREE_N)
            br = (.9 - .045 * l) * a * (1 if l < 8 else .55 ** (l - 7))
            polys(cv.bg, list(np.stack([p0, p1], 1)), sc(col, br), 2 if l < 5 else 1)
        if L >= 0:
            fr = pos(L, np.arange(2 ** L))
            dots(cv.bg, fr, sc(WHITE, a), 3 if L < 6 else (2 if L < 10 else 1))
            if L == 0:
                circle(cv.bg, cxy, 6, sc(WHITE, a), -1)
        # counter
        if t < 24.0:
            n = max(L, 0)
            ex = str(n)
        else:
            n = min(64, 12 + int((t - 24.0) / .025))
            ex = str(n)
        val = 2 ** n
        bump = math.exp(-((t - TREE_T0) % TREE_DT) * 8) if t < 24 else .3
        cv.math(r"2^{" + ex + "}", 1480, 340, 110, CYAN, a * ss(18, 18.3, t), scale=1 + .1 * bump)
        vs = f"{val:,}"
        size = 110 if len(vs) < 10 else max(40, int(110 * 10 / len(vs)))
        cv.text(vs, 1480, 500, size, "serifb", WHITE, a * ss(18, 18.3, t))
        cv.text("每多一次选择，可能性就翻一倍", 1480, 650, 38, "sans", mix(WHITE, CYAN, .3), a * ss(19.5, 20.2, t), spacing=4)
        if t >= 25.0:
            cv.text("64 次二选一  >  地球上的沙粒数", 1480, 740, 36, "sansb", CYAN, a * ss(25.0, 25.3, t), spacing=3)


PERMS = list(itertools.permutations(range(4)))
FACTS = [(n, math.factorial(n)) for n in range(5, 17)]


def perm(cv, t):
    chapter_card(cv, t, 1)
    if 28.8 <= t < 35.2:
        a = win(t, 28.8, 35.1, .3, .4)
        k = int(clamp((t - PERM_T0) / PERM_DT, 0, 23))
        u = eio((t - PERM_T0 - k * PERM_DT) / (PERM_DT * .8)) if t >= PERM_T0 else 1
        prev = PERMS[k - 1] if k else PERMS[0]
        cur = PERMS[k]
        cols = [(255, 120, 150), (120, 220, 255), (255, 210, 120), (190, 150, 255)]
        for letter in range(4):
            i0, i1 = prev.index(letter), cur.index(letter)
            x = 960 + ((i0 + (i1 - i0) * u) - 1.5) * 200
            y = 420 - math.sin(math.pi * u) * 70 * np.sign(i1 - i0)
            circle(cv.bg, (x, y), 64, sc(cols[letter], .9 * a), 3)
            circle(cv.bg, (x, y), 58, sc(cols[letter], .15 * a), -1)
            cv.text("ABCD"[letter], x, y, 72, "serif", cols[letter], a)
        # accumulated list of permutations
        for j in range(k + 1):
            r, c = divmod(j, 8)
            s = "".join("ABCD"[v] for v in PERMS[j])
            hl = j == k
            cv.text(s, 960 + (c - 3.5) * 190, 660 + r * 72, 44, "sansb" if hl else "sans",
                    WHITE if hl else VIOLET, a * (1 if hl else .55), spacing=6)
        cv.text(f"{k + 1} / 24", 1700, 420, 50, "serifb", VIOLET, a)
        cv.math(r"4! = 4\times3\times2\times1 = 24", 960, 200, 76, WHITE, a * ss(33.0, 33.4, t))
    if 34.9 <= t < 38.05:
        a = win(t, 34.9, 38.0, .2, .12)
        k = int(clamp((t - FACT_T0) / FACT_DT, 0, 11))
        scroll = eo((t - FACT_T0 - k * FACT_DT) / .18)
        for j in range(k + 1):
            n, v = FACTS[j]
            y = 880 - (k - j - 1 + scroll) * 76 if j < k else 880 - (scroll - 1) * 0 - 0
            if j == k:
                y = 880 + (1 - scroll) * 40
            al = a * clamp(1 - (880 - y) / 800) * (scroll if j == k else 1)
            cv.text(f"{n}!", 760, y, 58, "serif", VIOLET, al, anchor="r")
            cv.text("=  " + f"{v:,}", 800, y, 58, "serifb", WHITE, al, anchor="l")
    if 38 <= t < 42:
        u = t - 38
        a = 1 - ss(41.5, 42.0, t)
        # swirling deck of cards
        r = np.random.default_rng(52)
        ph = r.random(52) * 2 * np.pi; rad = 300 + r.random(52) * 480; tilt = r.random(52) * 2 * np.pi
        ang = ph + u * (.5 + .6 * r.random(52))
        cx = CX + np.cos(ang) * rad * (0.4 + .6 * eo(u / .6)); cy = CY + np.sin(ang) * rad * .45
        for i in range(52):
            c, s_ = math.cos(tilt[i] + u * 1.5), math.sin(tilt[i] + u * 1.5)
            corners = np.array([[-26, -38], [26, -38], [26, 38], [-26, 38]]) @ np.array([[c, s_], [-s_, c]])
            polys(cv.bg, [corners + [cx[i], cy[i]]], sc(mix(VIOLET, WHITE, (i % 13) / 13), .55 * a), 1, True)
        cv.dim(300, 250, 1620, 900, .75 * a)
        cv.text("52!", CX, 420, 330, "serif", WHITE, a, scale=1.5 - .5 * eo(u / .3))
        digits = str(math.factorial(52))
        cv.text(digits, CX, 640, 34, "sans", VIOLET, a * .9, spacing=2, wipe=eo((u - .4) / .8))
        cv.math(r"\approx 8.07 \times 10^{67}", CX, 740, 84, WHITE, a * ss(39.1, 39.4, t))
        cv.text("随手洗一副牌，这个顺序几乎肯定从未在宇宙中出现过", CX, 870, 42, "sans", WHITE,
                a * ss(39.7, 40.2, t), spacing=3)


def pascal(n, k): return math.comb(n, k)
ODD = np.array([(r, k) for r in range(512) for k in range(r + 1) if (k & r) == k], np.float32)


def comb(cv, t):
    chapter_card(cv, t, 2)
    if 44.8 <= t < 48.1:
        a = win(t, 44.8, 48.0, .3, .35)
        c0 = np.array([700, 540])
        pts = [c0 + 230 * np.array([math.cos(-math.pi / 2 + i * 2 * math.pi / 5),
                                    math.sin(-math.pi / 2 + i * 2 * math.pi / 5)]) for i in range(5)]
        pairs = list(itertools.combinations(range(5), 2))
        k = int((t - PAIR_T0) / PAIR_DT) + 1 if t >= PAIR_T0 else 0
        for j in range(min(k, 10)):
            p, q = pairs[j]
            u = eo((t - PAIR_T0 - j * PAIR_DT) / .2)
            hl = math.exp(-(t - PAIR_T0 - j * PAIR_DT) * 5)
            line(cv.bg, pts[p], pts[p] + (pts[q] - pts[p]) * u, sc(mix(GOLD, WHITE, hl), a * (.7 + .3 * hl)), 2 + int(2 * hl))
        for i, p in enumerate(pts):
            circle(cv.bg, p, 22, sc(GOLD, a), -1)
            cv.text("ABCDE"[i], *(c0 + (p - c0) * 1.28), 40, "serifb", WHITE, a)
        cv.math(r"\binom{5}{2} = " + str(min(k, 10)), 1350, 420, 110, WHITE, a)
        cv.math(r"\binom{n}{k} = \frac{n!}{k!\,(n-k)!}", 1350, 680, 84, GOLD, a * ss(46.4, 46.8, t))
    if 47.8 <= t < 54.3:
        a = win(t, 47.8, 60, .3, .1) * (1 - ss(54.0, 54.3, t))
        R = int((t - PASCAL_T0) / PASCAL_DT) if t >= PASCAL_T0 else -1
        dx, dy, top = 78, 64, 150
        for r in range(min(R, PASCAL_N - 1) + 1):
            u0 = t - PASCAL_T0 - r * PASCAL_DT
            for k in range(r + 1):
                u = u0 - k * .025
                x = CX + (k - r / 2) * dx; y = top + r * dy
                if r and u > 0:
                    for kk in (k - 1, k):
                        if 0 <= kk <= r - 1:
                            px, py = CX + (kk - (r - 1) / 2) * dx, top + (r - 1) * dy
                            e = eo(u / .25)
                            line(cv.bg, (px, py + 20), (px + (x - px) * e, py + 20 + (y - 20 - py - 20) * e),
                                 sc(GOLD, a * (.25 + .5 * math.exp(-u * 4))), 1)
                if u > 0:
                    v = pascal(r, k)
                    s = pop(u / .25)
                    size = 30 if v < 100 else 26
                    cv.text(str(v), x, y, size, "sansb", mix(GOLD, WHITE, math.exp(-u * 3)), a * clamp(u / .1), scale=s)
        cv.math(r"\binom{n}{k}=\binom{n-1}{k-1}+\binom{n-1}{k}", 1560, 930, 58, WHITE, a * ss(50.0, 50.4, t))
    if 54 <= t < 60:
        a = 1 - ss(59.4, 60.0, t)
        u = eio((t - 54) / 4.6)
        N = 12 * (512 / 12) ** u
        top, hgt = 110, 860
        sp = hgt / N
        sel = ODD[ODD[:, 0] < N]
        x = CX + (sel[:, 1] - sel[:, 0] / 2) * sp * 1.15
        y = top + sel[:, 0] * sp
        col = sc(mix(GOLD, WHITE, math.exp(-(t - 54) * 1.5)), a)
        if sp > 5:
            for xi, yi in zip(x, y):
                circle(cv.bg, (xi, yi), sp * .32, col, -1)
        else:
            dots(cv.bg, np.stack([x, y], 1), col, 2 if sp > 2 else 1)
        cv.text("把奇数点亮", 250, 470, 50, "serifb", WHITE, a * ss(55.0, 55.4, t), anchor="l")
        cv.text("谢尔宾斯基三角形", 250, 550, 40, "sans", GOLD, a * ss(55.5, 55.9, t), anchor="l", spacing=3)
        cv.text("无穷层的自相似", 250, 620, 34, "sans", WHITE, .7 * a * ss(56.3, 56.7, t), anchor="l", spacing=3)


VENN_C = [(680, 470), (920, 470), (800, 675)]
VENN_R = 205
_vy, _vx = np.mgrid[0:H // 2, 0:W // 2]
VIN = [((_vx * 2 - cx) ** 2 + (_vy * 2 - cy) ** 2 < VENN_R ** 2) for cx, cy in VENN_C]
TERMS = [((0,), 1), ((1,), 1), ((2,), 1), ((0, 1), -1), ((0, 2), -1), ((1, 2), -1), ((0, 1, 2), 1)]
ATOMS = {(1, 0, 0): (610, 420), (0, 1, 0): (990, 420), (0, 0, 1): (800, 760),
         (1, 1, 0): (800, 420), (1, 0, 1): (680, 610), (0, 1, 1): (920, 610), (1, 1, 1): (800, 540)}
DER = [sum((-1) ** k / math.factorial(k) for k in range(n + 1)) for n in range(1, DER_N + 1)]


def incl(cv, t):
    chapter_card(cv, t, 3)
    if 62.8 <= t < 67.1:
        a = win(t, 62.8, 67.0, .3, .35)
        cols = [TEAL, MAGENTA, GOLD]
        k = int((t - VENN_T0) / VENN_DT) + 1 if t >= VENN_T0 else 0
        k = min(k, 7)
        if k:
            sets, sg = TERMS[k - 1]
            m = np.logical_and.reduce([VIN[i] for i in sets])
            hl = math.exp(-(t - VENN_T0 - (k - 1) * VENN_DT) * 4)
            c = np.array((90, 255, 160) if sg > 0 else (255, 70, 90)) * (.18 + .3 * hl) * a
            full = cv2.resize(m.astype(np.uint8) * 255, (W, H), interpolation=cv2.INTER_LINEAR)
            np.maximum(cv.bg, (full[..., None] / 255.0 * c).astype(np.uint8), out=cv.bg)
        for (cx, cy), c in zip(VENN_C, cols):
            circle(cv.bg, (cx, cy), VENN_R, sc(c, a), 3)
        for i, (cx, cy) in enumerate(VENN_C):
            off = [(-150, -150), (150, -150), (0, 170)][i]
            cv.text("ABC"[i], cx + off[0], cy + off[1], 56, "serif", cols[i], a)
        for atom, (x, y) in ATOMS.items():
            cnt = sum(sg for sets, sg in TERMS[:k] if all(atom[i] for i in sets))
            if any(all(atom[i] for i in sets) for sets, _ in TERMS[:k]):
                col = TEAL if cnt == 1 else (RED if cnt > 1 else WHITE)
                cv.text(str(cnt), x, y, 46, "sansb", col, a)
        lines = [(r"|A\cup B\cup C|", 0), (r"= |A|+|B|+|C|", 1), (r"-\,|A\cap B|-|A\cap C|-|B\cap C|", 4),
                 (r"+\,|A\cap B\cap C|", 7)]
        for j, (tex, need) in enumerate(lines):
            cv.math(tex, 1170, 330 + j * 100, 48, WHITE, a * (1 if k >= need else 0), anchor="l")
        cv.text("每块区域最终都只算一次", 1170, 780, 38, "sansb", TEAL, a * ss(66.3, 66.6, t), anchor="l", spacing=3)
    if 66.8 <= t < 76:
        a = win(t, 66.8, 75.8, .3, .5)
        cv.text("n 封信随机装进 n 个信封，全部装错的概率？", CX, 140, 46, "sansb", WHITE, a, spacing=3)
        x0, x1, ybase = 300, 1300, 880
        def Y(v): return ybase - v * 1000
        line(cv.bg, (x0 - 20, ybase), (x1 + 40, ybase), sc(WHITE, .35 * a), 1)
        e = 1 / math.e
        dash = 1 + .5 * hit_env(t) * (t > 72)
        for xs in range(x0, x1 + 40, 24):
            line(cv.bg, (xs, Y(e)), (xs + 12, Y(e)), sc(GOLD, clamp(.6 * a * dash)), 2)
        k = int((t - DER_T0) / DER_DT) + 1 if t >= DER_T0 else 0
        k = min(k, DER_N)
        pts = [(x0 + (n) * (x1 - x0) / (DER_N - 1), Y(DER[n])) for n in range(DER_N)]
        for n in range(k):
            u = eo((t - DER_T0 - n * DER_DT) / .25)
            if n:
                line(cv.bg, pts[n - 1], (pts[n - 1][0] + (pts[n][0] - pts[n - 1][0]) * u,
                                         pts[n - 1][1] + (pts[n][1] - pts[n - 1][1]) * u), sc(TEAL, a), 2)
            circle(cv.bg, pts[n], 7 * pop(u), sc(WHITE, a), -1)
            cv.text(str(n + 1), pts[n][0], ybase + 40, 28, "sans", WHITE, .6 * a)
        if k:
            cv.text(f"{DER[k - 1]:.7f}", 1620, 360, 70, "serifb", WHITE, a)
            cv.text(f"n = {k}", 1620, 280, 40, "sans", TEAL, a)
        cv.math(r"\frac{D_n}{n!} = \sum_{k=0}^{n}\frac{(-1)^k}{k!}", 1620, 560, 60, WHITE, a * ss(68.5, 69, t))
        if t >= 72:
            u = t - 72
            cv.math(r"\to\ \frac{1}{e}", 1620, 800, 150, GOLD, a, scale=1.4 - .4 * eo(u / .3))
            cv.text("e = 2.71828…  从数数里冒了出来", CX - 180, 980, 38, "sans", GOLD, a * ss(72.6, 73.1, t), spacing=3)


def dyck_paths(n):
    out = []
    for combo in itertools.combinations(range(2 * n), n):
        s = [1 if i in combo else -1 for i in range(2 * n)]
        if all(sum(s[:i + 1]) >= 0 for i in range(2 * n)):
            out.append(s)
    return out
DYCK = dyck_paths(4)


def hex_triangulations():
    diags = [(i, j) for i in range(6) for j in range(i + 2, 6) if not (i == 0 and j == 5)]
    def cross(a, b):
        (p, q), (r, s) = a, b
        return (p < r < q < s) or (r < p < s < q)
    return [c for c in itertools.combinations(diags, 3)
            if not any(cross(x, y) for x, y in itertools.combinations(c, 2))]
TRI = hex_triangulations()
CATALAN = [math.comb(2 * n, n) // (n + 1) for n in range(40)]


def catalan(cv, t):
    chapter_card(cv, t, 4)
    if 78.8 <= t < 85.1:
        a = win(t, 78.8, 85.0, .3, .4)
        sx, sy, st = 500, 700, 110
        for i in range(9):
            for j in range(5):
                if j <= i <= 8 - j:
                    if (i + j) % 2 == 0:
                        dots(cv.bg, np.array([[sx + i * st, sy - j * st]]), sc(WHITE, .35 * a), 3)
        line(cv.bg, (sx - 40, sy), (sx + 8 * st + 40, sy), sc(WHITE, .3 * a), 1)
        k = int((t - DYCK_T0) / DYCK_DT) if t >= DYCK_T0 else -1
        k = min(k, 13)
        for j in range(k + 1):
            u = (t - DYCK_T0 - j * DYCK_DT) / .3
            path = DYCK[j]
            h = np.concatenate([[0], np.cumsum(path)])
            xy = np.stack([sx + np.arange(9) * st, sy - h * st], 1).astype(float)
            m = clamp(u) * 8
            nfull = int(m)
            seg = xy[:nfull + 1]
            if nfull < 8:
                seg = np.vstack([seg, xy[nfull] + (xy[nfull + 1] - xy[nfull]) * (m - nfull)])
            cur = j == k
            col = mix(INDIGO, MAGENTA, j / 13) if not cur else WHITE
            off = (j - 6.5) * 1.6
            polys(cv.bg, [seg + [0, off]], sc(col, a * (1 if cur else .45)), 3 if cur else 2)
            if cur:
                dots(cv.bg, seg[-1:], sc(WHITE, a), 6)
                par = " ".join("(" if s > 0 else ")" for s in path)
                cv.text(par, CX, 820, 62, "sansb", WHITE, a, spacing=4)
        if k >= 0:
            cv.text(f"{k + 1}", 1620, 330, 170, "serif", INDIGO, a)
            cv.text("/ 14", 1620, 450, 40, "sans", WHITE, .7 * a)
        cv.text("配对的括号  =  不跌破地平线的山路", CX, 950, 40, "sans", mix(WHITE, INDIGO, .3), a * ss(82.0, 82.5, t), spacing=3)
    if 84.8 <= t < 94:
        a = win(t, 84.8, 93.8, .3, .4)
        shrink = eio((t - 90) / .8) if t >= 90 else 0
        cv.text("六边形的三角剖分 —— 也恰好 14 种", CX, 150, 46, "sansb", WHITE, a * (1 - shrink), spacing=3)
        k = int((t - TRI_T0) / TRI_DT) + 1 if t >= TRI_T0 else 0
        for i in range(14):
            r_, c_ = divmod(i, 7)
            cx = CX + (c_ - 3) * 240; cy = 400 + r_ * 270
            cy = cy + shrink * (-cy + 110 + r_ * 70); cx = CX + (cx - CX) * (1 - .55 * shrink)
            R = 92 * (1 - .65 * shrink)
            vs = [(cx + R * math.cos(math.pi / 2 + j * math.pi / 3), cy - R * math.sin(math.pi / 2 + j * math.pi / 3)) for j in range(6)]
            polys(cv.bg, [np.array(vs)], sc(WHITE, .45 * a), 1, True)
            if i < k:
                u = t - TRI_T0 - i * TRI_DT
                hl = math.exp(-u * 4)
                for (p, q) in TRI[i]:
                    e = eo(u / .2)
                    line(cv.bg, vs[p], (vs[p][0] + (vs[q][0] - vs[p][0]) * e, vs[p][1] + (vs[q][1] - vs[p][1]) * e),
                         sc(mix(INDIGO, WHITE, hl), a), 2)
    if 90 <= t < 94:
        u = t - 90
        a = 1 - ss(93.5, 94.0, t)
        cv.dim(200, 380, 1720, 960, .6 * a)
        cv.math(r"C_n = \frac{1}{n+1}\binom{2n}{n}", CX, 560, 120, WHITE, a, scale=1.3 - .3 * eo(u / .3))
        off = u * 380 * (1 + u * .6)
        x = W + 60 - off
        for n, v in enumerate(CATALAN):
            s = f"{v:,}"
            if x > W + 200:
                break
            if x > -800:
                cv.text(s, x, 800, 52, "serifb", mix(INDIGO, WHITE, min(1, n / 12)), a, anchor="l")
            x += len(s) * 30 + 90
        cv.text("括号 · 山路 · 剖分 · 二叉树 · 出栈顺序 …… 两百多种问题，同一个答案", CX, 930, 36, "sans",
                WHITE, .8 * a * ss(91, 91.5, t), spacing=2)


def fib_squares():
    out = []
    f = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55]
    x0, y0, x1, y1 = 0, 0, 1, 1
    out.append(((0, 0, 1, 1), "U"))
    dirs = ["R", "D", "L", "U"]
    for i, s in enumerate(f[1:]):
        d = dirs[i % 4]
        if d == "R": sq = (x1, y0, x1 + s, y0 + s)
        elif d == "D": sq = (x0, y1, x0 + s, y1 + s)
        elif d == "L": sq = (x0 - s, y0, x0, y0 + s)
        else: sq = (x0, y0 - s, x0 + s, y0)
        out.append((sq, d))
        x0, y0, x1, y1 = min(x0, sq[0]), min(y0, sq[1]), max(x1, sq[2]), max(y1, sq[3])
    return out, (x0, y0, x1, y1)
FIB_SQ, FIB_BB = fib_squares()


def tree_segments(depth=10):
    segs = []
    def rec(x, y, ang, ln, d):
        if d > depth:
            return
        x2, y2 = x + math.cos(ang) * ln, y + math.sin(ang) * ln
        segs.append((x, y, x2, y2, d))
        rec(x2, y2, ang - .45, ln * .74, d + 1)
        rec(x2, y2, ang + .45, ln * .74, d + 1)
    rec(0, 0, -math.pi / 2, 170, 0)
    return np.array(segs)
TREE = tree_segments()


def genf(cv, t):
    chapter_card(cv, t, 5)
    if 96.8 <= t < 102.1:
        a = win(t, 96.8, 102.0, .3, .3)
        # golden spiral backdrop
        s = 15.0
        bx0, by0, bx1, by1 = FIB_BB
        ox = CX - (bx0 + bx1) / 2 * s; oy = CY + 30 - (by0 + by1) / 2 * s
        nsq = clamp((t - 97) / 3.5) * len(FIB_SQ)
        for i, ((x0, y0, x1, y1), d) in enumerate(FIB_SQ):
            if i >= nsq:
                break
            e = clamp(nsq - i)
            cv2.rectangle(cv.bg, P(ox + x0 * s, oy + y0 * s), P(ox + x1 * s, oy + y1 * s), sc(GOLD, .22 * a * e), 1, cv2.LINE_AA, SH)
            r = (x1 - x0) * s
            cen, st = {"R": ((x0, y1), 270), "D": ((x0, y0), 0), "L": ((x1, y0), 90), "U": ((x1, y1), 180)}[d]
            cv2.ellipse(cv.bg, P(ox + cen[0] * s, oy + cen[1] * s), (int(r * S16), int(r * S16)), 0, st, st + 90 * e,
                        sc(GOLD, .7 * a), 2, cv2.LINE_AA, SH)
        cv.dim(260, 330, 1660, 780, .65 * a)
        terms = ["1", "+\\,x", "+\\,2x^2", "+\\,3x^3", "+\\,5x^4", "+\\,8x^5", "+\\,13x^6", "+\\,21x^7", "+\\,\\cdots"]
        k = int(clamp((t - 97.2) / .3 + 1, 0, len(terms)))
        coll = eio((t - 100.3) / .5)
        tex = "".join(terms[:k]) if k else "\\,"
        cv.math(tex, CX, 430 + 40 * coll, 76, WHITE, a * (1 - .5 * coll))
        cv.text("斐波那契：1, 1, 2, 3, 5, 8, 13, 21 …", CX, 300, 40, "sans", GOLD, a * ss(97, 97.4, t), spacing=3)
        if t >= 100.1:
            cv.math(r"= \frac{1}{1-x-x^2}", CX, 640, 120, GOLD, a, scale=1.4 - .4 * eo((t - 100.1) / .3))
            cv.text("整条无穷序列  =  一个分式", CX, 860, 40, "sansb", WHITE, a * ss(100.7, 101.1, t), spacing=4)
    if 102 <= t < 108:
        u = t - 102
        a = 1 - ss(107.4, 108.0, t)
        dep = clamp(u / 3.5) * 11
        sel = TREE[TREE[:, 4] < dep]
        e = np.clip(dep - sel[:, 4], 0, 1)[:, None]
        p0 = sel[:, :2] + [CX, 1040]; p1 = p0 + (sel[:, 2:4] - sel[:, :2]) * e
        for d in range(11):
            m = sel[:, 4] == d
            polys(cv.bg, list(np.stack([p0[m], p1[m]], 1)), sc(mix(GOLD, WHITE, d / 10), .45 * a * (1 - d / 14)), 2 if d < 3 else 1)
        cv.dim(300, 250, 1620, 880, .7 * a)
        cv.math(r"C(x) = 1 + x\,C(x)^2", CX, 360, 90, WHITE, a * ss(102, 102.2, t), scale=1.3 - .3 * eo(u / .3))
        cv.math(r"C(x) = \frac{1-\sqrt{1-4x}}{2x}", CX, 580, 110, GOLD, a * ss(103.0, 103.3, t),
                scale=1.3 - .3 * eo((u - 1) / .3))
        cv.text("一个方程，解出整条卡特兰数列", CX, 800, 42, "sansb", WHITE, a * ss(104.0, 104.5, t), spacing=4)


def ramsey(cv, t):
    chapter_card(cv, t, 6)
    rr = np.random.default_rng(int(t * 15))
    if 110.8 <= t < 115.05:
        a = win(t, 110.8, 115.0, .3, .12)
        j = int(clamp((t - K6_T0) / K6_DT, 0, 7))
        r = np.random.default_rng(100 + j)
        c0 = np.array([700, 560])
        pts = [c0 + 290 * np.array([math.cos(i * math.pi / 3 - math.pi / 2), math.sin(i * math.pi / 3 - math.pi / 2)]) for i in range(6)]
        edges = list(itertools.combinations(range(6), 2))
        col = {e: r.integers(2) for e in edges}
        tri = next(tr for tr in itertools.combinations(range(6), 3)
                   if col[(tr[0], tr[1])] == col[(tr[0], tr[2])] == col[(tr[1], tr[2])])
        hl = math.exp(-(t - K6_T0 - j * K6_DT) * 3) if t >= K6_T0 else 0
        for e in edges:
            c = RED if col[e] else BLUE
            intri = e[0] in tri and e[1] in tri
            line(cv.bg, pts[e[0]], pts[e[1]], sc(c, a * (1 if intri and t >= K6_T0 else .45)), 6 if intri and t >= K6_T0 else 2)
        if t >= K6_T0:
            tc = RED if col[(tri[0], tri[1])] else BLUE
            polys(cv.bg, [np.array([pts[i] for i in tri])], sc(mix(tc, WHITE, hl), a * (.6 + .4 * hl)), 3 + int(6 * hl), True)
        for p in pts:
            circle(cv.bg, p, 18, sc(WHITE, a), -1)
        cv.text("任意 6 个人之中", 1400, 360, 48, "sansb", WHITE, a, spacing=3)
        cv.text("必有 3 人两两相识", 1400, 440, 48, "sans", RED, a * ss(111.6, 112, t), spacing=3)
        cv.text("或两两陌生", 1400, 510, 48, "sans", BLUE, a * ss(112.1, 112.5, t), spacing=3)
        cv.math(r"R(3,3) = 6", 1400, 680, 110, WHITE, a * ss(113, 113.3, t))
    if 115 <= t < CUT:
        u = t - 115
        n = 17 if u < 1.5 else 43
        grow = eo(u / .4) if n == 17 else eo((u - 1.5) / .5)
        rad = 420 * grow + 60
        ang = np.arange(n) * 2 * np.pi / n - np.pi / 2 + u * .05
        pts = np.stack([CX + np.cos(ang) * rad, CY + np.sin(ang) * rad], 1)
        edges = np.array(list(itertools.combinations(range(n), 2)))
        colr = np.random.default_rng(int(t * 15)).integers(2, size=len(edges)).astype(bool)
        bgk = 1 - .65 * ss(119, 119.6, t)
        br = (.55 if n == 17 else .32) * bgk * (1 + .6 * kick_env(t))
        polys(cv.bg, list(np.stack([pts[edges[colr, 0]], pts[edges[colr, 1]]], 1)), sc(RED, br), 1)
        polys(cv.bg, list(np.stack([pts[edges[~colr, 0]], pts[edges[~colr, 1]]], 1)), sc(BLUE, br), 1)
        dots(cv.bg, pts, sc(WHITE, bgk), 4 if n == 17 else 3)
        if t < 119:
            a = 1 - ss(118.8, 119.0, t)
            if u < 1.5:
                cv.dim(700, 440, 1220, 640, .8)
                cv.math(r"R(4,4) = 18", CX, 540, 110, WHITE, a, scale=1.25 - .25 * eo(u / .25))
            else:
                cv.dim(420, 280, 1500, 900, .85 * a)
                cv.math(r"R(5,5) = \ ?", CX, 400, 150, WHITE, a, scale=1.3 - .3 * eo((u - 1.5) / .3))
                cv.math(r"43 \leq R(5,5) \leq 46", CX, 570, 100, RED, a * ss(117.3, 117.5, t))
                cv.text("光是 43 个点的红蓝染色方式，就有", CX, 700, 40, "sansb", WHITE, a * ss(118.0, 118.3, t), spacing=3)
                cv.math(r"2^{903} \approx 6.8\times10^{271}", CX, 790, 64, WHITE, a * ss(118.2, 118.5, t))
        else:
            q = [("“假如外星人兵临城下，", 119.3, WHITE), ("要我们说出 R(5,5) 的值，否则就毁灭地球——", 120.3, WHITE),
                 ("我们应该集结全世界的数学家和计算机。", 121.5, WHITE), ("但如果它们要的是 R(6,6)，", 122.8, WHITE)]
            cv.dim(160, 200, 1760, 930, .85)
            for i, (s, t0, c) in enumerate(q):
                cv.text(s, CX, 290 + i * 105, 54, "serifb", c, ss(t0, t0 + .3, t), spacing=3, wipe=eo((t - t0) / .5))
            if t >= 124.0:
                v = t - 124.0
                cv.text("我们应该先发制人。”", CX, 760, 96, "serif", RED, 1, spacing=8, scale=1.35 - .35 * eo(v / .25))
            cv.text("—— 保罗 · 埃尔德什", 1500, 880, 36, "sans", WHITE, .8 * ss(124.8, 125.1, t), spacing=3)


def outro(cv, t):
    if t < FINAL:
        return
    u = t - FINAL
    a = 1 - ss(132.3, 133.9, t)
    cv.text("数得清吗？", CX, CY - 30, 230, "serif", WHITE, a, spacing=24, scale=(1.35 - .35 * eo(u / .35)) * (1 + .012 * u))
    cv.text("组合数学  ·  COMBINATORICS", CX, CY + 150, 32, "sans", ICE, .65 * a * ss(129.5, 130.3, t), spacing=10)


SCENES = {"intro": intro, "mult": mult, "perm": perm, "comb": comb, "incl": incl,
          "catalan": catalan, "genf": genf, "ramsey": ramsey, "outro": outro}


# ================================================================ compositing
def render(t, fidx=0):
    cv = Canvas()
    name, a, b = section_at(t)
    fog = ambient(cv, t)
    SCENES[name](cv, t)
    hud(cv, t)
    if t >= CUT and t < FINAL:
        return np.zeros((H, W, 3), np.uint8)

    bg = cv.bg.astype(np.float32) * (1 / 255)
    fg = cv.fg.astype(np.float32) * (1 / 255)
    if cv.dims:
        dm = np.zeros((H // 8, W // 8), np.float32)
        for x0, y0, x1, y1, al in cv.dims:
            cv2.rectangle(dm, (x0 // 8, y0 // 8), (x1 // 8, y1 // 8), al, -1)
        dm = cv2.resize(cv2.GaussianBlur(dm, (0, 0), 8), (W, H))[..., None]
        bg *= 1 - dm
        if fog is not None:
            fog *= 1 - dm
    k = kick_env(t) if t >= 26 else 0
    small = cv2.resize(bg * (1 + .5 * k) + fg * .45, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    bloom = cv2.GaussianBlur(small, (0, 0), 2.5) * .7 + cv2.GaussianBlur(small, (0, 0), 10) * .9
    img = bg + fg + cv2.resize(bloom, (W, H), interpolation=cv2.INTER_LINEAR)
    if fog is not None:
        img += fog

    # --- camera: punch zoom, shake, chromatic aberration, flash
    he = hit_env(t)
    press = ss(60, CUT, t)
    shake = 16 * he + (3 + 5 * ss(119, CUT, t)) * ss(108, 110, t) * (t < CUT)
    rs = np.random.default_rng(fidx)
    dx, dy = rs.uniform(-1, 1, 2) * shake
    zoom = 1 + .035 * hit_env(t, 5) + .006 * k
    rot = rs.uniform(-1, 1) * .25 * he
    if abs(dx) + abs(dy) > .3 or zoom > 1.001 or abs(rot) > .01:
        M = cv2.getRotationMatrix2D((CX, CY), rot, zoom)
        M[:, 2] += (dx, dy)
        img = cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
    ca = 9 * hit_env(t, 7) + 2.5 * ss(115, CUT, t)
    if ca > .5:
        for ch, s in ((0, 1 + ca / 1000), (2, 1 - ca / 1000)):
            M = cv2.getRotationMatrix2D((CX, CY), 0, s)
            img[..., ch] = cv2.warpAffine(img[..., ch], M, (W, H), flags=cv2.INTER_LINEAR)
    flash = sum(.45 * s * math.exp(-(t - h) * 9) for h, s in HITS if 0 <= t - h < 1)
    if flash > .005:
        img += flash
    # --- grade: vignette, grain, letterbox, soft shoulder
    vig = .35 + .3 * press
    img *= np.clip(1 - vig * RAD ** 2.2, 0, 1)[..., None]
    img += GRAIN[fidx % 8][..., None] * (.018 + .02 * press)
    np.clip(img, 0, None, out=img)
    img = np.where(img < .8, img, .8 + .2 * (1 - np.exp(-(img - .8) / .2)))
    bar = int(40 * ss(108, 109, t) + 70 * ss(119, 125, t)) if t < CUT else 0
    out = (np.clip(img, 0, 1) * 255).astype(np.uint8)
    if bar:
        out[:bar] = 0; out[-bar:] = 0
    return out


FFMPEG = None
def ffmpeg():
    global FFMPEG
    if FFMPEG is None:
        try:
            import imageio_ffmpeg
            FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
        except ImportError:
            FFMPEG = "ffmpeg"
    return FFMPEG


def render_chunk(args):
    i0, i1, path = args
    p = subprocess.Popen([ffmpeg(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                          "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow",
                          "-crf", "19", "-maxrate", "7M", "-bufsize", "14M", "-tune", "film",
                          "-pix_fmt", "yuv420p", "-g", "60", path], stdin=subprocess.PIPE)
    for i in range(i0, i1):
        p.stdin.write(render(i / FPS, i).tobytes())
        if i % 150 == 0:
            print(f"frame {i}/{NF}", flush=True)
    p.stdin.close(); p.wait()
    return path


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "still":
        for tt in sys.argv[2].split(","):
            cv2.imwrite(sys.argv[3].replace("#", tt), cv2.cvtColor(render(float(tt), int(float(tt) * FPS)), cv2.COLOR_RGB2BGR))
    elif mode == "video":
        from multiprocessing import Pool
        out, audio = sys.argv[2], sys.argv[3]
        nproc = int(os.environ.get("NPROC", os.cpu_count()))
        tmp = os.path.join(os.path.dirname(os.path.abspath(out)), "_seg")
        os.makedirs(tmp, exist_ok=True)
        start, end = (int(float(x) * FPS) for x in os.environ.get("RANGE", f"0,{TOTAL}").split(","))
        n = nproc * 3
        bounds = np.linspace(start, end, n + 1).astype(int)
        jobs = [(bounds[i], bounds[i + 1], os.path.join(tmp, f"seg{i:03d}.mp4")) for i in range(n)]
        with Pool(nproc) as pool:
            segs = pool.map(render_chunk, jobs)
        lst = os.path.join(tmp, "list.txt")
        open(lst, "w").write("".join(f"file '{s}'\n" for s in segs))
        subprocess.run([ffmpeg(), "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst,
                        "-ss", str(start / FPS), "-i", audio, "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                        "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", out], check=True)
