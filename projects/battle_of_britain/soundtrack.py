"""Procedural SFX for 'Paper Plane', placed on the same timeline as the picture, then mixed under the music.

Outputs in out/: sfx_ambience.wav, sfx_events.wav, sfx_mix.wav, music_sfx_mix.wav (if music/song.wav exists)
"""
import math, os, random, wave
import numpy as np
from silhouette_kit.sfx import (SR, ns, tvec, _norm, lp, hp, bp, env, pink, white, brown, smooth_noise, tone, damped,
                                wind, birds, crickets, engine_drone, explosion, gunshot, machine_gun, flyby, whoosh,
                                impact, footstep, flak_pop, Mix, reverb, dive_scream, fire, bell)

D = os.path.dirname(os.path.abspath(__file__))
TAU = 2 * math.pi


# ------------------------------------------------------------------ small synths
def grass_rustle(d, seed, a=1.0):
    x = bp(pink(d, seed), 1800, 8000) * (0.4 + 0.6 * smooth_noise(d, 3, seed + 1) ** 2)
    return x * a


def paper_flutter(d, seed):
    t = tvec(d)
    am = 0.55 + 0.45 * np.sin(2 * np.pi * (17 + 3 * np.sin(t * 1.3)) * t)
    return bp(white(d, seed), 700, 3500) * am * (0.6 + 0.4 * smooth_noise(d, 2, seed + 1))


def paper_crinkle(seed, d=0.35):
    rng = np.random.default_rng(seed)
    out = np.zeros(ns(d), np.float32)
    for _ in range(26):
        L = rng.uniform(0.004, 0.02)
        c = bp(white(L, int(rng.integers(0, 1e6))), 1500, 9000) * env(ns(L), 0.0005, L * 0.4)
        i = int(rng.uniform(0, d - L) * SR)
        out[i:i + len(c)] += c * rng.uniform(0.3, 1.0)
    return out


def swish(seed, d=0.3):
    return whoosh(d, seed, up=True, lo=600, hi=5000) * np.linspace(1, 0.2, ns(d)) ** 0.5


def breath(seed, inhale=True, d=0.55):
    x = bp(pink(d, seed), 350 if inhale else 250, 2600 if inhale else 1800)
    n = ns(d)
    e = np.sin(np.linspace(0, math.pi, n)) ** (1.5 if inhale else 0.8)
    return (x * e).astype(np.float32)


def heartbeat(seed):
    t = tvec(0.45)
    thump = lambda: np.sin(2 * math.pi * 52 * t) * np.exp(-t / 0.05)
    x = thump()
    x[ns(0.18):] += thump()[: len(x) - ns(0.18)] * 0.7
    return lp(x, 160)


def metal_hits(seed, n=9, d=0.6):
    rng = np.random.default_rng(seed)
    out = np.zeros(ns(d), np.float32)
    for k in range(n):
        f = rng.uniform(900, 2600)
        c = damped([f, f * 1.47, f * 2.3], 0.12, [0.03, 0.02, 0.012], [1, 0.5, 0.3])
        c += hp(white(0.12, int(rng.integers(0, 1e6))), 2500) * env(ns(0.12), 0.0003, 0.006)
        i = int(rng.uniform(0, d - 0.12) * SR)
        out[i:i + len(c)] += c * rng.uniform(0.5, 1.0)
    return out


def glass_crack(seed):
    d = 0.5
    x = hp(white(d, seed), 3000) * env(ns(d), 0.0005, 0.03)
    x += damped([4200, 6100, 7800], d, [0.08, 0.05, 0.04], [0.4, 0.3, 0.2])
    return x


def sputter_gate(d, seed, start_rate=1.0):
    """1 = engine on, dips to 0 in stutters that get more frequent."""
    rng = np.random.default_rng(seed)
    g = np.ones(ns(d), np.float32)
    t = 0.2
    while t < d:
        L = rng.uniform(0.06, 0.22)
        g[ns(t):ns(t + L)] = rng.uniform(0.0, 0.25)
        t += L + rng.uniform(0.15, 0.9) / (start_rate + 2.5 * t / d)
    return lp(g, 30)


