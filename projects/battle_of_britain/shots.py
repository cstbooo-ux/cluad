"""Shot library for 'Paper Plane' (Battle of Britain).

Every shot is  fn(ctx, u, T, **kw)
  u : 0..1 progress through the shot (drives camera moves / actions)
  T : absolute time in seconds (drives looping motion: clouds, props, flicker)
They only draw the picture; subtitles, flashes and grading are added by the compositor.
"""
import math, random
import cairo
from silhouette_kit.core import (W, H, hx, mix, src, poly, fill_poly, rect, circle, ellipse, line, vgrad, glow)
from silhouette_kit import landscape as L
from silhouette_kit import aircraft as A
from silhouette_kit import fx
from silhouette_kit.child import child, run_travel
from silhouette_kit.pilot import pilot_profile, spade_grip

TAU = 2 * math.pi

# ------------------------------------------------------------------ palettes
GOLD_SKY = [(0, "#9fb2bd"), (0.5, "#e6d6ad"), (0.85, "#f4d193"), (1, "#f7c784")]
RED_SKY = [(0, "#24080e"), (0.45, "#7e2220"), (0.8, "#cf5230"), (1, "#ec8440")]
KENT = dict(far="#c7b289", fields="#a08e60", hedge="#5f5838", oast="#7e6f50", near="#2b2717", fg="#15130c",
            oak="#231f14")
RED_LIGHT = "#ff6a44"


def lerp_stops(a, b, t):
    return [(sa, mix(ca, cb, t)) for (sa, ca), (_, cb) in zip(a, b)]


def sky(ctx, redness, y0=0, y1=H):
    stops = lerp_stops(GOLD_SKY, RED_SKY, max(0.0, min(1.0, redness)))
    g = cairo.LinearGradient(0, y0, 0, y1)
    for t, c in stops:
        g.add_color_stop_rgb(t, *(hx(c) if isinstance(c, str) else c))
    ctx.rectangle(0, 0, W, H); ctx.set_source(g); ctx.fill()


def sun(ctx, x, y, r, redness):
    c = mix("#fff4d6", "#ffb07a", redness)
    glow(ctx, x, y, r * 5, c, 0.35)
    circle(ctx, x, y, r, c, 0.95)


def ease(u):
    u = max(0.0, min(1.0, u))
    return u * u * (3 - 2 * u)


# ================================================================== 1930 · KENT
def kent_background(ctx, pan, T, redness=0.0, tilt=0.0, climb=0.0):
    """Countryside layers under one camera model.
    pan   : camera travel to the right (px at the near-ground layer)
    tilt  : camera pitching up (px) - moves EVERY layer down by the same amount (rotation, no parallax)
    climb : camera rising (px at the near-ground layer) - moves each layer down by climb * depth factor
    Each layer uses one depth factor f for both axes: offset = (-pan * f, tilt + climb * f)."""
    def layer(f):
        ctx.save(); ctx.translate(-pan * f, tilt + climb * f)
    sky(ctx, redness)
    # sun and clouds are very far away: they barely move while the fields fall away below (calm sky before the battle)
    sky_dy = tilt * 0.3 + climb * 0.04
    sun(ctx, 1500 - pan * 0.01, 300 + sky_dy, 70, redness)
    ctx.save(); ctx.translate(0, sky_dy)
    L.sky_clouds(ctx, T, L.tones_mix("gold", "red", redness), seed=5, scroll=pan * 0.04, speed=0.4,
                 density=1.0, haze=mix("#f4d193", HAZE, redness), horizon=560, scale=0.62)
    ctx.restore()
    layer(0.05)
    L.rolling_field(ctx, 640, 26, mix(KENT["far"], "#9a4a3a", redness), seed=1, freq=0.5)
    ctx.restore()
    layer(0.15)
    L.rolling_field(ctx, 700, 18, mix(KENT["fields"], "#7a3028", redness), seed=2, freq=0.8)
    L.oast_house(ctx, 1320, 712, 120, mix(KENT["oast"], "#5a2420", redness), cowl="#efe6d2", t=T)
    L.oast_house(ctx, 1470, 716, 95, mix(KENT["oast"], "#5a2420", redness), cowl="#efe6d2", t=T + 1)
    L.hedgerow(ctx, 742, -200, W + 600, mix(KENT["hedge"], "#4a1a18", redness), seed=3, h=30)
    ctx.restore()
    layer(0.35)
    L.rolling_field(ctx, 800, 14, mix("#6f6440", "#4a1c18", redness), seed=4, freq=1.0)
    L.field_stripes(ctx, 800, 900, "#3e3824", a=0.25)
    L.oak_tree(ctx, 420, 812, 380, mix(KENT["oak"], "#1a0a0a", redness), seed=7, t=T)
    L.hedgerow(ctx, 836, -200, W + 900, mix("#3e3a24", "#2a0e0c", redness), seed=6, h=24, trees=False)
    ctx.restore()


def kent_ground(ctx, pan, T, drop=0.0, hill=True):
    """Near ground the boy runs on, with the small hillock he throws from."""
    ctx.save(); ctx.translate(-pan, drop)
    pts = [(-300, H + 60), (-300, 900)]
    for xx in range(-300, W + 2200, 20):
        yy = 900 + 8 * math.sin(xx * 0.006)
        if hill:
            yy -= 120 * math.exp(-((xx - 1900) / 320) ** 2)          # the hillock
        pts.append((xx, yy))
    pts.append((W + 2200, H + 60))
    fill_poly(ctx, pts, KENT["near"])
    L.grass(ctx, 912, -300, W + 2200, 26, KENT["near"], seed=8, t=T, density=9)
    ctx.restore()


