"""Procedural sound effects (no music): ambience beds, footsteps and battle events,
all synthesised with numpy/scipy and placed on the video's beat grid.

build(...) returns stereo stems: ambience, events, footsteps (float32, shape (N, 2)).
"""
import math
import numpy as np
from scipy import signal

SR = 48000
TAU = 2 * math.pi


# ================================================================ basics
def ns(d):
    return max(1, int(round(d * SR)))


def tvec(d):
    return np.arange(ns(d)) / SR


def white(d, seed):
    return np.random.default_rng(seed).standard_normal(ns(d)).astype(np.float32)


def _norm(x):
    m = np.max(np.abs(x)) + 1e-9
    return (x / m).astype(np.float32)


def pink(d, seed):
    x = white(d, seed)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X[1:] /= np.sqrt(f[1:]); X[0] = 0
    return _norm(np.fft.irfft(X, len(x)))


def brown(d, seed):
    x = np.cumsum(white(d, seed)) / 60.0
    return _norm(hp(x, 20))


def _sos(kind, f, order=2):
    if kind == "bandpass":
        lo, hi = f
        f = [max(10, lo), min(hi, SR * 0.45)]
    else:
        f = min(f, SR * 0.45)
    return signal.butter(order, f, btype=kind, fs=SR, output="sos")


def lp(x, f, order=2):
    return signal.sosfilt(_sos("lowpass", f, order), x).astype(np.float32)


def hp(x, f, order=2):
    return signal.sosfilt(_sos("highpass", f, order), x).astype(np.float32)


def bp(x, lo, hi, order=2):
    return signal.sosfilt(_sos("bandpass", (lo, hi), order), x).astype(np.float32)


def env(n, attack, decay, hold=0.0):
    t = np.arange(n) / SR
    a = np.clip(t / max(attack, 1e-4), 0, 1)
    d = np.where(t < attack + hold, 1.0, np.exp(-(t - attack - hold) / max(decay, 1e-4)))
    return (a * d).astype(np.float32)


def smooth_noise(d, rate, seed):
    """Slowly varying random curve in [0,1] (for amplitude / wind gusts)."""
    k = max(2, int(d * rate) + 3)
    pts = np.random.default_rng(seed).random(k)
    x = np.linspace(0, k - 3, ns(d))
    i = np.floor(x).astype(int)
    f = x - i
    f = f * f * (3 - 2 * f)
    return (pts[i] * (1 - f) + pts[i + 1] * f).astype(np.float32)


def tone(freq, d, harm=(1.0,), phase0=0.0):
    """freq: scalar or array (Hz) -> additive tone."""
    n = ns(d)
    f = np.full(n, freq, np.float32) if np.isscalar(freq) else np.asarray(freq, np.float32)[:n]
    ph = TAU * np.cumsum(f) / SR + phase0
    out = np.zeros(n, np.float32)
    for k, a in enumerate(harm, 1):
        out += a * np.sin(k * ph)
    return out


def damped(freqs, d, taus, amps=None):
    t = tvec(d)
    out = np.zeros_like(t, dtype=np.float32)
    for i, (f, tau) in enumerate(zip(freqs, taus)):
        a = 1.0 if amps is None else amps[i]
        out += a * np.sin(TAU * f * t) * np.exp(-t / tau)
    return out.astype(np.float32)


# ================================================================ ambience beds
def rain(d, seed, heavy=0.6):
    hiss = bp(pink(d, seed), 900, 9000) * (0.35 + 0.4 * heavy)
    rng = np.random.default_rng(seed + 1)
    imp = np.zeros(ns(d), np.float32)
    k = int(d * (180 + 500 * heavy))
    imp[rng.integers(0, len(imp), k)] = rng.uniform(0.2, 1.0, k) * rng.choice([-1, 1], k)
    drops = bp(imp, 2200, 8500) * 1.6 + lp(imp, 900) * 0.5
    return hiss + drops


