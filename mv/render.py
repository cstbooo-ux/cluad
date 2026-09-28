import numpy as np, cv2, json, sys, os, subprocess
from PIL import Image, ImageDraw, ImageFont

D = os.path.dirname(os.path.abspath(__file__))
AUDIO = "/root/.claude/uploads/93e1386f-6f2e-51d5-9d2c-32b3fb875e1b/b0460060-__.wav"
W, H, FPS, DUR = 1920, 1080, 30, 30.0
NF = int(DUR * FPS)
BPM, PH = 147.0, 0.03
BEAT = 60 / BPM
FONT_B = os.path.join(D, "fonts/NotoSerifSC-Bold.otf")
FONT_K = os.path.join(D, "fonts/NotoSerifSC-Black.otf")

# ---------------------------------------------------------------- audio features
feat = json.load(open(os.path.join(D, "feat.json")))
LOW = np.array(feat["low"]); ENV = np.array(feat["env"])
KICK = np.zeros(NF)
for i in range(NF):
    KICK[i] = max(min(LOW[i], 1.2), (KICK[i - 1] * 0.78 if i else 0))
ONS = np.zeros(NF)
for i in range(NF):
    ONS[i] = max(min(ENV[i], 1.2), (ONS[i - 1] * 0.8 if i else 0))
# cumulative wind "distance" (gusts on kicks)
GUST = np.cumsum(0.6 + 1.4 * KICK) / FPS

def fi(t): return int(np.clip(t * FPS, 0, NF - 1))
def beat_pulse(t):
    k = np.floor((t - PH) / BEAT); lb = PH + k * BEAT
    return np.exp(-(t - lb) * 9) if t >= PH else 0.0
def ss(a, b, x):
    x = np.clip((x - a) / (b - a), 0, 1); return x * x * (3 - 2 * x)
def ease_out(x): return 1 - (1 - np.clip(x, 0, 1)) ** 3

# ---------------------------------------------------------------- lyrics
# (screen, text, time, size, weight, emphasis, row, joinPrev)
FR = [
    (0, "吹散了天", 1.81, 120, "b", 0, 0, 0), (0, "吹乱了地", 2.65, 120, "b", 0, 0, 0),
    (0, "吹远了", 3.50, 120, "b", 0, 1, 0), (0, "哦~哦", 4.00, 120, "b", 0, 1, 0),
    (1, "啊", 5.50, 96, "b", 0, 0, 0), (1, "有些话还", 5.70, 132, "b", 0, 1, 0), (1, "没说出口", 6.70, 132, "b", 0, 1, 1),
    (2, "就随着晚风", 8.40, 110, "b", 0, 0, 0),
    (2, "飘呀", 9.40, 92, "b", 0, 1, 0), (2, "飘呀", 9.77, 92, "b", 0, 1, 0), (2, "飘呀", 10.13, 92, "b", 0, 1, 0),
    (2, "飘到远方", 10.50, 146, "k", 1, 2, 0),
    (3, "我却成了", 12.80, 112, "b", 0, 0, 0), (3, "阶下囚", 13.80, 250, "k", 2, 1, 0),
    (4, "可能是我", 17.00, 132, "b", 0, 0, 0), (4, "不懂", 18.00, 160, "k", 1, 0, 0),
    (5, "可是我们", 18.80, 122, "b", 0, 0, 0), (5, "没什么", 20.00, 122, "b", 0, 1, 0), (5, "不同", 20.60, 210, "k", 2, 1, 0),
    (6, "故事", 21.42, 124, "b", 0, 0, 0),
    (6, "走呀", 21.84, 82, "b", 0, 1, 0), (6, "走呀", 22.25, 82, "b", 0, 1, 0),
    (6, "走呀", 22.67, 82, "b", 0, 1, 0), (6, "走呀", 23.08, 82, "b", 0, 1, 0),
    (6, "走到了尽头", 23.50, 160, "k", 2, 2, 0),
    (7, "还有个人", 25.00, 124, "b", 0, 0, 0), (7, "却不肯", 26.00, 124, "b", 0, 0, 0),
    (7, "放手", 27.00, 320, "k", 3, 1, 0),
]
NS = 8
S_START = [min(f[2] for f in FR if f[0] == s) for s in range(NS)]
S_END = [S_START[s + 1] - 0.22 for s in range(NS - 1)] + [28.35]

