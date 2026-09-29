"""Environment + battle effects. Every function is deterministic in (seed, t) so it animates smoothly."""
import math, random
import cairo
import numpy as np
from lib import hx, src, fill_poly, rect, circle, ellipse, line, glow, W, H

TAU = 2 * math.pi


# ---------------------------------------------------------------- weather
def snow(ctx, t, seed, n=320, wind=60.0, c="#ffffff", big=12, blizzard=0.0):
    rnd = random.Random(seed)
    for _ in range(n):
        x0, y0, z = rnd.uniform(0, W), rnd.uniform(0, H), rnd.random()
        sway = 14 * math.sin(t * (1 + z) + x0)
        x = (x0 - t * (wind + 110 * z + 400 * blizzard) + sway) % W
        y = (y0 + t * (45 + 120 * z)) % H
        circle(ctx, x, y, 1.1 + 3.0 * z, c, 0.5 + 0.45 * z)
    for _ in range(big):
        x = (rnd.uniform(0, W) - t * (240 + 500 * blizzard)) % W
        y = (rnd.uniform(0, H) + t * 280) % H
        glow(ctx, x, y, rnd.uniform(9, 17), c, 0.8)
    if blizzard > 0:           # wind-driven drift streaks near the ground
        for _ in range(int(60 * blizzard)):
            x = (rnd.uniform(0, W) - t * 900) % W
            y = rnd.uniform(H * 0.55, H)
            line(ctx, [(x, y), (x + rnd.uniform(40, 120), y - 4)], c, 1.5, 0.35)


def rain(ctx, t, seed, n=260, angle=0.18, speed=1900, c="#dfe6ee", a=0.45, ground=None, length=34):
    rnd = random.Random(seed)
    dx, dy = math.sin(angle), math.cos(angle)
    for _ in range(n):
        x0, y0, z = rnd.uniform(-200, W + 200), rnd.uniform(0, H), rnd.random()
        L = length * (0.5 + z)
        y = (y0 + t * speed * (0.6 + 0.6 * z)) % (H + 100) - 50
        x = x0 - (y - y0) * dx / dy * 0.4
        line(ctx, [(x, y), (x - dx * L, y - dy * L)], c, 1 + 1.2 * z, a * (0.5 + 0.5 * z))
    if ground is not None:     # splashes
        for _ in range(40):
            x = rnd.uniform(0, W)
            ph = (t * 3 + rnd.random()) % 1
            if ph < 0.3:
                r = 3 + ph * 30
                ctx.save(); ctx.translate(x, ground + rnd.uniform(0, 60)); ctx.scale(1, 0.3)
                ctx.arc(0, 0, r, math.pi, TAU); ctx.restore()
                ctx.set_line_width(1.5); src(ctx, c, a * (1 - ph / 0.3)); ctx.stroke()


def dust(ctx, t, seed, n=160, c="#f4d9a0", y0=500, y1=H, speed=260, a=0.55):
    rnd = random.Random(seed)
    for _ in range(n):
        x0, yy, z = rnd.uniform(0, W), rnd.uniform(y0, y1), rnd.random()
        x = (x0 - t * speed * (0.5 + z)) % (W + 100) - 50
        y = yy + 10 * math.sin(t * 2 + x0)
        if z > 0.75:
            line(ctx, [(x, y), (x + 30 + 60 * z, y - 2)], c, 1.2, a * 0.5)
        else:
            circle(ctx, x, y, 1 + 2 * z, c, a * (0.4 + 0.6 * z))


def fog(ctx, y, h, c, a=0.5, t=0.0, drift=20.0, seed=0):
    """Soft horizontal fog band with drifting puffs."""
    g = cairo.LinearGradient(0, y - h, 0, y + h)
    cc = hx(c)
    g.add_color_stop_rgba(0, *cc, 0); g.add_color_stop_rgba(0.5, *cc, a); g.add_color_stop_rgba(1, *cc, 0)
    ctx.rectangle(0, y - h, W, 2 * h); ctx.set_source(g); ctx.fill()
    rnd = random.Random(seed)
    for _ in range(8):
        x = (rnd.uniform(0, W + 600) - t * drift) % (W + 600) - 300
        ellipse(ctx, x, y + rnd.uniform(-h * 0.3, h * 0.3), rnd.uniform(200, 420), h * rnd.uniform(0.25, 0.45), c, a * 0.45)


def haze(ctx, y0, y1, c, a):
    g = cairo.LinearGradient(0, y0, 0, y1)
    cc = hx(c)
    g.add_color_stop_rgba(0, *cc, 0); g.add_color_stop_rgba(1, *cc, a)
    ctx.rectangle(0, y0, W, y1 - y0); ctx.set_source(g); ctx.fill()