def wind(d, seed, strength=0.5, howl=0.0):
    b = lp(brown(d, seed), 450) * 0.9 + bp(pink(d, seed + 1), 250, 1400) * 0.25
    gust = 0.45 + 0.55 * smooth_noise(d, 0.8, seed + 2)
    out = b * gust * (0.4 + strength)
    if howl > 0:
        w = white(d, seed + 3)
        for i, f in enumerate((340, 520, 760)):
            band = bp(w, f * 0.96, f * 1.04, order=3)
            out += _norm(band) * howl * 0.35 * smooth_noise(d, 1.2, seed + 10 + i) ** 2
    return out


def fire(d, seed, size=0.6):
    roar = lp(brown(d, seed), 280) * 0.8 + bp(pink(d, seed + 1), 300, 2200) * 0.25
    roar *= 0.6 + 0.4 * smooth_noise(d, 3, seed + 2)
    rng = np.random.default_rng(seed + 3)
    imp = np.zeros(ns(d), np.float32)
    k = int(d * 40 * size)
    imp[rng.integers(0, len(imp), k)] = rng.uniform(0.3, 1.0, k) ** 2
    crackle = bp(imp, 1500, 7000) * 3 + lp(imp, 400) * 0.6
    return (roar * size + crackle)


def sea(d, seed, big=0.5):
    t = tvec(d)
    swell = 0.35 + 0.65 * (0.5 - 0.5 * np.cos(TAU * t / 5.2 + seed)) ** 2
    body = lp(pink(d, seed), 700) * swell
    wash = bp(pink(d, seed + 1), 2500, 9000) * np.roll(swell, int(0.6 * SR)) * 0.4
    return (body + wash) * (0.5 + big)


def crickets(d, seed, n=3):
    t = tvec(d)
    out = np.zeros_like(t, dtype=np.float32)
    rng = np.random.default_rng(seed)
    for i in range(n):
        f = rng.uniform(4200, 5200)
        rate = rng.uniform(0.8, 1.4)
        ph = rng.uniform(0, 1)
        gate = (((t * rate + ph) % 1) < 0.18) * (np.sin(TAU * 32 * t) > 0)
        out += np.sin(TAU * f * t) * gate * rng.uniform(0.3, 0.6)
    return lp(out, 7000)


def insects(d, seed):
    w = white(d, seed)
    t = tvec(d)
    a = bp(w, 4200, 6800) * (0.55 + 0.45 * np.sign(np.sin(TAU * 26 * t)))
    b = bp(white(d, seed + 1), 2800, 3600) * (0.5 + 0.5 * np.sin(TAU * 11 * t)) * 0.6
    return (a + b) * (0.6 + 0.4 * smooth_noise(d, 0.5, seed + 2))


def birds(d, seed, density=1.5, lo=2600, hi=4800):
    out = np.zeros(ns(d), np.float32)
    rng = np.random.default_rng(seed)
    t0 = rng.uniform(0, 0.3)
    while t0 < d - 0.2:
        for _ in range(rng.integers(2, 6)):
            L = rng.uniform(0.04, 0.12)
            f = np.linspace(rng.uniform(lo, hi), rng.uniform(lo, hi), ns(L))
            c = tone(f, L) * np.sin(np.linspace(0, math.pi, ns(L))) ** 2
            i = ns(t0)
            out[i:i + len(c)] += c[: max(0, len(out) - i)] * rng.uniform(0.4, 1.0)
            t0 += L + rng.uniform(0.02, 0.08)
        t0 += rng.uniform(0.3, 1.2) / density
    return out


