"""Synthesize the score and sound effects from scratch and mix them with the
dialogue stem. Reads build/timeline.json + build/dialogue.wav, writes
build/mix.wav (44.1 kHz stereo)."""
import json, os
import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt, fftconvolve, lfilter

D = os.path.dirname(os.path.abspath(__file__))
B = os.path.join(D, "build")
SR = 44100
TL = json.load(open(os.path.join(B, "timeline.json"), encoding="utf-8"))
TOTAL = TL["total"] + 0.5
N = int(TOTAL * SR)
rng = np.random.default_rng(3)

# ------------------------------------------------------------------ helpers
def tt(d): return np.arange(int(d * SR)) / SR
def hz(m): return 440.0 * 2 ** ((m - 69) / 12)
def bp(x, lo, hi, o=2): return sosfilt(butter(o, [lo, hi], "band", fs=SR, output="sos"), x)
def lp(x, f, o=2): return sosfilt(butter(o, f, "low", fs=SR, output="sos"), x)
def hp(x, f, o=2): return sosfilt(butter(o, f, "high", fs=SR, output="sos"), x)
def noise(d): return rng.standard_normal(int(d * SR))
def adsr(n, a=0.01, r=0.1):
    e = np.ones(n); na, nr = min(n, int(a * SR)), min(n, int(r * SR))
    if na: e[:na] = np.linspace(0, 1, na)
    if nr: e[-nr:] *= np.linspace(1, 0, nr)
    return e
def mx(*xs):
    n = max(len(x) for x in xs); return sum(np.pad(x, (0, n - len(x))) for x in xs)
def norm(x, p=1.0): return x / (np.abs(x).max() + 1e-9) * p
def put(buf, x, t, g=1.0, pan=0.0):
    i = int(t * SR)
    if i >= len(buf) or i + len(x) <= 0: return
    if i < 0: x, i = x[-i:], 0
    x = x[: len(buf) - i]
    if buf.ndim == 2:
        buf[i:i + len(x), 0] += x * g * np.sqrt(0.5 * (1 - pan))
        buf[i:i + len(x), 1] += x * g * np.sqrt(0.5 * (1 + pan))
    else:
        buf[i:i + len(x)] += x * g

_ir = {}
def reverb(x, sec=2.0, wet=0.3, seed=0):
    k = (sec, seed)
    if k not in _ir:
        r = np.random.default_rng(seed)
        t = tt(sec)
        ir = r.standard_normal(len(t)) * np.exp(-t * 6.9 / sec)
        _ir[k] = lp(ir, 6000) / np.sqrt(np.sum(ir ** 2))
    y = fftconvolve(x, _ir[k])[: len(x)]
    return x * (1 - wet) + y * wet * 2.2

def stereo_reverb(x, sec=2.2, wet=0.3):
    return np.stack([reverb(x, sec, wet, 1), reverb(x, sec, wet, 2)], 1)

# ------------------------------------------------------------------ instruments
def piano(m, d, v=0.6):
    f = hz(m); t = tt(d + 1.2); y = np.zeros_like(t)
    for k in range(1, 9):
        fk = k * f * np.sqrt(1 + 0.0004 * k * k)
        if fk > 16000: break
        y += np.sin(2 * np.pi * fk * t) / k ** 1.6 * np.exp(-t * (1.1 + 0.9 * k) * (f / 400) ** 0.3)
    y *= adsr(len(t), 0.004, 0.3)
    rel = np.ones_like(t); rel[t > d] = np.exp(-(t[t > d] - d) * 8)
    return y * rel * v

def bell(m, d=1.2, v=0.4):
    f = hz(m); t = tt(d)
    y = np.sin(2 * np.pi * f * t + 1.4 * np.exp(-t * 4) * np.sin(2 * np.pi * f * 3.5 * t))
    y += 0.3 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t * 6)
    return y * np.exp(-t * 3.2) * adsr(len(t), 0.002, 0.05) * v

