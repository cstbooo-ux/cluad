"""Synthesised score (no samples): D minor, 96 BPM, every hit locked to timeline.HITS.
Writes out/score.wav (44.1 kHz stereo)."""
import os
import numpy as np
from scipy.signal import butter, lfilter, sosfilt, fftconvolve
from timeline import *

D = os.path.dirname(os.path.abspath(__file__))
SR = 44100
N = int((DUR + 0.5) * SR)
rng = np.random.default_rng(2026)


def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def bus():
    return np.zeros((2, N))


def put(b, sig, t0, pan=0.0, gain=1.0):
    """mix mono (n,) or stereo (2,n) signal into bus b at time t0 with equal-power pan."""
    i0 = int(round(t0 * SR))
    if i0 >= N:
        return
    if sig.ndim == 1:
        th = (pan + 1) * np.pi / 4
        sig = np.stack([sig * np.cos(th), sig * np.sin(th)])
    n = min(sig.shape[1], N - i0)
    if i0 < 0:
        sig = sig[:, -i0:]
        n = min(sig.shape[1], N)
        i0 = 0
    b[:, i0:i0 + n] += sig[:, :n] * gain


def lp(x, fc, order=2):
    return sosfilt(butter(order, min(fc, SR * 0.45), "low", fs=SR, output="sos"), x)


def hp(x, fc, order=2):
    return sosfilt(butter(order, fc, "high", fs=SR, output="sos"), x)


def bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], "band", fs=SR, output="sos"), x)


# ------------------------------------------------------------------ harmony
CH = {
    "Dm": [50, 57, 62, 65, 69], "Dm9": [50, 57, 62, 64, 65, 69], "Bb": [46, 53, 58, 62, 65, 69],
    "F": [53, 57, 60, 65, 69], "C": [48, 55, 60, 64, 67], "Gm": [43, 50, 55, 58, 62, 67],
    "A": [45, 52, 57, 61, 64], "Asus": [45, 52, 57, 62, 64], "D": [50, 57, 62, 66, 69, 76],
}
ROOT = {"Dm": 38, "Dm9": 38, "Bb": 34, "F": 41, "C": 36, "Gm": 43, "A": 45, "Asus": 45, "D": 38}
PROG = (["Dm9"] * 3 + ["Bb", "C"] + ["Dm", "Bb", "F", "C", "Dm"] + ["Bb", "F", "Gm", "Asus"]
        + ["Dm", "Bb", "F", "C", "Dm", "A"] + ["Dm", "F", "C", "Bb"] * 2
        + ["Gm", "Bb", "F", "A", "Dm"] + ["Bb", "F", "Dm", "C"] + ["Dm", "C", "Bb", "A"]
        + ["Gm", "Dm", "Bb", "A"] + ["A", "A"] + ["D"] * 5)
NB = len(PROG)  # 52 bars


def chord_at(t):
    return PROG[min(int(t / BAR), NB - 1)]


def seg_level(t, pts):
    """piecewise-linear automation"""
    ts, vs = zip(*pts)
    return np.interp(t, ts, vs)


# ------------------------------------------------------------------ instruments
def pad_note(f0, dur, cutoff, att=0.9, rel=1.8):
    n = int((dur + rel) * SR)
    t = np.arange(n) / SR
    env = np.minimum(t / att, 1) ** 2 * np.where(t > dur, np.exp(-(t - dur) / (rel / 3.5)), 1.0)
    out = np.zeros((2, n))
    for det, pan in ((-8, -0.7), (0, 0.0), (8, 0.7)):
        f = f0 * 2 ** (det / 1200)
        s = np.zeros(n)
        vib = 0.0015 * np.sin(2 * np.pi * rng.uniform(4.5, 5.5) * t + rng.uniform(0, 6))
        for k in range(1, 16):
            if k * f > min(cutoff * 3, 15000):
                break
            s += (1 / k) * np.exp(-k * f / cutoff) * np.sin(2 * np.pi * k * f * t * (1 + vib) + rng.uniform(0, 6.28))
        th = (pan + 1) * np.pi / 4
        out[0] += s * np.cos(th)
        out[1] += s * np.sin(th)
    return out * env


def bell(f, dec=1.2, ratio=2.0, idx=2.2):
    n = int(dec * 5 * SR)
    t = np.arange(n) / SR
    I = idx * np.exp(-t / 0.22)
    s = np.sin(2 * np.pi * f * t + I * np.sin(2 * np.pi * f * ratio * t))
    s += 0.3 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t / 0.25)
    return s * np.exp(-t / dec) * (1 - np.exp(-t / 0.002))


