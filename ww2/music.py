"""代码合成的配乐与音效 -> build/music.wav, build/sfx.wav（44.1kHz 立体声）

D 小调，120 BPM，段落起点都对齐在拍子上。画面里的爆炸、日期卡、换台等事件时间
直接从 render.py 的编排里取，保证声画同步。
"""
import math, os, sys

import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfilt, fftconvolve

D = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, D)
import render as R  # noqa: E402  (只用编排数据)

SR = 44100
BEAT = 0.5
BAR = 2.0
DUR = R.DUR
N = int(DUR * SR) + SR
rng = np.random.default_rng(1936)
S, END = R.SEG, R.END


def midi(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def lp(x, fc, order=2):
    return sosfilt(butter(order, min(fc, SR * 0.45), "low", fs=SR, output="sos"), x, axis=0)


def hp(x, fc, order=2):
    return sosfilt(butter(order, fc, "high", fs=SR, output="sos"), x, axis=0)


def bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, min(hi, SR * 0.45)], "band", fs=SR, output="sos"), x, axis=0)


def saw(freq, n, ph0=None):
    """PolyBLEP 锯齿波；freq 可为常数或逐样本数组"""
    f = np.broadcast_to(np.asarray(freq, np.float64), (n,))
    dt = f / SR
    ph = ((rng.random() if ph0 is None else ph0) + np.cumsum(dt)) % 1.0
    y = 2 * ph - 1
    m = ph < dt
    x = ph[m] / dt[m]
    y[m] -= x + x - x * x - 1
    m = ph > 1 - dt
    x = (ph[m] - 1) / dt[m]
    y[m] -= x * x + x + x + 1
    return y


def sine(freq, n, ph0=0.0):
    f = np.broadcast_to(np.asarray(freq, np.float64), (n,))
    return np.sin(2 * np.pi * (ph0 + np.cumsum(f / SR)))


def env_adsr(n, a, d, s, r, hold=None):
    t = np.arange(n) / SR
    L = n / SR
    hold = L - r if hold is None else hold
    e = np.where(t < a, t / max(a, 1e-4), s + (1 - s) * np.exp(-(t - a) / max(d, 1e-4)))
    e *= np.where(t > hold, np.exp(-(t - hold) / max(r / 4, 1e-4)), 1.0)
    return e


class Bus:
    def __init__(self):
        self.x = np.zeros((N, 2))

    def add(self, t, sig, gain=1.0, pan=0.0):
        i = int(t * SR)
        if i >= N or i + len(sig) <= 0:
            return
        if sig.ndim == 1:
            l, r = math.cos((pan + 1) * math.pi / 4), math.sin((pan + 1) * math.pi / 4)
            sig = np.stack([sig * l, sig * r], 1) * 1.414
        a = max(0, -i)
        sig = sig[a:]
        i = max(0, i)
        j = min(N, i + len(sig))
        self.x[i:j] += sig[:j - i] * gain


mus, drums, sfx = Bus(), Bus(), Bus()

# ------------------------------------------------------------------ 段落与强度
T = lambda k: S[k]["t0"]
SECTIONS = [  # (起, 止, 名)
    (0.0, T("poland"), "A"),
    (T("poland"), T("barbarossa"), "B"),
    (T("barbarossa"), T("stalingrad"), "C"),
    (T("stalingrad"), T("pacific"), "D"),
    (T("pacific"), END["hiro_t0"], "E"),
    (END["hiro_t0"], END["flash1"], "F"),
]
CHORDS = {
    "A": [[38, 50, 53, 57], [34, 50, 53, 58], [43, 50, 55, 58], [45, 49, 52, 57]],
    "B": [[38, 50, 53, 57], [36, 48, 52, 55], [34, 50, 53, 58], [45, 49, 52, 57]],
    "C": [[38, 50, 53, 57], [39, 51, 55, 58], [34, 50, 53, 58], [45, 49, 52, 57]],
    "D": [[34, 50, 53, 58], [41, 48, 53, 57], [36, 48, 52, 55], [38, 50, 53, 57]],
    "E": [[38, 50, 53, 57], [36, 50, 53, 57], [34, 50, 53, 58], [45, 49, 52, 57]],
    "F": [[38, 50, 53, 57]] * 4,
}
VICTORY = S["berlin"]["t1"] - 1.2  # "Победа" 之后的大和弦