def pad(ms, d, v=0.15, bright=5):
    t = tt(d); L = np.zeros_like(t); R = np.zeros_like(t)
    for m in ms:
        f = hz(m)
        for k in range(1, bright + 1):
            L += np.sin(2 * np.pi * f * k * 0.998 * t + k) / k ** 1.3
            R += np.sin(2 * np.pi * f * k * 1.002 * t + 2 * k) / k ** 1.3
    e = adsr(len(t), min(0.8, d / 3), min(1.0, d / 3)) * v / len(ms)
    return np.stack([L * e, R * e], 1)

def pluck(m, d=0.6, v=0.5, damp=0.996):
    f = hz(m); Np = max(2, int(SR / f)); n = int(d * SR)
    x = np.zeros(n); x[:Np] = rng.uniform(-1, 1, Np)
    a = np.zeros(Np + 2); a[0] = 1; a[Np] = -0.5 * damp; a[Np + 1] = -0.5 * damp
    y = lfilter([1], a, x)
    return lp(y, 5000) * adsr(n, 0.001, 0.05) * v

def saw(m, d, v=0.3, cut=2500):
    f = hz(m); t = tt(d)
    y = sum(np.sin(2 * np.pi * f * k * t) / k for k in range(1, 12) if f * k < 12000)
    return lp(y, cut) * adsr(len(t), 0.01, 0.06) * v

def bass(m, d, v=0.5):
    f = hz(m); t = tt(d)
    y = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(4 * np.pi * f * t)
    return y * adsr(len(t), 0.01, 0.12) * np.exp(-t * 1.2) * v

def kick(v=0.8):
    t = tt(0.45); f = 45 + 80 * np.exp(-t * 25)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9) * v

def taiko(v=0.9):
    t = tt(0.9); f = 55 + 45 * np.exp(-t * 12)
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 5)
    y += lp(noise(0.9), 300) * np.exp(-t * 18) * 0.5
    return y * v

def hat(v=0.15):
    t = tt(0.06); return hp(noise(0.06), 7000) * np.exp(-t * 60) * v

def clap(v=0.3):
    t = tt(0.2); return bp(noise(0.2), 900, 3500) * np.exp(-t * 25) * v

def crash(d=2.0, v=0.35):
    t = tt(d); return hp(noise(d), 4000) * np.exp(-t * 2.2) * v

# ------------------------------------------------------------------ score
CH = {"Am": [57, 60, 64], "F": [53, 57, 60], "C": [48, 52, 55], "G": [55, 59, 62], "Dm": [50, 53, 57],
      "E": [52, 56, 59], "Bb": [46, 50, 53], "Em": [52, 55, 59], "C/E": [52, 55, 60]}

def cue_sad(d, thin=False):
    out = np.zeros((int(d * SR) + SR * 3, 2))
    bpm = 66; beat = 60 / bpm; bar = 4 * beat
    prog = ["Am", "F", "C", "G", "Am", "F", "Dm", "E"]
    mel = {0: [(0, 76, 2), (2, 74, 1), (3, 72, 1)], 1: [(0, 72, 3)], 2: [(0, 71, 2), (2, 72, 2)], 3: [(0, 74, 4)],
           4: [(0, 76, 2), (2, 79, 2)], 5: [(0, 77, 2), (2, 76, 1), (3, 74, 1)], 6: [(0, 72, 2), (2, 74, 2)], 7: [(0, 71, 4)]}
    nb = int(np.ceil(d / bar))
    for b in range(nb):
        c = CH[prog[b % 8]]; t0 = b * bar
        put(out, piano(c[0] - 12, bar, 0.45), t0)
        if not thin:
            arp = [c[0], c[1] + 12, c[2] + 12, c[1] + 12 + 12 * 0, c[0] + 12, c[2] + 12, c[1] + 12, c[2]]
            for i, m in enumerate(arp):
                put(out, piano(m, beat * 0.5, 0.22), t0 + i * beat / 2, pan=0.2 * np.sin(i))
            if b >= 1:
                for (bt, m, ln) in mel[b % 8]:
                    put(out, piano(m, ln * beat, 0.32), t0 + bt * beat)
            out[int(t0 * SR):int(t0 * SR) + int(bar * SR)] += pad([m + 12 for m in c], bar, 0.1)[: len(out) - int(t0 * SR)]
        else:
            for i in (0, 2):
                put(out, piano(c[2] + 12, beat, 0.2), t0 + i * beat + 0.5 * beat)
    return out