def gull(seed):
    rng = np.random.default_rng(seed)
    parts = []
    for k in range(rng.integers(2, 4)):
        L = rng.uniform(0.28, 0.42)
        f = np.linspace(1750, 1150, ns(L)) * (1 + 0.03 * np.sin(TAU * 28 * tvec(L)))
        c = tone(f, L, harm=(1, 0.6, 0.4, 0.25)) * env(ns(L), 0.03, L * 0.5)
        parts.append(np.concatenate([c, np.zeros(ns(rng.uniform(0.05, 0.12)), np.float32)]))
    return bp(np.concatenate(parts), 700, 6000)


def crowd(d, seed, n=12):
    out = np.zeros(ns(d), np.float32)
    for i in range(n):
        f0 = 220 + 40 * (i % 7) + 13 * i
        v = bp(white(d, seed + i), f0, f0 * 2.4)
        out += _norm(v) * smooth_noise(d, 4.5, seed + 100 + i) ** 3
    return lp(out, 2500)


def siren(d, seed, period=5.5):
    t = tvec(d)
    f = 430 + 330 * (0.5 - 0.5 * np.cos(TAU * t / period + seed))
    return lp(tone(f, d, harm=(1, 0.35, 0.15)), 2200)


def bell(seed=0, f0=196.0, d=4.0):
    ratios = (0.5, 1.0, 1.19, 1.5, 2.0, 2.52, 3.0, 4.1)
    amps = (0.5, 1.0, 0.6, 0.4, 0.5, 0.3, 0.2, 0.12)
    taus = (3.0, 2.2, 1.6, 1.2, 1.0, 0.7, 0.5, 0.3)
    s = damped([f0 * r for r in ratios], d, taus, amps)
    strike = bp(white(0.03, seed), 1500, 6000) * env(ns(0.03), 0.001, 0.008)
    s[: len(strike)] += strike * 2
    return s


def engine_drone(d, seed, freqs=(55, 57.5, 61, 63.5), noise=0.3):
    out = np.zeros(ns(d), np.float32)
    for i, f in enumerate(freqs):
        out += tone(f * (1 + 0.004 * np.sin(TAU * 0.3 * tvec(d) + i)), d, harm=(1, 0.7, 0.5, 0.35, 0.25, 0.15))
    out += lp(brown(d, seed), 300) * noise * 4
    return lp(out, 900)


def steam_hiss(d, seed):
    return bp(white(d, seed), 2500, 9000) * (0.7 + 0.3 * smooth_noise(d, 2, seed + 1))


# ================================================================ events
def explosion(seed, size=1.0, dist=0.0):
    L = 1.1 + 0.9 * size + 1.2 * dist
    n = ns(L)
    body = lp(brown(L, seed), 900 - 650 * dist) * env(n, 0.004 + 0.02 * dist, 0.22 * size + 0.4 * dist)
    t = tvec(L)
    f = 38 + 45 * np.exp(-t / 0.12)
    sub = tone(f, L) * env(n, 0.003, 0.3 * size + 0.2 * dist) * 1.2
    crack = hp(white(L, seed + 1), 900) * env(n, 0.0005, 0.012) * (1 - dist)
    rng = np.random.default_rng(seed + 2)
    imp = np.zeros(n, np.float32)
    k = int(60 * size)
    pos = (rng.random(k) ** 2 * 0.9 * L * SR + 0.08 * SR).astype(int)
    imp[np.clip(pos, 0, n - 1)] = rng.uniform(0.1, 0.6, k)
    debris = bp(imp, 1800, 6000) * 2 * (1 - dist) * np.exp(-t / 0.6)
    out = body * 1.4 + sub + crack * 0.8 + debris
    if dist > 0:
        out = lp(out, 1800 - 1200 * dist)
    return _norm(out)


def gunshot(seed, dist=0.0):
    L = 0.25
    n = ns(L)
    crack = white(L, seed) * env(n, 0.0003, 0.004)
    body = bp(white(L, seed + 1), 700, 5000) * env(n, 0.0005, 0.03)
    thump = lp(white(L, seed + 2), 220) * env(n, 0.001, 0.05) * 3
    out = crack + body + thump
    if dist > 0:
        out = lp(out, 3000 - 2200 * dist)
    return _norm(out)


