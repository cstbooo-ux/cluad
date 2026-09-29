"""Sound-effects track that follows the video timeline (no music).

Stems (48 kHz stereo):
  ambience  - per-shot environment bed, hard-cut on the beat with the picture
  events    - explosions, gunfire, planes, splashes, whistles, risers/impacts, synced to the visuals
  footsteps - one step per beat (half-beat while running), surface depends on the scene
"""
import math
import numpy as np
from sfx import (SR, ns, _norm, lp, hp, bp, pink, brown, white, env, smooth_noise, rain, wind, fire, sea, crickets,
                 insects, birds, gull, crowd, siren, bell, engine_drone, steam_hiss, explosion, gunshot, machine_gun,
                 cannon, splash, flyby, dive_scream, tank, chuffs, whistle, flak_pop, whoosh, impact, tinnitus,
                 flare_hiss, footstep, Mix, reverb)

W = 1920
SURF = {"prologue": "grass", "paris": "wet", "station": "wood", "london": "hard", "berlin": "rubble",
        "stalingrad": "snow", "moscow": "snow", "warship": "metal", "carrier": "metal", "desert": "sand",
        "jungle": "mud", "normandy": "sand", "mountains": "gravel", "airfield": "grass", "trench": "mud",
        "airbattle": "grass", "dawn": "rubble"}

# x position of the scene's explosion (mirrors scenes.py) -> stereo pan
EXPL_X = {"paris": lambda v: 900 + 300 * (v % 3), "london": lambda v: 1200 + 250 * (v % 2),
          "berlin": lambda v: 1000 + 400 * (v % 2), "stalingrad": lambda v: 1150 + 300 * (v % 2),
          "moscow": lambda v: 1500 + 150 * (v % 2), "carrier": lambda v: 1600 + 200 * (v % 2),
          "desert": lambda v: 1250 + 150 * (v % 2), "jungle": lambda v: 1000 + 300 * (v % 2),
          "station": lambda v: 1200 + 400 * (v % 2), "airfield": lambda v: 1500 + 200 * (v % 2),
          "trench": lambda v: 1320 - 200 * (v % 2)}


def pan_of(x):
    return max(-0.9, min(0.9, (x / W * 2 - 1) * 0.8))


class Bed:
    def __init__(self, d, seed):
        self.d, self.seed = d, seed
        self.L = np.zeros(ns(d), np.float32)
        self.R = np.zeros(ns(d), np.float32)
        self.k = 0

    def add(self, fn, gain, width=1.0, **kw):
        self.k += 1
        s = self.seed * 97 + self.k * 13
        a = _norm(fn(self.d, s, **kw))[: len(self.L)]
        b = _norm(fn(self.d, s + 5000, **kw))[: len(self.L)]
        m = (a + b) / 2
        self.L[: len(a)] += (m + (a - m) * width) * gain
        self.R[: len(b)] += (m + (b - m) * width) * gain

    def mono(self, sig, gain, pan=0.0, t=0.0):
        sig = sig[: max(0, len(self.L) - ns(t))]
        a = (pan + 1) * math.pi / 4
        i = ns(t) if t > 0 else 0
        self.L[i:i + len(sig)] += sig * gain * math.cos(a)
        self.R[i:i + len(sig)] += sig * gain * math.sin(a)


def rumble(d, seed):
    return lp(brown(d, seed), 120) * (0.6 + 0.4 * smooth_noise(d, 2, seed + 1))


def sand_hiss(d, seed):
    return bp(pink(d, seed), 2000, 7500) * (0.4 + 0.6 * smooth_noise(d, 1.5, seed + 1))


def jungle_birds(d, seed):
    return birds(d, seed, density=0.8, lo=1100, hi=2600)