_fonts = {}
def font(w, size):
    k = (w, size)
    if k not in _fonts:
        _fonts[k] = ImageFont.truetype(FONT_K if w == "k" else FONT_B, size)
    return _fonts[k]

class Frag: pass
frags = []
rng = np.random.default_rng(7)

def build():
    for s in range(NS):
        fs = [f for f in FR if f[0] == s]
        rows = sorted(set(f[6] for f in fs))
        row_items = {r: [f for f in fs if f[6] == r] for r in rows}
        # measure
        row_w, row_h = {}, {}
        meas = {}
        for r in rows:
            x = 0; hmax = 0
            for j, f in enumerate(row_items[r]):
                fo = font(f[4], f[3]); bb = fo.getbbox(f[1])
                gap = 0 if (j == 0 or f[7]) else int(f[3] * 0.42)
                x += gap; meas[id(f)] = (x, bb); x += bb[2]
                hmax = max(hmax, f[3])
            row_w[r] = x; row_h[r] = hmax * 1.28
        total_h = sum(row_h.values())
        y = H * 0.46 - total_h / 2
        for r in rows:
            x0 = (W - row_w[r]) / 2
            for j, f in enumerate(row_items[r]):
                o, bb = meas[id(f)]
                fr = Frag(); fr.s, fr.text, fr.t, fr.size, fr.w, fr.emph = s, f[1], f[2], f[3], f[4], f[5]
                fr.kind = "piao" if f[1] == "飘呀" else ("zou" if f[1] == "走呀" else "")
                idx = sum(1 for g in row_items[r][:j] if g[1] == f[1])
                oy = 0
                if fr.kind == "zou": oy = (idx - 1.5) * -26   # climbing steps
                fr.idx = idx
                # render mask on crop canvas
                pad = 90
                cw, ch = bb[2] + 2 * pad, int(f[3] * 1.5) + 2 * pad
                im = Image.new("L", (cw, ch), 0)
                ImageDraw.Draw(im).text((pad, pad + (row_h[r] - f[3] * 1.28) / 2), f[1], font=font(f[4], f[3]), fill=255)
                m = np.asarray(im, np.float32) / 255
                fr.mask = m
                fr.g1 = cv2.GaussianBlur(m, (0, 0), 8 + f[3] * 0.04)
                fr.g2 = cv2.GaussianBlur(m, (0, 0), 26 + f[3] * 0.12)
                fr.ox, fr.oy = x0 + o - pad, y - pad + oy
                fr.cx, fr.cy = fr.ox + cw / 2, fr.oy + ch / 2
                fr.end = S_END[s]
                # particles
                ys, xs = np.nonzero(m > 0.5)
                n = min(len(xs), int(len(xs) / 5) + 200, 7000)
                sel = rng.choice(len(xs), n, replace=False)
                tx = xs[sel] + fr.ox + rng.uniform(-.5, .5, n); ty = ys[sel] + fr.oy + rng.uniform(-.5, .5, n)
                fr.tx, fr.ty = tx, ty
                fr.sx = tx - rng.uniform(350, 1200, n) * (1.3 if fr.emph >= 2 else 1)
                fr.sy = ty + rng.normal(0, 170, n)
                fr.del_in = rng.uniform(0, 0.12, n)
                fr.ph = rng.uniform(0, 6.28, n)
                fr.br = rng.uniform(0.35, 1.0, n)
                fr.vx = rng.uniform(80, 420, n); fr.vy = rng.normal(-40, 110, n)
                fr.del_out = (tx / W) * 0.14 + rng.uniform(0, 0.08, n)
                # sparks
                ns = 260 if fr.emph else 120
                ang = rng.uniform(0, 6.28, ns); sp = rng.uniform(150, 900 if fr.emph else 500, ns) * (1 + fr.emph * 0.4)
                fr.spx, fr.spy = np.cos(ang) * sp, np.sin(ang) * sp * 0.6
                fr.sp0x = rng.uniform(tx.min(), tx.max(), ns); fr.sp0y = rng.uniform(ty.min(), ty.max(), ns)
                frags.append(fr)
            y += row_h[r]
build()

def frag_offset(fr, t):
    if fr.kind == "piao":
        return 0.0, 20 * np.sin(2 * np.pi * 0.8 * t + fr.idx * 2.1)
    return 0.0, 0.0