def machine_gun(d, seed, rate=13.0, dist=0.0):
    out = np.zeros(ns(d) + ns(0.3), np.float32)
    rng = np.random.default_rng(seed)
    tt = 0.0
    k = 0
    while tt < d:
        g = gunshot(seed * 131 + k, dist) * rng.uniform(0.7, 1.0)
        i = ns(tt)
        out[i:i + len(g)] += g[: len(out) - i]
        tt += 1 / rate * rng.uniform(0.9, 1.1)
        k += 1
    return out


def cannon(seed):
    e = explosion(seed, size=1.6)
    t = tvec(len(e) / SR)
    e[: ns(0.6)] += (tone(30 + 40 * np.exp(-t[: ns(0.6)] / 0.08), 0.6) * env(ns(0.6), 0.002, 0.2))
    return _norm(e)


def splash(seed):
    L = 1.6
    n = ns(L)
    thump = lp(white(L, seed), 160) * env(n, 0.002, 0.12) * 3
    spray = bp(pink(L, seed + 1), 900, 9000) * env(n, 0.03, 0.55) * 1.5
    rng = np.random.default_rng(seed + 2)
    imp = np.zeros(n, np.float32)
    k = 120
    imp[(rng.random(k) * 0.6 * L * SR + 0.3 * SR).astype(int)] = rng.uniform(0.1, 0.5, k)
    drops = bp(imp, 2000, 7000) * 2
    return _norm(thump + spray + drops)


def flyby(d, seed, f0=80.0, pass_t=None, doppler=0.14, harm=(1, 0.8, 0.6, 0.45, 0.3, 0.2)):
    """Piston engine passing: pitch and loudness peak at pass_t."""
    pass_t = d * 0.5 if pass_t is None else pass_t
    t = tvec(d)
    x = (t - pass_t) / 0.6
    ratio = 1 + doppler * (-np.tanh(x))
    s = tone(f0 * ratio, d, harm=harm)
    s *= 1 + 0.25 * np.sin(TAU * f0 * 0.5 * t)
    s += bp(white(d, seed), 300, 3000) * 0.4
    return lp(s, 2500) * (1 / (1 + x * x)) ** 0.8


def dive_scream(d, seed):
    t = tvec(d)
    f = 650 + 700 * (t / d) ** 1.4
    s = tone(f, d, harm=(1, 0.3, 0.2)) * np.clip(t / (d * 0.3), 0, 1)
    return s + flyby(d, seed, f0=95, pass_t=d * 0.9) * 0.8


def tank(d, seed):
    t = tvec(d)
    eng = tone(31 * (1 + 0.02 * np.sin(TAU * 0.7 * t)), d, harm=(1, 0.9, 0.7, 0.6, 0.4, 0.3, 0.2)) * 0.7
    eng += lp(brown(d, seed), 220) * 0.8
    out = lp(eng, 700)
    rng = np.random.default_rng(seed + 1)
    tt = 0.0
    while tt < d - 0.05:                      # track clanks
        c = damped([1150 + rng.uniform(-80, 80), 2350, 3900], 0.05, [0.012, 0.008, 0.005], [1, 0.6, 0.3])
        i = ns(tt)
        out[i:i + len(c)] += c[: len(out) - i] * 0.35
        tt += 1 / 7.5 * rng.uniform(0.85, 1.15)
    return out


def chuffs(d, seed, rate=3.0):
    out = np.zeros(ns(d) + ns(0.3), np.float32)
    rng = np.random.default_rng(seed)
    tt, k = 0.05, 0
    while tt < d:
        L = 0.28
        c = bp(white(L, seed + k), 250, 3500) * env(ns(L), 0.006, 0.09)
        c = c * (1.0 if k % 2 == 0 else 0.7)
        i = ns(tt)
        out[i:i + len(c)] += c[: len(out) - i]
        tt += 1 / rate
        k += 1
    return out