def skylark(d, seed, density=1.0):
    """A skylark high over the field: long runs of quick, trilling, jumping notes."""
    out = np.zeros(ns(d), np.float32)
    rng = np.random.default_rng(seed)
    t0 = rng.uniform(0, 0.4)
    while t0 < d - 0.3:
        run = rng.uniform(0.6, 1.8)
        te = min(d - 0.1, t0 + run)
        f = rng.uniform(3200, 5200)
        while t0 < te:
            L = rng.uniform(0.025, 0.07)
            f = float(np.clip(f + rng.uniform(-900, 900), 2800, 6800))
            fr = np.linspace(f, f * rng.uniform(0.85, 1.2), ns(L))
            c = tone(fr, L) * np.sin(np.linspace(0, math.pi, ns(L))) ** 2
            c *= 1 + 0.5 * np.sin(TAU * rng.uniform(40, 90) * tvec(L))
            i = ns(t0)
            out[i:i + len(c)] += c[: max(0, len(out) - i)] * rng.uniform(0.4, 1.0)
            t0 += L + rng.uniform(0.005, 0.03)
        t0 += rng.uniform(0.4, 1.4) / density
    return out


def radio_chatter(d, seed):
    """R/T in a headset: squelch click, band-limited 'speech' (syllable-gated noise with formant sweeps), hiss."""
    rng = np.random.default_rng(seed)
    t = tvec(d)
    syl = np.zeros(ns(d), np.float32)
    x = 0.05
    while x < d - 0.1:
        L = rng.uniform(0.06, 0.16)
        syl[ns(x):ns(x + L)] = rng.uniform(0.5, 1.0)
        x += L + rng.uniform(0.02, 0.12)
    syl = lp(syl, 25)
    voice = bp(white(d, seed), 450, 2600) * syl
    form = np.sin(TAU * (700 + 400 * np.sin(TAU * 3.1 * t)) * t) * syl * 0.3
    hiss = bp(white(d, seed + 1), 1500, 6000) * 0.15
    clk = np.zeros(ns(d), np.float32)
    for tc in (0.0, d - 0.03):
        c = bp(white(0.02, seed + 2), 1000, 5000) * env(ns(0.02), 0.0005, 0.006)
        clk[ns(tc):ns(tc) + len(c)] += c[: len(clk) - ns(tc)]
    return np.tanh((voice + form + hiss) * 2.5) * 0.6 + clk


def rattle(d, seed, rate=35.0):
    """Airframe rattle: a dense spray of tiny metallic ticks riding on the engine vibration."""
    rng = np.random.default_rng(seed)
    imp = np.zeros(ns(d), np.float32)
    k = int(d * rate)
    imp[rng.integers(0, len(imp), k)] = rng.uniform(0.3, 1.0, k)
    ticks = bp(imp, 1200, 4500) * 3
    vib = 0.6 + 0.4 * np.sin(TAU * 29 * tvec(d)) * smooth_noise(d, 2, seed + 1)
    return ticks * vib + lp(brown(d, seed + 2), 120) * 0.8


def creak(seed, d=0.4):
    """Leather glove tightening: stick-slip pulses sweeping in rate."""
    rng = np.random.default_rng(seed)
    out = np.zeros(ns(d), np.float32)
    x = 0.0
    while x < d - 0.01:
        c = bp(white(0.006, int(rng.integers(0, 1e6))), 700, 2600) * env(ns(0.006), 0.0003, 0.002)
        out[ns(x):ns(x) + len(c)] += c * (0.5 + 0.5 * math.sin(math.pi * x / d))
        x += 0.012 + 0.02 * (x / d)
    return out


def click(seed):
    return damped([2900, 4700], 0.05, [0.006, 0.004], [1, 0.5]) + hp(white(0.05, seed), 3000) * env(ns(0.05), 0.0003, 0.003)


def casings(d, seed, rate=18.0):
    """Spent cases and links tinkling out of the wing chutes."""
    rng = np.random.default_rng(seed)
    out = np.zeros(ns(d), np.float32)
    for _ in range(int(d * rate)):
        f = rng.uniform(3500, 7500)
        c = damped([f, f * 1.6], 0.08, [0.02, 0.012], [1, 0.4])
        i = ns(rng.uniform(0, d - 0.08))
        out[i:i + len(c)] += c * rng.uniform(0.2, 0.7)
    return out


