"""Synthesize the background score (calm piano + pad, D major, 60 BPM) -> build/music.wav

One bar = 4 s, so the scene changes at 8 / 28 / 56 / 80 / 104 s fall on bar lines,
and the final D chord lands at 116 s with the closing title card.
"""
import os
import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt, fftconvolve

D = os.path.dirname(os.path.abspath(__file__))
SR, TOTAL = 44100, 120.0
N = int(TOTAL * SR)
rng = np.random.default_rng(7)
L, R = np.zeros(N), np.zeros(N)


def hz(m): return 440.0 * 2 ** ((m - 69) / 12)
def lp(x, f, o=2): return sosfilt(butter(o, f, "low", fs=SR, output="sos"), x)
def hp(x, f, o=2): return sosfilt(butter(o, f, "high", fs=SR, output="sos"), x)
def bp(x, lo, hi, o=2): return sosfilt(butter(o, [lo, hi], "band", fs=SR, output="sos"), x)


def put(x, t, g=1.0, pan=0.0):
    i = int(t * SR)
    if i >= N: return
    if i < 0: x, i = x[-i:], 0
    x = x[: N - i]
    L[i:i + len(x)] += x * g * np.sqrt(0.5 * (1 - pan))
    R[i:i + len(x)] += x * g * np.sqrt(0.5 * (1 + pan))