def section_at(t):
    for a, b, k in SECTIONS:
        if a <= t < b:
            return k
    return None


def pad_voice(m, n, bright=1.0):
    f = midi(m)
    x = np.zeros((n, 2))
    for c, det in ((0, (-7, 5)), (1, (6, -4))):
        for d in det:
            x[:, c] += saw(f * 2 ** (d / 1200), n)
    x = lp(x, 600 + 1400 * bright)
    return x * 0.18


# ------------------------------------------------------------------ 弦乐铺底（每小节一个和弦）
t = 0.0
bar = 0
while t < END["flash1"]:
    sec = section_at(t + 0.01)
    if sec:
        ch = CHORDS[sec][bar % 4]
        if sec == "D" and t >= VICTORY - 0.01:
            ch = [38, 50, 54, 57, 62]  # D 大调
        inten = {"A": 0.55, "B": 0.8, "C": 0.95, "D": 0.9, "E": 0.55, "F": 0.7}[sec]
        n = int((BAR + 0.9) * SR)
        e = env_adsr(n, 0.35, 1.5, 0.8, 0.9, hold=BAR)
        for k, m in enumerate(ch):
            if k == 0:
                bass = (saw(midi(m), n) + 0.6 * sine(midi(m) / 2, n))
                mus.add(t, lp(bass, 220) * e * 0.28 * inten)
                continue
            v = pad_voice(m, n, bright=inten)
            mus.add(t, v * e[:, None] * inten * (0.9 if sec != "F" else 0.6))
            if sec in ("C", "D"):
                mus.add(t, pad_voice(m + 12, n, bright=inten * 0.8) * e[:, None] * 0.35 * inten)
    t += BAR
    bar += 1

# 胜利和弦加长
n = int(3.2 * SR)
e = env_adsr(n, 0.08, 2.0, 0.7, 1.5)
for m in (38, 50, 54, 57, 62, 66, 69):
    mus.add(VICTORY, pad_voice(m, n, 1.1) * e[:, None] * 0.9)


# ------------------------------------------------------------------ 低音弦跳弓（节奏驱动）
def pluck(m, dur, bright=900):
    n = int(dur * SR)
    x = saw(midi(m), n) + 0.5 * saw(midi(m) * 1.003, n)
    e = np.exp(-np.arange(n) / SR / (dur * 0.35))
    e[: int(0.004 * SR)] *= np.linspace(0, 1, int(0.004 * SR))
    return lp(x, bright) * e


t = 0.0
k = 0
PAT8 = [0, 0, 12, 0, 7, 0, 12, 7]
while t < END["flash1"]:
    sec = section_at(t + 0.01)
    if sec in ("A", "B", "C", "D", "E"):
        bar_i = int(t / BAR)
        ch = CHORDS[sec][bar_i % 4]
        root = ch[0] + 12
        step = 0.25 if sec in ("B", "C", "D") else 0.5
        pos = int(round((t % BAR) / step))
        acc = 1.0 if pos % (4 if step == 0.25 else 2) == 0 else 0.6
        g = {"A": 0.30, "B": 0.42, "C": 0.5, "D": 0.45, "E": 0.25}[sec]
        if not (sec == "D" and t > VICTORY - 0.01 and t < S["berlin"]["t1"] + 0.5):
            mus.add(t, pluck(root + PAT8[pos % 8], step * 0.9, 700 + 900 * acc) * g * acc, pan=-0.25)
        t += step
    else:
        t += BEAT


# ------------------------------------------------------------------ 打击乐
def taiko(size=1.0):
    n = int(0.9 * SR)
    tt = np.arange(n) / SR
    f = 48 + 90 * np.exp(-tt * 28)
    body = sine(f, n) * np.exp(-tt / (0.22 * size))
    skin = lp(rng.normal(0, 1, n), 1800) * np.exp(-tt / 0.03) * 0.5
    return np.tanh((body + skin) * 1.6) * 0.8


