"""Synthesises the soundtrack from scratch (no samples): D minor, 120 BPM,
getting denser, lower and louder section by section until the hard cut."""
import sys
import numpy as np
from scipy import signal
from scipy.io import wavfile
from timeline import *

SR = 44100
N = int(TOTAL * SR) + SR
rng = np.random.default_rng(7)
BUS = {k: np.zeros((2, N)) for k in ("drums", "pump", "hall", "sub")}


def mtof(m): return 440.0 * 2 ** ((np.asarray(m, float) - 69) / 12)
def tarr(d): return np.arange(int(d * SR)) / SR
def noise(d): return rng.standard_normal(int(d * SR))


def put(bus, t, x, pan=0.0, g=1.0):
    i = int(round(t * SR))
    if x.ndim == 1:
        a = (pan + 1) * np.pi / 4
        x = np.vstack([x * np.cos(a), x * np.sin(a)]) * np.sqrt(2)
    n = min(x.shape[1], N - i)
    if n > 0:
        BUS[bus][:, i:i + n] += g * x[:, :n]


# ------------------------------------------------------------------ oscillators
def phase(f, n):
    f = np.broadcast_to(np.asarray(f, float), (n,)) if np.ndim(f) == 0 else f[:n]
    return f, (np.cumsum(f / SR) + rng.random()) % 1.0


def saw(f, d):
    n = int(d * SR)
    f, p = phase(f, n)
    dt = f / SR
    y = 2 * p - 1
    m = p < dt; x = p[m] / dt[m]; y[m] -= x + x - x * x - 1
    m = p > 1 - dt; x = (p[m] - 1) / dt[m]; y[m] -= x * x + x + x + 1
    return y


def sine(f, d):
    n = int(d * SR)
    f, p = phase(f, n)
    return np.sin(2 * np.pi * p)


def filt(x, fc, kind="low", order=2):
    if kind == "band":
        fc = [max(fc[0], 20), min(fc[1], SR * .45)]
    else:
        fc = float(np.clip(fc, 20, SR * .45))
    return signal.sosfilt(signal.butter(order, fc, kind, fs=SR, output="sos"), x)


def lp_sweep(x, fcs, block=256):
    """2-pole low-pass whose cutoff follows the per-sample array `fcs`."""
    y = np.empty_like(x); zi = np.zeros((1, 2))
    for i in range(0, len(x), block):
        fc = float(np.clip(fcs[min(i, len(fcs) - 1)], 30, SR * .45))
        sos = signal.butter(2, fc, "low", fs=SR, output="sos")
        y[i:i + block], zi = signal.sosfilt(sos, x[i:i + block], zi=zi)
    return y


def fade(x, a=0.005, r=0.02):
    na, nr = max(1, int(a * SR)), max(1, int(r * SR))
    x = x.copy(); x[:na] *= np.linspace(0, 1, na); x[-nr:] *= np.linspace(1, 0, nr)
    return x


# ------------------------------------------------------------------ instruments
def kick(g=1.0):
    t = tarr(.55)
    f = 44 + 120 * np.exp(-t * 28)
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 5.5)
    y += filt(noise(.55), 3000, "high") * np.exp(-t * 250) * .25
    return np.tanh(1.8 * y) * g


def boom(s=1.0):
    t = tarr(4.0)
    f = 30 + 70 * np.exp(-t * 7)
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * (1.4 / s))
    y += filt(noise(4.0), 300) * np.exp(-t * 3) * .9
    y += filt(noise(4.0), 2500, "high") * np.exp(-t * 18) * .25 * s
    return np.tanh(2.2 * y) * s


def swell(d=1.6):
    t = tarr(d)
    return filt(noise(d), 1800, "high") * (t / d) ** 3


def clap(g=1.0):
    t = tarr(.35)
    e = np.exp(-t * 22) + .6 * np.exp(-np.maximum(t - .012, 0) * 40) * (t > .012)
    y = filt(noise(.35), (900, 5000), "band") * e
    y += np.sin(2 * np.pi * 190 * t) * np.exp(-t * 35) * .5
    return y * g


def hat(g=1.0, d=.06):
    t = tarr(d + .05)
    return filt(noise(d + .05), 7000, "high") * np.exp(-t / d * 4) * g


def pluck(m, d=.9):
    t = tarr(d); s = saw(mtof(m), d) + .5 * saw(mtof(m) * 1.004, d)
    y = filt(s, 4200) * np.exp(-t * 16) + filt(s, 900) * np.exp(-t * 5)
    return fade(y, .002, .05)