def sea_glints(ctx, t, seed, cx, y0, y1, spread, c, a=0.8, n=50):
    rnd = random.Random(seed)
    for i in range(n):
        f = (i / n) ** 1.5
        y = y0 + f * (y1 - y0)
        w = rnd.uniform(30, 200) * (1 - f * 0.5)
        x = cx + rnd.uniform(-spread, spread) * (1 + f * 2) + 8 * math.sin(t * 2.5 + i)
        flick = 0.6 + 0.4 * math.sin(t * 5 + i * 1.7)
        line(ctx, [(x - w / 2, y), (x + w / 2, y)], c, 2 + 2 * f, a * flick * (1 - f * 0.6))


def waves(ctx, t, y, c, a=0.6, amp=6, n=3, speed=60, wl=160):
    for k in range(n):
        yy = y + k * 22
        pts = [(x, yy + amp * math.sin((x + t * speed * (k + 1)) / wl * TAU + k)) for x in range(-20, W + 40, 16)]
        line(ctx, pts, c, 2, a * (1 - k / (n + 1)))


def spray(ctx, t, seed, y, c="#ffffff", n=60, a=0.7):
    rnd = random.Random(seed)
    for _ in range(n):
        x0 = rnd.uniform(0, W)
        ph = (t * rnd.uniform(0.6, 1.4) + rnd.random()) % 1
        x = x0 - ph * 80
        yy = y - math.sin(ph * math.pi) * rnd.uniform(30, 90)
        circle(ctx, x, yy, 1.5 + 2.5 * rnd.random(), c, a * (1 - ph))


def falling_leaves(ctx, t, seed, n=18, c="#000000"):
    rnd = random.Random(seed)
    for _ in range(n):
        x = (rnd.uniform(0, W) - t * 90) % W
        y = (rnd.uniform(0, H) + t * 70) % H
        ellipse(ctx, x, y, 6, 2.5, c, 0.8, rot=t * 3 + x)


# ---------------------------------------------------------------- fire & battle
def flames(ctx, x, base, w, h, t, seed, a=1.0):
    """Flickering layered flame tongues with glow."""
    rnd = random.Random(seed)
    glow(ctx, x, base - h * 0.4, max(w, h) * 1.6, "#ff8a30", 0.45 * a)
    for layer, (c, sh) in enumerate((("#d9431f", 1.0), ("#ff8f2e", 0.72), ("#ffd76a", 0.42))):
        n = max(3, int(w / 22))
        pts = [(x - w / 2, base)]
        for i in range(n + 1):
            fx = x - w / 2 + w * i / n
            env = max(0.0, math.sin(math.pi * i / n)) ** 0.8
            fl = 0.65 + 0.35 * math.sin(t * rnd.uniform(9, 15) + rnd.uniform(0, TAU))
            pts.append((fx + rnd.uniform(-4, 4), base - h * sh * env * fl * rnd.uniform(0.6, 1.0)))
            if i < n:
                pts.append((fx + w / n / 2, base - h * sh * env * 0.3))
        pts.append((x + w / 2, base))
        fill_poly(ctx, pts, c, a)


def embers(ctx, t, seed, n=90, c="#ffcf7a", x0=0, x1=W, rise=110):
    rnd = random.Random(seed)
    for _ in range(n):
        xx, yy, z = rnd.uniform(x0, x1), rnd.uniform(0, H), rnd.random()
        x = (xx + t * (30 + 70 * z) + 14 * math.sin(t * 3 + xx)) % W
        y = (yy - t * (rise * 0.5 + rise * z)) % H
        circle(ctx, x, y, 0.9 + 2.2 * z, c, 0.45 + 0.55 * z * (0.6 + 0.4 * math.sin(t * 10 + xx)))


def ash(ctx, t, seed, n=80, c="#3a3030"):
    rnd = random.Random(seed)
    for _ in range(n):
        x = (rnd.uniform(0, W) + t * 40) % W
        y = (rnd.uniform(0, H) + t * 50 + 12 * math.sin(t * 2 + x)) % H
        rect(ctx, x, y, 3, 2, c, 0.6)


def smoke(ctx, x, base, h, width, c, seed, t=0.0, a=0.85, lean=0.25, rise=18.0):
    """Billowing smoke column as one merged flat shape, slowly rolling upward."""
    rnd = random.Random(seed)
    n = 16
    ctx.push_group()
    for i in range(n):
        tt = i / (n - 1)
        cx = x + lean * h * tt ** 1.4 + rnd.uniform(-12, 12) + 6 * math.sin(t + i)
        cy = base - h * tt - (t * rise) % (h / n)
        r = width * (0.35 + 0.9 * tt) * rnd.uniform(0.8, 1.15) * (1 + 0.04 * math.sin(t * 2 + i))
        circle(ctx, cx, cy, r, c)
        circle(ctx, cx + r * 0.5, cy + r * 0.2, r * 0.7, c)
    ctx.pop_group_to_source(); ctx.paint_with_alpha(a)