def bullet_cracks(d, seed, rate=10.0):
    """Rounds snapping past close by: sharp cracks with a tiny whizz."""
    rng = np.random.default_rng(seed)
    out = np.zeros(ns(d), np.float32)
    for _ in range(int(d * rate)):
        L = 0.07
        c = hp(white(L, int(rng.integers(0, 1e6))), 2500) * env(ns(L), 0.0002, 0.004)
        c += whoosh(L, int(rng.integers(0, 1e6)), up=False, lo=1500, hi=7000) * 0.3
        i = ns(rng.uniform(0, max(0.01, d - L)))
        out[i:i + len(c)] += c[: len(out) - i] * rng.uniform(0.4, 1.0)
    return out


def buffet(seed, size=1.0):
    """A thump of rough air against the airframe."""
    L = 0.5
    return lp(brown(L, seed), 140) * env(ns(L), 0.01, 0.12 * size) * 2 + rattle(L, seed + 1, 60) * env(ns(L), 0.005, 0.1) * 0.4


def ignite(seed):
    """Fuel catching: a rushing whump that opens into flame."""
    L = 1.2
    return (whoosh(L, seed, up=False, lo=200, hi=3000) * env(ns(L), 0.01, 0.4) + lp(brown(L, seed + 1), 300) *
            env(ns(L), 0.005, 0.25) * 1.5 + fire(L, seed + 2, size=0.8) * np.linspace(0, 1, ns(L)))


def caption_burn(seed, d=0.9):
    """The caption catching fire and burning away: a soft flare-up, crackle and paper curling."""
    return (whoosh(d, seed, up=True, lo=300, hi=4000) * 0.5 + fire(d, seed + 1, size=0.4) * env(ns(d), 0.05, d * 0.5)
            + paper_crinkle(seed + 2, d) * 0.4)