def boom(amp=1.0, f_hi=90, f_lo=31, dec=1.1):
    n = int(3.0 * SR)
    t = np.arange(n) / SR
    f = f_lo + (f_hi - f_lo) * np.exp(-t / 0.07)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / dec)
    nz = lp(rng.normal(size=n), 900) * np.exp(-t / 0.15) * 0.8
    return (np.tanh(1.6 * (s + nz)) * amp)


def braam(root, dur=2.6, amp=1.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    cut = 180 + 2600 * np.exp(-t / 0.35)
    out = np.zeros((2, n))
    for m in (root, root + 7, root + 12):
        for det, pan in ((-10, -0.8), (10, 0.8), (0, 0)):
            f = mtof(m) * 2 ** (det / 1200)
            s = np.zeros(n)
            for k in range(1, 60):
                if k * f > 5000:
                    break
                s += (1 / k) * np.exp(-k * f / cut) * np.sin(2 * np.pi * k * f * t + rng.uniform(0, 6.28))
            th = (pan + 1) * np.pi / 4
            out[0] += s * np.cos(th)
            out[1] += s * np.sin(th)
    env = (1 - np.exp(-t / 0.01)) * np.exp(-t / (dur / 3))
    return np.tanh(out * env * 0.5) * amp


def kick(amp=1.0):
    n = int(0.6 * SR)
    t = np.arange(n) / SR
    f = 45 + 110 * np.exp(-t / 0.035)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.32)
    click = hp(rng.normal(size=n), 2000) * np.exp(-t / 0.004) * 0.3
    return np.tanh(1.8 * (s + click)) * amp


def snare(amp=1.0):
    n = int(0.6 * SR)
    t = np.arange(n) / SR
    nz = bp(rng.normal(size=n), 400, 7000) * np.exp(-t / 0.16)
    tone = np.sin(2 * np.pi * 185 * t) * np.exp(-t / 0.07)
    return (nz * 0.8 + tone * 0.6) * amp


def tom(f0, amp=1.0):
    n = int(0.9 * SR)
    t = np.arange(n) / SR
    f = f0 * (1 + 0.6 * np.exp(-t / 0.04))
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.35)
    s += lp(rng.normal(size=n), 1500) * np.exp(-t / 0.03) * 0.3
    return np.tanh(1.4 * s) * amp


def hat(amp=1.0, dec=0.035):
    n = int(0.3 * SR)
    t = np.arange(n) / SR
    return hp(rng.normal(size=n), 7500) * np.exp(-t / dec) * amp


def tick(f, amp=1.0):
    n = int(0.5 * SR)
    t = np.arange(n) / SR
    s = np.sin(2 * np.pi * f * t) * np.exp(-t / 0.09) + 0.4 * np.sin(2 * np.pi * f * 2.01 * t) * np.exp(-t / 0.04)
    s += hp(rng.normal(size=n), 5000) * np.exp(-t / 0.003) * 0.5
    return s * amp