def ground_y(xw, hill=True):
    y = 900 + 8 * math.sin(xw * 0.006)
    if hill:
        y -= 120 * math.exp(-((xw - 1900) / 320) ** 2)
    return y


def shot_kent_run(ctx, u, T, boy_x=None, pan=0.0, phase=None):
    """0-~4.5 s: the boy runs left -> right holding the paper plane."""
    kent_background(ctx, pan, T)
    kent_ground(ctx, pan, T)
    xw = boy_x if boy_x is not None else -120 + u * 1500
    ph = T / 0.36 if phase is None else phase
    r = child(ctx, xw - pan, ground_y(xw) + 4, 250, ph, run=1.0)
    A.paper_plane(ctx, r["hand"][0] + 4, r["hand"][1] - 6, 58, pitch=0.25)
    L.grass(ctx, H - 40, -100, W + 100, 70, KENT["fg"], seed=9, t=T, density=12)


def shot_kent_throw(ctx, u, T, pan=700.0, k=None, fly=0.0):
    """Boy on the hillock throws; the plane leaves his hand at k = 0.5. fly: 0..1 plane flight after release."""
    kent_background(ctx, pan, T)
    kent_ground(ctx, pan, T)
    xw = 1880
    k = min(1.0, u * 1.2) if k is None else k
    r = child(ctx, xw - pan, ground_y(xw) + 4, 250, 0.0, throw=k)
    if k < 0.5:
        pose = (r["hand"][0], r["hand"][1] - 6, 58, 0.5)
    else:
        q = max((k - 0.5) / 0.5, fly)
        pose = (r["hand"][0] + q * 300, r["hand"][1] - 20 - q * 150, 58 + q * 40, 0.42)
    A.paper_plane(ctx, pose[0], pose[1], pose[2], pitch=pose[3])
    L.grass(ctx, H - 40, -100, W + 100, 70, KENT["fg"], seed=9, t=T, density=12)
    return pose


def shot_follow_plane(ctx, u, T, redness=0.0, tilt=0.0, climb=0.0, plane_xy=(820, 560), size=260, pitch=0.38,
                      pan=700.0, craft="paper"):
    """Camera rides with the paper plane: the camera pitches up and climbs, the fields fall away with proper
    parallax, the far cloud bank stays calm on the horizon, the sky turns from gold to red.
    craft='spitfire' draws the fighter in exactly the same pose (the transformation)."""
    kent_background(ctx, pan, T, redness=redness, tilt=tilt, climb=climb)
    kent_ground(ctx, pan, T, drop=tilt + climb)
    if tilt + climb < 600:                               # the boy, left behind on the hillock
        ctx.save(); ctx.translate(0, tilt + climb)
        child(ctx, 1880 - pan, ground_y(1880) + 4, 250, 0.0, throw=1.0)
        ctx.restore()
    x, y = plane_xy
    yy, pp = y + 6 * math.sin(T * 2.3), pitch + 0.03 * math.sin(T * 1.7)
    if craft == "paper":
        A.paper_plane(ctx, x, yy, size, pitch=pp)
    elif craft == "none":
        pass
    else:
        A.aircraft(ctx, "spitfire", x, yy, size, pitch=pp, prop_t=T, light=RED_LIGHT, light_amt=0.45)


# ================================================================== air traffic
HAZE = "#b3483a"
RED_TONES = L.CLOUD_TONES["red"]


def smoke_trail(ctx, pts, w0, w1, c, a=0.8, fire=False, T=0.0):
    """Continuous smoke ribbon. pts: newest first; it widens and billows along its length."""
    n = len(pts)
    if n < 2:
        return
    ctx.push_group()
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    src(ctx, c)
    for k in range(n - 1):
        q = k / (n - 1)
        wob = 1 + 0.25 * math.sin(k * 1.7 + T * 4)
        ctx.new_path(); ctx.move_to(*pts[k]); ctx.line_to(*pts[k + 1])
        ctx.set_line_width((w0 + (w1 - w0) * q) * 2 * wob); ctx.stroke()
    ctx.set_line_cap(cairo.LINE_CAP_BUTT)
    ctx.pop_group_to_source(); ctx.paint_with_alpha(a)
    if fire:
        fx.flames(ctx, pts[0][0], pts[0][1] + 8, 24, 30, T, seed=int(abs(pts[0][0])) % 97)


def streaming(ctx, T, xy, pitch, speed, nose, size, life=1.2, a=0.5, seed=0, fire=False, flip=False):
    """Smoke from the engine of a plane the camera is tracking: every puff stays in the air where it was emitted,
    so relative to the camera it streams backwards at the plane's airspeed, grows and fades.
    Returns the engine position (for flames)."""
    d = -1 if flip else 1
    dx, dy = d * math.cos(pitch), -math.sin(pitch)            # nose direction on screen (pitch = nose-up)
    ex, ey = xy[0] + dx * nose * 0.72, xy[1] + dy * nose * 0.72 + size * 0.02
    pos = lambda tau: (ex + (tau - T) * speed * dx, ey + (tau - T) * speed * dy)
    fx.trail_smoke(ctx, pos, T, life=life, dt=0.025, r0=size * 0.03, r1=size * 0.28, dark="#120505",
                   hot="#ffb048" if fire else None, fade_to="#8a3a30", a=a, rise=60, wind=(0, 0), seed=seed,
                   turbulence=size * 0.04)
    return ex, ey