def whistle(d=1.3, seed=0):
    t = tvec(d)
    vib = 1 + 0.006 * np.sin(TAU * 5.5 * t)
    s = sum(tone(f * vib, d, harm=(1, 0.3)) for f in (523, 659, 784))
    s = s * env(ns(d), 0.08, 0.3, hold=d - 0.5)
    s += bp(white(d, seed), 1500, 5000) * 0.3 * env(ns(d), 0.05, 0.3, hold=d - 0.45)
    return _norm(s)


def flak_pop(seed):
    return explosion(seed, size=0.35, dist=0.6) * 0.8


def whoosh(d, seed, up=True, lo=250, hi=6000):
    """Filtered-noise swell sweeping up (riser) or down."""
    n = ns(d)
    w = pink(d, seed)
    out = np.zeros(n, np.float32)
    seg = 1024
    nb = n // seg + 1
    win = np.hanning(2 * seg).astype(np.float32)
    for b in range(nb):
        k = b / max(1, nb - 1)
        k = k if up else 1 - k
        fc = lo * (hi / lo) ** k
        i0 = max(0, b * seg - seg // 2)
        blk = w[i0:i0 + 2 * seg]
        if len(blk) < 32:
            continue
        f = bp(blk, fc * 0.6, fc * 1.6)
        out[i0:i0 + len(f)] += f * win[: len(f)]
    shape = np.linspace(0, 1, n) ** (2.2 if up else 0.4) if up else np.linspace(1, 0, n) ** 1.5
    return _norm(out) * shape


def impact(seed, size=1.0):
    L = 1.6
    t = tvec(L)
    sub = tone(28 + 55 * np.exp(-t / 0.09), L) * env(ns(L), 0.002, 0.45 * size)
    boom = lp(brown(L, seed), 180) * env(ns(L), 0.004, 0.35 * size)
    return _norm(sub * 1.3 + boom)


def tinnitus(d, seed=0):
    t = tvec(d)
    s = np.sin(TAU * 5400 * t) * 0.7 + np.sin(TAU * 7300 * t) * 0.25
    return (s * env(ns(d), 0.02, d * 0.35)).astype(np.float32)


def flare_hiss(d, seed):
    return bp(white(d, seed), 3000, 8000) * (0.6 + 0.4 * smooth_noise(d, 6, seed + 1))


# ---------------------------------------------------------------- footsteps
def footstep(surface, seed, heavy=1.0, gear=False):
    L = 0.45
    n = ns(L)
    rng = np.random.default_rng(seed)
    out = np.zeros(n, np.float32)

    def hit(off, amp):
        i = ns(off)
        m = n - i
        click = white(L, seed + int(off * 1e4)) * env(n, 0.0003, 0.003)
        body = lp(white(L, seed + 7 + int(off * 1e4)), 1300) * env(n, 0.001, 0.025)
        thud = lp(white(L, seed + 11 + int(off * 1e4)), 170) * env(n, 0.002, 0.045) * 2.5
        out[i:] += (click * 0.5 + body + thud)[:m] * amp

    if surface in ("hard", "wet", "wood", "metal", "rubble"):
        hit(0.0, heavy)
        hit(0.07 * rng.uniform(0.8, 1.2), 0.45 * heavy)
    if surface == "wet":
        out += bp(white(L, seed + 3), 1800, 7500) * env(n, 0.004, 0.09) * 1.6
    if surface == "wood":
        out += damped([170, 410], L, [0.05, 0.03], [0.8, 0.3]) * env(n, 0.001, 0.2)
    if surface == "metal":
        out += damped([360, 880, 1760], L, [0.09, 0.05, 0.03], [0.5, 0.35, 0.15]) * heavy
    if surface in ("snow", "rubble", "gravel"):
        grains = np.zeros(n, np.float32)
        k = 45 if surface == "snow" else 30
        pos = (rng.random(k) * (0.16 if surface == "snow" else 0.09) * SR).astype(int)
        grains[pos] = rng.uniform(0.2, 1.0, k)
        lo, hi = (1500, 6000) if surface == "snow" else (700, 3500)
        out += bp(grains, lo, hi) * 4 * heavy
        out += lp(white(L, seed + 5), 200) * env(n, 0.004, 0.05) * 1.5 * heavy
    if surface == "sand":
        out += lp(pink(L, seed + 6), 2500) * env(n, 0.015, 0.09) * 1.2 * heavy
        out += lp(white(L, seed + 8), 180) * env(n, 0.004, 0.05) * 1.2 * heavy
    if surface in ("grass",):
        out += bp(white(L, seed + 9), 2000, 7500) * env(n, 0.01, 0.1) * 0.9
        out += lp(white(L, seed + 10), 200) * env(n, 0.003, 0.05) * 1.5 * heavy
    if surface == "mud":
        out += bp(white(L, seed + 12), 250, 1600) * env(n, 0.01, 0.12) * 2 * heavy
        out += lp(white(L, seed + 13), 150) * env(n, 0.003, 0.06) * 2 * heavy
    if gear:                                   # rifle sling / canteen rattle
        for k in range(3):
            j = damped([rng.uniform(3800, 6000)], 0.05, [0.01])
            i = ns(rng.uniform(0.01, 0.08))
            out[i:i + len(j)] += j[: n - i] * 0.25
    return out


# ================================================================ mixing
class Mix:
    def __init__(self, dur):
        self.n = ns(dur) + ns(3.0)
        self.buf = np.zeros((self.n, 2), np.float32)

    def add(self, sig, t, gain=1.0, pan=0.0, fade_out=None):
        i = ns(t) if t > 0 else 0
        s = sig[ns(-t):] if t < 0 else sig
        s = s[: self.n - i].astype(np.float32)
        if fade_out:
            s = s[: ns(fade_out)]
            f = min(len(s), ns(0.012))
            if f:
                s = s.copy(); s[-f:] *= np.linspace(1, 0, f)
        a = (pan + 1) * math.pi / 4
        self.buf[i:i + len(s), 0] += s * gain * math.cos(a)
        self.buf[i:i + len(s), 1] += s * gain * math.sin(a)

    def add_st(self, l, r, t, gain=1.0, dur=None, fade=0.008):
        """Stereo bed with short fades so it can be hard-cut on the beat."""
        m = min(len(l), len(r)) if dur is None else min(len(l), len(r), ns(dur))
        l, r = l[:m].copy(), r[:m].copy()
        f = min(m // 2, ns(fade))
        ramp = np.linspace(0, 1, f, dtype=np.float32)
        for x in (l, r):
            x[:f] *= ramp; x[-f:] *= ramp[::-1]
        i = ns(t)
        m = min(m, self.n - i)
        self.buf[i:i + m, 0] += l[:m] * gain
        self.buf[i:i + m, 1] += r[:m] * gain


def reverb(x, seconds=1.2, wet=0.15, seed=7):
    n = ns(seconds)
    t = np.arange(n) / SR
    out = x.copy()
    for ch in range(2):
        ir = white(seconds, seed + ch) * np.exp(-t / (seconds / 5)).astype(np.float32)
        ir = lp(ir, 5000)
        ir /= np.sqrt(np.sum(ir ** 2)) + 1e-9
        out[:, ch] += signal.fftconvolve(x[:, ch], ir)[: len(x)].astype(np.float32) * wet
    return out


def stereo(fn, *a, **k):
    """Build a decorrelated stereo bed by calling a mono generator with two seeds."""
    seed = k.pop("seed")
    return fn(*a, seed=seed, **k), fn(*a, seed=seed + 5000, **k)
