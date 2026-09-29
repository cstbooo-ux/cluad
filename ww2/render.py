"""逐帧渲染：暗色地图 + 墨迹式扩散的占领区 + 箭头 + 日期大字卡 + 收音机 UI + 双语字幕。

用法:
  python3 render.py still 12.3 [更多时间...]   # 输出单帧到 build/still_<t>.png
  python3 render.py video out.mp4 [t0 t1]      # 渲染整段（或区间）无声视频
"""
import json, math, os, pickle, subprocess, sys
from functools import lru_cache

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

D = os.path.dirname(os.path.abspath(__file__))
B = os.path.join(D, "build")
W, H, FPS = 1920, 1080, 30
TL = json.load(open(os.path.join(B, "timeline.json")))
GEO = pickle.load(open(os.path.join(B, "geo.pkl"), "rb"))
SEG = {s["id"]: s for s in TL["segs"]}
END = TL["end"]
DUR = TL["duration"]
NF = int(round(DUR * FPS))
sys.path.insert(0, D)
import script  # noqa: E402

# ------------------------------------------------------------------ 调色
OCEAN = np.array([0.030, 0.042, 0.058], np.float32)
OCEAN2 = np.array([0.052, 0.066, 0.084], np.float32)
LAND = np.array([0.150, 0.146, 0.138], np.float32)
COAST = np.array([0.36, 0.35, 0.32], np.float32)
BORDER = np.array([0.46, 0.44, 0.40], np.float32)
RED = np.array([0.66, 0.085, 0.07], np.float32)
EMBER = np.array([1.0, 0.52, 0.18], np.float32)
ALLY = np.array([0.30, 0.44, 0.60], np.float32)
AXIS_ARROW = (0.98, 0.26, 0.18)
ALLY_ARROW = (0.60, 0.84, 1.0)
WHITE = (0.94, 0.93, 0.89)
GREY = (0.62, 0.63, 0.62)


def clamp(x, a=0.0, b=1.0):
    return min(max(x, a), b)


def ss(a, b, x):
    x = clamp((x - a) / (b - a)) if b != a else float(x >= a)
    return x * x * (3 - 2 * x)


def e5(u):
    u = clamp(u)
    return u * u * u * (u * (6 * u - 15) + 10)


def eo(u):
    u = clamp(u)
    return 1 - (1 - u) ** 3


def win(t, a, b, fi=0.25, fo=0.25):
    """a..b 窗口内为 1，两端淡入淡出"""
    if t < a or t > b:
        return 0.0
    return min(ss(a, a + fi, t) if fi > 0 else 1.0, 1 - ss(b - fo, b, t) if fo > 0 else 1.0)


# ------------------------------------------------------------------ 时间锚点
def seg(i):
    return SEG[i]


def ch(sid, i=0, end=False):
    c = SEG[sid]["chunks"][i]
    return c["t"] + (c["dur"] if end else 0)


def wt(sid, i, sub, after=0.0):
    """某句里某个词开始的时刻：有 edge-tts 词时间戳就用，否则按字符位置估算"""
    c = SEG[sid]["chunks"][i]
    for w in c.get("words") or []:
        if sub.lower() in w["w"].lower() or w["w"].lower() in sub.lower() and len(w["w"]) > 1 and sub.lower().startswith(w["w"].lower()):
            return c["t"] + w["t"] + after
    txt = c["text"]
    k = txt.lower().find(sub.lower())
    if k < 0:
        raise KeyError((sid, i, sub))
    return c["t"] + c["dur"] * k / max(1, len(txt)) + after


# ------------------------------------------------------------------ 字体与文字贴图
FONT_FILES = dict(
    osw="Oswald.ttf", rc="RobotoCondensed.ttf", mono="IBMPlexMono-SemiBold.ttf", monom="IBMPlexMono-Medium.ttf",
    type="SpecialElite.ttf", bebas="BebasNeue-Regular.ttf",
    sans="NotoSansCJKsc-Regular.otf", sansb="NotoSansCJKsc-Bold.otf", sansk="NotoSansCJKsc-Black.otf",
    serif="NotoSerifCJKsc-Bold.otf", serifk="NotoSerifCJKsc-Black.otf",
)


@lru_cache(maxsize=None)
def font(name, size, wght=None):
    f = ImageFont.truetype(os.path.join(D, "fonts", FONT_FILES[name]), size)
    if wght is not None:
        f.set_variation_by_axes([wght])
    return f


