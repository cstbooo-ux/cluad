"""Shared timeline: scene boundaries and every audible/visible accent.
96 BPM -> one beat 0.625 s, one bar 2.5 s. render.py and music.py both read this."""
import numpy as np

BPM = 96.0
BEAT = 60.0 / BPM
BAR = 4 * BEAT
DUR = 130.0

SCENES = [  # name, start, end
    ("intro", 0.0, 7.5),
    ("conics", 7.5, 12.5),
    ("cubic", 12.5, 25.0),
    ("torus", 25.0, 35.0),
    ("clebsch", 35.0, 50.0),
    ("race", 50.0, 70.0),
    ("fermat", 70.0, 82.5),
    ("calabi", 82.5, 92.5),
    ("finite", 92.5, 102.5),
    ("scheme", 102.5, 112.5),
    ("finale", 112.5, DUR),
]

# 27 Clebsch lines: accelerating over 40..45 s, snapped to a 1/16-note grid feel
LINE_T = [40.0 + 5.0 * (1 - (1 - k / 27) ** 1.6) for k in range(27)]
# singularity race: node pop windows (start, end) per surface
RACE = [("cayley", 50.0, 4), ("kummer", 55.0, 16), ("barth6", 60.0, 65), ("barth10", 65.0, 345)]
# finite field primes, one per half bar
PRIMES_T = [(93.75, 13), (95.0, 31), (96.25, 61), (97.5, 127), (98.75, 257), (100.0, 521), (101.25, 1031)]
# scheme: fibres appear on 1/16 notes
SCHEME_PRIMES = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47]
FIBRE_T = [102.5 + 0.16 * i for i in range(len(SCHEME_PRIMES))]
# group law beats
GL = dict(P=17.5, Q=18.125, line0=18.75, line1=19.375, R=20.0, refl0=20.625, refl1=21.0, S=21.25)
MULT_T = [22.5 + i * BEAT / 4 for i in range(16)]
# Fermat curves n = 3..18 on 1/16 notes
FERMAT_T = [72.5 + i * BEAT / 4 for i in range(16)]
# finale montage cuts
MONTAGE_T = [112.5, 113.125, 113.75, 114.375] + [115.0 + i * BEAT / 2 for i in range(8)]

# (time, strength 0..1, kind)  kind: big | mid | soft | tick
HITS = [
    (2.5, 0.55, "mid"), (7.5, 0.25, "soft"), (12.5, 0.5, "mid"), (15.0, 0.55, "mid"),
    (GL["P"], 0.2, "tick"), (GL["Q"], 0.2, "tick"), (GL["R"], 0.3, "tick"), (GL["S"], 0.6, "mid"),
    (25.0, 0.3, "soft"), (30.0, 0.5, "mid"),
    (35.0, 1.0, "big"), (45.0, 0.9, "big"),
    (50.0, 0.9, "big"), (55.0, 0.9, "big"), (60.0, 0.95, "big"), (65.0, 1.0, "big"),
    (70.0, 1.0, "big"), (78.75, 0.5, "mid"), (82.5, 0.6, "mid"), (92.5, 0.6, "mid"), (93.75, 0.4, "mid"),
    (102.5, 0.6, "mid"), (110.0, 0.4, "soft"),
    (117.5, 1.0, "big"),
]
HITS += [(t, 0.12, "tick") for t in LINE_T]
HITS += [(t, 0.1, "tick") for t in MULT_T]
HITS += [(t, 0.1, "tick") for t in FERMAT_T]
HITS += [(t, 0.25, "tick") for t, _ in PRIMES_T[1:]]
HITS += [(t, 0.08, "tick") for t in FIBRE_T]
HITS += [(t, 0.35, "tick") for t in MONTAGE_T[1:]]
HITS.sort()


def scene_at(t):
    for name, a, b in SCENES:
        if a <= t < b:
            return name, a, b
    return SCENES[-1]


def fx(t):
    """flash, shake (dx, dy), aberration, punch-zoom from hits"""
    flash = shake = ab = zoom = 0.0
    sx = sy = 0.0
    for th, a, kind in HITS:
        if th > t or t - th > 1.2:
            continue
        dt = t - th
        if kind == "tick":
            flash += 0.05 * a * np.exp(-dt / 0.05)
            continue
        k = {"big": 1.0, "mid": 0.55, "soft": 0.25}[kind]
        flash += a * k * 0.9 * np.exp(-dt / 0.07)
        ab += a * k * 4.0 * np.exp(-dt / 0.18)
        zoom += a * k * 0.035 * np.exp(-dt / 0.22)
        amp = a * k * 9.0 * np.exp(-dt / 0.16)
        rng = np.random.default_rng(int(th * 1000) + int(dt * FPS_HINT))
        sx += amp * rng.uniform(-1, 1)
        sy += amp * rng.uniform(-1, 1)
    return flash, (sx, sy), ab, zoom


FPS_HINT = 30