# ---------------------------------------------------------------- ambient particles
NA = 4200
A_x0 = rng.uniform(0, W + 200, NA); A_y0 = rng.uniform(-50, H + 50, NA)
A_d = rng.uniform(0.15, 1.0, NA) ** 1.6     # depth: 1 = near
A_sp = 60 + 380 * A_d
A_amp = rng.uniform(10, 70, NA); A_w = rng.uniform(0.3, 1.2, NA); A_ph = rng.uniform(0, 6.28, NA)
A_br = rng.uniform(0.2, 0.8, NA) * (0.3 + 1.4 * A_d ** 1.5)
A_tw = rng.uniform(2, 6, NA)

# wind streaks
NSTR = 46
S_y0 = rng.uniform(40, H - 40, NSTR); S_x0 = rng.uniform(0, W * 2.4, NSTR)
S_sp = rng.uniform(500, 1300, NSTR); S_len = rng.uniform(200, 700, NSTR)
S_k = rng.uniform(0.002, 0.006, NSTR); S_amp = rng.uniform(8, 45, NSTR); S_ph = rng.uniform(0, 6.28, NSTR)
S_br = rng.uniform(0.25, 0.9, NSTR)

# ---------------------------------------------------------------- background
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
def grad(stops):
    v = yy[:, :1] / H
    out = np.zeros((H, 1, 3), np.float32)
    ps = [s[0] for s in stops]
    for c in range(3):
        out[:, 0, c] = np.interp(v[:, 0], ps, [s[1][c] for s in stops])
    return np.repeat(out, W, 1)
BG_A = grad([(0, (0.015, 0.02, 0.07)), (0.45, (0.07, 0.05, 0.16)), (0.74, (0.30, 0.13, 0.20)),
             (0.80, (0.42, 0.19, 0.18)), (0.86, (0.10, 0.05, 0.11)), (1, (0.03, 0.02, 0.05))])
BG_B = grad([(0, (0.01, 0.015, 0.05)), (0.45, (0.04, 0.04, 0.13)), (0.74, (0.16, 0.09, 0.22)),
             (0.80, (0.24, 0.12, 0.22)), (0.86, (0.06, 0.04, 0.10)), (1, (0.02, 0.015, 0.04))])