@lru_cache(maxsize=4096)
def sprite(text, fname, size, color=WHITE, wght=None, track=0, stroke=0, shadow=0):
    """文字 -> (rgb float32 HxWx3, alpha float32 HxW)。track=字距(px)，stroke=描边，shadow=柔和投影半径"""
    f = font(fname, size, wght)
    pad = stroke + shadow * 2 + 4
    if track:
        widths = [f.getlength(c) for c in text]
        tw = int(sum(widths) + track * (len(text) - 1)) + 1
    else:
        tw = int(f.getlength(text)) + 1
    asc, desc = f.getmetrics()
    th = asc + desc
    Wd, Hd = tw + 2 * pad, th + 2 * pad
    fill = Image.new("L", (Wd, Hd), 0)
    dr = ImageDraw.Draw(fill)
    if track:
        x = pad
        for c, w in zip(text, widths):
            dr.text((x, pad), c, font=f, fill=255, stroke_width=0)
            x += w + track
    else:
        dr.text((pad, pad), text, font=f, fill=255)
    a_fill = np.asarray(fill, np.float32) / 255
    a = a_fill.copy()
    rgb = np.ones((Hd, Wd, 3), np.float32) * np.array(color, np.float32)
    if stroke:
        k = 2 * stroke + 1
        a_st = cv2.dilate(a_fill, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
        a_st = cv2.GaussianBlur(a_st, (0, 0), 0.8)
        a = np.maximum(a_fill, a_st * 0.85)
        # 描边为黑色：颜色按填充占比从文字色过渡到黑
        rgb = np.array(color, np.float32) * (a_fill / np.maximum(a, 1e-4))[..., None]
    if shadow:
        sh = cv2.GaussianBlur(a, (0, 0), shadow)
        out_a = a + sh * 0.75 * (1 - a)
        rgb = rgb * (a / np.maximum(out_a, 1e-4))[..., None]
        a = out_a
    return rgb.astype(np.float32), a.astype(np.float32)


def blit(frame, spr, x, y, alpha=1.0, anchor="lt", scale=1.0):
    """把贴图叠到 frame 上。anchor: l/c/r + t/m/b"""
    if alpha <= 0.003:
        return
    rgb, a = spr
    if scale != 1.0:
        h0, w0 = a.shape
        nw, nh = max(1, int(w0 * scale)), max(1, int(h0 * scale))
        rgb = cv2.resize(rgb, (nw, nh), interpolation=cv2.INTER_LINEAR)
        a = cv2.resize(a, (nw, nh), interpolation=cv2.INTER_LINEAR)
    h, w = a.shape
    if anchor[0] == "c":
        x -= w / 2
    elif anchor[0] == "r":
        x -= w
    if anchor[1] == "m":
        y -= h / 2
    elif anchor[1] == "b":
        y -= h
    x, y = int(round(x)), int(round(y))
    x0, y0, x1, y1 = max(0, x), max(0, y), min(W, x + w), min(H, y + h)
    if x1 <= x0 or y1 <= y0:
        return
    aa = a[y0 - y:y1 - y, x0 - x:x1 - x, None] * alpha
    reg = frame[y0:y1, x0:x1]
    reg += (rgb[y0 - y:y1 - y, x0 - x:x1 - x] - reg) * aa


def paint(frame, mask, color, alpha=1.0, box=None):
    """uint8 蒙版按颜色叠加（box 限定区域以省时间）"""
    if box is None:
        a = mask.astype(np.float32) * (alpha / 255)
        frame += (np.asarray(color, np.float32) - frame) * a[..., None]
    else:
        x0, y0, x1, y1 = box
        x0, y0, x1, y1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
        if x1 <= x0 or y1 <= y0:
            return
        a = mask[y0:y1, x0:x1].astype(np.float32) * (alpha / 255)
        reg = frame[y0:y1, x0:x1]
        reg += (np.asarray(color, np.float32) - reg) * a[..., None]


def soft_glow(mask, sigma, gain):
    small = cv2.resize(mask, (W // 4, H // 4), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
    small = cv2.GaussianBlur(small, (0, 0), sigma / 4)
    return cv2.resize(small, (W, H), interpolation=cv2.INTER_LINEAR) * gain


# ------------------------------------------------------------------ 镜头
class Cam:
    def __init__(self):
        self.keys = []

    def k(self, t, cx, cy, z):
        self.keys.append((t, cx, cy, math.log(z)))

    def __call__(self, t):
        ks = self.keys
        if t <= ks[0][0]:
            k = ks[0]
            return k[1], k[2], math.exp(k[3])
        for a, b in zip(ks, ks[1:]):
            if a[0] <= t <= b[0]:
                u = e5((t - a[0]) / max(1e-6, b[0] - a[0]))
                return (a[1] + (b[1] - a[1]) * u, a[2] + (b[2] - a[2]) * u, math.exp(a[3] + (b[3] - a[3]) * u))
        k = ks[-1]
        return k[1], k[2], math.exp(k[3])


class View:
    def __init__(self, cx, cy, z):
        self.cx, self.cy, self.z = cx, cy, z
        self.kx = math.cos(math.radians(clamp(cy, -20, 62)))
        self.sx = z * self.kx
        hw, hh = W / 2 / self.sx, H / 2 / z
        self.bb = (cx - hw, cy - hh, cx + hw, cy + hh)

    def p(self, pts):
        pts = np.asarray(pts, np.float32)
        return np.stack([(pts[..., 0] - self.cx) * self.sx + W / 2, (self.cy - pts[..., 1]) * self.z + H / 2], -1)

    def p1(self, lon, lat):
        return ((lon - self.cx) * self.sx + W / 2, (self.cy - lat) * self.z + H / 2)

    def visible(self, bb, m=0.0):
        return not (bb[2] < self.bb[0] - m or bb[0] > self.bb[2] + m or bb[3] < self.bb[1] - m or bb[1] > self.bb[3] + m)


SHIFT = 4
FX = float(1 << SHIFT)


def ipts(v, ring):
    return np.round(v.p(ring) * FX).astype(np.int32)


# ------------------------------------------------------------------ 几何缓存（带包围盒，用于剔除）
def prep(polys):
    out = []
    for rs in polys:
        r0 = rs[0]
        bb = (float(r0[:, 0].min()), float(r0[:, 1].min()), float(r0[:, 0].max()), float(r0[:, 1].max()))
        out.append((bb, rs))
    return out


LAND50 = prep(GEO["land50"])
LAND10 = prep(GEO["land10"])
LAKES = prep(GEO["lakes"])
BORDERS = [((float(l[:, 0].min()), float(l[:, 1].min()), float(l[:, 0].max()), float(l[:, 1].max())), l)
           for l in GEO["borders"] if len(l) > 1]
PIECES = {k: prep(v) for k, v in GEO["pieces"].items()}
ALLIES = {k: prep(v) for k, v in GEO["allies"].items()}


def piece_bb(ps):
    bbs = np.array([p[0] for p in ps])
    return (bbs[:, 0].min(), bbs[:, 1].min(), bbs[:, 2].max(), bbs[:, 3].max())


PIECE_BB = {k: piece_bb(v) for k, v in PIECES.items() if v}
ALLY_BB = {k: piece_bb(v) for k, v in ALLIES.items() if v}


def fill(mask, v, polys, color=255, offset=(0, 0)):
    cs = []
    for bb, rs in polys:
        if not v.visible(bb, 0.5):
            continue
        for r in rs:
            p = ipts(v, r)
            if offset != (0, 0):
                p -= np.array([offset[0] * FX, offset[1] * FX], np.int32).astype(np.int32)
            cs.append(p)
    if cs:
        cv2.fillPoly(mask, cs, color, lineType=cv2.LINE_AA, shift=SHIFT)
    return len(cs)


def screen_box(v, bb, pad=2):
    x0, y0 = v.p1(bb[0], bb[3])
    x1, y1 = v.p1(bb[2], bb[1])
    return (max(0, int(x0) - pad), max(0, int(y0) - pad), min(W, int(x1) + pad + 1), min(H, int(y1) + pad + 1))


# ------------------------------------------------------------------ 世界噪声纹理（墨迹边缘与红色区域质感）
NRES = 6.0
NX0, NY1 = -30.0, 85.0


def make_noise(seed=7):
    rng = np.random.default_rng(seed)
    w, h = int(360 * NRES), int(155 * NRES)
    acc = np.zeros((h, w), np.float32)
    amp, tot = 1.0, 0.0
    for cell in (48, 24, 12, 6, 3):
        g = rng.random((h // cell + 2, w // cell + 2)).astype(np.float32)
        up = cv2.resize(g, (w + 2 * cell, h + 2 * cell), interpolation=cv2.INTER_CUBIC)[cell:cell + h, cell:cell + w]
        acc += up * amp
        tot += amp
        amp *= 0.55
    acc /= tot
    acc = (acc - acc.min()) / (acc.max() - acc.min())
    return acc


NOISE = make_noise()
UU, VV = np.meshgrid(np.arange(W, dtype=np.float32), np.arange(H, dtype=np.float32))


def map_grids(v):
    X = v.cx + (UU - W / 2) / v.sx
    Y = v.cy - (VV - H / 2) / v.z
    mx, my = (X - NX0) * NRES, (NY1 - Y) * NRES
    N = cv2.remap(NOISE, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    # 细一级的噪声，让扩散前沿像墨迹一样参差
    Nf = cv2.remap(NOISE, mx * 3.3 + 517, my * 3.3 + 211, cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
    return X, Y, N, 0.45 * N + 0.55 * Nf


# ================================================================== 编排
CAM = Cam()
SCHED = {}      # 占领区: name -> dict(on=(t,d,origin,mode), off=(...), strength)
ALLY_T = {}     # 盟国浅蓝底色: name -> (t_on, t_off)
ARROWS, ROUTES, PLANES, PULSES, BOOMS, FIRES, SHIPS, LABEL_T, TAGS = [], [], [], [], [], [], [], [], []
SHAKES = []     # (t, 振幅px)
DATES = []      # 年月计数器: (t, y, m)


def on(name, t, d, o=None, mode="from", strength=1.0):
    SCHED.setdefault(name, dict(strength=strength))["on"] = (t, d, o, mode)
    SCHED[name]["strength"] = strength


def off(name, t, d, o=None, mode="from"):
    SCHED.setdefault(name, dict(strength=1.0))["off"] = (t, d, o, mode)


def catmull(pts, n=64):
    p = np.asarray(pts, np.float64)
    if len(p) == 2:
        s = np.linspace(0, 1, n)[:, None]
        return (p[0] * (1 - s) + p[1] * s).astype(np.float32)
    ext = np.vstack([2 * p[0] - p[1], p, 2 * p[-1] - p[-2]])
    out = []
    per = max(4, n // (len(p) - 1))
    for i in range(1, len(ext) - 2):
        p0, p1, p2, p3 = ext[i - 1], ext[i], ext[i + 1], ext[i + 2]
        for s in np.linspace(0, 1, per, endpoint=False):
            s2, s3 = s * s, s * s * s
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * s + (2 * p0 - 5 * p1 + 4 * p2 - p3) * s2
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * s3))
    out.append(p[-1])
    return np.asarray(out, np.float32)


def arrow(pts, t, d, t_end, kind="axis", w=13):
    ARROWS.append(dict(path=catmull(pts), t=t, d=d, t_end=t_end, kind=kind, w=w))


def route(pts, t, d, t_end, plane=True, col=WHITE, size=26):
    ROUTES.append(dict(path=catmull(pts, 96), t=t, d=d, t_end=t_end, plane=plane, col=col, size=size))


def label(key, t_on, t_off):
    LABEL_T.append((key, t_on, t_off))


def pulse(lon, lat, t, col=AXIS_ARROW, size=40):
    PULSES.append((lon, lat, t, col, size))


def boom(lon, lat, t, size=30, col=(1.0, 0.72, 0.38)):
    BOOMS.append((lon, lat, t, size, col))


def shake(t, amp):
    SHAKES.append((t, amp))


LABELS = {
    # key: (中文, 当地名, 经度, 纬度, 类型, 文字放在点的哪一侧)
    "berlin": ("柏林", "BERLIN", 13.40, 52.52, "city", "r"),
    "rhineland": ("莱茵兰", "RHEINLAND", 7.0, 51.25, "region", "c"),
    "paris": ("巴黎", "PARIS", 2.35, 48.86, "city", "r"),
    "london": ("伦敦", "LONDON", -0.13, 51.51, "city", "l"),
    "vienna": ("维也纳", "WIEN", 16.37, 48.21, "city", "r"),
    "munich": ("慕尼黑", "MÜNCHEN", 11.58, 48.14, "city", "l"),
    "prague": ("布拉格", "PRAHA", 14.42, 50.08, "city", "r"),
    "sudeten": ("苏台德", "SUDETENLAND", 15.2, 50.85, "region", "c"),
    "warsaw": ("华沙", "WARSZAWA", 21.01, 52.23, "city", "r"),
    "moscow": ("莫斯科", "МОСКВА", 37.62, 55.76, "city", "r"),
    "leningrad": ("列宁格勒", "ЛЕНИНГРАД", 30.32, 59.94, "city", "r"),
    "kyiv": ("基辅", "KYIV", 30.52, 50.45, "city", "r"),
    "stalingrad": ("斯大林格勒", "СТАЛИНГРАД", 44.52, 48.71, "city", "r"),
    "peiping": ("北平", "PEIPING", 116.40, 39.90, "city", "r"),
    "shanghai": ("上海", "SHANGHAI", 121.47, 31.23, "city", "r"),
    "nanking": ("南京", "NANKING", 118.80, 32.06, "city", "l"),
    "chungking": ("重庆", "CHUNGKING", 106.55, 29.56, "city", "l"),
    "tokyo": ("东京", "TŌKYŌ", 139.69, 35.69, "city", "r"),
    "pearl": ("珍珠港", "PEARL HARBOR", 202.03, 21.36, "city", "r"),
    "hongkong": ("香港", "HONG KONG", 114.17, 22.30, "city", "r"),
    "manila": ("马尼拉", "MANILA", 120.98, 14.60, "city", "r"),
    "singapore": ("新加坡", "SINGAPORE", 103.82, 1.35, "city", "r"),
    "midway": ("中途岛", "MIDWAY", 182.63, 28.21, "city", "r"),
    "normandy": ("诺曼底", "NORMANDIE", -0.55, 49.30, "city", "b"),
    "iwojima": ("硫磺岛", "IWO JIMA", 141.32, 24.78, "city", "r"),
    "okinawa": ("冲绳", "OKINAWA", 127.80, 26.33, "city", "l"),
    "tinian": ("提尼安", "TINIAN", 145.63, 15.00, "city", "r"),
    "hiroshima": ("广岛", "HIROSHIMA", 132.46, 34.39, "city", "r"),
    "nagasaki": ("长崎", "NAGASAKI", 129.87, 32.75, "city", "l"),
}


def choreograph():
    global DATES
    S = SEG
    rl, mp, mu, po, de, fr, bl, ba, pe, sw, mi, st, dd, be, pa, tr = (S[k] for k in (
        "rhineland", "marcopolo", "munich", "poland", "declare", "france", "blitz", "barbarossa", "pearl",
        "southward", "midway", "stalingrad", "dday", "berlin", "pacific", "truman"))

    # ---------------- 片头 + 莱茵兰 1936
    CAM.k(0.0, 14, 50.5, 19)
    CAM.k(rl["tv"] + 0.4, 7.6, 50.4, 60)
    CAM.k(rl["t1"], 7.0, 50.2, 66)
    DATES.append((0.6, 1936, 3))
    on("germany", 0.7, 1.1, (13.4, 52.5))
    on("japan", 0.7, 0.8, None, "fade")
    label("berlin", 1.0, mu["t1"])
    tr_ = wt("rhineland", 0, "Truppen")
    arrow([(10.4, 50.7), (9.0, 50.5), (7.5, 50.3)], tr_ - 0.1, 0.9, mu["t0"], "axis")
    on("rhineland", tr_, 1.6, (9.6, 50.3))
    label("rhineland", wt("rhineland", 0, "Rheinland") - 0.2, rl["t1"] + 0.3)
    label("paris", ch("rhineland", 1), rl["t1"] + 0.2)
    label("london", ch("rhineland", 1) + 0.2, rl["t1"] + 0.2)
    pulse(2.35, 48.86, wt("rhineland", 1, "Paris"), ALLY_ARROW)
    pulse(-0.13, 51.51, wt("rhineland", 1, "London"), ALLY_ARROW)

    # ---------------- 卢沟桥 1937
    t0 = mp["t0"]
    CAM.k(t0, 7.0, 50.2, 66)
    CAM.k(t0 + 0.55, 62, 44, 8.5)
    CAM.k(mp["tv"] + 0.1, 116.8, 35.8, 50)
    CAM.k(mp["t1"], 117.6, 35.0, 58)
    DATES += [(t0, 1937, 7), (ch("marcopolo", 2), 1937, 12)]
    ALLY_T["china"] = (t0 + 0.9, 1e9)
    label("peiping", mp["tv"] - 0.3, mp["t1"])
    pulse(116.21, 39.85, mp["tv"] + 0.3, AXIS_ARROW, 60)
    shake(mp["tv"] + 0.3, 6)
    arrow([(117.8, 41.4), (116.6, 39.6), (115.2, 37.0)], ch("marcopolo", 1) - 0.2, 1.0, mu["t0"], "axis")
    on("china_n", ch("marcopolo", 1) - 0.3, 2.2, (117.0, 40.4))
    label("shanghai", ch("marcopolo", 2) - 0.2, mp["t1"])
    arrow([(124.2, 31.8), (122.2, 31.3), (120.4, 31.6), (119.0, 32.0)], ch("marcopolo", 2) - 0.1, 1.2, mu["t0"], "axis")
    on("china_e", ch("marcopolo", 2), 1.5, (121.5, 31.2))
    tn = wt("marcopolo", 2, "南京")
    label("nanking", tn - 0.2, mp["t1"])
    pulse(118.8, 32.06, tn + 0.3, AXIS_ARROW, 70)
    pulse(118.8, 32.06, wt("marcopolo", 2, "屠城"), (0.75, 0.05, 0.05), 110)
    on("china_38", mu["t0"] + 1.0, 1.0, (116, 33))
    on("canton", po["t0"], 0.8, (114, 22.5))
    on("hainan", po["t0"], 0.8, None, "fade")

    # ---------------- 德奥合并 / 慕尼黑 1938
    t0 = mu["t0"]
    CAM.k(t0, 117.6, 35.0, 58)
    CAM.k(t0 + 0.4, 68, 46, 9)
    CAM.k(mu["tv"] + 0.45, 13.6, 49.3, 78)
    CAM.k(mu["t1"], 14.2, 49.6, 86)
    DATES += [(t0, 1938, 3), (ch("munich", 1), 1938, 9)]
    ta = wt("munich", 0, "annexes")
    arrow([(11.6, 48.2), (13.6, 48.35), (16.1, 48.2)], ta - 0.1, 0.9, po["t0"], "axis", 11)
    on("austria", ta, 1.2, (11.6, 48.1))
    label("vienna", ta + 0.1, mu["t1"])
    label("munich", ch("munich", 1) - 0.1, mu["t1"])
    pulse(11.58, 48.14, wt("munich", 1, "Munich"), WHITE, 45)
    tsu = wt("munich", 1, "Sudetenland")
    on("sudeten", tsu - 0.1, 1.3, (14.9, 49.8), "inward")
    label("sudeten", tsu, mu["t1"] - 0.3)
    arc = mu["archival"]
    tc = mu["t1"] - 0.95
    on("czech", tc, 0.8, (14.4, 50.1))
    TAGS.append(("1939.03  捷克斯洛伐克被吞并", 14.42, 50.08, tc, mu["t1"] + 0.3))
    DATES.append((tc, 1939, 3))

    # ---------------- 波兰 1939
    t0 = po["t0"]
    CAM.k(t0, 14.2, 49.6, 86)
    CAM.k(po["tv"] + 0.3, 19.2, 51.9, 68)
    CAM.k(po["t1"], 19.6, 52.0, 74)
    DATES.append((t0, 1939, 9))
    ALLY_T["poland"] = (t0 + 0.4, 1e9)
    shake(t0 + 0.08, 14)
    label("warsaw", po["tv"], po["t1"] + 0.3)
    pulse(18.67, 54.41, po["tv"] + 0.3, AXIS_ARROW, 50)
    tw = ch("poland", 1)
    arrow([(20.7, 54.1), (20.9, 53.2), (21.0, 52.4)], tw - 0.2, 1.1, de["t1"], "axis")
    arrow([(17.0, 51.1), (19.1, 51.6), (20.7, 52.1)], tw - 0.1, 1.1, de["t1"], "axis")
    arrow([(16.1, 53.6), (17.6, 53.4), (18.6, 53.1)], tw, 1.0, de["t1"], "axis", 11)
    arrow([(18.3, 49.7), (19.4, 50.0), (20.2, 50.3)], tw + 0.1, 0.9, de["t1"], "axis", 10)
    on("poland_w", tw, 1.9, (15.5, 52.0))
    for k in range(4):
        boom(21.01 + 0.25 * math.sin(k * 2.1), 52.23 + 0.18 * math.cos(k * 1.7), tw + 0.9 + 0.22 * k, 24)
    shake(tw + 0.9, 5)

    # ---------------- 英法宣战
    t0 = de["t0"]
    CAM.k(t0, 19.6, 52.0, 74)
    CAM.k(de["tv"] + 0.5, 8.5, 50.6, 42)
    CAM.k(de["t1"], 8.2, 50.5, 44)
    label("london", t0, de["t1"])
    label("paris", t0, de["t1"])
    tb = wt("declare", 0, "Britain")
    ALLY_T["uk"] = (tb, 1e9)
    pulse(-0.13, 51.51, tb, ALLY_ARROW, 55)
    tf = wt("declare", 0, "France")
    ALLY_T["france"] = (tf, ch("france", 1) + 0.2)
    pulse(2.35, 48.86, tf, ALLY_ARROW, 55)

    # ---------------- 法国 1940
    t0 = fr["t0"]
    CAM.k(t0, 8.2, 50.5, 44)
    CAM.k(t0 + 0.55, 9.0, 55.5, 26)
    CAM.k(fr["tv"] + 0.2, 8.0, 54.8, 27)
    CAM.k(fr["tv"] + 1.3, 4.2, 49.9, 56)
    CAM.k(fr["t1"], 3.4, 49.4, 60)
    DATES += [(t0, 1940, 4), (fr["tv"], 1940, 5), (ch("france", 1), 1940, 6)]
    on("denmark", t0 + 0.1, 0.6, (10, 54.6))
    arrow([(10.4, 55.2), (10.6, 58.0), (10.7, 59.5)], t0 + 0.15, 0.6, fr["tv"] + 1.0, "axis", 9)
    on("norway", t0 + 0.25, 1.2, (10.7, 59.9))
    on("benelux", fr["tv"] + 0.4, 1.0, (7.0, 51.6))
    tar = wt("france", 0, "Ardennes")
    arrow([(6.8, 50.0), (5.3, 49.8), (3.8, 50.0), (1.7, 50.2)], tar - 0.5, 1.5, bl["t0"], "axis", 14)
    arrow([(6.6, 51.7), (5.0, 51.1), (3.4, 50.85)], tar - 0.3, 1.2, bl["t0"], "axis", 11)
    on("france_occ", tar - 0.2, 2.8, (5.6, 49.9))
    tp = wt("france", 1, "Paris")
    arrow([(2.9, 49.9), (2.5, 49.25), (2.36, 48.92)], ch("france", 1), 0.8, bl["t0"], "axis", 11)
    label("paris", ch("france", 1) - 0.2, fr["t1"] + 0.2)
    pulse(2.35, 48.86, tp, AXIS_ARROW, 60)
    ti = ch("france", 1) + 0.4
    for k in ("italy_n", "italy_s", "albania", "libya"):
        on(k, ti, 1.0, (12.5, 41.9))
    on("vichy", st["t0"], 0.5, (5, 46))

    # ---------------- 不列颠 1940
    t0 = bl["t0"]
    CAM.k(t0, 3.4, 49.4, 60)
    CAM.k(bl["tv"] + 0.2, 0.9, 51.1, 70)
    CAM.k(bl["t1"], 0.3, 51.35, 80)
    DATES.append((t0, 1940, 9))
    label("london", t0, bl["t1"] + 0.2)
    rng = np.random.default_rng(3)
    for k in range(7):
        a = t0 + 0.1 + k * (bl["t1"] - t0 - 1.8) / 7
        sx, sy = 2.2 + rng.random() * 1.6, 49.9 + rng.random() * 1.0
        ex, ey = -0.13 + rng.normal() * 0.12, 51.5 + rng.normal() * 0.07
        PLANES.append(dict(path=catmull([(sx, sy), (ex, ey)], 24), t0=a, t1=a + 2.0, size=18))
        boom(ex, ey, a + 2.0, 22)
        boom(ex + 0.05, ey - 0.03, a + 2.15, 16)
    shake(bl["t1"] - 1.2, 4)

    # ---------------- 巴巴罗萨 1941
    t0 = ba["t0"]
    CAM.k(t0, 0.3, 51.35, 80)
    CAM.k(t0 + 0.9, 27, 51.5, 26)
    CAM.k(ba["tv"] + 0.4, 29, 52.2, 26)
    CAM.k(ba["t1"], 31, 52.4, 24.5)
    DATES += [(t0, 1941, 4), (ba["tv"], 1941, 6)]
    on("balkans", t0 + 0.2, 1.0, (18, 46))
    shake(t0 + 0.08, 14)
    tj = ch("barbarossa", 1)
    ALLY_T["ussr"] = (tj, 1e9)
    arrow([(21.5, 55.2), (25.5, 57.0), (28.5, 58.6), (30.1, 59.6)], tj - 0.1, 2.0, pe["t0"], "axis", 16)
    arrow([(23.8, 52.6), (27.5, 53.9), (31.5, 54.7), (35.6, 55.5)], tj + 0.1, 2.3, pe["t0"], "axis", 18)
    arrow([(24.2, 50.2), (27.5, 50.3), (30.5, 50.3), (34.5, 48.5), (38.4, 47.4)], tj + 0.3, 2.3, pe["t0"], "axis", 16)
    on("ussr41", tj + 0.2, 3.2, (23.5, 52.5))
    for k in ("leningrad", "moscow", "kyiv"):
        label(k, ba["tv"] + 0.2, ba["t1"] + 0.3)
    shake(tj + 0.3, 6)

    # ---------------- 珍珠港 1941.12
    t0 = pe["t0"]
    CAM.k(t0, 31, 52.4, 24.5)
    CAM.k(t0 + 0.6, 95, 42, 6.5)
    CAM.k(t0 + 1.45, 174, 33, 19)
    CAM.k(ch("pearl", 0, True) + 0.1, 186, 28, 22)
    tst = wt("pearl", 1, "strike")
    CAM.k(tst + 0.15, 202.0, 21.47, 140)
    CAM.k(pe["t1"], 201.99, 21.44, 175)
    DATES.append((t0, 1941, 12))
    label("tokyo", t0 + 0.9, ch("pearl", 1))
    route([(141.5, 43.6), (147.6, 44.8), (165, 43.5), (185, 38.5), (198, 30.5), (202.0, 26.2)],
          t0 + 1.0, ch("pearl", 0, True) - t0 - 0.8, sw["t0"], plane=False, col=(0.95, 0.55, 0.45))
    for k in range(4):
        PLANES.append(dict(path=catmull([(202.0 + 0.25 * (k - 1.5), 25.9), (202.0 + 0.05 * (k - 1.5), 23.2),
                                         (202.03, 21.37)], 24),
                           t0=ch("pearl", 1) - 0.4 + 0.12 * k, t1=tst + 0.25 + 0.12 * k, size=16))
    ALLY_T["usa"] = (tst, 1e9)
    label("pearl", tst, pe["t1"])
    rng = np.random.default_rng(11)
    for k in range(12):
        tt = tst + 0.3 + k * 0.23
        boom(202.03 + rng.normal() * 0.02, 21.365 + rng.normal() * 0.012, tt, 26 + rng.random() * 20)
        FIRES.append((202.03 + rng.normal() * 0.02, 21.365 + rng.normal() * 0.012, tt, pe["t1"] + 0.4))
        if k % 3 == 0:
            shake(tt, 5)

    # ---------------- 南进 1942
    t0 = sw["t0"]
    CAM.k(t0, 201.99, 21.44, 175)
    CAM.k(t0 + 0.55, 160, 30, 8)
    CAM.k(t0 + 1.2, 110, 29, 24)
    CAM.k(sw["tv"] - 0.1, 111, 27.5, 25)
    CAM.k(sw["tv"] + 1.0, 113, 12, 20)
    CAM.k(sw["t1"], 114, 10, 19)
    DATES += [(t0, 1941, 12), (ch("southward", 1), 1942, 2)]
    label("chungking", t0 + 0.9, sw["tv"] + 0.4)
    pulse(106.55, 29.56, t0 + 1.2, ALLY_ARROW, 60)
    on("indochina", ba["t1"], 0.5, None, "fade")
    on("siam", pe["t1"], 0.5, None, "fade")
    th = wt("southward", 1, "香港")
    arrow([(113.9, 23.6), (114.15, 22.45)], th - 0.2, 0.6, mi["t0"], "axis", 10)
    on("hongkong", th, 0.5, None, "fade")
    label("hongkong", th - 0.1, sw["t1"])
    tm = wt("southward", 1, "マニラ")
    arrow([(121.4, 21.8), (120.7, 17.8), (121.0, 14.8)], tm - 0.3, 0.8, mi["t0"], "axis", 12)
    on("phil", tm - 0.2, 1.3, (121, 18.5))
    label("manila", tm - 0.1, sw["t1"])
    tsg = wt("southward", 1, "シンガポール")
    arrow([(107, 10.5), (102.5, 6.4), (103.3, 3.0), (103.8, 1.5)], tsg - 0.4, 0.9, mi["t0"], "axis", 12)
    on("malaya", tsg - 0.5, 1.2, (101.5, 6.8))
    label("singapore", tsg - 0.1, sw["t1"])
    pulse(103.82, 1.35, tsg + 0.4, AXIS_ARROW, 60)
    te = ch("southward", 1, True)
    on("dei", te - 0.6, 1.6, (109, 3))
    on("burma", te - 0.3, 1.4, (99, 15))
    on("png_n", te, 1.0, (141, -3))
    on("perim", te - 0.4, 1.8, (128, 26), strength=0.30)

    # ---------------- 中途岛 1942.6
    t0 = mi["t0"]
    CAM.k(t0, 114, 10, 19)
    CAM.k(t0 + 0.45, 150, 22, 8)
    CAM.k(mi["tv"] + 0.7, 181.4, 29.8, 44)
    CAM.k(mi["t1"], 181.6, 29.6, 50)
    DATES.append((t0, 1942, 6))
    label("midway", mi["tv"] + 0.3, mi["t1"])
    tsu = wt("midway", 1, "sunk")
    for k, (x, y) in enumerate([(179.6, 31.0), (180.1, 30.6), (179.9, 31.5), (180.6, 31.1)]):
        ts = tsu - 0.2 + 0.28 * k
        SHIPS.append(dict(x=x, y=y, t0=mi["tv"] + 0.3, t1=ts))
        boom(x, y, ts, 34)
        shake(ts, 4)
    arrow([(185.5, 32.4), (183.2, 31.9), (181.0, 31.3)], ch("midway", 1) - 0.3, 0.8, mi["t1"], "ally", 11)

    # ---------------- 斯大林格勒 1942-43
    t0 = st["t0"]
    CAM.k(t0, 181.6, 29.6, 50)
    CAM.k(t0 + 0.5, 110, 42, 6)
    CAM.k(st["tv"] + 0.3, 41.5, 48.3, 36)
    CAM.k(ch("stalingrad", 1) + 0.3, 43.3, 48.5, 44)
    CAM.k(st["t1"], 40, 49, 32)
    DATES += [(t0, 1942, 8), (ch("stalingrad", 1), 1943, 2)]
    on("ussr42", t0 + 0.3, 1.5, (37, 49.5))
    arrow([(36.9, 50.0), (40.0, 49.3), (42.5, 48.9), (44.2, 48.72)], t0 + 0.5, 1.1, ch("stalingrad", 1), "axis", 14)
    arrow([(39.5, 47.2), (40.6, 45.5), (42.4, 44.2)], t0 + 0.6, 1.0, ch("stalingrad", 1), "axis", 12)
    label("stalingrad", st["tv"], st["t1"])
    for k in range(9):
        boom(44.52 + 0.12 * math.sin(k * 2.3), 48.71 + 0.08 * math.cos(k * 1.3), st["tv"] + 0.2 + k * 0.2, 18)
    t1c = ch("stalingrad", 1)
    arrow([(42.6, 50.0), (43.1, 49.2), (43.55, 48.75)], t1c - 0.2, 1.0, st["t1"], "ally", 13)
    arrow([(45.3, 47.7), (44.4, 48.2), (43.7, 48.62)], t1c - 0.1, 1.0, st["t1"], "ally", 13)
    off("ussr42", t1c + 0.7, 1.6, (45.5, 48), "from")
    pulse(44.52, 48.71, wt("stalingrad", 1, "капитулировала"), ALLY_ARROW, 70)

    # ---------------- 诺曼底 1944
    t0 = dd["t0"]
    CAM.k(t0, 40, 49, 32)
    CAM.k(t0 + 0.6, 18, 50, 14)
    CAM.k(dd["tv"] + 0.2, -0.6, 49.85, 90)
    CAM.k(ch("dday", 1, True) - 0.1, -0.5, 49.6, 108)
    CAM.k(dd["t1"], 12, 51, 21)
    DATES.append((t0, 1944, 6))
    shake(t0 + 0.08, 14)
    on("ichigo", t0, 0.5, None, "fade")
    off("libya", t0, 0.5, None, "fade")
    label("normandy", dd["tv"], ch("dday", 1, True) + 0.3)
    tsm = wt("dday", 1, "storm")
    for k, (a, b) in enumerate([((-1.9, 50.65), (-1.2, 49.45)), ((-1.3, 50.8), (-0.95, 49.4)),
                                ((-0.8, 50.8), (-0.5, 49.37)), ((-0.3, 50.75), (-0.25, 49.35))]):
        arrow([a, ((a[0] + b[0]) / 2 + 0.1, (a[1] + b[1]) / 2), b], tsm - 0.5 + 0.12 * k, 0.9, dd["t1"], "ally", 11)
    for k in range(5):
        boom(-1.0 + 0.2 * k, 49.36 + 0.03 * math.sin(k), tsm + 0.5 + 0.15 * k, 16, (1.0, 0.8, 0.6))
    te = ch("dday", 1, True)
    off("france_occ", te - 0.2, 2.2, (-0.6, 49.3))
    off("vichy", te + 0.2, 1.6, (5.5, 43.2))
    off("italy_s", te, 1.2, (15.5, 38))
    off("ussr41", te - 0.1, 2.4, (38, 55))
    arrow([(31, 54.6), (27, 54.1), (23.4, 52.8)], te, 1.4, be["t0"] + 0.5, "ally", 16)
    arrow([(-0.3, 49.2), (1.2, 49.0), (2.3, 48.9)], te + 0.3, 1.0, be["t0"] + 0.5, "ally", 12)

    # ---------------- 攻克柏林 1945.5
    t0 = be["t0"]
    CAM.k(t0, 12, 51, 21)
    CAM.k(be["tv"] + 0.2, 13.5, 51.9, 40)
    CAM.k(be["t1"], 13.4, 52.25, 52)
    DATES.append((t0, 1945, 5))
    shake(t0 + 0.08, 12)
    label("berlin", be["tv"], be["t1"] + 0.2)
    arrow([(19.8, 52.3), (16.6, 52.5), (13.9, 52.52)], be["tv"] - 0.05, 1.1, be["t1"], "ally", 16)
    arrow([(18.2, 50.3), (15.6, 51.4), (13.8, 52.3)], be["tv"] + 0.05, 1.1, be["t1"], "ally", 13)
    arrow([(6.6, 51.3), (9.5, 51.9), (11.8, 52.4)], be["tv"] + 0.1, 1.1, be["t1"], "ally", 14)
    tv = be["tv"]
    dcol = ch("berlin", 1, True) - tv + 0.3
    for k in ("germany", "rhineland", "austria", "sudeten", "czech", "poland_w", "benelux", "denmark", "norway",
              "italy_n", "balkans", "albania"):
        off(k, tv, dcol, (13.4, 52.52), "collapse")
    pulse(13.40, 52.52, wt("berlin", 0, "Берлин"), ALLY_ARROW, 80)
    pulse(13.40, 52.52, wt("berlin", 2, "Победа"), WHITE, 140)

    # ---------------- 太平洋 1945
    t0 = pa["t0"]
    CAM.k(t0, 13.4, 52.25, 52)
    CAM.k(t0 + 0.45, 80, 40, 6)
    CAM.k(pa["tv"] + 0.4, 152, 17, 15)
    CAM.k(pa["t1"], 142, 22, 18)
    DATES.append((t0, 1945, 6))
    label("tokyo", pa["tv"], END["flash1"])
    tc0 = ch("pacific", 0)
    chain = [((202, 21.4), (186, 10), (172.9, 1.5)), ((172.9, 1.5), (169.5, 6), (167.7, 8.7)),
             ((167.7, 8.7), (156, 12.5), (145.7, 15.2))]
    for k, pts in enumerate(chain):
        arrow(list(pts), tc0 + 0.1 + 0.45 * k, 0.6, pa["t1"] + 0.6, "ally", 12)
    arrow([(147.5, -8.5), (141, -3.5), (132, 4.5), (125.2, 10.9)], tc0 + 0.4, 1.3, pa["t1"] + 0.6, "ally", 12)
    tiw = wt("pacific", 1, "Iwo")
    arrow([(145.7, 15.2), (143.2, 20.2), (141.4, 24.6)], tiw - 0.3, 0.6, pa["t1"] + 0.6, "ally", 12)
    label("iwojima", tiw, pa["t1"] + 0.5)
    tok = wt("pacific", 1, "Okinawa")
    arrow([(141.3, 24.8), (134.5, 26.6), (128.0, 26.4)], tok - 0.35, 0.6, pa["t1"] + 0.6, "ally", 12)
    label("okinawa", tok, pa["t1"] + 0.5)
    off("perim", tc0, 2.2, (178, 5))
    off("png_n", tc0 + 0.2, 1.0, (152, -6))
    off("phil", tc0 + 0.6, 1.4, (125.5, 10))
    off("burma", ch("pacific", 1), 1.2, (93, 22))

    # ---------------- 结尾：广岛 / 长崎
    h0, f1 = END["hiro_t0"], END["flash1"]
    CAM.k(h0, 141, 23, 21)
    CAM.k(h0 + 0.8, 139, 24.5, 30)
    CAM.k(f1, 133.5, 32.8, 58)
    CAM.k(f1 + 0.05, 132.46, 34.0, 92)
    CAM.k(END["naga_t0"], 132.2, 33.9, 106)
    CAM.k(END["flash2"] + 1.0, 131.2, 33.5, 112)
    DATES.append((h0, 1945, 8))
    label("tinian", h0, f1)
    label("hiroshima", h0 + 0.5, END["surrender"])
    route([(145.63, 15.0), (141.5, 24.2), (136.3, 30.6), (132.46, 34.39)], h0 + 0.2, f1 - h0 - 0.45, f1,
          plane=True, col=(0.9, 0.9, 0.86), size=30)
    label("nagasaki", END["naga_t0"], END["surrender"])
    route([(134.8, 28.8), (131.3, 31.6), (129.87, 32.75)], END["naga_t0"] + 0.1, END["flash2"] - END["naga_t0"] - 0.3,
          END["flash2"], plane=True, col=(0.9, 0.9, 0.86), size=30)
    CAM.keys.sort(key=lambda k: k[0])
    DATES.sort()


choreograph()


# ================================================================== 地图绘制
def make_bg():
    g = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
    bg = OCEAN * (1 - g * 0.25) + OCEAN2 * g * 0.25
    rng = np.random.default_rng(5)
    n = cv2.GaussianBlur(rng.random((H // 2, W // 2)).astype(np.float32), (0, 0), 1.2)
    n = cv2.resize(n, (W, H))
    return (bg + (n[..., None] - 0.5) * 0.012).astype(np.float32)


BG = make_bg()
_dmax = {}


def dmax_for(name, o, mode):
    key = (name, o, mode)
    if key not in _dmax:
        kx0 = math.cos(math.radians(o[1]))
        m = 1e-3
        for bb, rs in PIECES[name]:
            r = rs[0]
            d = np.sqrt(((r[:, 0] - o[0]) * kx0) ** 2 + (r[:, 1] - o[1]) ** 2)
            m = max(m, float(d.max()))
        _dmax[key] = m
    return _dmax[key]


def front(name, spec, t, X, Y, N):
    """返回 (到达时刻数组, 软化宽度)"""
    t0, d, o, mode = spec
    if o is None or mode == "fade":
        return t0 + d * (0.15 + 0.6 * N), 0.06 + 0.08 * d, None
    kx0 = math.cos(math.radians(o[1]))
    dm = dmax_for(name, o, mode)
    dist = np.sqrt(((X - o[0]) * kx0) ** 2 + (Y - o[1]) ** 2) / dm
    if mode in ("inward", "collapse"):
        dist = 1 - dist
    return t0 + d * np.clip(0.82 * dist + 0.46 * (N - 0.5) + 0.05, 0, 1), None, dm / (0.82 * d)


def widths(w, speed, z):
    """把边缘软化与火光宽度换算成屏幕像素，保证任何缩放下都是细线"""
    if speed is None:
        return w, None
    px = speed * z
    return clamp(22 / px, 0.02, 0.3), clamp(9 / px, 0.01, 0.15)


def territory(t, v, grids):
    A = np.zeros((H, W), np.float32)
    G = np.zeros((H, W), np.float32)
    Gb = np.zeros((H, W), np.float32)
    for name, sc in SCHED.items():
        if "on" not in sc or name not in PIECE_BB:
            continue
        t_on, d_on = sc["on"][0], sc["on"][1]
        if t < t_on:
            continue
        if "off" in sc and t > sc["off"][0] + sc["off"][1] + 0.6:
            continue
        if not v.visible(PIECE_BB[name], 0.2):
            continue
        x0, y0, x1, y1 = screen_box(v, PIECE_BB[name])
        if x1 <= x0 or y1 <= y0:
            continue
        m = np.zeros((y1 - y0, x1 - x0), np.uint8)
        if not fill(m, v, PIECES[name], 255, (x0, y0)):
            continue
        a = m.astype(np.float32) / 255
        spreading = t < t_on + d_on + 0.6
        leaving = "off" in sc and t >= sc["off"][0]
        if spreading or leaving:
            if grids[0] is None:
                grids[0] = map_grids(v)
            X, Y, _, N = (g[y0:y1, x0:x1] for g in grids[0])
        if spreading:
            arr, w, sp = front(name, sc["on"], t, X, Y, N)
            w, wg = widths(w, sp, v.z)
            a_on = np.clip((t - arr) / w, 0, 1)
            if wg is not None:
                g = np.exp(-(((t - arr) / wg - 1.2) ** 2) / 0.9) * (t < t_on + d_on + 0.4)
                G[y0:y1, x0:x1] = np.maximum(G[y0:y1, x0:x1], g * a * sc["strength"] ** 0.5)
            a = a * a_on
        if leaving:
            dep, w, sp = front(name, sc["off"], t, X, Y, N)
            w, wg = widths(w, sp, v.z)
            a_left = 1 - np.clip((t - dep) / w, 0, 1)
            if wg is not None:
                gb = np.exp(-(((t - dep) / wg - 0.5) ** 2) / 0.9) * m / 255
                Gb[y0:y1, x0:x1] = np.maximum(Gb[y0:y1, x0:x1], gb * sc["strength"] ** 0.5)
            a = a * a_left
        A[y0:y1, x0:x1] = np.maximum(A[y0:y1, x0:x1], a * sc["strength"])
    return A, G, Gb


def ally_tint(t, v):
    T = O = None
    for name, (ta, tb) in ALLY_T.items():
        al = ss(ta, ta + 0.7, t) * (1 - ss(tb, tb + 0.7, t))
        if al <= 0 or not v.visible(ALLY_BB[name]):
            continue
        m = np.zeros((H, W), np.uint8)
        fill(m, v, ALLIES[name], int(255 * al))
        o = np.zeros((H, W), np.uint8)
        cs = [ipts(v, rs[0]) for bb, rs in ALLIES[name] if v.visible(bb, 0.3)]
        cv2.polylines(o, cs, True, int(255 * al), 2, cv2.LINE_AA, SHIFT)
        T = m if T is None else np.maximum(T, m)
        O = o if O is None else np.maximum(O, o)
    return T, O


def graticule(v):
    m = np.zeros((H, W), np.uint8)
    step = 10 if v.z < 40 else 5 if v.z < 120 else 1
    x0, y0, x1, y1 = v.bb
    for lon in np.arange(math.floor(x0 / step) * step, x1 + step, step):
        a, b = v.p1(lon, y1), v.p1(lon, y0)
        cv2.line(m, (int(a[0] * FX), int(a[1] * FX)), (int(b[0] * FX), int(b[1] * FX)), 255, 1, cv2.LINE_AA, SHIFT)
    for lat in np.arange(math.floor(y0 / step) * step, y1 + step, step):
        a, b = v.p1(x0, lat), v.p1(x1, lat)
        cv2.line(m, (int(a[0] * FX), int(a[1] * FX)), (int(b[0] * FX), int(b[1] * FX)), 255, 1, cv2.LINE_AA, SHIFT)
    return m


def draw_map(t, v):
    frame = BG.copy()
    grids = [None]
    paint(frame, graticule(v), (0.30, 0.36, 0.42), 0.10)
    land_src = LAND10 if v.z > 55 else LAND50
    land = np.zeros((H, W), np.uint8)
    fill(land, v, land_src)
    lk = np.zeros((H, W), np.uint8)
    if fill(lk, v, LAKES):
        land = cv2.subtract(land, lk)
    # 海岸外侧的微光
    halo = soft_glow(land, 22, 1.0)
    frame += (np.array([0.05, 0.075, 0.10], np.float32) * (halo * (1 - land / 255.0))[..., None])
    if grids[0] is None:
        grids[0] = map_grids(v)
    N = grids[0][2]
    landc = LAND[None, None] * (0.9 + 0.2 * N[..., None])
    la = (land.astype(np.float32) / 255)[..., None]
    frame += (landc - frame) * la
    T, O = ally_tint(t, v)
    if T is not None:
        paint(frame, T, ALLY, 0.24)
        paint(frame, O, (0.55, 0.75, 0.95), 0.35)
    A, G, Gb = territory(t, v, grids)
    if A.max() > 0:
        redc = RED[None, None] * (0.78 + 0.45 * N[..., None])
        frame += (redc - frame) * (A * 0.9)[..., None]
    # 国界与海岸线
    bm = np.zeros((H, W), np.uint8)
    cs = [np.round(v.p(l) * FX).astype(np.int32) for bb, l in BORDERS if v.visible(bb, 0.2)]
    if cs:
        cv2.polylines(bm, cs, False, 255, 1, cv2.LINE_AA, SHIFT)
        paint(frame, bm, BORDER, 0.42)
    cm = np.zeros((H, W), np.uint8)
    cs = [ipts(v, rs[0]) for bb, rs in land_src if v.visible(bb, 0.2)]
    if cs:
        cv2.polylines(cm, cs, True, 255, 1, cv2.LINE_AA, SHIFT)
        paint(frame, cm, COAST, 0.55)
    if G.max() > 0.01:
        frame += EMBER * (G * 0.45)[..., None]
        gs = cv2.resize(cv2.GaussianBlur(cv2.resize(G, (W // 4, H // 4)), (0, 0), 2.5), (W, H))
        frame += EMBER * (gs * 0.15)[..., None]
    if Gb.max() > 0.01:
        frame += np.array([0.55, 0.78, 1.0], np.float32) * (Gb * 0.55)[..., None]
    perim_outline(frame, t, v)
    return frame


def perim_outline(frame, t, v):
    """日本 1942 年防御圈：海上半透明红区再描一圈虚线边"""
    sc = SCHED.get("perim")
    if not sc or "on" not in sc:
        return
    ga = ss(sc["on"][0], sc["on"][0] + sc["on"][1], t)
    if "off" in sc:
        ga *= 1 - ss(sc["off"][0], sc["off"][0] + sc["off"][1], t)
    if ga <= 0.01 or not v.visible(PIECE_BB["perim"]):
        return
    m = np.zeros((H, W), np.uint8)
    for line in [GEO["perim_line"]]:
        # 只描外侧那条弧（阿留申 → 马绍尔 → 所罗门 → 爪哇 → 缅甸），内侧贴着大陆海岸的部分不画
        sp = v.p(catmull(line[:20], 300))
        seg = np.sqrt(((sp[1:] - sp[:-1]) ** 2).sum(1))
        cum = np.concatenate([[0], np.cumsum(seg)])
        s0 = 0.0
        while s0 < cum[-1]:
            s1 = min(cum[-1], s0 + 12)
            pts = np.stack([np.interp([s0, s1], cum, sp[:, 0]), np.interp([s0, s1], cum, sp[:, 1])], 1)
            cv2.polylines(m, [np.round(pts * FX).astype(np.int32)], False, 255, 2, cv2.LINE_AA, SHIFT)
            s0 += 20
    paint(frame, m, (0.95, 0.38, 0.28), 0.55 * ga)


# ------------------------------------------------------------------ 箭头 / 航线 / 飞机 / 特效
def arc_cut(sp, frac):
    seg = np.sqrt(((sp[1:] - sp[:-1]) ** 2).sum(1))
    cum = np.concatenate([[0], np.cumsum(seg)])
    L = cum[-1] * frac
    k = int(np.searchsorted(cum, L))
    if k <= 0:
        return sp[:1], 0.0
    if k >= len(sp):
        return sp, cum[-1]
    u = (L - cum[k - 1]) / max(1e-6, seg[k - 1])
    p = sp[k - 1] + (sp[k] - sp[k - 1]) * u
    return np.vstack([sp[:k], p[None]]), L


def normals(sp):
    d = np.gradient(sp, axis=0)
    d /= np.maximum(np.linalg.norm(d, axis=1, keepdims=True), 1e-6)
    return d, np.stack([-d[:, 1], d[:, 0]], 1)


def draw_arrows(frame, t, v):
    masks = {}
    zs = clamp((v.z / 40) ** 0.22, 0.75, 1.35)
    for a in ARROWS:
        if t < a["t"] or t > a["t_end"] + 0.5:
            continue
        fade = 1 - ss(a["t_end"], a["t_end"] + 0.5, t)
        p = eo((t - a["t"]) / a["d"])
        sp = v.p(a["path"])
        part, L = arc_cut(sp, max(p, 0.02))
        if len(part) < 2 or L < 3:
            continue
        w = a["w"] * zs
        hl = w * 1.9
        # 身体截到箭头底部
        body, _ = arc_cut(part, max(0.0, 1 - hl / max(L, 1e-3)))
        if len(body) < 2:
            body = part[:2]
        d, n = normals(body)
        k = np.linspace(0.25, 1.0, len(body))[:, None]
        left = body + n * (w * 0.5 * k)
        right = body - n * (w * 0.5 * k)
        poly = np.vstack([left, right[::-1]])
        tip = part[-1]
        dirv = tip - part[-2]
        dirv /= max(np.linalg.norm(dirv), 1e-6)
        nv = np.array([-dirv[1], dirv[0]])
        base = tip - dirv * hl
        head = np.array([tip + dirv * 2, base + nv * w * 1.25, base - nv * w * 1.25])
        m = masks.setdefault(a["kind"], np.zeros((H, W), np.uint8))
        val = int(255 * fade)
        cv2.fillPoly(m, [np.round(poly * FX).astype(np.int32)], val, cv2.LINE_AA, SHIFT)
        cv2.fillPoly(m, [np.round(head * FX).astype(np.int32)], val, cv2.LINE_AA, SHIFT)
    for kind, m in masks.items():
        col = np.array(AXIS_ARROW if kind == "axis" else ALLY_ARROW, np.float32)
        g = soft_glow(m, 14, 0.55)
        frame += col * g[..., None] * 0.6
        dil = cv2.dilate(m, np.ones((5, 5), np.uint8))
        paint(frame, dil, (0.02, 0.02, 0.03), 0.55)
        paint(frame, m, col, 1.0)
        # 箭头中心高光
        er = cv2.erode(m, np.ones((5, 5), np.uint8))
        paint(frame, er, np.minimum(col * 1.25 + 0.12, 1.0), 0.35)


PLANE = [np.array(p, np.float32) for p in (
    [(0.5, 0), (0.36, 0.06), (-0.44, 0.05), (-0.5, 0), (-0.44, -0.05), (0.36, -0.06)],
    [(0.12, 0.02), (-0.06, 0.52), (-0.17, 0.52), (-0.08, 0.02), (-0.08, -0.02), (-0.17, -0.52), (-0.06, -0.52), (0.12, -0.02)],
    [(-0.36, 0.02), (-0.44, 0.2), (-0.5, 0.2), (-0.47, 0.0), (-0.5, -0.2), (-0.44, -0.2), (-0.36, -0.02)])]
SHIP = np.array([(0.5, 0), (0.32, 0.11), (-0.5, 0.11), (-0.5, -0.11), (0.32, -0.11)], np.float32)


def shape_at(m, shapes, x, y, ang, size, val=255):
    c, s = math.cos(ang), math.sin(ang)
    R = np.array([[c, -s], [s, c]], np.float32)
    cs = [np.round(((sh * size) @ R.T + np.array([x, y], np.float32)) * FX).astype(np.int32) for sh in shapes]
    cv2.fillPoly(m, cs, val, cv2.LINE_AA, SHIFT)


def draw_routes(frame, t, v):
    m = np.zeros((H, W), np.uint8)
    pm = np.zeros((H, W), np.uint8)
    any_ = False
    for r in ROUTES:
        if t < r["t"] or t > r["t_end"] + 0.4:
            continue
        any_ = True
        fade = 1 - ss(r["t_end"], r["t_end"] + 0.4, t)
        p = clamp((t - r["t"]) / r["d"])
        p = p * p * (3 - 2 * p) * 0.3 + p * 0.7
        sp = v.p(r["path"])
        part, L = arc_cut(sp, max(p, 0.005))
        seg = np.sqrt(((part[1:] - part[:-1]) ** 2).sum(1))
        cum = np.concatenate([[0], np.cumsum(seg)])
        # 按弧长切虚线
        dash, gap = 16.0, 11.0
        s0 = 0.0
        while s0 < L:
            s1 = min(L, s0 + dash)
            idx = (cum >= s0) & (cum <= s1)
            pts = part[idx]
            if len(pts) >= 1:
                a0 = np.interp(s0, cum, part[:, 0]), np.interp(s0, cum, part[:, 1])
                a1 = np.interp(s1, cum, part[:, 0]), np.interp(s1, cum, part[:, 1])
                pts = np.vstack([a0, pts, a1])
                cv2.polylines(m, [np.round(pts * FX).astype(np.int32)], False, int(220 * fade), 3, cv2.LINE_AA, SHIFT)
            s0 += dash + gap
        if r["plane"] and p < 1 and len(part) >= 2:
            d = part[-1] - part[-2]
            shape_at(pm, PLANE, part[-1][0], part[-1][1], math.atan2(d[1], d[0]), r["size"], int(255 * fade))
    if any_:
        paint(frame, m, (0.92, 0.90, 0.85), 0.85)
        frame += np.array([1.0, 0.9, 0.75], np.float32) * soft_glow(pm, 8, 0.6)[..., None]
        paint(frame, pm, (0.97, 0.96, 0.92), 1.0)


def draw_planes(frame, t, v):
    pm = np.zeros((H, W), np.uint8)
    tm = np.zeros((H, W), np.uint8)
    hit = False
    for pl in PLANES:
        if not (pl["t0"] <= t <= pl["t1"]):
            continue
        hit = True
        u = (t - pl["t0"]) / (pl["t1"] - pl["t0"])
        sp = v.p(pl["path"])
        part, L = arc_cut(sp, u)
        if len(part) < 2:
            continue
        d = part[-1] - part[-2]
        trail = part[max(0, len(part) - 12):]
        cv2.polylines(tm, [np.round(trail * FX).astype(np.int32)], False, 150, 2, cv2.LINE_AA, SHIFT)
        shape_at(pm, PLANE, part[-1][0], part[-1][1], math.atan2(d[1], d[0]), pl["size"])
    if hit:
        paint(frame, tm, (0.8, 0.8, 0.78), 0.35)
        paint(frame, cv2.dilate(pm, np.ones((3, 3), np.uint8)), (0.02, 0.02, 0.02), 0.6)
        paint(frame, pm, (0.88, 0.87, 0.82), 1.0)


def radial(frame, x, y, r, col, gain):
    R = int(r * 2.5) + 2
    x0, y0, x1, y1 = int(x) - R, int(y) - R, int(x) + R + 1, int(y) + R + 1
    cx0, cy0, cx1, cy1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
    if cx1 <= cx0 or cy1 <= cy0:
        return
    yy, xx = np.mgrid[cy0:cy1, cx0:cx1].astype(np.float32)
    d2 = ((xx - x) ** 2 + (yy - y) ** 2) / max(r * r, 1e-3)
    frame[cy0:cy1, cx0:cx1] += np.asarray(col, np.float32) * (np.exp(-d2) * gain)[..., None]


def draw_fx(frame, t, v):
    rng = np.random.default_rng(int(t * 30))
    for (lon, lat, t0, col, size) in PULSES:
        u = (t - t0) / 1.0
        if 0 <= u <= 1:
            x, y = v.p1(lon, lat)
            m = np.zeros((H, W), np.uint8)
            r = 6 + size * eo(u)
            cv2.circle(m, (int(x * FX), int(y * FX)), int(r * FX), 255, 2, cv2.LINE_AA, SHIFT)
            R = int(r) + 6
            paint(frame, m, col, (1 - u) ** 1.3, (int(x) - R, int(y) - R, int(x) + R, int(y) + R))
            radial(frame, x, y, 10 + 10 * u, col, 0.5 * (1 - u) ** 2)
    zs = clamp((v.z / 40) ** 0.3, 0.6, 1.6)
    for (lon, lat, t0, size, col) in BOOMS:
        u = (t - t0) / 0.7
        if 0 <= u <= 1:
            x, y = v.p1(lon, lat)
            s = size * zs
            radial(frame, x, y, s * (0.35 + 0.8 * eo(u)), col, 1.6 * (1 - u) ** 1.6)
            radial(frame, x, y, s * 0.25, (1, 1, 0.95), 1.4 * (1 - u) ** 3)
    for (lon, lat, t0, t1) in FIRES:
        if t0 <= t <= t1:
            x, y = v.p1(lon, lat)
            fl = 0.7 + 0.3 * rng.random()
            radial(frame, x, y, 7 * zs, (1.0, 0.45, 0.12), 0.8 * fl * (1 - ss(t1 - 0.4, t1, t)))
    for s in SHIPS:
        if s["t0"] <= t <= s["t1"] + 0.15:
            x, y = v.p1(s["x"] + (t - s["t0"]) * 0.05, s["y"] - (t - s["t0"]) * 0.03)
            m = np.zeros((H, W), np.uint8)
            al = ss(s["t0"], s["t0"] + 0.3, t) * (1 - ss(s["t1"], s["t1"] + 0.15, t))
            shape_at(m, [SHIP], x, y, math.radians(155), 30, 255)
            b = (int(x) - 30, int(y) - 30, int(x) + 30, int(y) + 30)
            paint(frame, cv2.dilate(m, np.ones((3, 3), np.uint8)), (0, 0, 0), 0.6 * al, b)
            paint(frame, m, AXIS_ARROW, al, b)


def draw_labels(frame, t, v):
    for key, a, b in LABEL_T:
        al = win(t, a, b, 0.25, 0.3)
        if al <= 0:
            continue
        zh, loc, lon, lat, kind, side = LABELS[key]
        x, y = v.p1(lon, lat)
        if not (-200 < x < W + 200 and -100 < y < H + 100):
            continue
        s1 = sprite(zh, "sansb", 30, WHITE, shadow=3)
        s2 = sprite(loc, "rc", 17, (0.75, 0.76, 0.74), wght=500, track=2, shadow=2)
        if kind == "city":
            m = np.zeros((H, W), np.uint8)
            cv2.circle(m, (int(x * FX), int(y * FX)), int(5.5 * FX), 255, -1, cv2.LINE_AA, SHIFT)
            bx = (int(x) - 12, int(y) - 12, int(x) + 12, int(y) + 12)
            paint(frame, cv2.dilate(m, np.ones((4, 4), np.uint8)), (0.02, 0.02, 0.02), 0.7 * al, bx)
            paint(frame, m, WHITE, al, bx)
            if side == "r":
                blit(frame, s1, x + 12, y - 2, al, "lb")
                blit(frame, s2, x + 14, y - 6, al, "lt")
            elif side == "l":
                blit(frame, s1, x - 12, y - 2, al, "rb")
                blit(frame, s2, x - 14, y - 6, al, "rt")
            else:
                blit(frame, s1, x, y + 8, al, "ct")
                blit(frame, s2, x, y + 44, al, "ct")
        else:
            blit(frame, sprite(zh, "sansk", 40, (1.0, 0.86, 0.80), track=6, shadow=4), x, y - 4, al * 0.95, "cb")
            blit(frame, sprite(loc, "rc", 18, (0.95, 0.80, 0.74), wght=600, track=5, shadow=2), x, y, al * 0.9, "ct")
    for text, lon, lat, a, b in TAGS:
        al = win(t, a, b, 0.2, 0.3)
        if al > 0:
            x, y = v.p1(lon, lat)
            spr = sprite(text, "sansb", 24, (1, 0.9, 0.86), shadow=3)
            blit(frame, spr, x + 16, y + 30, al, "lt")


# ================================================================== 界面
MON_EN = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
SEGS = TL["segs"]
STATION_AT = [(s["t0"], s["st"]) for s in SEGS]


def date_at(t):
    cur, prev, tc = DATES[0], DATES[0], DATES[0][0]
    for d in DATES:
        if d[0] <= t:
            prev, cur, tc = cur, d, d[0]
    return cur, prev, tc


def month_row(frame, d, yb, al):
    s1 = sprite(f"{d[2]}月", "sansb", 28, (0.95, 0.35, 0.28), shadow=2)
    blit(frame, s1, 74, yb, al, "lb")
    blit(frame, sprite(MON_EN[d[2] - 1], "rc", 20, GREY, wght=600, track=4, shadow=2),
         74 + s1[1].shape[1] + 2, yb - 5, al, "lb")


def draw_year(frame, t, al):
    cur, prev, tc = date_at(t)
    u = eo((t - tc) / 0.4) if t >= tc else 1.0
    x, y = 70, 34
    for (d, dy, a) in ((prev, -34 * u, 1 - u), (cur, 34 * (1 - u), u)):
        if a <= 0.01 or (d is cur and d is prev):
            continue
        blit(frame, sprite(str(d[1]), "osw", 96, WHITE, wght=600, track=3, shadow=4), x, y + dy, al * a)
        month_row(frame, d, y + 172 + dy * 0.5, al * a)
    if cur is prev or u >= 1:
        blit(frame, sprite(str(cur[1]), "osw", 96, WHITE, wght=600, track=3, shadow=4), x, y, al)
        month_row(frame, cur, y + 172, al)


def draw_timebar(frame, t, al):
    cur, prev, tc = date_at(t)
    dv0, dv1 = prev[1] + (prev[2] - 1) / 12, cur[1] + (cur[2] - 1) / 12
    dv = dv0 + (dv1 - dv0) * e5((t - tc) / 0.6)
    x0, x1, y = 330, 1300, 70
    X = lambda d: x0 + (d - 1936) / (1945.75 - 1936) * (x1 - x0)
    m = np.zeros((H, W), np.uint8)
    cv2.line(m, (x0, y), (x1, y), 150, 2, cv2.LINE_AA)
    for yr in range(1936, 1946):
        xx = int(X(yr))
        cv2.line(m, (xx, y - 7), (xx, y + 7), 200, 1, cv2.LINE_AA)
    box = (x0 - 20, y - 30, x1 + 40, y + 40)
    paint(frame, m, (0.7, 0.7, 0.68), 0.5 * al, box)
    for yr in range(1936, 1946):
        blit(frame, sprite(str(yr), "rc", 16, (0.66, 0.66, 0.64), wght=500, track=1, shadow=2),
             X(yr), y + 12, al * 0.85, "ct")
    mm = np.zeros((H, W), np.uint8)
    xm = X(dv)
    cv2.line(mm, (x0 * 16, y * 16), (int(xm * 16), y * 16), 255, 3, cv2.LINE_AA, 4)
    cv2.circle(mm, (int(xm * 16), y * 16), 7 * 16, 255, -1, cv2.LINE_AA, 4)
    paint(frame, mm, (0.92, 0.25, 0.18), al, box)
    radial(frame, xm, y, 10, (1.0, 0.4, 0.25), 0.5 * al)


def make_radio_bg():
    w, h = 470, 118
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    dr.rounded_rectangle((0, 0, w - 1, h - 1), 10, fill=(8, 10, 12, 150), outline=(120, 118, 110, 110), width=1)
    f = font("monom", 13)
    x0, x1, yb = 22, w - 22, 86
    for i in range(0, 61):
        x = x0 + (x1 - x0) * i / 60
        L = 12 if i % 10 == 0 else 7 if i % 5 == 0 else 4
        dr.line((x, yb - L, x, yb), fill=(190, 188, 180, 200 if i % 5 == 0 else 120), width=1)
    for i, n in enumerate(["55", "60", "70", "80", "100", "120", "140", "160"]):
        x = x0 + (x1 - x0) * i / 7
        tw = f.getlength(n)
        dr.text((x - tw / 2, yb + 5), n, font=f, fill=(160, 158, 150, 200))
    a = np.asarray(img, np.float32) / 255
    return a[..., :3].copy(), a[..., 3].copy()


RADIO_BG = make_radio_bg()
RX, RY = W - 530, 32


def needle_pos(t):
    pos = lambda st: script.STATIONS[st][2]
    if t < SEGS[0]["t0"]:
        u = e5((t - 0.15) / 1.6)
        return 0.02 + (pos("berlin") - 0.02) * u + 0.015 * math.sin(t * 23) * (1 - u)
    p_prev = pos(SEGS[0]["st"])
    for i, (ts, st) in enumerate(STATION_AT):
        if t < ts:
            break
        p_new = pos(st)
        if i > 0:
            p_prev = pos(STATION_AT[i - 1][1])
        u = clamp((t - ts) / 0.55)
        back = 1 + 2.2 * (u - 1) ** 3 + 1.2 * (u - 1) ** 2 if u < 1 else 1
        cur = p_prev + (p_new - p_prev) * back
    return cur


def station_now(t):
    st, ts = SEGS[0]["st"], SEGS[0]["t0"]
    for a, s in STATION_AT:
        if a <= t:
            st, ts = s, a
    return st, ts


def voice_level(t):
    for s in SEGS:
        for c in s["chunks"]:
            if c["t"] <= t <= c["t"] + c["dur"]:
                return 0.45 + 0.55 * abs(math.sin(t * 37.0) * math.sin(t * 11.3 + 1))
        a = s.get("archival")
        if a and a.get("t") is not None and a["t"] <= t <= a["t"] + a["dur"]:
            return 0.4 + 0.5 * abs(math.sin(t * 29.0) * math.sin(t * 7.1))
    return 0.05


VENV = None
_ve = os.path.join(B, "voice_env.npy")
if os.path.exists(_ve):
    VENV = np.load(_ve)


def draw_radio(frame, t, al):
    blit(frame, RADIO_BG, RX, RY, al)
    st, ts = station_now(t)
    city, lang, _ = script.STATIONS[st]
    silent = END["flash1"] + 0.3 < t < SEG["truman"]["t0"]
    blink = 0.55 + 0.45 * (math.sin(t * 6.0) > 0)
    m = np.zeros((H, W), np.uint8)
    cv2.circle(m, ((RX + 24) * 16, (RY + 26) * 16), 6 * 16, 255, -1, cv2.LINE_AA, 4)
    paint(frame, m, (0.95, 0.2, 0.15) if not silent else (0.35, 0.35, 0.35), al * blink,
          (RX + 10, RY + 12, RX + 40, RY + 40))
    blit(frame, sprite("ON AIR" if not silent else "NO SIGNAL", "mono", 15, (0.95, 0.35, 0.28) if not silent else GREY),
         RX + 38, RY + 16, al)
    ca = ss(ts + 0.12, ts + 0.35, t) if t > 1 else 1
    if not silent:
        blit(frame, sprite(city, "sansb", 22, WHITE), RX + 130, RY + 11, al * ca)
        blit(frame, sprite(lang, "rc", 15, GREY, wght=600, track=3), RX + 130 + sprite(city, "sansb", 22)[1].shape[1] + 4,
             RY + 19, al * ca)
    # 电平表
    if VENV is not None:
        lv = float(VENV[min(len(VENV) - 1, int(t * FPS))])
    else:
        lv = voice_level(t)
    mm = np.zeros((H, W), np.uint8)
    for i in range(8):
        hh = int(4 + 22 * clamp(lv * (0.6 + 0.4 * math.sin(i * 1.7 + t * 13)) ** 1.2))
        x = RX + 470 - 22 - (8 - i) * 9
        cv2.rectangle(mm, (x, RY + 40 - hh), (x + 5, RY + 40), 255, -1)
    paint(frame, mm, (0.85, 0.83, 0.75), al * (0.25 if silent else 0.8), (RX + 380, RY + 8, RX + 470, RY + 44))
    # 指针
    p = needle_pos(t)
    nx = RX + 22 + (470 - 44) * p
    nm = np.zeros((H, W), np.uint8)
    cv2.line(nm, (int(nx * 16), (RY + 58) * 16), (int(nx * 16), (RY + 100) * 16), 255, 2, cv2.LINE_AA, 4)
    paint(frame, nm, (1.0, 0.25, 0.18), al, (RX, RY + 50, RX + 470, RY + 110))
    radial(frame, nx, RY + 79, 8, (1.0, 0.3, 0.2), 0.45 * al)


def wrap_words(text, maxw, fname, size):
    f = font(fname, size)
    if f.getlength(text) <= maxw:
        return [text]
    if " " in text:
        words, lines, cur = text.split(" "), [], ""
        for w_ in words:
            test = (cur + " " + w_).strip()
            if f.getlength(test) > maxw and cur:
                lines.append(cur)
                cur = w_
            else:
                cur = test
        return lines + [cur]
    n = len(text)
    for sep in "，、：——":
        k = text.find(sep, n // 3)
        if 0 < k < n - 2:
            return [text[:k + 1], text[k + 1:]]
    return [text[:n // 2], text[n // 2:]]


def draw_sub(frame, zh, orig, al, tag=None, ofont="rc"):
    y = H - 64
    for line in reversed(wrap_words(zh, 1500, "sansb", 46)):
        blit(frame, sprite(line, "sansb", 46, WHITE, stroke=3, shadow=5), W / 2, y, al, "cb")
        y -= 62
    if orig:
        osz = 30 if ofont == "rc" else 27
        for line in reversed(wrap_words(orig, 1600, ofont, osz)):
            blit(frame, sprite(line, ofont, osz, (0.82, 0.82, 0.80), stroke=2, shadow=3), W / 2, y + 2, al * 0.95, "cb")
            y -= 40
    if tag:
        blit(frame, sprite(tag, "sansb", 22, (1.0, 0.42, 0.34), track=2, shadow=3), W / 2, y + 4, al, "cb")


def subtitles(frame, t):
    for s in SEGS:
        cs = s["chunks"]
        for i, c in enumerate(cs):
            b = cs[i + 1]["t"] - 0.02 if i + 1 < len(cs) else c["t"] + c["dur"] + 0.45
            al = win(t, c["t"] - 0.06, b, 0.08, 0.12)
            if al > 0:
                orig = None if s["lang"] == "zh" else c["text"]
                tag = s.get("who") if s["id"] == "truman" else None
                draw_sub(frame, c["zh"], orig, al, tag, "sans" if s["lang"] == "ja" else "rc")
        a = s.get("archival")
        if a and a.get("t") is not None and a.get("file"):
            al = win(t, a["t"] - 0.05, a["t"] + a["dur"] + 0.3, 0.1, 0.2)
            if al > 0:
                draw_sub(frame, a["zh"], a["en"], al, f"◉ 历史原声 · {a['who']}")


def quote_cards(frame, t):
    for s in SEGS:
        a = s.get("archival")
        if not a or a.get("file") or a.get("t") is None or a["dur"] <= 0:
            continue
        al = win(t, a["t"] - 0.1, a["t"] + a["dur"] + 0.2, 0.15, 0.25)
        if al <= 0:
            continue
        frame *= 1 - 0.5 * al
        n = len(a["en"])
        k = int(n * clamp((t - a["t"]) / 0.9))
        en = a["en"][:k]
        yc = H * 0.76
        blit(frame, sprite("“" + en + ("”" if k >= n else ""), "type", 44, WHITE, shadow=4), W / 2, yc - 40, al, "cb")
        blit(frame, sprite(a["zh"], "serif", 38, (0.95, 0.93, 0.88), shadow=4), W / 2, yc + 6, al * ss(a["t"] + 0.5, a["t"] + 0.9, t), "ct")
        yr = {"张伯伦": "1938年9月30日", "罗斯福": "1941年12月8日", "杜鲁门": "1945年8月6日"}.get(a["who"], "")
        blit(frame, sprite(f"—— {a['who']}，{yr}", "sans", 24, GREY, shadow=3), W / 2 + 320, yc + 70, al, "rt")


def date_cards(frame, t):
    for s in SEGS:
        if not s.get("card"):
            continue
        a, b = s["t0"] + 0.05, s["tv"] + 0.3
        if not (a <= t <= b + 0.3):
            continue
        date, cap = s["card"]
        u = (t - a) / 0.14
        out = ss(b, b + 0.3, t)
        al = clamp(u * 2.5) * (1 - out)
        frame *= 1 - 0.58 * al
        sc = 1 + 0.32 * (1 - eo(u)) - 0.05 * out
        sd = sprite(date, "osw", 210, WHITE, wght=700, track=10, shadow=8)
        blit(frame, sd, W / 2, H / 2 - 30, al, "cb", sc)
        cap_s = sprite(cap, "sansk", 60, WHITE, track=14)
        cw = cap_s[1].shape[1] * sc
        bw, bh = int(cw + 70), int(86 * sc)
        x0, y0 = int(W / 2 - bw / 2), int(H / 2 + 6)
        reg = frame[y0:y0 + bh, x0:x0 + bw]
        reg += (np.array([0.72, 0.08, 0.06], np.float32) - reg) * (0.95 * al)
        blit(frame, cap_s, W / 2, y0 + bh / 2 + 2, al, "cm", sc)
        if u < 1.2:
            frame += 0.22 * (1 - clamp(u / 1.2))


def text_cards(frame, t):
    sw = SEG["southward"]
    a, b = sw["t0"] + 0.75, sw["tv"] - 0.05
    al = win(t, a, b, 0.25, 0.3)
    if al > 0:
        frame *= 1 - 0.3 * al
        blit(frame, sprite(script.CARDS["china_alone"], "serifk", 60, WHITE, track=6, shadow=6), W / 2, H * 0.40, al, "cm")
        m = np.zeros((H, W), np.uint8)
        L = int(300 * eo((t - a) / 0.6))
        cv2.line(m, (W // 2 - L, int(H * 0.40) + 52), (W // 2 + L, int(H * 0.40) + 52), 255, 3, cv2.LINE_AA)
        paint(frame, m, (0.85, 0.15, 0.12), al, (W // 2 - 320, int(H * 0.4) + 40, W // 2 + 320, int(H * 0.4) + 64))
    # 广岛 / 长崎 时间卡
    for key, a, b in (("hiroshima", END["hiro_t0"] + 0.3, END["flash1"] + 0.1), ("nagasaki", END["naga_t0"], END["flash2"] + 0.1)):
        al = win(t, a, b, 0.2, 0.05)
        if al <= 0:
            continue
        date, tm, name = script.CARDS[key]
        full = f"{date}  {tm}"
        k = int(len(full) * clamp((t - a) / 1.0))
        blit(frame, sprite(full[:k] if k else " ", "osw", 78, WHITE, wght=600, track=6, shadow=6), W / 2, 150, al, "ct")
        blit(frame, sprite(name, "sansb", 36, (1.0, 0.82, 0.74), track=8, shadow=4), W / 2, 262, al * ss(a + 0.8, a + 1.1, t), "ct")


def ending_texts(frame, t):
    for key, a, b, size in (("surrender", END["surrender"], END["toll"], 50), ("toll", END["toll"], END["title"], 50)):
        al = win(t, a + 0.1, b - 0.1, 0.5, 0.45)
        if al > 0:
            blit(frame, sprite(script.CARDS[key], "serif", size, (0.93, 0.92, 0.88), shadow=4), W / 2, H / 2, al, "cm")
    a, b = END["title"], END["end"] - 0.6
    al = win(t, a + 0.15, b, 0.7, 0.8)
    if al > 0:
        t1, t2 = script.CARDS["title"]
        blit(frame, sprite(t1, "serifk", 96, (0.95, 0.94, 0.9), track=14, shadow=6), W / 2, H / 2 - 24, al, "cb")
        m = np.zeros((H, W), np.uint8)
        L = int(260 * eo((t - a) / 1.2))
        cv2.line(m, (W // 2 - L, H // 2 + 4), (W // 2 + L, H // 2 + 4), 255, 2, cv2.LINE_AA)
        paint(frame, m, (0.8, 0.14, 0.1), al, (W // 2 - 300, H // 2 - 4, W // 2 + 300, H // 2 + 12))
        blit(frame, sprite(t2, "osw", 44, GREY, wght=400, track=16), W / 2, H / 2 + 30, al * ss(a + 0.6, a + 1.2, t), "ct")


# ================================================================== 后期
VIG = None


def vignette():
    global VIG
    if VIG is None:
        x = (UU - W / 2) / (W / 2)
        y = (VV - H / 2) / (H / 2)
        r = np.sqrt(x * x * 0.85 + y * y)
        VIG = (1 - 0.42 * np.clip(r - 0.35, 0, None) ** 1.6)[..., None].astype(np.float32)
    return VIG


GRAIN = None


def grain(i):
    global GRAIN
    if GRAIN is None:
        rng = np.random.default_rng(1)
        GRAIN = [cv2.GaussianBlur(rng.normal(0, 1, (H, W)).astype(np.float32), (0, 0), 0.7) for _ in range(6)]
    return GRAIN[i % 6]


def glitch_amt(t):
    g = 0.0
    for s in SEGS:
        g = max(g, math.exp(-((t - s["t0"] - 0.06) / 0.11) ** 2))
    g = max(g, 1 - ss(0.1, 0.9, t))
    return g


def glitch(frame, t, g, rng):
    if g < 0.03:
        return frame
    out = frame.copy()
    nb = 14
    edges = np.sort(rng.integers(0, H, nb))
    for a, b in zip(edges[:-1], edges[1:]):
        if rng.random() < 0.55:
            dx = int(rng.normal() * 40 * g)
            out[a:b] = np.roll(frame[a:b], dx, axis=1)
    sh = int(8 * g)
    if sh:
        out[..., 0] = np.roll(out[..., 0], sh, axis=1)
        out[..., 2] = np.roll(out[..., 2], -sh, axis=1)
    noise = rng.random((H // 4, W // 4)).astype(np.float32)
    noise = cv2.resize(noise, (W, H), interpolation=cv2.INTER_NEAREST)
    lines = (np.sin(np.arange(H, dtype=np.float32) * 2.1 + t * 90) > 0.6).astype(np.float32)[:, None]
    out += ((noise - 0.5) * 0.28 * g + lines * 0.05 * g)[..., None]
    return out


def shake_off(t):
    dx = dy = 0.0
    for (ts, amp) in SHAKES:
        if 0 <= t - ts < 0.8:
            k = amp * math.exp(-(t - ts) * 8)
            dx += k * math.sin((t - ts) * 71)
            dy += k * math.cos((t - ts) * 57)
    return dx, dy


def render(t, fi=0):
    cx, cy, z = CAM(t)
    dx, dy = shake_off(t)
    v = View(cx, cy, z)
    v = View(cx - dx / v.sx, cy + dy / z, z)
    frame = draw_map(t, v)
    draw_arrows(frame, t, v)
    draw_routes(frame, t, v)
    draw_planes(frame, t, v)
    draw_fx(frame, t, v)
    draw_labels(frame, t, v)
    # 核爆后画面褪色
    f1, f2 = END["flash1"], END["flash2"]
    if t > f1:
        gray = frame.mean(2, keepdims=True)
        frame += (gray * np.array([1.08, 0.98, 0.86], np.float32) - frame) * 0.7
        x, y = v.p1(132.46, 34.39)
        radial(frame, x, y, 18, (1.0, 0.55, 0.25), 0.9 + 0.1 * math.sin(t * 9))
        u = (t - f1) / 3.0
        if u < 1:
            m = np.zeros((H, W), np.uint8)
            cv2.circle(m, (int(x * 16), int(y * 16)), int((20 + 900 * eo(u)) * 16), 255, 3, cv2.LINE_AA, 4)
            paint(frame, m, (1.0, 0.9, 0.8), 0.6 * (1 - u))
    if t > f2:
        x, y = v.p1(129.87, 32.75)
        radial(frame, x, y, 16, (1.0, 0.55, 0.25), 0.9)
    date_cards(frame, t)
    quote_cards(frame, t)
    text_cards(frame, t)
    ui = ss(0.5, 1.1, t) * (1 - ss(END["surrender"] - 0.2, END["surrender"] + 0.3, t))
    if ui > 0:
        draw_year(frame, t, ui)
        draw_timebar(frame, t, ui)
        draw_radio(frame, t, ui)
    subtitles(frame, t)
    # 辉光 + 暗角
    small = cv2.resize(frame, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    bright = np.clip(small - 0.55, 0, None)
    frame += cv2.resize(cv2.GaussianBlur(bright, (0, 0), 6), (W, H)) * 0.7
    frame *= vignette()
    rng = np.random.default_rng(fi)
    frame = glitch(frame, t, glitch_amt(t), rng)
    # 白闪与黑场
    white = 0.0
    if f1 <= t:
        white = max(white, 1.0 if t < f1 + 0.4 else math.exp(-(t - f1 - 0.4) / 0.35))
    if f2 <= t:
        white = max(white, 0.9 if t < f2 + 0.22 else 0.9 * math.exp(-(t - f2 - 0.22) / 0.3))
    black = 1 - ss(0.15, 1.3, t)
    black = max(black, ss(f1 + 0.3, f1 + 1.3, t) * (1 - ss(SEG["truman"]["t0"] - 0.1, SEG["truman"]["t0"] + 0.9, t)))
    black = max(black, ss(f2 + 0.3, f2 + 1.4, t))
    if black > 0:
        frame *= 1 - black
    if white > 0:
        frame += (1.0 - frame) * white
    ending_texts(frame, t)
    frame += grain(fi)[..., None] * 0.028
    return np.clip(frame, 0, 1)


def to8(frame):
    return (frame * 255 + 0.5).astype(np.uint8)


def _job(i):
    return to8(render(i / FPS, i)).tobytes()


def main():
    mode = sys.argv[1]
    if mode == "still":
        for a in sys.argv[2:]:
            t = float(a)
            img = to8(render(t, int(t * FPS)))
            cv2.imwrite(os.path.join(B, f"still_{t:06.2f}.png"), cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
            print("still", t)
        return
    out = sys.argv[2]
    t0 = float(sys.argv[3]) if len(sys.argv) > 3 else 0
    t1 = float(sys.argv[4]) if len(sys.argv) > 4 else DUR
    frames = range(int(t0 * FPS), min(NF, int(t1 * FPS)))
    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "16",
                           "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    from multiprocessing import Pool
    import time
    st = time.time()
    with Pool(int(os.environ.get("JOBS", "4"))) as pool:
        for k, buf in enumerate(pool.imap(_job, frames, chunksize=4)):
            ff.stdin.write(buf)
            if k % 150 == 0:
                print(f"frame {k}/{len(frames)}  {time.time() - st:.0f}s", flush=True)
    ff.stdin.close()
    ff.wait()
    print("done", out, f"{time.time() - st:.0f}s")


if __name__ == "__main__":
    main()