def cue_glam(d, low=False):
    out = np.zeros((int(d * SR) + SR * 3, 2))
    bpm = 100; s16 = 60 / bpm / 4
    prog = ["Dm", "Bb", "F", "C"] if not low else ["Dm", "Dm", "Bb", "Bb"]
    bar = 16 * s16
    for b in range(int(np.ceil(d / bar))):
        c = CH[prog[b % 4]]; t0 = b * bar
        put(out, bass(c[0] - 12, bar * 0.9, 0.45), t0)
        for i in range(16):
            if low and i % 2: continue
            m = c[(i // 2) % 3] + (0 if low else 12)
            put(out, saw(m, s16 * 0.7, 0.10 if low else 0.13, 1800), t0 + i * s16, pan=-0.3 if i % 2 else 0.3)
        for i in range(4):
            put(out, (taiko(0.35) if not low else kick(0.4)), t0 + i * 4 * s16)
            put(out, hat(0.08), t0 + i * 4 * s16 + 2 * s16, pan=0.4)
        if not low:
            for i in range(4):
                put(out, bell(c[i % 3] + 24, 0.8, 0.12), t0 + i * 4 * s16 + 3 * s16, pan=-0.4)
        out[int(t0 * SR):int(t0 * SR) + int(bar * SR)] += pad(c, bar, 0.1, 7)[: len(out) - int(t0 * SR)]
    return out

def cue_comic(d, bpm=132):
    out = np.zeros((int(d * SR) + SR * 2, 2))
    e8 = 60 / bpm / 2
    mel = [72, None, 76, None, 79, 77, 76, None, 74, None, 71, None, 72, 74, 72, None]
    bas = [48, 55, 48, 55, 43, 50, 43, 50]
    for i in range(int(d / e8)):
        t0 = i * e8
        m = mel[i % 16]
        if m: put(out, pluck(m, 0.35, 0.35), t0, pan=0.25)
        if i % 2 == 0: put(out, pluck(bas[(i // 2) % 8] - 12, 0.3, 0.45, 0.99), t0, pan=-0.2)
        if i % 4 == 2: put(out, clap(0.12), t0)
    return out

def cue_comic2(d):
    out = np.zeros((int(d * SR) + SR * 2, 2))
    bpm = 120; e8 = 60 / bpm / 2
    prog = ["F", "C", "Dm", "C"]
    for i in range(int(d / e8)):
        t0 = i * e8; c = CH[prog[(i // 8) % 4]]
        if i % 2 == 0: put(out, bass(c[0] - 12, e8 * 0.9, 0.35), t0)
        put(out, pluck(c[i % 3] + 12 + (12 if i % 4 == 3 else 0), 0.25, 0.25), t0, pan=0.3 * ((-1) ** i))
        if i % 4 == 2: put(out, clap(0.16), t0)
        if i % 2 == 1: put(out, hat(0.07), t0, pan=0.5)
    return out

def cue_danger(d):
    out = np.zeros((int(d * SR) + SR * 2, 2))
    t = tt(d)
    drone = lp(sum(np.sin(2 * np.pi * hz(33) * k * t) / k for k in range(1, 8)), 400) * 0.25
    rise = np.sin(2 * np.pi * np.cumsum(hz(57) * 2 ** (t / d)) / SR) * 0.06 * (t / d)
    put(out, (drone + rise) * adsr(len(t), 0.3, 0.05), 0)
    tk, gap = 0.0, 0.6
    while tk < d:
        put(out, taiko(0.6), tk); tk += gap; gap = max(0.16, gap * 0.85)
    return out

def cue_soft(d):
    out = np.zeros((int(d * SR) + SR * 3, 2))
    beat = 60 / 58
    seq = [("F", [72, 69]), ("C/E", [67, 72]), ("Dm", [69, 65]), ("C", [67, 64]), ("F", [72, 76]), ("G", [74, 71])]
    for i, (c, ms) in enumerate(seq):
        t0 = i * 2 * beat
        if t0 > d: break
        put(out, piano(CH[c][0] - 12, 2 * beat, 0.35), t0)
        put(out, piano(ms[0], beat, 0.3), t0 + 0.02)
        put(out, piano(ms[1], beat, 0.24), t0 + beat)
    return out

def cue_romance(d, end=False):
    out = np.zeros((int(d * SR) + SR * 4, 2))
    bpm = 84; beat = 60 / bpm; bar = 4 * beat
    prog = ["C", "G", "Am", "F"]
    mel = [[(0, 76, 1.5), (1.5, 74, 0.5), (2, 72, 2)], [(0, 74, 2), (2, 71, 1), (3, 74, 1)],
           [(0, 72, 1.5), (1.5, 71, 0.5), (2, 69, 2)], [(0, 72, 3), (3, 77, 1)]]
    if end:
        put(out, crash(4.0, 0.25), 0.0)
        c = CH["C"]
        out[: int(4.5 * SR)] += pad([c[0], c[1] + 12, c[2] + 12, c[0] + 24], 4.5, 0.25, 7)
        put(out, piano(c[0] - 24, 4.0, 0.5), 0.0)
        for i, m in enumerate([72, 76, 79, 84, 88, 91, 96]):
            put(out, bell(m, 1.6, 0.16), 0.05 + i * 0.07, pan=-0.6 + 0.2 * i)
        return out
    for b in range(int(np.ceil(d / bar))):
        c = CH[prog[b % 4]]; t0 = b * bar
        put(out, piano(c[0] - 12, bar, 0.4), t0)
        for i in range(8):
            put(out, piano([c[0], c[1], c[2], c[1] + 12][i % 4] + 12, beat * 0.5, 0.15), t0 + i * beat / 2, pan=0.3 * np.sin(i))
        if b % 8 >= 2:
            for (bt, m, ln) in mel[b % 4]:
                put(out, bell(m + 12, ln * beat + 0.6, 0.11), t0 + bt * beat, pan=-0.2)
                put(out, piano(m, ln * beat, 0.2), t0 + bt * beat)
        if b >= 2:
            put(out, kick(0.25), t0); put(out, kick(0.2), t0 + 2 * beat)
        out[int(t0 * SR):int(t0 * SR) + int(bar * SR)] += pad([m + 12 for m in c], bar, 0.08)[: len(out) - int(t0 * SR)]
    return out

CUES = {"sad": cue_sad, "sad_thin": lambda d: cue_sad(d, True), "glam": cue_glam, "glam_low": lambda d: cue_glam(d, True),
        "comic": cue_comic, "comic2": cue_comic2, "danger": cue_danger, "soft": cue_soft, "romance": cue_romance,
        "romance_end": lambda d: cue_romance(d, True)}
LEVEL = {"sad": 0.26, "sad_thin": 0.22, "glam": 0.26, "glam_low": 0.2, "comic": 0.24, "comic2": 0.22,
         "danger": 0.3, "soft": 0.24, "romance": 0.26, "romance_end": 0.34}

def score():
    out = np.zeros((N, 2))
    segs = []
    for s in TL["shots"]:
        if segs and segs[-1][0] == s["mus"]:
            segs[-1][2] = s["start"] + s["dur"]
        else:
            segs.append([s["mus"], s["start"], s["start"] + s["dur"]])
    for cue, a, b in segs:
        if cue == "none": continue
        x = CUES[cue](b - a)
        x = stereo_reverb(x.mean(1), 2.4, 0.28) * 0.5 + x * 0.5
        tail = 2.5 if cue in ("romance_end", "soft") else 0.5
        n = min(len(x), int((b - a + tail) * SR))
        x = x[:n] * adsr(n, 0.02, min(tail, 1.2))[:, None]
        put_st(out, norm(x, LEVEL[cue]), a)
    # per-shot gain automation (e.g. music drops out on a beat of silence)
    g = np.ones(N)
    for s in TL["shots"]:
        if not s["mus_gain"]: continue
        a, b = int(s["start"] * SR), int((s["start"] + s["dur"]) * SR)
        ks = [(s["start"] + k, v) for k, v in s["mus_gain"]]
        tx = np.arange(a, min(b, N)) / SR
        g[a:min(b, N)] = np.interp(tx, [k for k, _ in ks], [v for _, v in ks])
    g = np.convolve(g, np.ones(int(0.03 * SR)) / int(0.03 * SR), "same")
    return out * g[:, None]

def put_st(buf, x, t):
    i = int(t * SR); x = x[: len(buf) - i]; buf[i:i + len(x)] += x

# ------------------------------------------------------------------ sfx
def s_rain(d):
    t = tt(d)
    y = bp(noise(d), 700, 9000) * (0.6 + 0.4 * lp(np.abs(noise(d)), 2)[: len(t)] * 8).clip(0.3, 1.4)
    drops = np.zeros(len(t)); idx = rng.integers(0, len(t), int(d * 90)); drops[idx] = rng.uniform(0.3, 1, len(idx))
    y += bp(lfilter([1], [1, -0.97], drops), 1500, 6000) * 0.6
    return norm(y) * adsr(len(t), 0.8, 1.2)

def s_thunder(d=4.0, soft=False):
    t = tt(d)
    crack = hp(noise(d), 800) * np.exp(-t * 18) * (0 if soft else 0.8)
    rum = lp(noise(d), 160, 4) * 6
    env = np.exp(-t * 0.9) * (1 + 0.6 * np.sin(2 * np.pi * 1.3 * t) ** 2)
    return norm(crack + rum * env * adsr(len(t), 0.08, 0.6))

def s_hit(d=2.5, f0=70, f1=28):
    t = tt(d); f = f1 + (f0 - f1) * np.exp(-t * 3)
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 1.8)
    y += lp(noise(d), 250) * np.exp(-t * 6) * 2
    return norm(reverb(y, 2.5, 0.25))

def s_burst(d, lo, hi, dec): t = tt(d); return norm(bp(noise(d), lo, hi) * np.exp(-t * dec))

def s_sweep(d, f0, f1, v=1.0):
    t = tt(d); f = f0 * (f1 / f0) ** (t / d)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * adsr(len(t), 0.01, d * 0.4) * v

def s_murmur(d):
    t = tt(d); y = np.zeros(len(t))
    for k in range(14):
        c = rng.uniform(350, 1400)
        syl = np.clip(lp(np.abs(noise(d)), 4) * 40, 0, 1)
        y += bp(noise(d), c * 0.8, c * 1.25) * syl
    return norm(y) * adsr(len(t), 0.4, 0.3)

def s_gasp(d=1.1, f1=700, f2=1200, rise=False):
    t = tt(d); y = np.zeros(len(t))
    for k in range(10):
        sh = rng.uniform(0.9, 1.15)
        y += bp(noise(d), f1 * sh * 0.85, f1 * sh * 1.15) + 0.7 * bp(noise(d), f2 * sh * 0.9, f2 * sh * 1.1)
    env = np.sin(np.pi * np.clip(t / d, 0, 1)) ** (0.6 if rise else 1.5)
    return norm(y * env)

def s_claps(d=2.5):
    y = np.zeros(int(d * SR))
    for _ in range(int(d * 45)):
        tc = rng.uniform(0, d); put(y, clap(rng.uniform(0.3, 1)), tc)
    return norm(y) * adsr(len(y), 0.2, 0.8)

def s_crow():
    y = np.zeros(int(1.4 * SR))
    for i, f in enumerate([760, 700, 620]):
        t = tt(0.24); fr = f * (1 - 0.25 * t / 0.24)
        ph = np.cumsum(fr) / SR
        v = np.sign(np.sin(2 * np.pi * ph)) * 0.6 + np.sin(4 * np.pi * ph) * 0.3
        put(y, bp(v, 500, 2600) * np.sin(np.pi * t / 0.24) ** 0.5, i * 0.38)
    return norm(y)

def s_boing():
    t = tt(0.9); f = 180 + 120 * np.exp(-t * 2) * np.sin(2 * np.pi * 9 * t) + 60 * t
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 3.5)

def s_sparkle():
    y = np.zeros(int(1.8 * SR))
    for i in range(9):
        put(y, bell([96, 98, 100, 103, 105, 108, 110, 112, 115][i] - 12, 1.0, 0.3), i * 0.05 + rng.uniform(0, 0.03))
    return norm(y)

def s_jet(d=2.6):
    t = tt(d); y = bp(noise(d), 300, 3000) * np.exp(-((t - d * 0.45) / (d * 0.28)) ** 2)
    y += s_sweep(d, 900, 500, 0.4) * np.exp(-((t - d * 0.45) / (d * 0.3)) ** 2)
    return norm(y)

def s_heels():
    y = np.zeros(int(2.0 * SR))
    for i in range(4):
        put(y, mx(s_burst(0.08, 1800, 5000, 70) * 0.7, s_burst(0.08, 150, 400, 50) * 0.4), i * 0.42, 1 - i * 0.18)
    return reverb(y, 1.0, 0.3)

def s_heartbeat():
    y = np.zeros(int(2.2 * SR))
    for i in range(2):
        put(y, lp(s_hit(0.3, 60, 40), 200), i * 0.9); put(y, lp(s_hit(0.3, 55, 38), 200) * 0.7, i * 0.9 + 0.22)
    return norm(y)

def s_fire(d):
    t = tt(d)
    y = lp(noise(d), 500, 3) * (0.7 + 0.3 * np.sin(2 * np.pi * 0.7 * t))
    cr = np.zeros(len(t)); idx = rng.integers(0, len(t), int(d * 25)); cr[idx] = rng.uniform(0.2, 1, len(idx))
    y = norm(y) + norm(hp(lfilter([1], [1, -0.9], cr), 1500)) * 0.5
    return norm(y) * adsr(len(t), 0.6, 0.15)

def s_scratch():
    t = tt(0.45); f = 900 + 700 * np.sin(2 * np.pi * 7 * t)
    return norm(bp(noise(0.45), 600, 3500) * (0.5 + 0.5 * np.sin(2 * np.pi * np.cumsum(f) / SR / 40)) * np.exp(-t * 4))

def s_monitor():
    y = np.zeros(int(4.2 * SR))
    for i in range(4): put(y, np.sin(2 * np.pi * 1000 * tt(0.12)) * adsr(int(0.12 * SR), 0.005, 0.03), i * 1.0)
    return y

def tone_seq(seq):
    y = np.zeros(int(sum(d for _, d in seq) * SR) + SR)
    t0 = 0
    for f, d in seq:
        if f: put(y, np.sin(2 * np.pi * f * tt(d)) * adsr(int(d * SR), 0.01, 0.02), t0)
        t0 += d
    return y

SFX = {
    "thunder": (lambda d: s_thunder(4.5), 0.55), "thunder_soft": (lambda d: s_thunder(3.5, True), 0.3),
    "paper": (lambda d: s_burst(0.45, 2000, 7000, 7), 0.18), "low_hit": (lambda d: s_hit(2.0, 60, 30), 0.45),
    "swish": (lambda d: s_burst(0.35, 3000, 9000, 9), 0.25), "heels": (lambda d: s_heels(), 0.3),
    "door": (lambda d: norm(mx(s_burst(0.5, 60, 300, 9), 0.3 * s_burst(0.05, 2000, 6000, 80))), 0.55),
    "tick": (lambda d: s_burst(0.03, 3000, 8000, 150), 0.25), "ring": (lambda d: tone_seq([(450, 0.55)]), 0.12),
    "hangup": (lambda d: tone_seq([(450, 0.14), (0, 0.12)] * 3), 0.12),
    "ding": (lambda d: norm(np.concatenate([bell(88, 0.12, 1), bell(95, 0.6, 1)])), 0.22),
    "murmur": (s_murmur, 0.22), "freeze": (lambda d: bell(103, 1.6, 1), 0.2),
    "doors": (lambda d: norm(mx(s_burst(1.2, 200, 3000, 2.5), s_hit(1.5, 50, 30))), 0.4),
    "gasp": (lambda d: s_gasp(), 0.28), "ooh": (lambda d: s_gasp(1.4, 450, 850, True), 0.25),
    "flashcam": (lambda d: norm(mx(s_burst(0.04, 1500, 6000, 120), s_sweep(0.25, 3500, 7000, 0.15))), 0.2),
    "sparkle": (lambda d: s_sparkle(), 0.22), "boom": (lambda d: s_hit(3.0), 0.7),
    "slam": (lambda d: reverb(s_burst(0.25, 80, 600, 25), 1.2, 0.3), 0.5), "boing": (lambda d: s_boing(), 0.35),
    "crow": (lambda d: s_crow(), 0.3), "power_down": (lambda d: s_sweep(0.7, 420, 40, 1), 0.35),
    "fire": (s_fire, 0.35), "crack": (lambda d: s_burst(0.35, 900, 5000, 14), 0.45),
    "ring_ear": (lambda d: s_sweep(2.5, 3600, 3550, 1) * np.exp(-tt(2.5) * 1.4), 0.07),
    "monitor": (lambda d: s_monitor(), 0.08), "applause": (lambda d: s_claps(), 0.25),
    "whoosh": (lambda d: s_burst(0.5, 400, 4000, 6), 0.3), "jet": (lambda d: s_jet(), 0.45),
    "elevator": (lambda d: bell(88, 1.0, 1), 0.18), "heartbeat": (lambda d: s_heartbeat(), 0.5),
    "toss": (lambda d: s_burst(0.25, 800, 5000, 14), 0.2), "catch": (lambda d: s_burst(0.08, 300, 2500, 50), 0.35),
    "box": (lambda d: s_burst(0.06, 1500, 6000, 90), 0.3), "click": (lambda d: s_burst(0.05, 1500, 6000, 100), 0.3),
    "swell": (lambda d: (hp(noise(2.0), 3000) * np.linspace(0, 1, int(2.0 * SR)) ** 2), 0.18),
    "pop": (lambda d: s_sweep(0.12, 400, 900, 1), 0.3), "scratch": (lambda d: s_scratch(), 0.45),
    "rain_memory": (lambda d: s_rain(d), 0.2),
}

def main():
    dia = wavfile.read(os.path.join(B, "dialogue.wav"))[1].astype(np.float64)
    dia = np.pad(dia, (0, max(0, N - len(dia))))[:N]
    mus = score()
    amb = np.zeros((N, 2)); fx = np.zeros((N, 2))
    # rain bed across every shot flagged rain=true
    spans = []
    for s in TL["shots"]:
        if s["rain"]:
            if spans and abs(spans[-1][1] - s["start"]) < 1e-3: spans[-1][1] = s["start"] + s["dur"]
            else: spans.append([s["start"], s["start"] + s["dur"]])
    for a, b in spans:
        r = s_rain(b - a + 1.0)
        put_st(amb, np.stack([r, np.roll(r, 900)], 1) * 0.11, a)
    for row in TL["sfx"]:
        name, t0 = row[0], row[1]
        d = (row[2] - t0) if len(row) > 2 else 2.0
        f, g = SFX[name]
        x = f(max(0.3, d))
        put(fx, x, t0, g, pan=rng.uniform(-0.25, 0.25))
    # duck music + ambience under dialogue
    env = np.abs(dia)
    k = int(0.25 * SR)
    env = np.convolve(env, np.ones(k) / k, "same")
    duck = 1 - 0.5 * np.clip(env / 0.05, 0, 1)
    mix = (mus + amb) * duck[:, None] + fx + dia[:, None] * 0.95
    mix = np.tanh(mix * 1.1) / np.tanh(1.1)
    mix = mix / np.abs(mix).max() * 0.94
    wavfile.write(os.path.join(B, "mix.wav"), SR, (mix * 32767).astype(np.int16))
    print("mix", mix.shape[0] / SR, "s")

if __name__ == "__main__":
    main()
