"""Procedural SFX for 'Paper Plane', placed on the same timeline as the picture, then mixed under the music.

Outputs in out/: sfx_ambience.wav, sfx_events.wav, sfx_mix.wav, music_sfx_mix.wav (if music/song.wav exists)
"""
import math, os, random, wave
import numpy as np
from silhouette_kit.sfx import (SR, ns, tvec, _norm, lp, hp, bp, env, pink, white, brown, smooth_noise, tone, damped,
                                wind, birds, crickets, engine_drone, explosion, gunshot, machine_gun, flyby, whoosh,
                                impact, footstep, flak_pop, Mix, reverb, dive_scream, fire)

D = os.path.dirname(os.path.abspath(__file__))


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


# ------------------------------------------------------------------ build
def build(out, TL, IMPACTS, beat, DROP, END, DUR):
    os.makedirs(out, exist_ok=True)
    amb, ev = Mix(DUR), Mix(DUR)

    # ======== 1930: field, wind, the run, the throw
    d0 = DROP
    wl, wr = wind(d0, 11, strength=0.15), wind(d0, 12, strength=0.15)
    ramp = np.clip(np.linspace(0, d0, ns(d0)) / d0, 0, 1) ** 2
    amb.add_st(wl * (0.25 + 0.5 * ramp), wr * (0.25 + 0.5 * ramp), 0.0, gain=0.5)
    amb.add(grass_rustle(5.8, 13), 0.0, gain=0.25, fade_out=5.8)
    amb.add(birds(5.8, 14, density=1.2, lo=3000, hi=5200), 0.0, gain=0.12, pan=0.4, fade_out=5.8)
    t = 0.3
    k = 0
    while t < 4.6:                                          # the boy's running steps (light, quick)
        ev.add(hp(footstep("grass", 100 + k, heavy=0.55), 250), t, gain=0.35, pan=-0.3 + 0.35 * t / 4.6)
        t += 0.18
        k += 1
    ev.add(swish(201, 0.35), 5.2, gain=0.55, pan=0.2)               # the throw
    ev.add(paper_flutter(DROP - 5.6, 202), 5.6, gain=0.18)
    rush = hp(pink(DROP - 5.6, 203), 400) * np.linspace(0.2, 1, ns(DROP - 5.6))
    amb.add(rush, 5.6, gain=0.18)
    # distant engines creep in while the sky reddens, then a riser into the drop
    eng = engine_drone(DROP - 8.0, 204, freqs=(41, 43, 46)) * np.linspace(0, 1, ns(DROP - 8.0)) ** 2
    amb.add(eng, 8.0, gain=0.35)
    ev.add(whoosh(DROP - 11.4, 205, up=True), 11.4, gain=0.5)
    for tt, st in ((10.86, 0.5), (11.36, 0.35)):                     # caption burn accents
        ev.add(bp(pink(0.9, int(tt * 100)), 300, 4000) * env(ns(0.9), 0.02, 0.35), tt, gain=0.25 * st / 0.5)

    # ======== 1940: the battle
    dB = END - DROP
    merlin = engine_drone(dB, 301, freqs=(58, 60.5, 63, 87), noise=0.4)
    gate = np.ones(ns(dB), np.float32)
    hit_t = beat(17)
    gi = ns(hit_t + 0.4 - DROP)
    gate[gi:] = sputter_gate(dB - (hit_t + 0.4 - DROP), 302)[: len(gate) - gi]
    amb.add(merlin * gate, DROP, gain=0.55)
    bl, br = wind(dB, 303, strength=0.9, howl=0.4), wind(dB, 304, strength=0.9, howl=0.4)
    ramp = np.clip((np.arange(ns(dB)) / SR - (hit_t - DROP)) / (END - hit_t), 0, 1)
    amb.add_st(bl * (0.5 + 0.8 * ramp), br * (0.5 + 0.8 * ramp), DROP, gain=0.45)
    rng = random.Random(305)
    t = DROP + 0.3
    while t < hit_t + 1.5:                                  # distant flak and explosions
        if rng.random() < 0.6:
            ev.add(flak_pop(int(t * 97)), t, gain=0.2, pan=rng.uniform(-0.8, 0.8))
        else:
            ev.add(explosion(int(t * 31), size=0.8, dist=0.85), t, gain=0.25, pan=rng.uniform(-0.8, 0.8))
        t += rng.uniform(0.35, 0.9)
    # the drop itself
    ev.add(impact(401, size=2.2), DROP, gain=1.0)
    ev.add(explosion(402, size=1.3), DROP, gain=0.6)
    ev.add(flyby(1.6, 403, f0=112, pass_t=0.25), DROP - 0.05, gain=0.7, pan=0.3)
    ev.add(machine_gun(0.5, 404, rate=16, dist=0.4), DROP + 0.25, gain=0.35, pan=0.7)
    # every cut / accent
    for ti, st, col in IMPACTS:
        if DROP < ti < END and st >= 0.5:
            ev.add(impact(int(ti * 13), size=0.5 * st), ti, gain=0.45)
            ev.add(whoosh(0.22, int(ti * 17), up=False, lo=500, hi=6000), ti - 0.05, gain=0.3)
    # near fly-bys (same schedule as shots.air_traffic near passes)
    near_shots = {6: 2, 10: 11, 11: 13}
    PER, DUR_ = 1.1, 0.24                                   # must match shots.air_traffic
    for idx, seed in near_shots.items():
        t0, t1 = TL[idx][0], TL[idx][1]
        k = math.floor((t0 + seed * 0.37) / PER)
        while True:
            start = k * PER - seed * 0.37
            if start > t1:
                break
            if start + DUR_ > t0:
                ev.add(flyby(1.1, int(start * 50), f0=random.Random(k).uniform(95, 125), pass_t=0.4),
                       max(t0, start + DUR_ / 2) - 0.4, gain=0.55, pan=random.Random(k).choice((-0.6, 0.6)))
            k += 1
    # near clouds / smoke racing past (shots.speed_layer): a whoosh on each pass
    import shots as S_
    speed_shots = {4: (3, 0.9, 1.3, 2), 5: (17, 1.0, 1.4, 1), 6: (4, 1.0, 1.3, 2), 7: (5, 0.8, 1.3, 2),
                   8: (7, 1.0, 1.3, 2), 9: (9, 0.8, 1.3, 1), 10: (11, 1.0, 1.2, 2), 11: (13, 1.0, 1.2, 2),
                   12: (3, 0.9, 1.3, 2), 13: (15, 1.0, 1.2, 2)}
    for idx, (seed, amt, rate, nl) in speed_shots.items():
        t0, t1 = TL[idx][0], TL[idx][1]
        for st, du, li in S_.speed_passes(t0, t1, seed, amt, rate, nl):
            ev.add(whoosh(du + 0.25, int(st * 71), up=False, lo=250, hi=2500), st, gain=0.22,
                   pan=0.5 if li == 0 else -0.5)
    # gunsight + wing guns + dogfight
    ev.add(machine_gun(0.35, 501, rate=18), beat(8) + 0.3, gain=0.5, pan=0.0)
    ev.add(machine_gun(beat(10) - beat(9), 502, rate=19), beat(9), gain=0.75, pan=-0.2)
    ev.add(machine_gun(0.7, 503, rate=14, dist=0.35), beat(12) + 0.3, gain=0.4, pan=-0.5)
    ev.add(machine_gun(0.5, 504, rate=14, dist=0.35), beat(13) + 0.1, gain=0.4, pan=-0.4)
    ev.add(machine_gun(0.8, 505, rate=18), beat(14) + 0.2, gain=0.55, pan=0.3)
    ev.add(explosion(506, size=0.7, dist=0.3), beat(15.6), gain=0.45, pan=0.5)
    # the half-beat of relief, then the hit
    ev.add(breath(507, True, 0.35), beat(16.5) + 0.02, gain=0.35)
    ev.add(impact(601, size=2.4), hit_t, gain=1.0)
    ev.add(metal_hits(602), hit_t, gain=0.6, pan=0.2)
    ev.add(glass_crack(603), hit_t + 0.05, gain=0.45, pan=-0.2)
    ev.add(machine_gun(0.6, 604, rate=16, dist=0.2), hit_t - 0.1, gain=0.55, pan=-0.6)
    # falling: breathing, heartbeat, wind, the guns receding
    t = hit_t + 1.2
    k = 0
    while t < END - 0.3:
        ev.add(breath(700 + k, k % 2 == 0, 0.45 - 0.15 * (t - hit_t) / (END - hit_t)), t, gain=0.45)
        t += 0.55 - 0.25 * (t - hit_t) / (END - hit_t)
        k += 1
    t = beat(22)
    while t < END - 0.2:
        ev.add(heartbeat(int(t * 10)), t, gain=0.5)
        t += 0.75 - 0.3 * (t - beat(22)) / (END - beat(22))
    ev.add(machine_gun(0.6, 710, rate=12, dist=0.9), beat(20), gain=0.2, pan=0.7)
    fall_d = END - beat(19)
    ev.add(dive_scream(fall_d, 713) * np.linspace(0.3, 1.0, ns(fall_d)), beat(19), gain=0.3)   # the dive screams
    amb.add(fire(fall_d, 714, size=0.7), beat(19), gain=0.3)                                  # engine on fire
    for tt in (beat(19) + 1.3, beat(24)):                                                      # through the cloud
        ev.add(whoosh(0.9, int(tt * 7), up=False, lo=200, hi=4000), tt, gain=0.45)
    ev.add(whoosh(END - beat(29), 712, up=True, lo=200, hi=7000), beat(29), gain=0.6)

    # the memory cuts in the fall: the battle drops away to a hush, a soft wind and the paper plane's flutter
    for st_, en_, _, cam_ in TL:
        if cam_.get("soft") and beat(19) < st_ < END:
            i0, i1 = ns(st_), ns(en_)
            f = min(ns(0.06), (i1 - i0) // 3)
            g = np.full(i1 - i0, 0.22, np.float32)
            g[:f] = np.linspace(1, 0.22, f); g[-f:] = np.linspace(0.22, 1, f)
            for m in (amb, ev):
                m.buf[i0:i1] *= g[:, None] if m.buf.ndim == 2 else g
            amb.add(paper_flutter(en_ - st_, int(st_ * 100)), st_, gain=0.35)
            amb.add(wind(en_ - st_, int(st_ * 101), strength=0.15), st_, gain=0.4)

    # hard cut at END: every battle sound stops dead
    for m in (amb, ev):
        m.buf[ns(END):] = 0.0

    # ======== 1930 again: only the wind and the field
    d1 = DUR - END
    wl, wr = wind(d1, 801, strength=0.12), wind(d1, 802, strength=0.12)
    amb.add_st(wl, wr, END, gain=0.35)
    amb.add(grass_rustle(d1, 803), END, gain=0.22)
    amb.add(birds(d1, 804, density=1.0, lo=3000, hi=5200), END + 0.6, gain=0.1, pan=0.4)
    ev.add(paper_crinkle(805, 0.25), 35.55, gain=0.3)                      # lands in the grass
    t = 35.8
    k = 0
    while t < 37.2:
        ev.add(hp(footstep("grass", 900 + k, heavy=0.5), 250), t, gain=0.3, pan=-0.4 + 0.4 * (t - 35.8) / 1.4)
        t += 0.18
        k += 1
    ev.add(paper_crinkle(806, 0.3), 37.95, gain=0.4)                       # picks it up
    ev.add(paper_crinkle(807, 0.4), 38.5, gain=0.35)                       # smooths the nose

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