def bell(m, d=3.0):
    t = tarr(d); f0 = mtof(m); y = np.zeros_like(t)
    for r, a, k in [(1, 1, 1.2), (2.0, .5, 2.2), (2.76, .35, 3.1), (4.07, .25, 4.5), (5.43, .15, 6)]:
        y += a * np.sin(2 * np.pi * f0 * r * t) * np.exp(-t * k)
    return fade(y, .001, .2) * .5


def pad(notes, d, bright=1500):
    out = np.zeros((2, int((d + 1.2) * SR)))
    dd = d + 1.2
    t = tarr(dd)
    env = np.minimum(t / .9, 1) * np.clip((dd - t) / 1.2, 0, 1)
    for i, m in enumerate(notes):
        for k, det in enumerate([-.12, -.05, 0, .06, .13]):
            v = filt(saw(mtof(m + det), dd), bright) * env * .12
            out[(i + k) % 2] += v
    return out


def bass(m, d, fc=500, drive=1.5):
    t = tarr(d)
    s = saw(mtof(m), d) + saw(mtof(m) * 1.007, d) + .8 * sine(mtof(m - 12), d) * 2
    y = filt(s, fc) * np.minimum(1, np.exp(-t * .8) + .2)
    return fade(np.tanh(drive * y) * .5, .003, .03)


def strings(m, d=.12, fc=2400):
    t = tarr(d + .1)
    s = saw(mtof(m), d + .1) + saw(mtof(m) * 1.005, d + .1)
    env = np.minimum(t / .01, 1) * np.exp(-np.maximum(t - d, 0) * 30)
    return fade(filt(s, fc) * env * .35)


def braam(root=26, d=2.2, g=1.0):
    t = tarr(d)
    y = np.zeros_like(t)
    for m, a in [(root, 1), (root + 12, .8), (root + 19, .5), (root + 24, .45), (root + 12.08, .6)]:
        y += a * saw(mtof(m), d)
    fcs = 120 + 2600 * np.minimum(t / .18, 1) * np.exp(-np.maximum(t - .18, 0) * 2.4)
    y = lp_sweep(y, fcs)
    env = np.minimum(t / .03, 1) * np.clip((d - t) / .4, 0, 1)
    return np.tanh(2.0 * y * env) * .55 * g


def taiko(g=1.0, f0=95):
    t = tarr(.9)
    f = f0 * .62 + f0 * .6 * np.exp(-t * 18)
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 6)
    y += filt(noise(.9), 900) * np.exp(-t * 30) * .7
    return np.tanh(1.5 * y) * g


def riser(d, top=7000):
    t = tarr(d); x = t / d
    y = lp_sweep(filt(noise(d), 200, "high"), 300 + top * x ** 2)
    y += .25 * saw(110 * 2 ** (3 * x ** 1.5), d) * x
    return y * x ** 2


def shepard(t0, t1, rate=.12):
    d = t1 - t0; n = int(d * SR); t = np.arange(n) / SR
    y = np.zeros(n)
    for k in range(9):
        p = (k + rate * t) % 9                      # octave position
        f = 27.5 * 2 ** p
        a = np.exp(-((p - 4.5) / 1.6) ** 2)
        y += a * np.sin(2 * np.pi * np.cumsum(f) / SR)
    return y * np.minimum(t / 4, 1) ** 2


# ------------------------------------------------------------------ harmony
Dm, Bb, F_, C_ = [50, 53, 57], [50, 53, 58], [53, 57, 60], [52, 55, 60]
Gm, A_, Eb = [50, 55, 58], [49, 52, 57], [51, 55, 58]
ROOT = {tuple(Dm): 38, tuple(Bb): 34, tuple(F_): 41, tuple(C_): 36,
        tuple(Gm): 43, tuple(A_): 33, tuple(Eb): 39}
PROG = {"intro": [Dm] * 4, "mult": [Dm, Bb, F_, C_], "perm": [Dm, Bb, F_, C_],
        "comb": [Dm, Bb, F_, C_], "incl": [Dm, Bb, Gm, A_],
        "catalan": [Dm, Bb, Gm, A_], "genf": [Dm, Eb, Dm, A_],
        "ramsey": [Dm, Eb, Dm, A_], "outro": [Dm] * 4}
ORDER = [s[0] for s in SECTIONS]