def snare(g=1.0):
    n = int(0.25 * SR)
    tt = np.arange(n) / SR
    x = bp(rng.normal(0, 1, n), 900, 6000) * np.exp(-tt / 0.055) + sine(190, n) * np.exp(-tt / 0.03) * 0.5
    return x * g * 0.5


def timpani(m=38, g=1.0):
    n = int(2.2 * SR)
    tt = np.arange(n) / SR
    f0 = midi(m)
    x = sum(sine(f0 * r * (1 + 0.02 * np.exp(-tt * 6)), n) * a * np.exp(-tt / d)
            for r, a, d in ((1, 1, 0.9), (1.5, 0.5, 0.6), (1.98, 0.35, 0.45), (2.44, 0.2, 0.3)))
    x += lp(rng.normal(0, 1, n), 1200) * np.exp(-tt / 0.02) * 0.4
    return x * g * 0.7


def hat(g=0.3):
    n = int(0.06 * SR)
    return hp(rng.normal(0, 1, n), 7000) * np.exp(-np.arange(n) / SR / 0.012) * g


t = 0.0
while t < END["flash1"]:
    sec = section_at(t + 0.01)
    pos8 = int(round((t % BAR) / 0.25))  # 16 分位置 0..7 (每小节 8 个 8 分)
    if sec in ("B", "C", "D"):
        gt = {"B": 0.75, "C": 0.95, "D": 0.8}[sec]
        if pos8 in (0, 3, 4, 6) and not (VICTORY - 0.3 < t < S["berlin"]["t1"] + 0.3):
            drums.add(t, taiko(1.2 if pos8 == 0 else 0.8) * gt * (1.0 if pos8 in (0, 4) else 0.65), pan=0.1)
        # 军鼓：16 分音符滚奏，重音在 2、4 拍
        for sub in (0, 0.125):
            acc = 1.0 if (pos8 in (2, 6) and sub == 0) else 0.16
            drums.add(t + sub, snare(acc * 0.55 * gt), pan=0.3)
    elif sec in ("A", "E", "F"):
        if pos8 % 2 == 0:
            drums.add(t, hat(0.12 if sec == "A" else 0.08), pan=0.4)
        if sec == "A" and pos8 == 0 and t > 1.5:
            drums.add(t, taiko(0.8) * 0.45)
    if sec == "F":
        # 钟表滴答
        n = int(0.02 * SR)
        tick = bp(rng.normal(0, 1, n), 2500, 9000) * np.exp(-np.arange(n) / SR / 0.004)
        sfx.add(t, tick * (0.5 if pos8 % 4 == 0 else 0.3), pan=0.2 if pos8 % 4 == 0 else -0.2)
    t += 0.25


# ------------------------------------------------------------------ 重击（日期卡 / 段落切换）
def braam(dur=2.4, m=38):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    x = np.zeros((n, 2))
    for d in (-12, -5, 0, 7):
        for c in (0, 1):
            x[:, c] += saw(midi(m + d - 12) * (1 + 0.003 * (c - 0.5)), n)
    x = lp(np.tanh(x * 0.6), 900) * np.exp(-tt / 0.9)[:, None]
    sub = sine(midi(m - 24) * (1 + 0.5 * np.exp(-tt * 10)), n) * np.exp(-tt / 0.8)
    x += sub[:, None] * 0.9
    noise = lp(rng.normal(0, 1, (n, 2)), 3000) * np.exp(-tt / 0.15)[:, None] * 0.3
    return (x + noise) * 0.55


def riser(dur=1.2):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    u = tt / dur
    nz = rng.normal(0, 1, (n, 2))
    out = np.zeros((n, 2))
    blocks = 24
    for b in range(blocks):
        a, z = b * n // blocks, (b + 1) * n // blocks
        fc = 300 + 5000 * (b / blocks) ** 2
        out[a:z] = bp(nz[a:z], fc * 0.7, fc * 1.4)
    out *= (u ** 2)[:, None] * 0.5
    out += (sine(200 + 600 * u ** 2, n) * u ** 3 * 0.12)[:, None]
    return out


for s in R.SEGS:
    if s.get("card"):
        tc = s["t0"] + 0.05
        mus.add(tc, braam(), 1.0)
        drums.add(tc, timpani(38, 1.0))
        drums.add(tc, taiko(1.5) * 0.9)
        mus.add(tc - 1.2, riser(1.2), 0.8)
    elif s["id"] not in ("truman",):
        drums.add(s["t0"], timpani(38 if s["y"] < 1942 else 45, 0.45))