def shot_audio(scene, B, d, seed, var):
    """Returns (bed, events) where events = [(t, signal, gain, pan)] relative to shot start."""
    bed = Bed(d, seed)
    ev = []
    if not B:
        if scene == "prologue":
            bed.add(wind, 0.25, strength=0.15); bed.add(birds, 0.3); bed.add(crickets, 0.18)
        elif scene == "paris":
            bed.add(rain, 0.55, heavy=0.6); bed.add(wind, 0.12, strength=0.2)
            ev.append((0.9, explosion(seed, size=1.6, dist=1.0), 0.45, -0.4))            # distant thunder
        elif scene == "station":
            bed.add(crowd, 0.4); bed.add(steam_hiss, 0.12)
            bed.mono(_norm(chuffs(d, seed, rate=2.6)), 0.45, pan=0.45)
            ev.append((0.25, whistle(1.3, seed), 0.4, 0.5))
        elif scene == "london":
            bed.add(siren, 0.35, width=0.3); bed.add(engine_drone, 0.3, freqs=(48, 50, 53, 55)); bed.add(wind, 0.18)
            bed.add(sea, 0.1, big=0.1)
        elif scene == "berlin":
            bed.add(wind, 0.22); bed.add(fire, 0.16, size=0.4)
            ev += [(0.15, explosion(seed, 1.2, dist=0.9), 0.5, 0.5), (0.7, explosion(seed + 1, 1.0, dist=0.95), 0.4, -0.3)]
        elif scene == "stalingrad":
            bed.add(wind, 0.55, strength=0.7, howl=0.7)
            ev.append((0.45, machine_gun(0.6, seed, rate=11, dist=0.8), 0.25, 0.6))
        elif scene == "moscow":
            bed.add(wind, 0.5, strength=0.6, howl=0.5)
            ev.append((0.05, bell(seed, f0=174.6, d=3.0), 0.35, 0.4))
        elif scene == "warship":
            bed.add(sea, 0.5); bed.add(wind, 0.22); bed.add(engine_drone, 0.18, freqs=(38, 39.5))
            ev.append((0.3, gull(seed), 0.3, -0.5))
        elif scene == "desert":
            bed.add(wind, 0.4, strength=0.6); bed.add(sand_hiss, 0.25); bed.add(tank, 0.1, width=0.2)
        elif scene == "jungle":
            bed.add(rain, 0.6, heavy=0.95); bed.add(insects, 0.28); bed.add(jungle_birds, 0.2)
        elif scene == "carrier":
            bed.add(wind, 0.45, strength=0.8); bed.add(sea, 0.28)
            ev.append((0.0, flyby(d + 0.6, seed, f0=86, pass_t=d * 0.55, doppler=0.1), 0.6, 0.4))
        elif scene == "mountains":
            bed.add(wind, 0.2); bed.add(birds, 0.32); bed.add(tank, 0.08, width=0.2)
        elif scene == "normandy":
            bed.add(sea, 0.55, big=0.8); bed.add(wind, 0.28); bed.add(rain, 0.14, heavy=0.2)
            bed.add(engine_drone, 0.12, freqs=(60, 64))
            ev.append((0.5, gull(seed), 0.25, 0.6))
        elif scene == "airfield":
            bed.add(engine_drone, 0.4, freqs=(66, 68.5, 72, 75)); bed.add(wind, 0.22)
        elif scene == "trench":
            bed.add(rain, 0.28, heavy=0.2); bed.add(flare_hiss, 0.12); bed.add(wind, 0.15)
            ev.append((0.2, explosion(seed, 1.4, dist=0.9), 0.35, 0.6))
        elif scene == "dawn":
            bed.add(wind, 0.2, strength=0.1); bed.add(birds, 0.35)
            ev.append((0.9, bell(seed, f0=164.8, d=3.5), 0.3, 0.35))
        return bed, ev

    # ---------------- part B: battle
    bed.add(fire, 0.22, size=0.6); bed.add(rumble, 0.35)
    if scene in EXPL_X:
        ev.append((0.0, explosion(seed, size=1.0), 0.85, pan_of(EXPL_X[scene](var))))
    if scene == "paris":
        bed.add(tank, 0.3, width=0.2); ev.append((0.1, machine_gun(0.5, seed, rate=13), 0.3, 0.8))
    elif scene == "london":
        bed.add(siren, 0.3, width=0.3); bed.add(engine_drone, 0.35, freqs=(48, 50, 53, 55)); bed.add(fire, 0.3)
    elif scene == "berlin":
        bed.add(tank, 0.35, width=0.2); bed.add(fire, 0.3)
    elif scene == "stalingrad":
        bed.add(wind, 0.45, strength=0.8, howl=0.6); ev.append((0.15, machine_gun(0.45, seed, rate=12), 0.28, 0.5))
    elif scene == "moscow":
        bed.add(wind, 0.4, strength=0.8, howl=0.5); bed.add(tank, 0.45, width=0.3)
    elif scene == "warship":
        bed.add(sea, 0.35)
        ev.append((0.0, cannon(seed), 0.95, 0.85))
        ev.append((0.0, dive_scream(0.9, seed), 0.35, -0.4))
        ev.append((0.05, machine_gun(0.5, seed + 3, rate=6), 0.3, 0.5))
        for k in range(5):
            t = k * 0.13 - (var % 3) * 0.05
            if t >= 0:
                ev.append((t, splash(seed + k), 0.4, pan_of(250 + k * 360)))
    elif scene == "carrier":
        bed.add(sea, 0.3); bed.add(wind, 0.3)
        ev.append((0.0, dive_scream(0.8, seed), 0.4, 0.6)); ev.append((0.05, machine_gun(0.5, seed, rate=14), 0.3, 0.3))
    elif scene == "desert":
        bed.add(wind, 0.45, strength=0.8); bed.add(sand_hiss, 0.3); bed.add(tank, 0.4, width=0.3)
    elif scene == "jungle":
        bed.add(rain, 0.5, heavy=0.9); ev.append((0.08, machine_gun(0.5, seed, rate=12), 0.35, 0.8))
    elif scene == "normandy":
        bed.add(sea, 0.45, big=0.9)
        ev.append((0.0, machine_gun(0.55, seed, rate=14), 0.45, -0.7))
        for k in range(3):
            t = k * 0.18 - 0.05 * (var % 3)
            if t >= 0:
                ev.append((t, splash(seed + k), 0.5, pan_of(700 + k * 450)))
        ev.append((0.0, explosion(seed + 9, 0.8), 0.6, 0.2))
    elif scene == "station":
        bed.add(crowd, 0.2)
        ev.append((0.1, whistle(0.5, seed), 0.2, 0.5))
    elif scene == "mountains":
        for k in range(4):
            ev.append((k * 0.12, explosion(seed + k, 0.8, dist=0.5), 0.55, pan_of(1150 + k * 60)))
        ev.append((0.1, machine_gun(0.4, seed, rate=10, dist=0.3), 0.2, 0.8))
    elif scene == "airfield":
        bed.add(engine_drone, 0.55, freqs=(78, 81, 84, 88))
    elif scene == "trench":
        ev.append((0.0, machine_gun(0.55, seed, rate=14), 0.45, 0.8))
    elif scene == "airbattle":
        ev.append((0.0, flyby(1.0, seed, f0=110, pass_t=0.35), 0.65, 0.5))
        ev.append((0.1, flyby(1.0, seed + 1, f0=96, pass_t=0.55), 0.5, 0.2))
        ev.append((0.05, machine_gun(0.45, seed, rate=16), 0.35, 0.4))
        for k in range(4):
            ev.append((k * 0.11, flak_pop(seed + k), 0.3, pan_of(400 + k * 150)))
        ev.append((0.0, dive_scream(0.8, seed + 2)[::-1].copy(), 0.15, -0.6))
    return bed, ev