def parachute(ctx, x, y, s, c, T):
    sw = 0.12 * math.sin(T * 1.3 + x)
    ctx.save(); ctx.translate(x, y); ctx.rotate(sw)
    ctx.new_path(); ctx.arc(0, 0, s, math.pi, 2 * math.pi); ctx.close_path(); src(ctx, c); ctx.fill()
    for k in (-1, -0.4, 0.4, 1):
        line(ctx, [(k * s, 0), (0, s * 1.5)], c, max(1, s * 0.04))
    circle(ctx, 0, s * 1.55, s * 0.12, c); line(ctx, [(0, s * 1.6), (0, s * 2.0)], c, max(1.5, s * 0.1))
    ctx.restore()


class Flyer:
    """One aircraft on a curved path, respawning every `period` seconds with fresh random parameters.

    Kinematics (screen space, y down): constant turn rate on top of a straight heading, plus gravity for planes that
    are going down. The nose always points along the velocity."""

    TYPES = {"spitfire": 1.0, "bf109": 1.08, "he111": 0.62}

    def __init__(self, seed, zmax, y_band):
        self.seed, self.zmax, self.y_band = seed, zmax, y_band
        r = random.Random(seed)
        self.period = r.uniform(3.2, 6.5)
        self.offset = r.uniform(0, self.period)

    def params(self, cycle):
        r = random.Random(self.seed * 7919 + cycle * 104729)
        z = (r.random() ** 1.3) * self.zmax
        kind = r.choices(["spitfire", "bf109", "he111"], [0.42, 0.42, 0.16 if z < 0.4 else 0.03])[0]
        right = r.random() < 0.5
        state = r.choices(["ok", "smoking", "burning", "glide"], [0.6, 0.15, 0.15, 0.10])[0]
        size = (70 + 330 * z) * (1.35 if kind == "he111" else 1.0)
        speed = (240 + 900 * z) * self.TYPES[kind] * r.uniform(0.7, 1.35)
        if state == "glide":
            speed *= 0.6
        h0 = r.uniform(-0.3, 0.3)
        if state == "glide":
            h0 = r.uniform(0.12, 0.22)
        if state in ("smoking", "burning"):
            h0 = r.uniform(-0.05, 0.25)
        turn = r.uniform(-0.35, 0.35) if state == "ok" else r.uniform(-0.12, 0.12)
        if not right:
            h0 = math.pi - h0
            turn = -turn
        g = {"ok": 0.0, "smoking": r.uniform(60, 120), "burning": r.uniform(220, 380), "glide": 0.0}[state] * (0.5 + z)
        margin = size * 0.8 + 60
        x0 = -margin if right else W + margin
        y0 = r.uniform(*self.y_band)
        if state in ("smoking", "burning"):
            y0 = r.uniform(self.y_band[0], (self.y_band[0] + self.y_band[1]) / 2)
        return dict(z=z, kind=kind, state=state, size=size, v=speed, h0=h0, w=turn, g=g, x0=x0, y0=y0,
                    chase=(state == "ok" and r.random() < 0.4), roll=r.uniform(4, 8), rs=r.random())

    def pos(self, P, a):
        if a < 0:
            return None
        v, h0, w = P["v"], P["h0"], P["w"]
        if abs(w) < 1e-3:
            x = P["x0"] + v * a * math.cos(h0)
            y = P["y0"] + v * a * math.sin(h0)
        else:
            x = P["x0"] + v / w * (math.sin(h0 + w * a) - math.sin(h0))
            y = P["y0"] - v / w * (math.cos(h0 + w * a) - math.cos(h0))
        return x, y + 0.5 * P["g"] * a * a

    def vel(self, P, a):
        h = P["h0"] + P["w"] * a
        return P["v"] * math.cos(h), P["v"] * math.sin(h) + P["g"] * a

    def at(self, T):
        c = math.floor((T + self.offset) / self.period)
        return c, (T + self.offset) - c * self.period