mus.add(VICTORY, braam(3.0, 50) * 0.6)
drums.add(VICTORY, timpani(38, 1.2))

# ------------------------------------------------------------------ 进场弦乐颤音（广岛前）
h0, f1 = END["hiro_t0"], END["flash1"]
n = int((f1 - h0) * SR)
tt = np.arange(n) / SR
u = tt / (f1 - h0)
trem = (0.55 + 0.45 * np.sin(2 * np.pi * 12 * tt))
for m in (62, 63, 69, 74):
    v = pad_voice(m, n, 1.2) * (trem * u ** 1.5)[:, None] * 0.8
    mus.add(h0, v)
mus.x[int(f1 * SR):] = 0
drums.x[int(f1 * SR):] = 0


# ------------------------------------------------------------------ 结尾钢琴
def piano(m, dur=4.0, g=1.0):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    f0 = midi(m)
    x = np.zeros(n)
    for k in range(1, 9):
        fk = f0 * k * math.sqrt(1 + 0.0004 * k * k)
        x += sine(fk, n) * (1 / k ** 1.3) * np.exp(-tt / (2.6 / k ** 0.6))
    x += lp(rng.normal(0, 1, n), 2500) * np.exp(-tt / 0.004) * 0.08
    x *= np.minimum(1, tt / 0.003)
    return x * g * 0.32


for tm, m, g in ((END["surrender"] + 0.2, 57, 0.8), (END["surrender"] + 1.3, 53, 0.7),
                 (END["toll"] + 0.2, 52, 0.75), (END["toll"] + 1.4, 50, 0.7),
                 (END["title"] + 0.15, 38, 0.9), (END["title"] + 0.15, 50, 0.6), (END["title"] + 0.15, 57, 0.5)):
    mus.add(tm, piano(m, 5.0, g), pan=0.1 * (m - 50) / 10)
n = int((END["end"] - END["title"]) * SR)
mus.add(END["title"], lp(pad_voice(50, n, 0.4), 700) * env_adsr(n, 1.5, 3, 0.7, 1.5)[:, None] * 0.6)

# ================================================================== 音效
def static(dur, g=1.0):
    n = int(dur * SR)
    x = bp(rng.normal(0, 1, (n, 2)), 400, 7000)
    crack = (rng.random((n, 2)) > 0.9985) * rng.normal(0, 4, (n, 2))
    x = x + lp(crack, 5000)
    am = 0.6 + 0.4 * np.sin(2 * np.pi * rng.uniform(3, 9) * np.arange(n) / SR)[:, None]
    return x * am * g * 0.35


def tune_whistle(dur):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    f = 1800 - 1500 * np.sin(np.pi * tt / dur) * (0.6 + 0.4 * np.sin(tt * 17))
    return sine(f, n) * np.sin(np.pi * tt / dur) * 0.12


# 片头：静电 + 调台
sfx.add(0.0, static(1.9, 1.0) * np.linspace(0.2, 1, int(1.9 * SR))[:, None])
sfx.add(0.2, tune_whistle(1.5))
for s in R.SEGS:
    ts = s["t0"]
    dur = 0.45
    sfx.add(ts - 0.08, static(dur, 1.1) * np.hanning(int(dur * SR))[:, None])
    sfx.add(ts - 0.02, tune_whistle(0.4) * 0.8)


def siren(dur):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    f = 330 + 260 * (0.5 - 0.5 * np.cos(2 * np.pi * tt / 3.2))
    x = sine(f, n) + 0.4 * sine(2 * f, n) + 0.2 * sine(3 * f, n)
    e = np.minimum(1, tt / 0.8) * np.minimum(1, (dur - tt) / 1.0)
    return lp(x, 2500) * e * 0.22


bl = S["blitz"]
sfx.add(bl["t0"] - 0.3, siren(bl["t1"] - bl["t0"] + 0.5), pan=-0.3)