def steam(ctx, x, y, t, seed, c="#f2eee6", a=0.8, rate=1.0, drift=-120, n=9):
    rnd = random.Random(seed)
    ctx.push_group()
    for i in range(n):
        age = (t * rate + i / n) % 1.0
        px = x + drift * age + rnd.uniform(-10, 10)
        py = y - 260 * age ** 0.8
        r = 18 + 70 * age
        circle(ctx, px, py, r, c)
    ctx.pop_group_to_source(); ctx.paint_with_alpha(a)


def explosion(ctx, x, y, r, age, seed, dark="#2a0c08"):
    """Animated blast: age 0 = detonation, grows into a fireball then dark smoke."""
    rnd = random.Random(seed)
    if age < 0:
        return
    if age < 0.9:
        k = min(1.0, age / 0.12)
        fade = max(0.0, 1 - age / 0.9)
        glow(ctx, x, y, r * (2.5 + 2 * k), "#ff9a40", 0.6 * fade)
        n = 20
        pts = []
        for i in range(n):
            a_ = i / n * TAU
            rr = r * k * (1.0 if i % 2 == 0 else rnd.uniform(0.5, 0.75)) * rnd.uniform(0.85, 1.25)
            pts.append((x + math.cos(a_) * rr, y + math.sin(a_) * rr * 0.8))
        fill_poly(ctx, pts, "#ffb347", fade)
        glow(ctx, x, y, r * 0.9 * k, "#fff3cf", fade)
    # smoke mushroom
    sa = min(1.0, age / 0.25)
    ctx.push_group()
    for i in range(9):
        a_ = rnd.uniform(0, TAU)
        d = r * (0.3 + age * 1.2) * rnd.uniform(0.3, 1.0)
        circle(ctx, x + math.cos(a_) * d, y - age * r * 0.9 + math.sin(a_) * d * 0.6, r * (0.35 + age * 0.5), dark)
    ctx.pop_group_to_source(); ctx.paint_with_alpha(0.75 * sa * max(0.0, 1 - age / 3))
    # debris
    for i in range(22):
        a_ = rnd.uniform(-math.pi * 0.95, -math.pi * 0.05)
        v = rnd.uniform(0.6, 1.6) * r * 3
        px = x + math.cos(a_) * v * age
        py = y + math.sin(a_) * v * age + 900 * age * age
        if py < y + r:
            s = rnd.uniform(3, 9)
            fill_poly(ctx, [(px, py), (px + s, py + s * 0.3), (px + s * 0.2, py + s)], dark)


def tracers(ctx, t, seed, n=8, x0=W, y0=300, ang=math.pi + 0.12, spread=250, c="#ffe6a0", speed=2600):
    rnd = random.Random(seed)
    for _ in range(n):
        ph = (t * speed / 1400 + rnd.random()) % 1
        oy = rnd.uniform(-spread, spread)
        d = ph * 1600
        px, py = x0 + math.cos(ang) * d, y0 + oy + math.sin(ang) * d
        L = rnd.uniform(80, 180)
        line(ctx, [(px, py), (px - math.cos(ang) * L, py - math.sin(ang) * L)], c, 2.5, 0.9)
        glow(ctx, px, py, 10, c, 0.6)


def searchlights(ctx, t, beams, c="#fff3d6", a=0.12):
    for x0, y0, base_ang, sw, sp in beams:
        ang = base_ang + sw * math.sin(t * sp)
        L = 1600
        a1, a2 = ang - 0.03, ang + 0.03
        fill_poly(ctx, [(x0, y0), (x0 + L * math.sin(a1), y0 - L * math.cos(a1)), (x0 + L * math.sin(a2), y0 - L * math.cos(a2))], c, a)


def muzzle_flash(ctx, x, y, t, seed, s=30):
    rnd = random.Random(seed)
    if (t * 14 + rnd.random()) % 1 < 0.45:
        glow(ctx, x, y, s * 2, "#ffcf70", 0.8)
        fill_poly(ctx, [(x, y - s * 0.25), (x + s * 1.4, y), (x, y + s * 0.25)], "#fff0b0")


# ---------------------------------------------------------------- post effects (numpy)
def heat_shimmer(img, t, y0, y1, amp=2.5):
    out = img.copy()
    for y in range(int(y0), min(int(y1), H), 2):
        k = (y - y0) / max(1, (y1 - y0))
        s = int(round(amp * k * math.sin(y * 0.09 + t * 9)))
        if s:
            out[y:y + 2] = np.roll(img[y:y + 2], s, axis=1)
    return out