def build(SHOTS, VARS, BEAT, NB, DUR, beat_frame, FPS):
    amb, evt, stp = Mix(DUR), Mix(DUR), Mix(DUR)
    starts = [beat_frame(s[0]) / FPS for s in SHOTS] + [DUR]

    for i, (b0, nb, scene, B, fig) in enumerate(SHOTS):
        t0, t1 = starts[i], starts[i + 1]
        d = t1 - t0
        bed, ev = shot_audio(scene, B, d + 0.02, seed=1000 + i * 7, var=VARS[i])
        amb.add_st(bed.L, bed.R, t0, gain=1.0 if B else 1.4, dur=d + 0.01)
        for t, sig, g, p in ev:
            if t < d:
                evt.add(sig, t0 + t, gain=g, pan=p)
        if not B and 0 < i < len(SHOTS) - 1:          # soft thump that marks every calm cut
            evt.add(impact(i, size=0.4), t0, gain=0.14)

    # ---- footsteps: one per beat, two per beat while running
    def shot_of(t):
        for i in range(len(SHOTS)):
            if starts[i] <= t < starts[i + 1]:
                return i
        return len(SHOTS) - 1
    k = 0
    t = 0.0
    while t < DUR - 0.05:
        i = shot_of(t)
        fig = SHOTS[i][4]
        sol = fig["kind"] == "sol"
        run = fig.get("run", 0.0)
        heavy = 1.0 + 0.4 * run + 0.15 * sol
        stp.add(footstep(SURF[SHOTS[i][2]], 7000 + k, heavy=heavy, gear=sol), t, gain=1.25, pan=-0.22 + 0.08 * (k % 2))
        t += BEAT / 2 if run else BEAT
        # keep steps on the exact grid (avoid float drift)
        beats = t / BEAT
        t = round(beats * 2) / 2 * BEAT
        k += 1

    # ---- transitions
    b_start = 36 * BEAT
    evt.add(whoosh(4 * BEAT, 11, up=True), b_start - 4 * BEAT, gain=0.55, fade_out=4 * BEAT)
    tt = np.arange(ns(4 * BEAT)) / SR
    rise = np.sin(2 * math.pi * np.cumsum(80 * 2 ** (tt / (4 * BEAT) * 2.5)) / SR) * (tt / (4 * BEAT)) ** 2
    evt.add(rise.astype(np.float32), b_start - 4 * BEAT, gain=0.18, fade_out=4 * BEAT)
    evt.add(impact(12, size=1.6), b_start, gain=1.0)
    evt.add(explosion(13, size=1.6), b_start, gain=0.8, pan=0.1)
    for b in range(40, 68, 4):                          # bar downbeats in part B
        evt.add(impact(20 + b, size=0.8), b * BEAT, gain=0.5)
    for b in range(60, 68):                             # charge: off-beat shots + hits
        evt.add(gunshot(300 + b), (b + 0.5) * BEAT, gain=0.45, pan=0.5)
        evt.add(impact(400 + b, size=0.5), (b + 0.5) * BEAT, gain=0.28)
    o = 68 * BEAT
    evt.add(impact(500, size=1.2), o, gain=0.6)
    evt.add(tinnitus(3.0), o, gain=0.16)

    # ---- reverb on events + steps, muffle the outro (ears ringing after the battle)
    ev_buf = reverb(evt.buf, 1.3, wet=0.14)
    st_buf = reverb(stp.buf, 0.7, wet=0.1, seed=9)
    am_buf = amb.buf
    i0, i1 = ns(o), ns(o + 2.2)
    for buf in (am_buf, st_buf):
        seg = buf[i0:i1].copy()
        muff = np.stack([lp(seg[:, c], 500) for c in range(2)], 1)
        k_ = np.linspace(1, 0, len(seg), dtype=np.float32)[:, None] ** 1.5
        buf[i0:i1] = muff * k_ + seg * (1 - k_)

    # ---- fades matching the picture (fade-in 0.45 s, fade to black over the last beat)
    n = ns(DUR)
    fade = np.ones(n, np.float32)
    fi = ns(0.45); fade[:fi] = np.linspace(0, 1, fi)
    fo0 = ns(DUR - BEAT); fade[fo0:] = np.linspace(1, 0, n - fo0)
    stems = {}
    for name, buf in (("ambience", am_buf), ("events", ev_buf), ("footsteps", st_buf)):
        b = buf[:n] * fade[:, None]
        stems[name] = b
    return stems


def master(stems, peak=0.89, drive=1.4):
    mix = stems["ambience"] + stems["events"] + stems["footsteps"]
    g = peak / (np.max(np.abs(mix)) + 1e-9)
    out = np.tanh(mix * g * drive) / math.tanh(drive)
    out *= peak / (np.max(np.abs(out)) + 1e-9)
    scaled = {k: v * g for k, v in stems.items()}
    return out.astype(np.float32), scaled


def write_wav(path, x):
    import wave
    pcm = (np.clip(x, -1, 1) * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