def drone(dur, f0=85, g=1.0):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    x = saw(f0 * (1 + 0.01 * np.sin(tt * 3)), n) + saw(f0 * 1.51, n) * 0.5
    x = lp(x, 500) * (0.7 + 0.3 * np.sin(2 * np.pi * 23 * tt))
    e = np.sin(np.pi * np.clip(tt / dur, 0, 1)) ** 0.7
    return x * e * g * 0.12


for p in R.PLANES:
    sfx.add(p["t0"], drone(p["t1"] - p["t0"] + 0.3, rng.uniform(80, 100), 0.6), pan=rng.uniform(-0.5, 0.5))
for r in R.ROUTES:
    if r["plane"]:
        sfx.add(r["t"], drone(r["d"] + 0.2, 70, 1.2))


def explosion(size=1.0):
    n = int(1.6 * SR)
    tt = np.arange(n) / SR
    x = lp(rng.normal(0, 1, (n, 2)), 2100) * np.exp(-tt / (0.25 * size))[:, None]
    x += (sine(55 * (1 + np.exp(-tt * 15)), n) * np.exp(-tt / 0.35))[:, None] * 0.8
    return np.tanh(x * 1.5) * 0.35 * size


for (lon, lat, tb, size, col) in R.BOOMS:
    sfx.add(tb, explosion(min(1.3, size / 26)) * 0.8, pan=rng.uniform(-0.4, 0.4))

# 核爆：刺耳高频 + 延迟到达的超低频
for tf, g in ((END["flash1"], 1.0), (END["flash2"], 0.75)):
    n = int(4.5 * SR)
    tt = np.arange(n) / SR
    ring = sine(3520, n) * np.exp(-tt / 1.4) * 0.05
    sfx.add(tf, ring)
    n = int(6 * SR)
    tt = np.arange(n) / SR
    rumble = lp(rng.normal(0, 1, (n, 2)), 120, 4) * 3.0 + (sine(32 * (1 + 0.8 * np.exp(-tt * 2)), n) * 0.8)[:, None]
    e = np.minimum(1, tt / 0.25) * np.exp(-tt / 1.6)
    sfx.add(tf + 0.55, np.tanh(rumble * e[:, None] * 1.4) * 0.55 * g)
    # 闪光瞬间切断一切
    sfx.x[int((tf + 0.02) * SR):int((tf + 0.55) * SR)] *= 0.0

# 广岛之后电台重新接通前的沙沙声
tr0 = S["truman"]["t0"]
sfx.add(tr0 - 0.6, static(1.0, 0.8) * np.linspace(0, 1, int(1.0 * SR))[:, None])
# 结尾电台关机的咔哒声
n = int(0.05 * SR)
sfx.add(END["end"] - 0.9, lp(rng.normal(0, 1, n), 3000) * np.exp(-np.arange(n) / SR / 0.006) * 0.6)


# ================================================================== 混响与导出
def reverb(x, secs=2.4, wet=0.28):
    n = int(secs * SR)
    tt = np.arange(n) / SR
    ir = rng.normal(0, 1, (n, 2)) * np.exp(-tt / (secs / 6.9) * 1.0)[:, None]
    ir = lp(ir, 5000)
    ir[:int(0.012 * SR)] = 0
    ir /= np.sqrt((ir ** 2).sum(0))
    y = np.stack([fftconvolve(x[:, c], ir[:, c])[:len(x)] for c in (0, 1)], 1)
    return x * (1 - wet * 0.5) + y * wet


music = reverb(mus.x, 2.6, 0.32) + reverb(drums.x, 1.4, 0.18)
# 核爆后的静默
f1s = int(END["flash1"] * SR)
music[f1s:int(END["surrender"] * SR) - int(0.1 * SR)] *= 0
music = music[: int(DUR * SR)]
fx = reverb(sfx.x, 1.2, 0.15)[: int(DUR * SR)]
pk = max(np.abs(music).max(), 1e-6)
music *= 0.7 / pk
fx *= 0.7 / max(np.abs(fx).max(), 1e-6)
os.makedirs(os.path.join(D, "build"), exist_ok=True)
sf.write(os.path.join(D, "build", "music.wav"), music.astype(np.float32), SR)
sf.write(os.path.join(D, "build", "sfx.wav"), fx.astype(np.float32), SR)
print("music", music.shape, "sfx", fx.shape)