def chord_at(t):
    name, a, _ = section_at(t)
    return PROG[name][int((t - a) // 4) % 4]


def build():
    ks = kick_times()
    # --- intro -------------------------------------------------------------
    t = tarr(10)
    drone = (sine(mtof(26), 10) + .5 * sine(mtof(33), 10) + .3 * filt(saw(mtof(38), 10), 300))
    put("pump", 0, drone * np.minimum(t / 6, 1) * .35)
    put("hall", 0, filt(noise(10), (200, 900), "band") * (t / 10) ** 2 * .25)
    scale = [74, 77, 81, 84, 86, 89, 93, 96]
    for i, ts in enumerate(SPLITS):
        put("hall", ts, bell(scale[i], 2.5), pan=(-1) ** i * .4, g=.55)
    put("pump", 6, pad(Dm, 3.5, 900)[:, :], g=.8)

    # --- per-section instruments on a 16th grid ------------------------------
    for step in range(int(CUT / .125)):
        t = step * .125
        name, a, b = section_at(t)
        si = ORDER.index(name)
        s16 = step % 16                      # position in bar
        ch = chord_at(t)
        notes = ch + [c + 12 for c in ch]
        # arpeggio
        arp = None
        if name == "mult" and t >= 13 and step % 2 == 0:
            arp = .22
        elif name in ("perm", "comb", "incl", "catalan", "ramsey"):
            arp = .2 + .02 * si
        elif name == "genf" and step % 2 == 0:
            arp = .22
        if arp:
            pat = [0, 2, 4, 5, 3, 4, 1, 5] if si < 4 else [0, 3, 5, 3, 1, 4, 2, 5]
            m = notes[pat[step % 8]] + (12 if name in ("catalan", "ramsey") and step % 4 == 3 else 0)
            put("pump", t, pluck(m + 12), pan=.5 * np.sin(step * .7), g=arp)
        # pads on chord changes
        if name not in ("intro", "outro") and (t - a) % 4 == 0:
            d = min(4, b - t)
            put("pump", t, pad(ch, d, 700 + 280 * si), g=.5 + .05 * si)
        # bass
        if name == "perm" and (t - a) % 4 == 0:
            put("sub", t, bass(ROOT[tuple(ch)], min(4, b - t), 300), g=.5)
        elif name == "comb" and step % 2 == 0:
            put("sub", t, bass(ROOT[tuple(ch)], .24, 450), g=.55)
        elif name in ("incl", "catalan", "genf") and step % 2 == 0:
            fc = 500 + 900 * (.5 + .5 * np.sin(t * 1.3))
            put("sub", t, bass(ROOT[tuple(ch)] + (12 if step % 8 == 6 else 0), .24, fc, 2.5), g=.6)
        elif name == "ramsey":
            put("sub", t, bass(ROOT[tuple(ch)], .12, 900 + 1200 * ((t - a) / (b - a)), 3.5), g=.6)
        # hats / claps
        if name in ("comb", "incl") and s16 % 4 == 2:
            put("drums", t, hat(.35), pan=.3)
        if name in ("catalan", "ramsey"):
            put("drums", t, hat(.18 + .2 * (s16 % 4 == 2)), pan=.3 * (-1) ** step)
        if name in ("comb", "incl", "catalan", "ramsey") and s16 in (4, 12):
            put("drums", t, clap(.55), pan=-.1)
        # string ostinato
        if name in ("catalan", "genf", "ramsey"):
            m = [38, 50, 38, 45][step % 4] + (1 if name == "ramsey" and step % 8 == 7 else 0)
            put("pump", t, strings(m, fc=1600 + 500 * si), pan=-.4, g=.5 + .1 * (name == "ramsey"))

    for k in ks:
        g = .7 if k < 42 else .95
        put("drums", k, kick(g))
        if k >= 94:
            put("sub", k, kick(.5))

    # --- sonified counting --------------------------------------------------
    for i in range(TREE_N):
        put("hall", TREE_T0 + i * TREE_DT, bell(62 + [0, 3, 7, 10, 12, 15, 19, 22, 24, 27, 31, 34, 36][i], 1.5), g=.3)
    for i in range(PASCAL_N):
        put("hall", PASCAL_T0 + i * PASCAL_DT, bell([62, 65, 69, 72, 74, 77, 81, 84, 86, 89, 93, 96][i], 1.8), g=.3, pan=.3)
    for n in range(1, DER_N + 1):
        r = sum((-1) ** k / np.prod(range(1, k + 1)) for k in range(n + 1))
        put("hall", DER_T0 + (n - 1) * DER_DT, bell(62 + (r - .3679) * 40 + 12, 1.5), g=.35)
    for i in range(14):
        put("hall", DYCK_T0 + i * DYCK_DT, bell(74 + [0, 3, 5, 7, 10, 12, 15][i % 7], 1.2), g=.22, pan=-.3)

    # --- tension devices ------------------------------------------------------
    for t0 in range(94, 108, 2):
        put("hall", t0, braam(26, 2.2, .8))
    for t0 in np.arange(108, 115, 2):
        put("hall", t0, braam(26 if (t0 // 2) % 2 == 0 else 27, 2.2, 1.0))
    for t0 in np.arange(115, 119, .5):
        put("hall", t0, braam(26, .6, .9))
    for t0 in np.arange(119, CUT, 1.0):
        put("hall", t0, braam(26 + (t0 >= 123), 1.0, 1.1))
    for t0 in np.arange(115, CUT, .5):
        put("drums", t0, taiko(.8))
    for t0 in (88, 89):
        put("drums", t0, taiko(.5, 140)); put("drums", t0 + .5, taiko(.5, 120))
    # accelerating snare roll into the cut
    t0, dt = 122.0, .25
    while t0 < CUT:
        put("drums", t0, clap(.25 + .4 * (t0 - 122) / 4), pan=rng.uniform(-.3, .3))
        t0 += dt; dt = max(.03125, dt * .93)
    put("hall", 97, shepard(97, CUT, .10), g=.22)
    for a, b in [(70, 72), (88, 90), (100, 102), (105.5, 108), (112.5, 115), (117, 119), (120, CUT)]:
        put("hall", a, riser(b - a), g=.35 + .03 * (a > 110))
    for t0, s in HITS:
        put("hall", t0 - 1.6, swell(1.6), g=.35 * s)
        put("sub", t0, boom(s), g=.9)
        if t0 >= 90:
            put("hall", t0, braam(26, 3.0, .7 * s))

    # --- outro --------------------------------------------------------------
    put("hall", FINAL, braam(26, 5.0, 1.2))
    put("hall", FINAL, bell(62, 6.5), g=.8)
    put("hall", FINAL + .02, bell(74, 6.0), g=.5, pan=.3)
    t = tarr(TOTAL - FINAL)
    put("pump", FINAL, sine(mtof(38), TOTAL - FINAL) * np.exp(-t * .4) * .5)


def ir(rt, d, bright):
    t = tarr(d)
    e = np.exp(-6.9 * t / rt)
    return np.vstack([filt(noise(d), bright) * e, filt(noise(d), bright) * e]) * .08


def mix():
    ks = np.array(kick_times())
    tt = np.arange(N) / SR
    duck = np.ones(N)
    idx = np.searchsorted(ks, tt, side="right") - 1
    ok = idx >= 0
    dtk = tt[ok] - ks[idx[ok]]
    duck[ok] = 1 - .55 * np.exp(-dtk / .13) * (tt[ok] >= 42)
    pump = BUS["pump"] * duck
    room_in = BUS["drums"] * .15 + pump * .3
    hall_in = BUS["hall"] + pump * .15
    out = BUS["drums"] + pump + BUS["hall"] * .6 + BUS["sub"]
    out += np.vstack([signal.oaconvolve(room_in[c], ir(1.1, 1.5, 5000)[c])[:N] for c in (0, 1)])
    out += np.vstack([signal.oaconvolve(hall_in[c], ir(3.2, 4.0, 3500)[c])[:N] for c in (0, 1)])
    out = signal.sosfilt(signal.butter(2, 25, "high", fs=SR, output="sos"), out)
    # loudness shaping: pull short-term RMS towards a steadily rising target
    win = 4 * SR
    cs = np.cumsum(np.concatenate([[0], (out ** 2).mean(0)]))
    cen = np.arange(win // 2, N - win // 2, SR // 2)
    rms_db = 10 * np.log10((cs[cen + win // 2] - cs[cen - win // 2]) / win + 1e-12)
    ref = rms_db[(cen > 100 * SR) & (cen < 124 * SR)].mean()
    target = np.interp(cen / SR, [0, 10, 40, 76, 94, 108, 126], [-11, -10, -8, -6, -3.5, -1, 0]) + ref
    gdb = np.clip(target - rms_db, -4, 7)
    gdb = np.convolve(np.pad(gdb, 4, mode="edge"), np.ones(9) / 9, "valid")
    out *= 10 ** (np.interp(tt, cen / SR, gdb) / 20)
    # hard cut: absolute silence between CUT and FINAL
    g = np.ones(N); g[int(CUT * SR):int(FINAL * SR)] = 0
    g[int(CUT * SR) - 64:int(CUT * SR)] = np.linspace(1, 0, 64)
    # fade out the tail
    fs = int((TOTAL - 2.5) * SR); g[fs:] *= np.linspace(1, 0, N - fs) ** 2
    out *= g
    out /= np.percentile(np.abs(out), 99.9) + 1e-9
    out = np.tanh(out * 1.1) / np.tanh(1.1)
    out *= .93 / np.max(np.abs(out))
    return out[:, :int(TOTAL * SR)]


if __name__ == "__main__":
    build()
    y = mix()
    wavfile.write(sys.argv[1] if len(sys.argv) > 1 else "music.wav", SR, (y.T * 32767).astype(np.int16))