def riser(dur, f0=250, f1=9000, amp=1.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = rng.normal(size=n)
    out = np.zeros(n)
    blk = 512
    zi = None
    for i in range(0, n, blk):
        u = i / n
        fc = f0 * (f1 / f0) ** (u ** 1.5)
        b, a = butter(2, fc, "low", fs=SR)
        if zi is None:
            zi = np.zeros(max(len(a), len(b)) - 1)
        out[i:i + blk], zi = lfilter(b, a, x[i:i + blk], zi=zi)
    env = (t / dur) ** 2.2
    tone = np.sin(2 * np.pi * np.cumsum(110 * 2 ** (2 * t / dur)) / SR) * 0.25
    return (out * 1.2 + tone) * env * amp


def reverse_swell(dur=0.9, amp=1.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = lp(rng.normal(size=n), 6000) * np.exp(-t / 0.35)
    return x[::-1] * amp


def ir(rt60=3.2, pre=0.02):
    n = int(rt60 * SR)
    t = np.arange(n) / SR
    tau = rt60 / np.log(1000)
    out = []
    for _ in range(2):
        x = rng.normal(size=n) * np.exp(-t / tau)
        x = lp(x, 7000)
        x = np.concatenate([np.zeros(int(pre * SR)), x])
        out.append(x / np.sqrt(np.sum(x * x)))
    return out


def rms(b):
    m = np.abs(b).max(0) > 1e-6
    return np.sqrt(np.mean(b[:, m] ** 2)) if m.any() else 1.0


def db(x):
    return 10 ** (x / 20)


# ------------------------------------------------------------------ compose
def compose():
    pad, bass, arp, drums, hits, ticks, rise = (bus() for _ in range(7))
    tt = np.arange(N) / SR

    # pads + bass, one chord per bar
    for b, name in enumerate(PROG):
        t0 = b * BAR
        cut = seg_level(t0, [(0, 700), (12.5, 1100), (35, 1800), (50, 2400), (70, 1300), (82.5, 1500), (92.5, 1900),
                             (112.5, 2600), (117.5, 3200), (130, 1500)])
        dur = BAR + 0.15
        if name == "D" and b == NB - 5:
            dur = 5 * BAR - 1.0
        elif name == "D":
            continue
        for m in CH[name]:
            put(pad, pad_note(mtof(m), dur, cut), t0 - 0.05)
        # sub + bass
        n = int((dur + 0.8) * SR)
        t = np.arange(n) / SR
        f = mtof(ROOT[name])
        env = np.minimum(t / 0.25, 1) * np.where(t > dur, np.exp(-(t - dur) / 0.25), 1)
        s = np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * 2 * f * t) + 0.1 * np.sin(2 * np.pi * 3 * f * t)
        put(bass, np.tanh(1.3 * s) * env, t0)

    # arpeggio (FM bells)
    pattern = [0, 2, 1, 3, 2, 4, 3, 1]
    arp_sections = [(15.0, 35.0, 2, 0.55), (35.0, 50.0, 4, 0.8), (50.0, 70.0, 4, 1.0), (72.5, 82.5, 2, 0.5),
                    (82.5, 92.5, 2, 0.6), (92.5, 110.0, 4, 0.8), (118.75, 127.0, 2, 0.6)]
    for a, b_, per_beat, lvl in arp_sections:
        step = BEAT / per_beat
        k = 0
        t = a
        while t < b_ - 1e-6:
            tones = sorted(set(m + 24 for m in CH[chord_at(t)][1:]))
            m = tones[pattern[k % len(pattern)] % len(tones)]
            acc = 1.0 if k % per_beat == 0 else 0.7
            put(arp, bell(mtof(m), dec=0.9 if per_beat == 4 else 1.4) * acc * lvl, t, pan=0.5 * np.sin(k * 0.9))
            k += 1
            t += step

    # drums: 50-70 driving, 35-50 half-time, 92.5-110 pulse, 112.5-117.5 build
    def beats(a, b_, every):
        return np.arange(a, b_ - 1e-6, every)

    for t in beats(35.0, 50.0, BAR):
        put(drums, kick(0.9), t)
    for t in beats(35.0 + 2 * BEAT, 50.0, BAR):
        put(drums, snare(0.7), t)
    for t in beats(50.0, 70.0, BEAT):
        k = int(round((t - 50.0) / BEAT)) % 4
        put(drums, kick(1.0), t)
        if k in (1, 3):
            put(drums, snare(0.8), t)
        if k == 2:
            put(drums, kick(0.6), t + BEAT / 2)
    for t in beats(50.0, 70.0, BEAT / 2):
        put(drums, hat(0.35 if int(round((t - 50) / (BEAT / 2))) % 2 else 0.2), t, pan=0.3)
    for seg0 in (50.0, 55.0, 60.0, 65.0):  # tom fills into the next surface
        for i, f in enumerate((140, 120, 100, 85, 72, 62)):
            put(drums, tom(f, 0.7), seg0 + 5.0 - 6 * BEAT / 4 + i * BEAT / 4, pan=0.6 - 0.24 * i)
    for t in beats(92.5, 110.0, BEAT):
        k = int(round((t - 92.5) / BEAT)) % 4
        if k in (0, 2):
            put(drums, kick(0.75), t)
    for t in beats(92.5, 110.0, BEAT / 4):
        put(drums, hat(0.18 if int(round((t - 92.5) / (BEAT / 4))) % 2 else 0.1, 0.025), t, pan=-0.3)
    for t in beats(112.5, 115.0, BEAT):
        put(drums, kick(0.9), t)
    for t in beats(115.0, 117.5, BEAT / 2):
        put(drums, kick(0.9), t)
        put(drums, snare(0.35 + 0.5 * (t - 115) / 2.5), t)
    for t in beats(116.25, 117.5, BEAT / 4):
        put(drums, snare(0.25 + 0.5 * (t - 116.25) / 1.25), t)

    # hits
    for th, a, kind in HITS:
        root = ROOT[chord_at(th + 0.01)] - 12
        if kind == "big":
            put(hits, boom(1.0 * a), th)
            put(hits, braam(root, 3.0, 0.9 * a), th)
            put(hits, reverse_swell(0.9, 0.5 * a), th - 0.9)
        elif kind == "mid":
            put(hits, boom(0.7 * a, dec=0.8), th)
            put(hits, reverse_swell(0.6, 0.35 * a), th - 0.6)
        elif kind == "soft":
            put(hits, boom(0.4 * a, f_hi=60, dec=1.5), th)
            put(hits, reverse_swell(1.2, 0.4 * a), th - 1.2)
        else:
            tones = [m + 36 for m in CH[chord_at(th)]]
            f = mtof(tones[int(th * 13.7) % len(tones)])
            put(ticks, tick(f, 0.6 + a), th, pan=float(np.sin(th * 7.1)) * 0.6)
    for a, b_, amp in ((10.0, 12.5, 0.4), (32.5, 35.0, 0.8), (47.5, 50.0, 0.8), (67.5, 70.0, 0.9), (80.0, 82.5, 0.5),
                       (90.0, 92.5, 0.5), (112.5, 117.5, 1.2)):
        put(rise, riser(b_ - a, amp=amp), a, pan=0.0)
    # rising sea: slow whoosh
    put(rise, lp(riser(3.0, 150, 3000, 0.6), 4000), 109.6)

    # ------------------------------------------------------------ mix
    for b in (pad, bass, arp):
        b /= rms(b)
    for b in (drums, hits, ticks, rise):
        b /= np.abs(b).max() + 1e-9
    pad_auto = seg_level(tt, [(0, 0.0), (2.5, 0.35), (12.5, 0.5), (35, 0.9), (50, 0.8), (70, 0.55), (82.5, 0.7),
                              (92.5, 0.75), (110, 0.5), (112.5, 0.8), (117.5, 1.1), (126, 0.9), (130, 0.0)])
    bass_auto = seg_level(tt, [(0, 0.0), (2.5, 0.4), (12.5, 0.6), (35, 1.0), (70, 0.6), (92.5, 0.9), (117.5, 1.1),
                               (127, 0.8), (130, 0.0)])
    # sidechain pump from kicks
    duck = np.ones(N)
    for t in np.concatenate([np.arange(50.0, 70.0, BEAT), np.arange(92.5, 110.0, BEAT * 2),
                             np.arange(112.5, 117.5, BEAT / 2)]):
        i = int(t * SR)
        n = min(int(0.4 * SR), N - i)
        duck[i:i + n] *= 1 - 0.45 * np.exp(-np.arange(n) / SR / 0.12)
    dry = (pad * pad_auto * duck * db(-20) + bass * bass_auto * duck * db(-25) + arp * db(-24) + drums * db(-8)
           + hits * db(-1.5) + ticks * db(-16) + rise * db(-12))
    send = pad * pad_auto * db(-20) * 0.45 + arp * db(-24) * 0.7 + hits * db(-1.5) * 0.35 + ticks * db(-16) * 0.8 \
        + drums * db(-8) * 0.12 + rise * db(-12) * 0.4
    L, R = ir(3.4)
    wet = np.stack([fftconvolve(send[0], L)[:N], fftconvolve(send[1], R)[:N]])
    mix = dry + wet * db(-3)
    mix = hp(mix, 28)
    # master: gentle glue + soft limiter
    mix /= np.percentile(np.abs(mix), 99.9) + 1e-9
    mix = np.tanh(mix * 1.1) / np.tanh(1.1)
    mix *= db(-1.0) / np.abs(mix).max()
    fade = np.clip((DUR - tt) / 2.0, 0, 1) ** 1.5
    return mix * fade


if __name__ == "__main__":
    import soundfile as sf
    mix = compose()
    os.makedirs(os.path.join(D, "out"), exist_ok=True)
    sf.write(os.path.join(D, "out", "score.wav"), mix.T.astype(np.float32), SR, subtype="PCM_24")
    bars = [20 * np.log10(np.sqrt(np.mean(mix[:, int(b * BAR * SR):int((b + 1) * BAR * SR)] ** 2)) + 1e-9)
            for b in range(NB)]
    print("per-bar RMS dBFS:", " ".join(f"{x:.0f}" for x in bars))
    print("peak", np.abs(mix).max())