# ------------------------------------------------------------------ build
def build(out, TL, IMPACTS, beat, DROP, END, DUR, land_t=37.3):
    """The whole sound design, placed on the picture's own timeline and schedules."""
    import shots as S_
    os.makedirs(out, exist_ok=True)
    amb, ev = Mix(DUR), Mix(DUR)
    idx = {i: (s_[0], s_[1]) for i, s_ in enumerate(TL)}
    rnd = random.Random(1)

    # ======== 1930: a summer field in Kent
    d0 = DROP
    wl, wr = wind(d0, 11, strength=0.15), wind(d0, 12, strength=0.15)
    ramp = np.clip(np.linspace(0, d0, ns(d0)) / d0, 0, 1) ** 2
    amb.add_st(wl * (0.25 + 0.6 * ramp), wr * (0.25 + 0.6 * ramp), 0.0, gain=0.5)
    amb.add(grass_rustle(5.8, 13), 0.0, gain=0.25, fade_out=5.8)
    amb.add(birds(7.0, 14, density=1.2, lo=3000, hi=5200), 0.0, gain=0.12, pan=0.4, fade_out=7.0)
    amb.add(skylark(9.0, 15), 0.3, gain=0.07, pan=-0.3, fade_out=9.0)
    amb.add(crickets(5.5, 16), 0.0, gain=0.04, pan=0.6, fade_out=5.5)
    for tb, g in ((1.1, 0.12), (3.3, 0.09)):                          # the village church, far off
        ev.add(lp(bell(17, f0=174.6, d=3.5), 3000), tb, gain=g, pan=0.55)
    t = 0.3
    k = 0
    while t < 4.6:                                                     # the boy's running steps
        ev.add(hp(footstep("grass", 100 + k, heavy=0.55), 250), t, gain=0.35, pan=-0.3 + 0.35 * t / 4.6)
        t += 0.18
        k += 1
    for tb in (3.6, 4.0, 4.35):                                         # out of breath on the hillock
        ev.add(breath(120 + int(tb * 10), tb < 4.2, 0.3), tb, gain=0.12, pan=0.1)
    ev.add(swish(201, 0.35), 5.2, gain=0.6, pan=0.2)                    # the throw
    ev.add(paper_flutter(DROP - 5.6, 202) * np.linspace(0.6, 1.0, ns(DROP - 5.6)), 5.6, gain=0.2)
    rush = hp(pink(DROP - 5.6, 203), 400) * np.linspace(0.15, 1, ns(DROP - 5.6)) ** 1.5
    amb.add(rush, 5.6, gain=0.22)                                        # the climb: air rushing
    eng = engine_drone(DROP - 8.0, 204, freqs=(41, 43, 46)) * np.linspace(0, 1, ns(DROP - 8.0)) ** 2
    amb.add(eng, 8.0, gain=0.35)                                        # distant engines creep in
    ev.add(whoosh(DROP - 11.4, 205, up=True), 11.4, gain=0.5)          # riser into the drop
    for tt in (8.4, 9.9, 11.2, 11.86, 12.2, 12.37, 12.85, 13.22):      # turbulence jolts (picture IMPACTS)
        ev.add(buffet(int(tt * 100), 0.6 + 0.4 * (tt - 8) / 5), tt, gain=0.3)
    ev.add(caption_burn(210), 10.86, gain=0.35, pan=-0.5)             # '1930' burns away
    ev.add(caption_burn(211), beat(4), gain=0.35, pan=-0.5)           # '1940' burns away
    # a breath of near-silence right before the drop, so it hits harder
    i0, i1 = ns(DROP - 0.22), ns(DROP)
    for m in (amb, ev):
        m.buf[i0:i1] *= np.linspace(1, 0.15, i1 - i0)[:, None]

    # ======== 1940: the battle
    dB = END - DROP
    hit_t = beat(17)
    merlin = engine_drone(dB, 301, freqs=(58, 60.5, 63, 87), noise=0.4)
    gate = np.ones(ns(dB), np.float32)
    gi = ns(hit_t + 0.4 - DROP)
    gate[gi:] = sputter_gate(dB - (hit_t + 0.4 - DROP), 302)[: len(gate) - gi]
    amb.add(merlin * gate, DROP, gain=0.55)
    bl, br = wind(dB, 303, strength=0.9, howl=0.4), wind(dB, 304, strength=0.9, howl=0.4)
    ramp = np.clip((np.arange(ns(dB)) / SR - (hit_t - DROP)) / (END - hit_t), 0, 1)
    amb.add_st(bl * (0.5 + 0.9 * ramp), br * (0.5 + 0.9 * ramp), DROP, gain=0.45)
    # the whole sky at war, far off: engines, bursts of fire, flak, explosions
    far_eng = engine_drone(hit_t + 1 - DROP, 306, freqs=(71, 76, 83, 95), noise=0.2)
    amb.add(far_eng * np.clip(np.linspace(0, 6, ns(hit_t + 1 - DROP)), 0, 1), DROP, gain=0.18, pan=-0.2)
    t = DROP + 0.3
    while t < hit_t + 1.5:
        r_ = rnd.random()
        if r_ < 0.45:
            ev.add(flak_pop(int(t * 97)), t, gain=0.2, pan=rnd.uniform(-0.8, 0.8))
        elif r_ < 0.75:
            ev.add(machine_gun(rnd.uniform(0.3, 0.8), int(t * 53), rate=15, dist=0.85), t, gain=0.15,
                   pan=rnd.uniform(-0.9, 0.9))
        else:
            ev.add(explosion(int(t * 31), size=0.8, dist=0.85), t, gain=0.22, pan=rnd.uniform(-0.8, 0.8))
        t += rnd.uniform(0.3, 0.8)
    # the drop
    ev.add(impact(401, size=2.2), DROP, gain=1.0)
    ev.add(explosion(402, size=1.3), DROP, gain=0.6)
    ev.add(flyby(1.6, 403, f0=112, pass_t=0.25), DROP - 0.05, gain=0.7, pan=0.3)
    ev.add(machine_gun(0.5, 404, rate=16, dist=0.4), DROP + 0.25, gain=0.35, pan=0.7)
    # every hard cut / accent
    for ti, st, col in IMPACTS:
        if DROP < ti < END and st >= 0.5:
            ev.add(impact(int(ti * 13), size=0.5 * st), ti, gain=0.45)
            ev.add(whoosh(0.22, int(ti * 17), up=False, lo=500, hi=6000), ti - 0.05, gain=0.3)
    # near fly-bys (shots.air_traffic near passes)
    PER, DUR_ = 1.1, 0.24
    for i_, seed in {6: 2, 10: 11, 11: 13}.items():
        t0, t1 = idx[i_]
        k = math.floor((t0 + seed * 0.37) / PER)
        while True:
            start = k * PER - seed * 0.37
            if start > t1:
                break
            if start + DUR_ > t0:
                ev.add(flyby(1.1, int(start * 50), f0=random.Random(k).uniform(95, 125), pass_t=0.4),
                       max(t0, start + DUR_ / 2) - 0.4, gain=0.55, pan=random.Random(k).choice((-0.6, 0.6)))
            k += 1
    # planes coming head-on at the camera (some firing) and turning away (shots.depth_passes)
    for i_, seed in {3: 0, 4: 5, 5: 17, 6: 2, 8: 7, 9: 9, 10: 11, 11: 13, 12: 5, 13: 15}.items():
        t0, t1 = idx[i_]
        if i_ == 3:
            t0 = beat(1.5)
        for st, du, kind_, side, firing in S_.depth_schedule(t0, t1, seed):
            if kind_ == "toward":
                ev.add(flyby(du + 0.6, int(st * 41), f0=rnd.uniform(100, 130), pass_t=du * 0.95, doppler=0.2),
                       st, gain=0.4, pan=0.5 * side)
                if firing:
                    ev.add(machine_gun(du * 0.6, int(st * 43), rate=17, dist=0.5), st + du * 0.2, gain=0.3,
                           pan=0.3 * side)
                    ev.add(bullet_cracks(du * 0.5, int(st * 47), rate=12), st + du * 0.35, gain=0.25)
            else:
                ev.add(flyby(du + 0.4, int(st * 37), f0=rnd.uniform(90, 115), pass_t=0.05), st, gain=0.3,
                       pan=0.6 * side)
    # near clouds / smoke racing past (shots.speed_layer)
    for i_, (seed, amt, rate, nl) in {4: (3, 0.9, 1.3, 2), 5: (17, 1.0, 1.4, 1), 6: (4, 1.0, 1.3, 2),
                                      7: (5, 0.8, 1.3, 2), 8: (7, 1.0, 1.3, 2), 9: (9, 0.8, 1.3, 1),
                                      10: (11, 1.0, 1.2, 2), 11: (13, 1.0, 1.2, 2), 12: (3, 0.9, 1.3, 2),
                                      13: (15, 1.0, 1.2, 2)}.items():
        t0, t1 = idx[i_]
        for st, du, li in S_.speed_passes(t0, t1, seed, amt, rate, nl):
            ev.add(whoosh(du + 0.25, int(st * 71), up=False, lo=250, hi=2500), st, gain=0.22,
                   pan=0.5 if li == 0 else -0.5)
    # the first battle shot: comic speed-line slams get a whoosh each
    for tt in (DROP + 0.05, beat(2.9) - 0.15):
        ev.add(whoosh(0.35, int(tt * 19), up=True, lo=400, hi=7000), tt - 0.2, gain=0.35)
    # inside the cockpit: engine through the airframe, rattle, oxygen mask, R/T chatter
    for i_ in (4, 5, 12):
        t0, t1 = idx[i_]
        dd = t1 - t0
        amb.add(lp(merlin[ns(t0 - DROP):ns(t1 - DROP)] * 1.0, 250), t0, gain=0.45)
        amb.add(rattle(dd, 500 + i_), t0, gain=0.18)
    ev.add(breath(510, True, 0.45), idx[4][0] + 0.1, gain=0.35)
    ev.add(breath(511, False, 0.5), idx[4][0] + 0.6, gain=0.3)
    ev.add(radio_chatter(0.55, 512), idx[4][0] + 0.2, gain=0.22, pan=-0.2)
    ev.add(radio_chatter(0.4, 513), idx[12][0] + 0.02, gain=0.2, pan=0.2)
    t0, t1 = idx[5]                                                      # the stick: glove, button, the 109 across
    ev.add(creak(514), t0 + 0.02, gain=0.35)
    ev.add(click(515), t0 + 0.35, gain=0.4)
    ev.add(flyby(1.0, 516, f0=120, pass_t=0.35), t0, gain=0.4, pan=0.3)
    ev.add(machine_gun(t1 - t0 - 0.2, 517, rate=18, dist=0.25), t0 + 0.2, gain=0.25)
    # guns on the hero shots, matched to the flashes on screen
    ev.add(machine_gun(0.35, 501, rate=18), beat(8) + 0.3, gain=0.5, pan=0.0)                 # gunsight
    ev.add(machine_gun(beat(10) - beat(9), 502, rate=19), beat(9), gain=0.75, pan=-0.2)       # wing guns
    ev.add(casings(beat(10) - beat(9), 518), beat(9) + 0.1, gain=0.3, pan=-0.3)
    ev.add(whoosh(0.8, 519, up=True, lo=200, hi=5000), beat(10) - 0.2, gain=0.45)            # out of the cloud
    t0, t1 = idx[10]                                                    # the chase: the 109 firing at the wingman
    ev.add(machine_gun(t1 - t0, 503, rate=15, dist=0.35), t0, gain=0.45, pan=-0.4)
    ev.add(bullet_cracks(t1 - t0, 520, rate=6), t0, gain=0.2, pan=0.4)
    ev.add(metal_hits(521, n=5, d=t1 - t0), t0, gain=0.2, pan=0.5)
    t0, t1 = idx[11]                                                    # the attack: our eight guns
    ev.add(machine_gun(t1 - t0, 505, rate=19), t0, gain=0.6, pan=-0.3)
    ev.add(casings(t1 - t0, 522), t0, gain=0.25, pan=-0.4)
    ev.add(metal_hits(523, n=12, d=t1 - t0), t0 + 0.2, gain=0.35, pan=0.4)
    ev.add(ignite(524), t0 + (t1 - t0) * 0.4, gain=0.35, pan=0.5)                               # the 109 catches fire
    ev.add(explosion(506, size=0.7, dist=0.3), beat(15.6), gain=0.45, pan=0.5)
    ev.add(breath(507, True, 0.35), beat(16.5) + 0.02, gain=0.35)                              # half a beat of relief
    # the hit: the 109 behind him opens up; rounds smack into the airframe
    ev.add(machine_gun((idx[13][1] - hit_t) * 0.75 + 0.1, 604, rate=16, dist=0.2), hit_t - 0.1, gain=0.6, pan=-0.6)
    ev.add(impact(601, size=2.4), hit_t, gain=1.0)
    ev.add(metal_hits(602, n=22, d=1.0), hit_t, gain=0.6, pan=0.2)
    ev.add(bullet_cracks(0.9, 605, rate=14), hit_t + 0.05, gain=0.35)
    ev.add(glass_crack(603), hit_t + 0.05, gain=0.45, pan=-0.2)
    ev.add(ignite(606), hit_t + 0.5, gain=0.5, pan=0.1)                                         # he's on fire

    # ======== the fall
    fall_d = END - beat(19)
    ev.add(dive_scream(fall_d, 713) * np.linspace(0.3, 1.0, ns(fall_d)), beat(19), gain=0.3)
    amb.add(fire(fall_d, 714, size=0.8) * np.linspace(0.6, 1.0, ns(fall_d)), beat(19), gain=0.35)
    amb.add(hp(pink(fall_d, 715), 300) * np.linspace(0.3, 1.0, ns(fall_d)) ** 2, beat(19), gain=0.3)  # air roar
    ev.add(machine_gun(0.6, 710, rate=12, dist=0.9), beat(20), gain=0.2, pan=0.7)             # the fight above, going
    ev.add(whoosh(0.9, 716, up=False, lo=200, hi=4000), beat(19) + 1.3, gain=0.45)             # into the cloud
    ev.add(whoosh(0.9, 717, up=False, lo=200, hi=4000), beat(22) + 0.05, gain=0.4)             # out of it
    t = hit_t + 1.2
    k = 0
    while t < END - 0.3:
        ev.add(breath(700 + k, k % 2 == 0, 0.45 - 0.15 * (t - hit_t) / (END - hit_t)), t, gain=0.45)
        t += 0.55 - 0.25 * (t - hit_t) / (END - hit_t)
        k += 1
    t = beat(22)
    while t < END - 0.2:
        ev.add(heartbeat(int(t * 10)), t, gain=0.55)
        t += 0.75 - 0.3 * (t - beat(22)) / (END - beat(22))
    for ti in np.arange(beat(19) + 0.4, END, 0.5):                       # the burning airframe groaning / popping
        if rnd.random() < 0.6:
            ev.add(metal_hits(int(ti * 7), n=2, d=0.3), float(ti), gain=0.15, pan=rnd.uniform(-0.5, 0.5))
    ev.add(whoosh(END - beat(29), 712, up=True, lo=200, hi=7000), beat(29), gain=0.6)
    # his memory: each paper-plane cut drops the war to a hush - a summer breeze, a lark, the paper
    for st_, en_, _, cam_ in TL:
        if cam_.get("soft") and beat(19) < st_ < END:
            i0, i1 = ns(st_), ns(en_)
            f = min(ns(0.06), (i1 - i0) // 3)
            g = np.full(i1 - i0, 0.18, np.float32)
            g[:f] = np.linspace(1, 0.18, f); g[-f:] = np.linspace(0.18, 1, f)
            for m in (amb, ev):
                m.buf[i0:i1] *= g[:, None]
            dd = en_ - st_
            amb.add(paper_flutter(dd, int(st_ * 100)), st_, gain=0.35, fade_out=dd)
            amb.add(wind(dd, int(st_ * 101), strength=0.12), st_, gain=0.4, fade_out=dd)
            amb.add(skylark(dd, int(st_ * 103), density=2.0), st_, gain=0.08, pan=-0.3, fade_out=dd)
            amb.add(birds(dd, int(st_ * 107), density=2.0, lo=3000, hi=5200), st_, gain=0.07, pan=0.4, fade_out=dd)

    # hard cut at END: every battle sound stops dead
    for m in (amb, ev):
        m.buf[ns(END):] = 0.0

    # ======== 1930 again: only the paper plane, falling into the summer grass
    d1 = DUR - END - 0.35                                               # a held breath of silence first
    t1 = END + 0.35
    wl, wr = wind(d1, 801, strength=0.12), wind(d1, 802, strength=0.12)
    rise = np.clip(np.linspace(0, d1 / 1.5, ns(d1)), 0, 1)
    amb.add_st(wl * rise, wr * rise, t1, gain=0.35)
    amb.add(grass_rustle(d1, 803) * rise, t1, gain=0.22)
    amb.add(birds(d1, 804, density=1.0, lo=3000, hi=5200), t1 + 0.4, gain=0.1, pan=0.4)
    amb.add(skylark(d1, 808, density=0.8), t1 + 0.8, gain=0.06, pan=-0.4)
    amb.add(crickets(d1, 809), t1 + 1.0, gain=0.035, pan=0.6)
    ev.add(paper_flutter(land_t - t1, 805) * np.linspace(1.0, 0.4, ns(land_t - t1)), t1, gain=0.22, pan=-0.2)
    ev.add(paper_crinkle(806, 0.25), land_t - 0.05, gain=0.3, pan=0.05)               # touches the grass
    ev.add(bp(pink(0.5, 807), 1500, 7000) * env(ns(0.5), 0.02, 0.15), land_t - 0.03, gain=0.15)   # grass brushed
    ev.add(lp(bell(810, f0=174.6, d=4.0), 3000), land_t + 1.0, gain=0.07, pan=0.55)    # the church, once more

    # the quiet worlds (1930 and the ending) are mixed louder relative to the battle, so they are heard under the music
    for m in (amb, ev):
        m.buf[:ns(DROP)] *= 2.4
        m.buf[ns(END):] *= 2.8

    # ======== mix
    ev_buf = reverb(ev.buf, 1.1, wet=0.12)
    n = ns(DUR)
    stems = {"ambience": amb.buf[:n], "events": ev_buf[:n]}
    fade = np.ones(n, np.float32)
    fo = ns(DUR - 1.4)
    fade[fo:] = np.linspace(1, 0, n - fo)
    sfx = (stems["ambience"] + stems["events"]) * fade[:, None]
    sfx = sfx / (np.max(np.abs(sfx)) + 1e-9) * 0.9
    write_wav(os.path.join(out, "sfx_mix.wav"), np.tanh(sfx * 1.2) / math.tanh(1.2) * 0.9)
    for k_, v in stems.items():
        write_wav(os.path.join(out, f"sfx_{k_}.wav"), v / (np.max(np.abs(v)) + 1e-9) * 0.9)
    music_path = os.path.join(D, "music", "song.wav")
    if os.path.exists(music_path):
        import soundfile as sf
        m, sr = sf.read(music_path, dtype="float32", always_2d=True)
        if sr != SR:
            import librosa
            m = np.stack([librosa.resample(m[:, c], orig_sr=sr, target_sr=SR) for c in range(m.shape[1])], 1)
        if m.shape[1] == 1:
            m = np.repeat(m, 2, 1)
        m = m[:n]
        if len(m) < n:
            m = np.vstack([m, np.zeros((n - len(m), 2), np.float32)])
        mix = m * 0.85 + sfx * 0.42
        mix = np.tanh(mix * 1.1) / math.tanh(1.1)
        mix *= 0.95 / (np.max(np.abs(mix)) + 1e-9)
        write_wav(os.path.join(out, "music_sfx_mix.wav"), mix)


def write_wav(path, x):
    pcm = (np.clip(x, -1, 1) * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