def piano(m, dur=3.2, bright=1.0):
    f, n = hz(m), int(dur * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    for det in (1.0, 1.0007):
        for k in range(1, 10):
            fk = k * f * det * np.sqrt(1 + 0.0004 * k * k)
            if fk > SR / 2.3: break
            amp = (1 / k ** 1.35) * (bright if k > 2 else 1.0)
            out += amp * np.exp(-(0.7 + 0.55 * k + f / 900) * t) * np.sin(2 * np.pi * fk * t + rng.uniform(0, 6.3))
    a, r = int(0.004 * SR), int(0.08 * SR)
    out[:a] *= np.linspace(0, 1, a); out[-r:] *= np.linspace(1, 0, r)
    out += 0.02 * lp(rng.standard_normal(n), 3000) * np.exp(-60 * t)   # hammer
    return out / 2.2


def pad(ms, dur):
    n = int(dur * SR); t = np.arange(n) / SR
    out = np.zeros(n)
    for m in ms:
        for det in (-0.004, 0.0, 0.004):
            for k in range(1, 7):
                out += (1 / k) * np.sin(2 * np.pi * hz(m) * (1 + det) * k * t + rng.uniform(0, 6.3))
    out = lp(out, 900, 4)
    env = np.minimum(1, np.minimum(t / 1.6, (dur - t) / 1.6)).clip(0)
    lfo = 1 + 0.12 * np.sin(2 * np.pi * 0.21 * t)
    return out * env * lfo / (len(ms) * 8)


def bass(m, dur=4.0):
    n = int(dur * SR); t = np.arange(n) / SR
    x = np.sin(2 * np.pi * hz(m) * t) + 0.35 * np.sin(4 * np.pi * hz(m) * t)
    env = (1 - np.exp(-t / 0.02)) * np.exp(-t / 2.2)
    r = int(0.2 * SR); env[-r:] *= np.linspace(1, 0, r)
    return x * env


def bell(m, dur=4.0):
    n = int(dur * SR); t = np.arange(n) / SR
    f = hz(m)
    idx = 2.2 * np.exp(-t / 0.5)
    x = np.sin(2 * np.pi * f * t + idx * np.sin(2 * np.pi * 3.5 * f * t)) * np.exp(-t / 1.1)
    a = int(0.003 * SR); x[:a] *= np.linspace(0, 1, a)
    return x


def swell(t_peak, dur=1.6):
    n = int(dur * SR); t = np.arange(n) / SR
    x = bp(rng.standard_normal(n), 400, 5000) * (t / dur) ** 3
    r = int(0.15 * SR); x = np.concatenate([x, x[-1] * np.linspace(1, 0, r)])
    return x, t_peak - dur


# ---------------------------------------------------------------- harmony: Dmaj9 | Bm9 | Gmaj9 | Aadd9
CH = [
    dict(bass=38, arp=[57, 62, 64, 66, 69, 73], pad=[62, 66, 69, 73], mel=[(0, 78, 2), (2, 76, 2)]),
    dict(bass=35, arp=[54, 59, 61, 62, 66, 69], pad=[59, 62, 66, 69], mel=[(0, 74, 4)]),
    dict(bass=31, arp=[55, 59, 62, 66, 69, 71], pad=[59, 62, 66, 71], mel=[(0, 71, 2), (2, 74, 2)]),
    dict(bass=33, arp=[57, 61, 64, 69, 71, 76], pad=[61, 64, 69, 71], mel=[(0, 73, 3), (3, 76, 1)]),
]
PAT = [0, 2, 4, 1, 3, 5, 3, 2]
BAR = 4.0


def hum(): return rng.normal(0, 0.006)


for b in range(30):
    t0, c = b * BAR, CH[b % 4]
    last = b >= 28
    if not last:
        put(pad(c["pad"], BAR + 1.6), t0 - 0.2, 0.55 if b < 2 else 0.42, 0)
    if b < 2:                                   # intro: sparse high notes
        for k, beat in enumerate((0, 2.5)):
            put(piano(c["arp"][5 - k] + 12, 3.5, 0.8), t0 + beat + hum(), 0.16, 0.3 - 0.6 * k)
        continue
    if b < 28:
        put(bass(c["bass"]), t0, 0.32)
        sixteenth = 26 <= b < 28                # build before the recap
        steps = 16 if sixteenth else 8
        for i in range(steps):
            idx = PAT[i % 8]
            m = c["arp"][idx] + (12 if sixteenth and i >= 8 else 0)
            v = 0.15 + 0.05 * (i % 4 == 0) + rng.normal(0, 0.012)
            if sixteenth: v *= 0.8 + 0.4 * ((b - 26) * 16 + i) / 32
            put(piano(m, 2.6), t0 + i * BAR / steps + hum(), v, (idx - 2.5) / 5)
        if 7 <= b < 26:                         # melody from scene 2 on
            for beat, m, ln in c["mel"]:
                put(piano(m + (12 if b >= 20 and b % 8 >= 4 else 0), ln + 1.5, 1.2), t0 + beat + hum(), 0.2, -0.1)
        if 14 <= b < 26 and b % 2 == 1:         # bells in scenes 3-4
            put(bell(81 if b % 4 == 1 else 78), t0 + 2.0, 0.07, 0.4)

# ---------------------------------------------------------------- ending: G -> A run (112-116), D chord at 116
for i, m in enumerate([55, 59, 62, 66, 69, 71, 74, 78]):
    put(piano(m, 2.4), 112 + i * 0.25 + hum(), 0.16, (i - 3.5) / 8)
for i, m in enumerate([57, 61, 64, 69, 71, 73, 76, 81]):
    put(piano(m, 2.4), 114 + i * 0.25 + hum(), 0.16 + 0.01 * i, (i - 3.5) / 8)
put(pad([57, 61, 64, 69], 4.4), 111.8, 0.4)
put(bass(31, 2.0), 112, 0.3); put(bass(33, 2.0), 114, 0.3)
for k, m in enumerate([50, 57, 62, 66, 69, 73, 78]):
    put(piano(m, 4.2, 1.1), 116 + 0.012 * k, 0.17, (k - 3) / 7)
put(bass(38, 4.0), 116, 0.38)
put(pad([62, 66, 69, 73], 4.2), 115.8, 0.45)
put(bell(86, 4.0), 116.0, 0.06, 0.2)

# soft whooshes into each scene change
for tp in (8, 28, 56, 80, 104, 113):
    x, ts = swell(tp)
    put(x, ts, 0.025, 0.0)

# ---------------------------------------------------------------- reverb, master
ir_n = int(3.0 * SR); it = np.arange(ir_n) / SR
irs = [lp(rng.standard_normal(ir_n), 5000) * np.exp(-6.9 * it / 2.6) for _ in range(2)]
for ir in irs: ir[: int(0.012 * SR)] = 0
wetL = fftconvolve(L, irs[0])[:N]; wetR = fftconvolve(R, irs[1])[:N]
wet_g = 0.35 / np.sqrt(np.sum(irs[0] ** 2))
mix = np.stack([L + wetL * wet_g, R + wetR * wet_g], axis=1)
mix = hp(mix.T, 35).T
mix /= np.abs(mix).max() + 1e-9
mix = np.tanh(mix * 1.3) / np.tanh(1.3) * 0.8
t = np.arange(N) / SR
mix *= np.clip(t / 1.0, 0, 1)[:, None] * np.clip((TOTAL - t) / 3.0, 0, 1)[:, None]

os.makedirs(os.path.join(D, "build"), exist_ok=True)
wavfile.write(os.path.join(D, "build/music.wav"), SR, (mix * 32767).astype(np.int16))
print("wrote build/music.wav", mix.shape[0] / SR, "s")