def air_traffic(ctx, T, seed=0, density=1.0, near=True, far=True, mid=True, y_band=(120, 900), ground=None,
                zmax=1.0):
    """Friendly and enemy aircraft on curved paths at several depths: dogfights, burning planes falling
    under gravity, forced landings, parachutes; plus big close fly-bys."""
    flyers = [Flyer(900 + seed * 131 + i, zmax, y_band) for i in range(int(14 * density))]
    draw = []
    for f in flyers:
        c, a = f.at(T)
        P = f.params(c)
        if (P["z"] < 0.35 and not far) or (P["z"] >= 0.35 and not mid):
            continue
        draw.append((P["z"], f, P, a))
    rnd = random.Random(900 + seed)
    chutes = [(rnd.uniform(0.2, 0.6), rnd.uniform(100, W - 100), rnd.uniform(150, 600), rnd.uniform(14, 30))
              for _ in range(int(3 * density))]
    for z, x, y0, sz in chutes:
        draw.append((z, "chute", (x, y0, sz), 0))
    draw.sort(key=lambda d: d[0])
    for z, f, P, a in draw:
        haze = 0.75 * (1 - z)
        if f == "chute":
            x, y0, sz = P
            parachute(ctx, x + 30 * math.sin(T * 0.4 + x), y0 + (T * 18) % 500, sz, mix("#1a0a0a", HAZE, haze), T)
            continue
        st = P["state"]
        p = f.pos(P, a)
        if ground and p[1] > ground:
            continue
        if st != "ok":
            nose = P["size"] * 0.42
            def emit(tau, P=P, f=f, c0=T - a):
                q = f.pos(P, tau - c0)
                if q is None:
                    return None
                vx, vy = f.vel(P, tau - c0)
                n = math.hypot(vx, vy) or 1
                return q[0] + vx / n * nose * 0.6, q[1] + vy / n * nose * 0.6       # engine, near the nose
            fx.trail_smoke(ctx, emit, T, life={"smoking": 1.3, "burning": 1.7, "glide": 0.9}[st],
                           dt=0.03, r0=P["size"] * 0.02, r1=P["size"] * {"smoking": 0.13, "burning": 0.2, "glide": 0.07}[st],
                           dark=mix("#120505", HAZE, haze * 0.7), hot="#ffb048" if st == "burning" else None,
                           fade_to=HAZE, a={"smoking": 0.35, "burning": 0.45, "glide": 0.22}[st] * (1 - haze * 0.5),
                           rise=25, wind=(-20, 0), seed=f.seed * 31 + int(P["x0"]))
        vx, vy = f.vel(P, a)
        flip = vx < 0
        pitch = -math.atan2(vy, abs(vx))
        bank = 0.08 * math.sin(T + P["rs"] * 6)
        if st == "burning":
            bank = 0.5 * math.sin(a * P["roll"])
        A.aircraft(ctx, P["kind"], p[0], p[1], P["size"], pitch=pitch, flip=flip, bank=bank,
                   prop_t=0 if st == "glide" else T, damage=0.0 if st == "ok" else 0.7, light=RED_LIGHT,
                   light_amt=0.4, haze=HAZE, haze_amt=haze)
        if st == "burning":
            nx, ny = vx / (math.hypot(vx, vy) or 1), vy / (math.hypot(vx, vy) or 1)
            fx.flames(ctx, p[0] + nx * P["size"] * 0.25, p[1] + ny * P["size"] * 0.25 + 6, P["size"] * 0.1,
                      P["size"] * 0.12, T, seed=int(P["x0"]) % 97, a=1 - haze * 0.6)
        if P["chase"]:                                     # a chaser 0.45 s behind on the same curved path
            q = f.pos(P, a - 0.45)
            if q is not None:
                cvx, cvy = f.vel(P, a - 0.45)
                other = "spitfire" if P["kind"] != "spitfire" else "bf109"
                cp = -math.atan2(cvy, abs(cvx))
                A.aircraft(ctx, other, q[0], q[1], P["size"] * 0.95, pitch=cp, flip=cvx < 0, prop_t=T,
                           light=RED_LIGHT, light_amt=0.4, haze=HAZE, haze_amt=haze)
                if (T * 2.5 + P["rs"]) % 1 < 0.45:          # short bursts toward the target
                    dx, dy = p[0] - q[0], p[1] - q[1]
                    for k in range(4):
                        ph = (T * 7 + k / 4) % 1
                        tx, ty = q[0] + dx * ph, q[1] + dy * ph
                        line(ctx, [(tx, ty), (tx + dx * 0.08, ty + dy * 0.08)], "#ffe6a0",
                             max(1.5, P["size"] * 0.012), 0.9 * (1 - haze))
    if near:
        # a big close pass every ~1.6 s, with speed streaks, flying where its nose points
        period = 1.6
        k = math.floor((T + seed * 0.37) / period)
        ph = ((T + seed * 0.37) / period) - k
        r2 = random.Random(k * 7919 + seed)
        dur = 0.32
        if ph < dur / period:
            q = ph * period / dur
            d = r2.choice((1, -1))
            kind = r2.choice(("spitfire", "bf109"))
            size = r2.uniform(900, 1300)
            climb = r2.uniform(-0.18, 0.18)
            y0 = r2.uniform(250, 800)
            travel = W + size * 1.4
            xx = (-size * 0.7 + q * travel) if d > 0 else (W + size * 0.7 - q * travel)
            yy = y0 - math.tan(climb) * (q - 0.5) * travel
            for j in range(6):
                sy = yy + (j - 2.5) * size * 0.05
                L_ = size * (0.7 + 0.2 * j)
                line(ctx, [(xx - d * size * 0.5, sy + math.tan(climb) * size * 0.5),
                           (xx - d * (size * 0.5 + L_), sy + math.tan(climb) * (size * 0.5 + L_))], "#ffd8b0", 3, 0.35)
            A.aircraft(ctx, kind, xx, yy, size, pitch=climb, flip=d < 0, prop_t=T, light=RED_LIGHT, light_amt=0.5)