SUN = np.exp(-(((xx - 1560) / 560) ** 2 + ((yy - 830) / 260) ** 2))[..., None] * np.array([0.75, 0.36, 0.22], np.float32)
SUNC = np.exp(-(((xx - 1560) / 90) ** 2 + ((yy - 830) / 60) ** 2))[..., None] * np.array([1.0, 0.75, 0.5], np.float32)
# hills silhouette (far) — darker band under horizon
hill = (H * 0.84 + 18 * np.sin(xx[0] * 0.004 + 1) + 10 * np.sin(xx[0] * 0.011)).astype(np.float32)
HILL = (yy > hill[None, :]).astype(np.float32)
HILL = cv2.GaussianBlur(HILL, (0, 0), 1.5)[..., None]
# stars
STAR = np.zeros((H, W), np.float32)
sn = 420; sx = rng.integers(0, W, sn); sy = (rng.uniform(0, 1, sn) ** 1.8 * H * 0.6).astype(int)
STAR[sy, sx] = rng.uniform(0.2, 1, sn)
STAR = cv2.GaussianBlur(STAR, (0, 0), 0.8) * 3
STAR_PH = rng.uniform(0, 6.28, (H, W)).astype(np.float32) if False else None
VIG = (1 - 0.55 * (((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H / 2) / (H * 0.7)) ** 2)).clip(0.25, 1)[..., None]
GRAIN = [rng.normal(0, 0.012, (H // 2, W // 2)).astype(np.float32) for _ in range(6)]

# ---------------------------------------------------------------- hits
HITS = []
for fr in frags:
    HITS.append((fr.t, [0.25, 0.5, 0.9, 1.6][fr.emph]))
def env_sum(t, hits, k):
    v = 0.0
    for (ti, s) in hits:
        if t >= ti: v += s * np.exp(-(t - ti) * k)
    return v

# ---------------------------------------------------------------- render
def splat(buf, x, y, w):
    xi = np.round(x).astype(np.int64); yi = np.round(y).astype(np.int64)
    ok = (xi >= 0) & (xi < W) & (yi >= 0) & (yi < H) & (w > 0.003)
    buf += np.bincount(yi[ok] * W + xi[ok], w[ok], W * H).reshape(H, W).astype(np.float32)

def render(fidx):
    t = fidx / FPS
    f = fi(t)
    kick, ons, bp = KICK[f], ONS[f], beat_pulse(t)
    mix = ss(8, 26, t)
    img = BG_A * (1 - mix) + BG_B * mix
    img = img * (0.88 + 0.22 * kick)
    img = img * (1 - HILL * 0.75)
    img += SUN * (0.85 + 0.35 * kick + 0.25 * np.sin(t * 0.7)) + SUNC * (0.6 + 0.3 * kick)
    img += (STAR * (0.6 + 0.4 * np.sin(t * 3 + xx[:1, :] * 0.01)))[..., None] * np.array([0.8, 0.85, 1.0], np.float32)

    # explosion at 放手
    boom = ease_out((t - 27.0) / 0.9) if t >= 27.0 else 0.0
    # --- wind streaks (half res)
    sl = np.zeros((H // 2, W // 2), np.float32)
    G = GUST[f]
    gscale = 1 + 1.5 * ss(26.9, 27.2, t)
    for i in range(NSTR):
        hx = (S_x0[i] + S_sp[i] * G * gscale) % (W * 2.4) - W * 0.4
        xs = np.linspace(hx - S_len[i], hx, 24)
        ys = S_y0[i] + S_amp[i] * np.sin(xs * S_k[i] + S_ph[i] + t * 1.3)
        pts = np.stack([xs / 2, ys / 2], 1).astype(np.int32)
        b = S_br[i] * (0.35 + 0.9 * kick)
        for j in range(3):  # tapered tail
            a, bnd = j * 8, j * 8 + 9
            cv2.polylines(sl, [pts[a:bnd]], False, float(b * (0.25 + 0.37 * j)), 1, cv2.LINE_AA)
    sl = cv2.GaussianBlur(sl, (0, 0), 2.2)
    sl = cv2.resize(sl, (W, H), interpolation=cv2.INTER_LINEAR)
    img += sl[..., None] * np.array([0.55, 0.62, 0.85], np.float32) * 1.5

    # --- ambient particles
    ax = (A_x0 + A_sp * G * gscale + 6 * np.sin(t * A_w + A_ph)) % (W + 200) - 100
    ay = A_y0 + A_amp * np.sin(t * A_w + A_ph + ax * 0.002) - 25 * A_d * t
    ay = (ay + 60) % (H + 120) - 60
    if boom > 0:
        dx, dy = ax - W / 2, ay - H * 0.5
        r = np.sqrt(dx * dx + dy * dy) + 1
        push = boom * 700 * A_d + 450 * max(0, t - 27.9) * A_d
        ax = ax + dx / r * push; ay = ay + dy / r * push * 0.8
    ab = A_br * (0.55 + 0.45 * np.sin(t * A_tw + A_ph)) * (0.7 + 1.1 * kick + 0.4 * bp) * (1 + 2.5 * boom * np.exp(-(t - 27) * 1.2) if boom else 1)
    PA = np.zeros((H, W), np.float32)
    splat(PA, ax, ay, ab)

    # --- lyric particles + sparks + crisp text
    PT = np.zeros((H, W), np.float32)
    TXT = np.zeros((H, W, 3), np.float32)
    for fr in frags:
        if t < fr.t - 0.5 or t > fr.end + 1.8: continue
        ox, oy = frag_offset(fr, t)
        # particles
        tin = fr.t - 0.42 + fr.del_in * 0.3 - 0.02
        u = np.clip((t - tin) / 0.42, 0, 1)
        e = u ** 1.7
        px = fr.sx + (fr.tx - fr.sx) * e
        py = fr.sy + (fr.ty - fr.sy) * e + (1 - e) * 70 * np.sin(e * 6.28 + fr.ph)
        shim = 1.2 * np.sin(t * 7 + fr.ph)
        px = px + shim + ox; py = py + shim * 0.6 + oy
        br = fr.br * (u > 0) * (0.35 + 0.65 * (1 - e) + 0.25 * np.sin(t * 5 + fr.ph) * e)
        if t > fr.end:
            s = np.clip(t - fr.end - fr.del_out, 0, None)
            wind = 2600 * (1 - (fr.s == 7) * 0.5)
            px = px + fr.vx * s + 0.5 * wind * s * s
            py = py + fr.vy * s + 40 * np.sin(s * 5 + fr.ph) * s - 120 * s * s
            br = br * np.exp(-s * (1.4 if fr.s == 7 else 2.6)) * (1 + 1.5 * (s > 0) * np.exp(-s * 3))
        splat(PT, px, py, br * 0.9)
        # sparks on hit
        sdt = t - fr.t
        if 0 <= sdt < 1.2:
            k = (1 - np.exp(-sdt * 5)) / 5
            spx = fr.sp0x + fr.spx * k + 300 * sdt * sdt + ox
            spy = fr.sp0y + fr.spy * k + oy
            splat(PT, spx, spy, np.full(len(spx), 1.6 * np.exp(-sdt * 3.2)))
        # crisp text alpha
        a = ss(fr.t - 0.1, fr.t + 0.02, t)
        if t > fr.end: a *= 1 - ss(fr.end, fr.end + 0.14, t)
        if a <= 0.001: continue
        punch = 1 + (0.06 + 0.1 * fr.emph) * np.exp(-max(sdt, 0) * 11) * (sdt >= 0)
        if fr.s == 3 and t > 13.8: punch *= 1 + 0.03 * bp
        if fr.emph == 3 and t > 27: punch *= 1 + 0.02 * boom + 0.015 * (t - 27)
        m, g1, g2 = fr.mask, fr.g1, fr.g2
        ch_, cw_ = m.shape
        if abs(punch - 1) > 0.002:
            nw, nh = int(cw_ * punch), int(ch_ * punch)
            m = cv2.resize(m, (nw, nh)); g1 = cv2.resize(g1, (nw, nh)); g2 = cv2.resize(g2, (nw, nh))
        hh, ww = m.shape
        x0 = int(round(fr.cx + ox - ww / 2)); y0 = int(round(fr.cy + oy - hh / 2))
        xa, ya = max(x0, 0), max(y0, 0); xb, yb = min(x0 + ww, W), min(y0 + hh, H)
        if xb <= xa or yb <= ya: continue
        sm = (slice(ya - y0, yb - y0), slice(xa - x0, xb - x0))
        glow_c = np.array([1.0, 0.55, 0.42] if fr.emph else [1.0, 0.72, 0.6], np.float32)
        core_c = np.array([1.0, 0.96, 0.9], np.float32)
        gl = 0.55 + 0.5 * kick * (fr.s == 3) + 0.4 * (fr.emph >= 2) + 0.8 * np.exp(-max(sdt, 0) * 6)
        TXT[ya:yb, xa:xb] += a * (m[sm][..., None] * core_c * 1.6 + (g1[sm][..., None] * 0.55 + g2[sm][..., None] * 0.5) * glow_c * gl)

    # --- cage bars (阶下囚)
    BAR = None
    if 13.6 < t < 18.2:
        BAR = np.zeros((H, W), np.float32)
        nb = 11
        for i in range(nb):
            bx = 140 + i * (W - 280) / (nb - 1)
            td = 13.8 + abs(i - nb // 2) * 0.018
            d = ease_out((t - td + 0.12) / 0.16)
            if d <= 0: continue
            ybot = -H * 0.1 + d * H * 1.1
            xo = 0
            al = 0.35 + 0.55 * kick + 0.35 * bp
            if t > 16.92:
                s = max(0, t - 16.92 - i * 0.02)
                xo = 900 * s * s + 200 * s; al *= np.exp(-s * 3.5)
            x1 = int(bx + xo - 5); x2 = int(bx + xo + 5)
            if x2 < 0 or x1 >= W: continue
            BAR[:max(0, int(ybot)), max(0, x1):min(W, x2)] += al
        BAR = BAR * 0.5 + cv2.GaussianBlur(BAR, (0, 0), 14) * 1.4
        img += BAR[..., None] * np.array([0.45, 0.6, 1.0], np.float32) * 0.55

    # --- shockwave rings
    RING = np.zeros((H // 2, W // 2), np.float32)
    for fr in frags:
        if fr.emph >= 2 and 0 <= t - fr.t < 0.9:
            s = t - fr.t
            r = int((60 + 1400 * ease_out(s / 0.9)) / 2)
            cv2.circle(RING, (int(fr.cx / 2), int(fr.cy / 2)), r, float((1 - s / 0.9) ** 2 * (1.5 if fr.emph == 3 else 1)), 3 if fr.emph < 3 else 5, cv2.LINE_AA)
    if RING.any():
        RING = cv2.GaussianBlur(RING, (0, 0), 2.5) * 2
        RING = cv2.resize(RING, (W, H))
        img += RING[..., None] * np.array([1.0, 0.7, 0.55], np.float32)

    # --- composite particles
    pa = PA * 0.5 + cv2.GaussianBlur(PA, (0, 0), 1.4) * 2.8 + cv2.GaussianBlur(PA, (0, 0), 3.5) * 4.0
    pt = PT * 0.5 + cv2.GaussianBlur(PT, (0, 0), 1.1) * 2.0
    img += pa[..., None] * np.array([0.85, 0.85, 1.0], np.float32) * 1.0
    img += pt[..., None] * np.array([1.0, 0.82, 0.68], np.float32)
    img += TXT

    # --- bloom
    small = cv2.resize(img, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    small = np.clip(small - 0.5, 0, None)
    bl = cv2.GaussianBlur(small, (0, 0), 6) + cv2.GaussianBlur(small, (0, 0), 18) * 0.8
    img += cv2.resize(bl, (W, H)) * 0.55

    # --- flash
    fl = 0.0
    for fr in frags:
        if fr.emph >= 2 and t >= fr.t: fl += [0, 0, 0.35, 1.3][fr.emph] * np.exp(-(t - fr.t) * [0, 0, 12, 5][fr.emph])
    fl += 0.05 * kick
    img += fl * np.array([1.0, 0.9, 0.85], np.float32)

    img = img * VIG
    # fades
    fade = ss(0.0, 1.2, t) * (1 - ss(28.6, 30.0, t))
    img *= fade

    # --- tone map
    img = 1 - np.exp(-img * 1.35)
    g = cv2.resize(GRAIN[fidx % 6], (W, H), interpolation=cv2.INTER_NEAREST)
    img += g[..., None]

    # --- camera: shake + zoom pulse + chroma
    sh = env_sum(t, HITS, 10) + 0.18 * kick
    zoom = 1 + 0.012 * kick + 0.008 * bp + 0.03 * np.exp(-max(t - 27, 0) * 3) * (t >= 27)
    zoom *= 1 + 0.02 * t / DUR
    dx = sh * 14 * np.sin(t * 91.0) + sh * 6 * np.sin(t * 57.0)
    dy = sh * 12 * np.cos(t * 77.0)
    M = np.float32([[zoom, 0, (1 - zoom) * W / 2 + dx], [0, zoom, (1 - zoom) * H / 2 + dy]])
    img = cv2.warpAffine(img, M, (W, H), borderMode=cv2.BORDER_REFLECT)
    ca = int(round(min(sh, 2.0) * 5))
    if ca > 0:
        img[:, ca:, 0] = img[:, :-ca, 0].copy()
        img[:, :-ca, 2] = img[:, ca:, 2].copy()
    return (np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)

if __name__ == "__main__":
    cv2.setNumThreads(1)
    if sys.argv[1] == "stills":
        for tt in sys.argv[2:]:
            fr = render(int(float(tt) * FPS))
            Image.fromarray(fr).save(os.path.join(D, f"still_{tt}.jpg"), quality=88)
    elif sys.argv[1] == "video":
        from multiprocessing import Pool
        import imageio_ffmpeg
        ff = imageio_ffmpeg.get_ffmpeg_exe()
        out = sys.argv[2]
        cmd = [ff, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
               "-i", AUDIO, "-t", str(DUR), "-map", "0:v", "-map", "1:a",
               "-af", "afade=t=out:st=28.4:d=1.6",
               "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
               "-c:a", "aac", "-b:a", "320k", out]
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        with Pool(4) as pool:
            for i, fr in enumerate(pool.imap(render, range(NF), chunksize=2)):
                p.stdin.write(fr.tobytes())
                if i % 60 == 0: print("frame", i, flush=True)
        p.stdin.close(); p.wait()
        print("done", out)