# ================================================================== 1940 · BATTLE
def battle_sky(ctx, T, scroll=0.0, tilt=0.0, smoke=True, bombers=None, flak_n=10, seed=0, traffic=1.0, near=True,
               cloud_speed=1.0, zmax=0.55, traffic_alpha=1.0):
    ctx.save()
    if tilt:
        ctx.translate(W / 2, H / 2); ctx.rotate(tilt); ctx.scale(1.25, 1.25); ctx.translate(-W / 2, -H / 2)
    sky(ctx, 1.0)
    sun(ctx, 1450, 700, 60, 1.0)
    L.sky_clouds(ctx, T, RED_TONES, seed=31 + seed, scroll=scroll * 0.3, speed=cloud_speed, haze=HAZE, horizon=760)
    if smoke:
        fx.smoke(ctx, 300, 1100, 900, 60, "#2a0c0c", seed=33, t=T, a=0.55, lean=0.35)
        fx.smoke(ctx, 1650, 1100, 700, 45, "#2a0c0c", seed=34, t=T, a=0.45, lean=-0.2)
    rnd = random.Random(35 + seed)
    for _ in range(flak_n):
        from silhouette_kit.core import flak
        flak(ctx, rnd.uniform(0, W), rnd.uniform(80, 520), rnd.uniform(10, 22), "#1e0808", seed=rnd.randint(0, 999), a=0.7)
    if bombers:
        bx, by, s, n = bombers
        for i in range(n):
            A.aircraft(ctx, "he111", bx + (i % 3) * s * 0.9 - (i // 3) * s * 0.5 + T * 25,
                       by + (i % 3) * s * 0.18 + (i // 3) * s * 0.35, s, pitch=0.02, haze="#b3483a",
                       haze_amt=0.55, light=RED_LIGHT, light_amt=0.4)
    if traffic:
        ctx.push_group()
        air_traffic(ctx, T, seed=seed, density=traffic, near=False, zmax=zmax)
        ctx.pop_group_to_source(); ctx.paint_with_alpha(traffic_alpha)
    ctx.restore()
    if traffic and near:
        air_traffic(ctx, T, seed=seed, density=0, near=True, far=False, mid=False)


def shot_cut_spitfire(ctx, u, T, reveal=0.0, **follow):
    """One continuous shot from the transformation to the formation: same sky and clouds as the paper-plane ride.
    The paper plane is now a Spitfire; as `reveal` goes 0 -> 1 it levels off, the wingmen slide into formation
    and the battle (smoke columns, flak, bombers, distant dogfights) fades in in the SAME sky."""
    x, y = follow["plane_xy"]
    follow = dict(follow)
    follow["pitch"] = follow["pitch"] - 0.26 * ease(reveal)
    r = ease(reveal)
    # the follow background without the aircraft
    fp = dict(follow); fp["size"] = 0.0
    shot_follow_plane(ctx, 1.0, T, craft="none", **fp)
    if r > 0.001:
        ctx.push_group()                                        # the battle, far away in the same sky
        fx.smoke(ctx, 260, 1150, 900, 55, "#2a0c0c", seed=33, t=T, a=0.8, lean=0.35)
        fx.smoke(ctx, 1720, 1150, 760, 42, "#2a0c0c", seed=34, t=T, a=0.7, lean=-0.2)
        rnd = random.Random(35)
        from silhouette_kit.core import flak
        for _ in range(8):
            flak(ctx, rnd.uniform(0, W), rnd.uniform(60, 420), rnd.uniform(10, 20), "#1e0808", seed=rnd.randint(0, 999), a=0.7)
        for i in range(6):
            A.aircraft(ctx, "he111", 1250 + (i % 3) * 150 - (i // 3) * 90 + T * 25 - 400 * (1 - r),
                       120 + (i % 3) * 28 + (i // 3) * 60, 160, pitch=0.02, haze=HAZE, haze_amt=0.55,
                       light=RED_LIGHT, light_amt=0.4)
        air_traffic(ctx, T, seed=0, density=0.5, near=False, zmax=0.5)
        ctx.pop_group_to_source(); ctx.paint_with_alpha(r)
    size = follow["size"]
    yy, pp = y + 6 * math.sin(T * 2.3), follow["pitch"] + 0.03 * math.sin(T * 1.7)
    for i, (dx, dy, k) in enumerate(((-340, 130, 0.8), (-620, 250, 0.64))):     # wingmen sliding into formation
        if r > 0.001:
            wx = x + dx - 900 * (1 - r) ** 2
            A.aircraft(ctx, "spitfire", wx, yy + dy + 5 * math.sin(T * 2 + i), size * k, pitch=pp, prop_t=T + i,
                       light=RED_LIGHT, light_amt=0.45, haze=HAZE, haze_amt=0.1 * (i + 1))
    A.aircraft(ctx, "spitfire", x, yy, size, pitch=pp, prop_t=T, light=RED_LIGHT, light_amt=0.45)
    if 0.08 < u and reveal < 0.6:
        fx.tracers(ctx, T * 0.6 + u, 41, n=6, x0=W + 60, y0=380, ang=math.pi + 0.06, spread=60, speed=3000)


def shot_formation(ctx, u, T):
    """Pull back: our plane is one of a formation; bombers loom out of the clouds ahead. (1940 caption)
    Starts in the same pose as the transformation shot (climbing), then levels off."""
    pitch = 0.12 + 0.28 * (1 - ease(u * 2.2))
    ctx.push_group()
    battle_sky(ctx, T, scroll=u * 200, bombers=(1150 - u * 60, 300, 170, 6), traffic=0.6, near=False,
               traffic_alpha=ease((u - 0.1) / 0.4))
    ctx.pop_group_to_source(); ctx.paint()
    for i, (dx, dy, s) in enumerate(((0, 0, 190), (-230, 90, 150), (-420, 170, 120))):
        if i and u < 0.15:
            continue
        A.aircraft(ctx, "spitfire", 700 + dx + u * 60, 610 + dy + 5 * math.sin(T * 2 + i), s, pitch=pitch,
                   prop_t=T + i, light=RED_LIGHT, light_amt=0.45, haze="#b3483a", haze_amt=0.12 * i)


def shot_cockpit(ctx, u, T, jaw=1.0, look=0.0):
    """Close side view: helmet, goggles, a young face set hard. Clouds race past behind the canopy."""
    sky(ctx, 1.0)
    L.sky_clouds(ctx, T, RED_TONES, seed=51, speed=9.0, haze=HAZE, horizon=640)
    air_traffic(ctx, T, seed=5, density=0.45, near=False, zmax=0.6)
    shake = 3 * math.sin(T * 37)
    pilot_profile(ctx, 1000 + shake, 430, 400, nod=-0.05 + look, jaw=jaw, rim=RED_LIGHT, lens="#c85a3a")
    # canopy frame + armoured headrest + mirror
    c = "#0a0506"
    fill_poly(ctx, [(0, 0), (W, 0), (W, 90), (1500, 70), (400, 70), (0, 110)], c)          # canopy top rail
    line(ctx, [(1500, 70), (1780, 380), (1840, H)], c, 34)                                # windscreen frame
    fill_poly(ctx, [(1560, 40), (1700, 40), (1700, 110), (1560, 110)], c)                 # rear-view mirror
    fill_poly(ctx, [(0, 360), (330, 330), (380, 900), (0, 940)], c)                       # headrest armour
    fill_poly(ctx, [(0, 880), (W, 820), (W, H), (0, H)], c)                                # cockpit sill
    line(ctx, [(420, 70), (380, 830)], c, 22)                                              # canopy hoop


def shot_stick(ctx, u, T, squeeze=1.0):
    """Gloved hand tightening on the spade grip."""
    vgrad(ctx, 0, H, [(0, "#3a0c10"), (0.5, "#1a0808"), (1, "#070303")])
    # instrument panel shapes (dials) in shadow at the top
    for i, (x, y, r) in enumerate(((300, 120, 70), (480, 110, 60), (660, 125, 70), (1260, 120, 70), (1440, 115, 60),
                                   (1620, 125, 65))):
        circle(ctx, x, y, r, "#140606")
        ctx.new_path(); ctx.arc(x, y, r * 0.8, 0, TAU); ctx.set_line_width(3); src(ctx, "#5a1e18", 0.8); ctx.stroke()
        a = -2.2 + 0.6 * math.sin(T * (1 + i * 0.3) + i)
        line(ctx, [(x, y), (x + math.cos(a) * r * 0.7, y + math.sin(a) * r * 0.7)], "#c86040", 3, 0.8)
    glow(ctx, 960, 60, 700, "#ff5a30", 0.18)
    spade_grip(ctx, 900 + 4 * math.sin(T * 29), 560, 230, squeeze=squeeze, button="#c8a050", rim=RED_LIGHT)


def shot_wing_bank(ctx, u, T, bank=0.5):
    """Tilted wing filling the frame, the horizon rolling behind it."""
    battle_sky(ctx, T, tilt=-bank * 0.6, smoke=False, flak_n=6, seed=2)
    A.planform(ctx, "spitfire", 700, 780, 1500, heading=-0.25 - bank * 0.2, view="above",
               light=RED_LIGHT, light_amt=0.45)


def shot_gunsight(ctx, u, T, target_x=0.0):
    """Through the windscreen: reflector-sight ring with a 109 sliding across it."""
    battle_sky(ctx, T, tilt=0.12, smoke=False, flak_n=3, seed=5, traffic=0.3, near=False)
    tx = 960 + (target_x - 0.3 + u * 0.6) * 500
    A.tail_on(ctx, "bf109", tx, 520 + 20 * math.sin(T * 3), 360, roll=0.3 - u * 0.4, prop_t=T,
              light=RED_LIGHT, light_amt=0.4)
    # reflector sight: glowing ring + cross
    cx, cy = 960, 520
    c = "#ffb060"
    glow(ctx, cx, cy, 240, "#ff8040", 0.08)
    ctx.new_path(); ctx.arc(cx, cy, 200, 0, TAU); ctx.set_line_width(4); src(ctx, c, 0.85); ctx.stroke()
    for a0 in range(4):
        ang = a0 * math.pi / 2
        line(ctx, [(cx + math.cos(ang) * 40, cy + math.sin(ang) * 40), (cx + math.cos(ang) * 200, cy + math.sin(ang) * 200)],
             c, 3, 0.85)
    circle(ctx, cx, cy, 6, c, 0.9)
    # windscreen frame + armoured glass edge
    k = "#0a0506"
    fill_poly(ctx, [(0, 0), (380, 0), (240, H), (0, H)], k)
    fill_poly(ctx, [(W, 0), (1540, 0), (1680, H), (W, H)], k)
    fill_poly(ctx, [(0, 0), (W, 0), (W, 60), (0, 60)], k)
    fill_poly(ctx, [(0, 930), (W, 930), (W, H), (0, H)], k)
    rect(ctx, 880, 930, 160, -90, k)                                          # sight body


def shot_wing_guns(ctx, u, T, firing=True):
    """Close on the wing leading edge: the eight Brownings open up."""
    battle_sky(ctx, T, scroll=u * 300, smoke=False, flak_n=4, seed=7, traffic=0.5, near=False)
    ctx.save(); ctx.translate(-200, 380); ctx.rotate(-0.18)
    col = hx("#343a26")
    # wing seen from slightly above/behind: rounded leading edge, elliptical tip, aileron line
    top = [(0, 190), (900, 120), (1700, 80), (2050, 90), (2180, 150), (2150, 250), (1900, 330), (0, 700)]
    from silhouette_kit.figure import smooth_path as _sp
    _sp(ctx, top); src(ctx, "#3a3526"); ctx.fill()
    _sp(ctx, [(0, 190), (900, 120), (1700, 80), (2050, 90), (2180, 150), (2100, 130), (1700, 112), (900, 152),
              (0, 240)]); src(ctx, "#5a4a34"); ctx.fill()                                   # lit leading edge
    line(ctx, [(1300, 290), (1900, 250)], "#2a2618", 4)                                      # aileron hinge
    line(ctx, [(600, 200), (640, 520)], "#2e2a1c", 2, 0.6); line(ctx, [(1100, 160), (1140, 420)], "#2e2a1c", 2, 0.6)
    for i, (gx, gy) in enumerate(((700, 150), (820, 142), (1050, 128), (1150, 122))):
        rect(ctx, gx, gy - 8, 40, 16, "#111111")
        if firing and (T * 18 + i * 0.37) % 1 < 0.55:
            glow(ctx, gx + 60, gy, 60, "#ffc060", 0.9)
            fill_poly(ctx, [(gx + 40, gy - 14), (gx + 150, gy), (gx + 40, gy + 14)], "#fff0b0")
    # roundel on the wing top
    for rr, cc in ((70, "#b89a3a"), (60, "#2d3a66"), (40, "#cfcabb"), (20, "#8e2b25")):
        ellipse(ctx, 1500, 260, rr * 1.3, rr * 0.7, cc)
    ctx.restore()
    if firing:
        fx.tracers(ctx, T, 71, n=10, x0=900, y0=260, ang=-0.22, spread=40, speed=3600)


def shot_break_cloud(ctx, u, T):
    """The Spitfire punches out of the cloud top into open red sky."""
    battle_sky(ctx, T, smoke=True, flak_n=6, seed=9, near=False)
    k = ease(u * 1.3)
    A.aircraft(ctx, "spitfire", 560 + u * 800, 640 - k * 330, 340, pitch=0.42 - 0.2 * u, prop_t=T,
               light=RED_LIGHT, light_amt=0.45)
    # the cloud top it bursts out of drops away fast below
    for i in range(4):
        L.cumulus_rich(ctx, 250 + i * 430 - u * 700, 960 - i * 25 + k * 420, 820, RED_TONES, 80 + i, a=0.97, t=T)


def shot_chase(ctx, u, T, hit_wingman=0.0):
    """A 109 on the wingman's tail; tracer lines streak past the Spitfire's tail."""
    battle_sky(ctx, T, scroll=u * 400, smoke=True, flak_n=5, seed=11, traffic=0.6)
    A.aircraft(ctx, "spitfire", 1280 + u * 80, 520 + 20 * math.sin(T * 2), 300, pitch=0.06, bank=0.1, prop_t=T,
               light=RED_LIGHT, light_amt=0.45)
    A.aircraft(ctx, "bf109", 560 + u * 200, 580 + 15 * math.sin(T * 2.4), 280, pitch=0.02, prop_t=T,
               light=RED_LIGHT, light_amt=0.45)
    for k in range(6):
        ph = (T * 6 + k / 6) % 1
        x0 = 700 + u * 200 + ph * 800
        line(ctx, [(x0, 575 - ph * 60 + k * 3), (x0 + 90, 568 - ph * 60 + k * 3)], "#ffe6a0", 3, 0.9)


def shot_attack(ctx, u, T):
    """Our pilot dives in from the side; the 109 breaks off trailing smoke."""
    battle_sky(ctx, T, scroll=u * 300, smoke=True, flak_n=5, seed=13)
    bx, by, bp = 1100 + u * 250, 600 + u * 160, -0.25 - u * 0.3
    if u > 0.15:
        streaming(ctx, T, (bx, by), bp, 700, nose=280 * 0.4, size=280, life=1.2, a=0.5, seed=90, fire=u > 0.4)
    A.aircraft(ctx, "bf109", bx, by, 280, pitch=bp, prop_t=T, damage=u, light=RED_LIGHT, light_amt=0.45)
    A.aircraft(ctx, "spitfire", 380 + u * 380, 260 + u * 200, 330, pitch=-0.4, bank=-0.15, prop_t=T,
               light=RED_LIGHT, light_amt=0.45)
    fx.tracers(ctx, T, 93, n=8, x0=560 + u * 380, y0=360 + u * 200, ang=0.38, spread=20, speed=3000)


def shot_hit(ctx, u, T):
    """Tracers rake our own Spitfire: sparks, holes, a jolt."""
    battle_sky(ctx, T, scroll=u * 200, smoke=True, flak_n=6, seed=15, traffic=0.6, near=False)
    jolt = 14 * math.exp(-u * 6) * math.sin(T * 60)
    if u > 0.2:
        streaming(ctx, T, (960, 540), 0.05 + 0.1 * u, 900, nose=520 * 0.42, size=520, life=0.9,
                  a=0.35 * min(1, (u - 0.2) * 4), seed=91)
    A.aircraft(ctx, "spitfire", 960 + jolt, 540, 520, pitch=0.05 + 0.1 * u, prop_t=T, damage=min(1.0, u * 2),
               light=RED_LIGHT, light_amt=0.45)
    for k in range(9):
        ph = (T * 5 + k / 9) % 1
        x0 = -100 + ph * 1400
        line(ctx, [(x0, 420 + k * 18), (x0 + 120, 430 + k * 18)], "#ffe6a0", 3, 0.9)
    rnd = random.Random(int(T * 20))
    for _ in range(10):
        px, py = 900 + rnd.uniform(-200, 100), 540 + rnd.uniform(-40, 30)
        line(ctx, [(px, py), (px + rnd.uniform(-30, 30), py + rnd.uniform(-30, 30))], "#ffd070", 2, 0.9)


def shot_falling(ctx, u, T):
    """Wing torn, engine smoking; the tilted fields rush up - the countryside from the opening returns."""
    tilt = 0.35 + 0.1 * math.sin(T * 0.8)
    redness = 1.0 - 0.4 * u
    ctx.save()
    ctx.translate(W / 2, H / 2); ctx.rotate(tilt); ctx.scale(1.45, 1.45); ctx.translate(-W / 2, -H / 2)
    sky(ctx, redness)
    horizon = 520 - u * 380
    L.rolling_field(ctx, horizon, 20, mix(KENT["far"], "#8a3a30", redness), seed=1, freq=0.5)
    L.rolling_field(ctx, horizon + 80, 16, mix(KENT["fields"], "#6a2820", redness), seed=2, freq=0.8)
    L.oast_house(ctx, 1300, horizon + 92, 70 + u * 60, mix(KENT["oast"], "#4a1c18", redness), cowl="#e8dcc6", t=T)
    L.rolling_field(ctx, horizon + 150, 6, mix(KENT["hedge"], "#3a1414", redness), seed=3, freq=3.0)
    L.rolling_field(ctx, horizon + 175, 8, mix(KENT["fields"], "#5a2420", redness), seed=13, freq=0.9)
    L.rolling_field(ctx, horizon + 260, 12, mix("#6f6440", "#3a1614", redness), seed=4)
    L.field_stripes(ctx, horizon + 260, H + 300, "#3e3824", a=0.3)
    fx.smoke(ctx, 1650, horizon + 330, 320, 22, "#2a1210", seed=98, t=T, a=0.4, lean=0.3, rise=30)  # a wreck burning
    fx.flames(ctx, 1650, horizon + 330, 30, 30, T, seed=99)
    gx, gy = 1500 - u * 500, horizon + 120 + u * 80                                           # a 109 gliding in
    streaming(ctx, T, (gx, gy), -0.2, 260, nose=60, size=150, life=0.6, a=0.3, seed=92, flip=True)
    A.aircraft(ctx, "bf109", gx, gy, 150, pitch=-0.2, flip=True, prop_t=0, damage=0.6, light=RED_LIGHT,
               light_amt=0.3 * redness, haze=HAZE, haze_amt=0.25)
    ctx.restore()
    ang = -0.5 - 0.1 * u + 0.05 * math.sin(T * 2.1)
    x, y = 900 + 30 * math.sin(T * 3), 480 + 12 * math.sin(T * 1.7)
    ex, ey = streaming(ctx, T, (x, y), ang, 1100, nose=380 * 0.42, size=380, life=1.3, a=0.85, seed=95, fire=True)
    A.aircraft(ctx, "spitfire", x, y, 380, pitch=ang, bank=0.08 + 0.06 * math.sin(T * 5), prop_t=T * 0.4, damage=1.0,
               light=RED_LIGHT, light_amt=0.35 * redness)
    fx.flames(ctx, ex, ey + 12, 48, 64, T, seed=96)


def shot_tree(ctx, u, T):
    """Skimming low over the great oak - the same tree from the opening."""
    redness = 0.45
    kent_background(ctx, 900 + u * 900, T, redness=redness)
    px, py = 720 + u * 300, 250 + u * 90
    ex, ey = streaming(ctx, T, (px, py), -0.12, 1100, nose=360 * 0.42, size=360, life=1.3, a=0.85, seed=97, fire=True)
    A.aircraft(ctx, "spitfire", px, py, 360, pitch=-0.12, prop_t=T * 0.3, damage=1.0,
               light=RED_LIGHT, light_amt=0.25)
    fx.flames(ctx, ex, ey + 10, 44, 58, T, seed=98)
    L.oak_tree(ctx, 1500 - u * 1500, H + 150, 780, mix(KENT["oak"], "#140808", redness), seed=7, t=T, wind=3.0)


def shot_cockpit_fall(ctx, u, T):
    """Inside, still hauling on the stick; the ground fills the canopy."""
    shot_cockpit(ctx, u, T, jaw=1.0, look=0.08)
    rect(ctx, 0, 0, W, H, "#3a1a0a", 0.15 + 0.2 * u)


def shot_ending_grass(ctx, u, T, pick=0.0):
    """1930 again: the paper plane lies in the grass; the boy runs in, picks it up, straightens its nose
    and looks up at the sky.   pick: 0 plane alone .. 0.3 boy arrives .. 0.6 bent down .. 1 standing, looking up."""
    sky(ctx, 0.0)
    sun(ctx, 1500, 260, 80, 0.0)
    L.sky_clouds(ctx, T, L.CLOUD_TONES["gold"], seed=5, speed=0.3, density=0.5, haze="#f4d193", horizon=520,
                 scale=0.7)
    L.rolling_field(ctx, 640, 26, KENT["far"], seed=1, freq=0.5)
    L.oak_tree(ctx, 1500, 700, 330, mix(KENT["oak"], "#8a7a5a", 0.35), seed=7, t=T)
    L.rolling_field(ctx, 760, 18, KENT["fields"], seed=2, freq=0.8)
    L.grass(ctx, 900, -100, W + 100, 90, "#3a3420", seed=110, t=T, density=10)
    gy = 960
    px, py = 1000, gy - 14
    if pick < 0.05:                                  # the paper plane glides down into the grass
        q = ease(pick / 0.05)
        A.paper_plane(ctx, 300 + (px - 300) * q, 520 + (py - 520) * q ** 1.4, 170, pitch=0.12 - 0.18 * q)
    elif pick < 0.3:                                 # the plane alone in the grass, the boy running in
        A.paper_plane(ctx, px, py, 170, pitch=-0.06)
        if pick > 0.05:
            q = (pick - 0.05) / 0.25
            ph = q * 960 / run_travel(1.0, 520)            # phase from distance -> planted feet
            child(ctx, -100 + run_travel(ph, 520), gy, 520, ph, run=1.0)
    elif pick < 0.6:                                 # bending down
        q = ease((pick - 0.3) / 0.3)
        r = child(ctx, 860, gy, 520, 0.0, reach=q)
        A.paper_plane(ctx, px, py, 170, pitch=-0.06)
    else:                                            # standing up with it, looking up
        q = ease((pick - 0.6) / 0.25)
        r = child(ctx, 860, gy, 520, 0.0, reach=max(0.0, 1 - q * 1.2), hold=True, look_up=ease((pick - 0.75) / 0.25))
        A.paper_plane(ctx, r["hand"][0] + 10, r["hand"][1] - 10, 170, pitch=0.3 * q)
    L.grass(ctx, 1000, -100, W + 100, 60, "#1e1a10", seed=111, t=T, density=8)
