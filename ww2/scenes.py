"""Scene library. Every scene is draw(ctx, t, phase, fig) where
t      = seconds into the shot (for drifting smoke/snow/planes),
phase  = walk-cycle phase of the main figure,
fig    = dict(kind='civ'|'sol', run=0..1, charge=bool).
Layers are drawn back to front; the main figure is drawn by the scene so
foreground elements (snow, sparks, rubble) can go on top of it.
"""
import math, random
from lib import *


def main_figure(ctx, phase, fig):
    figure(ctx, FIG_X, GY, FIG_H, phase, fig.get("kind", "civ"), run=fig.get("run", 0.0),
           charge=fig.get("charge", False), suitcase=fig.get("suitcase", True))


def snowfall(ctx, t, seed, n=260, c="#ffffff", big=True):
    rnd = random.Random(seed)
    for _ in range(n):
        x0, y0 = rnd.uniform(0, W), rnd.uniform(0, H)
        z = rnd.random()
        r = 1.2 + 3.2 * z
        x = (x0 - t * (40 + 90 * z)) % W
        y = (y0 + t * (50 + 120 * z)) % H
        circle(ctx, x, y, r, c, 0.55 + 0.4 * z)
    if big:
        for _ in range(10):
            x = (rnd.uniform(0, W) - t * 220) % W
            y = (rnd.uniform(0, H) + t * 260) % H
            glow(ctx, x, y, rnd.uniform(10, 18), c, 0.75)


def embers(ctx, t, seed, n=90, c="#ffcf7a"):
    rnd = random.Random(seed)
    for _ in range(n):
        x0, y0 = rnd.uniform(0, W), rnd.uniform(0, H)
        z = rnd.random()
        x = (x0 + t * (30 + 80 * z) + 12 * math.sin(t * 3 + x0)) % W
        y = (y0 - t * (60 + 140 * z)) % H
        circle(ctx, x, y, 1.0 + 2.2 * z, c, 0.5 + 0.5 * z)


# ============================================================ 1. Stalingrad snow
def stalingrad(ctx, t=0.0, phase=0.0, fig=None, intensity=0.0):
    fig = fig or {"kind": "civ"}
    vgrad(ctx, 0, 700, [(0, "#6f7c8a"), (0.6, "#aab4bc"), (1, "#dde2e3")])
    glow(ctx, 1460, 300, 260, "#f4f1e8", 0.45)
    circle(ctx, 1460, 300, 58, "#f1efe7", 0.9)
    # far city: ruins + the grain elevator
    skyline(ctx, 660, 50, 150, "#a4aeb6", seed=11, broken=0.8)
    ruined_block(ctx, 1180, 665, 110, 250, "#97a2ab", random.Random(3), windows=False, broken=0.9)
    for i in range(6):
        rect(ctx, 1188 + i * 17, 470, 12, 200, "#97a2ab")
    smoke_column(ctx, 400, 640, 380, 55, "#8e98a2", seed=4, a=0.55, lean=0.5)
    smoke_column(ctx, 1600, 640, 300, 45, "#8e98a2", seed=5, a=0.5, lean=0.6)
    # mid ruins with window holes
    rnd = random.Random(21)
    for x, w, h in ((-30, 230, 330), (230, 150, 210), (1010, 170, 260), (1700, 260, 360)):
        ruined_block(ctx, x, 720, w, h, "#5d6873", rnd, windows=True, broken=1.0)
    chimney(ctx, 1560, 720, 36, 330, "#5d6873", broken=True)
    chimney(ctx, 1625, 720, 30, 250, "#5d6873")
    # snowfield
    vgrad(ctx, 700, H, [(0, "#e3e8eb"), (1, "#c6d0d7")])
    ridge(ctx, 715, 10, "#d3dbe0", seed=7, freq=1.2)
    ridge(ctx, 760, 8, "#e8edf0", seed=8, freq=0.8)
    t34(ctx, 1380, 800, 330, "#2a3139", tilt=-0.06, snow="#eef2f4")
    czech_hedgehog(ctx, 330, 790, 90, "#39424b")
    czech_hedgehog(ctx, 470, 775, 60, "#4a545e")
    # footprints trailing behind the walker
    for i in range(1, 12):
        fx = FIG_X - 60 - i * 95
        ellipse(ctx, fx, GY + 14 + (i % 2) * 10, 16, 5, "#9aa7b2", 0.8)
    ellipse(ctx, FIG_X + 10, GY + 18, 90, 10, "#9aa7b2", 0.55)
    main_figure(ctx, phase, fig)
    czech_hedgehog(ctx, 1790, 1110, 300, "#12161a")
    snowfall(ctx, t, 99, n=260 + int(200 * intensity))


# ============================================================ 2. Berlin street
def brandenburg(ctx, cx, base, s, c):
    u = s
    rect(ctx, cx - 0.5 * u, base - 0.06 * u, u, 0.06 * u, c)
    for i in range(6):
        x = cx - 0.46 * u + i * 0.184 * u
        rect(ctx, x, base - 0.62 * u, 0.07 * u, 0.58 * u, c)
    rect(ctx, cx - 0.53 * u, base - 0.72 * u, 1.06 * u, 0.12 * u, c)
    rect(ctx, cx - 0.36 * u, base - 0.86 * u, 0.72 * u, 0.15 * u, c)
    rect(ctx, cx - 0.2 * u, base - 0.9 * u, 0.4 * u, 0.05 * u, c)
    # quadriga: four horses + chariot + figure with staff
    for i in range(4):
        hx0 = cx - 0.14 * u + i * 0.055 * u
        ellipse(ctx, hx0, base - 0.975 * u, 0.06 * u, 0.028 * u, c)
        fill_poly(ctx, [(hx0 + 0.04 * u, base - 0.99 * u), (hx0 + 0.08 * u, base - 1.05 * u),
                        (hx0 + 0.1 * u, base - 1.04 * u), (hx0 + 0.06 * u, base - 0.97 * u)], c)
        for lx in (-0.04, 0.04):
            line(ctx, [(hx0 + lx * u, base - 0.96 * u), (hx0 + lx * u + 0.01 * u, base - 0.905 * u)], c, 0.012 * u)
    fill_poly(ctx, [(cx - 0.22 * u, base - 0.9 * u), (cx - 0.2 * u, base - 1.0 * u), (cx - 0.14 * u, base - 1.0 * u),
                    (cx - 0.13 * u, base - 0.9 * u)], c)
    fill_poly(ctx, [(cx - 0.2 * u, base - 1.0 * u), (cx - 0.19 * u, base - 1.12 * u), (cx - 0.16 * u, base - 1.12 * u),
                    (cx - 0.15 * u, base - 1.0 * u)], c)
    line(ctx, [(cx - 0.21 * u, base - 1.02 * u), (cx - 0.2 * u, base - 1.24 * u)], c, 0.012 * u)
    # side wings
    rect(ctx, cx - 0.78 * u, base - 0.42 * u, 0.24 * u, 0.42 * u, c)
    rect(ctx, cx + 0.54 * u, base - 0.42 * u, 0.24 * u, 0.42 * u, c)


def reichstag(ctx, cx, base, s, c):
    u = s
    rect(ctx, cx - 0.5 * u, base - 0.3 * u, u, 0.3 * u, c)
    for dx in (-0.5, 0.38):
        rect(ctx, cx + dx * u, base - 0.4 * u, 0.12 * u, 0.4 * u, c)
    fill_poly(ctx, [(cx - 0.14 * u, base - 0.3 * u), (cx, base - 0.4 * u), (cx + 0.14 * u, base - 0.3 * u)], c)
    rect(ctx, cx - 0.14 * u, base - 0.44 * u, 0.28 * u, 0.1 * u, c)
    # bombed-out dome: only the steel ribs remain
    for i in range(7):
        a0 = math.pi + i / 6 * math.pi
        ctx.arc(cx, base - 0.44 * u, 0.2 * u, math.pi, 2 * math.pi)
    ctx.set_line_width(0.012 * u); src(ctx, c); ctx.stroke()
    for i in range(7):
        k = -1 + i / 3
        pts = [(cx + k * 0.2 * u * math.cos(a), base - 0.44 * u - 0.2 * u * math.sin(a) * math.sqrt(max(0, 1 - k * k)) - 0)
               for a in [j / 10 * math.pi / 2 for j in range(11)]]
        line(ctx, [(cx + 0.2 * u * k, base - 0.44 * u), (cx + 0.2 * u * k * 0.5, base - 0.44 * u - 0.2 * u * math.sqrt(max(0, 1 - k * k)) * 0.9), (cx, base - 0.64 * u)], c, 0.008 * u)


def berlin_house(ctx, x, base, w, h, c, lit, rnd, lit_c="#f0a35a"):
    rect(ctx, x, base - h, w, h, c)
    fill_poly(ctx, [(x - 6, base - h), (x + w * 0.1, base - h - 70), (x + w * 0.9, base - h - 70), (x + w + 6, base - h)], c)
    for k in range(int(w / 70)):
        rect(ctx, x + 30 + k * 70, base - h - 110, 18, 60, c)
    cols, rows = int(w / 55), int(h / 80)
    for i in range(cols):
        for j in range(rows):
            wx = x + 18 + i * (w - 36) / cols
            wy = base - h + 30 + j * 80
            if rnd.random() < lit:
                rect(ctx, wx, wy, 20, 36, lit_c, 0.9)


def berlin(ctx, t=0.0, phase=0.0, fig=None, intensity=0.0):
    fig = fig or {"kind": "civ"}
    vgrad(ctx, 0, 820, [(0, "#34353e"), (0.42, "#6e6560"), (0.78, "#c89468"), (1, "#f0bb80")])
    # searchlights
    for x0, ang in ((300, -0.35 + 0.05 * math.sin(t)), (1000, 0.25 + 0.06 * math.sin(t * 0.8 + 1)), (1650, -0.1)):
        L = 1400
        a1, a2 = ang - 0.035, ang + 0.035
        fill_poly(ctx, [(x0, 720), (x0 + L * math.sin(a1), 720 - L * math.cos(a1)),
                        (x0 + L * math.sin(a2), 720 - L * math.cos(a2))], "#fff3d6", 0.13)
    glow(ctx, 1500, 740, 520, "#ff9a4a", 0.35 + 0.3 * intensity)
    smoke_column(ctx, 1380, 700, 520, 70, "#7a655c", seed=31, a=0.6, lean=0.4)
    smoke_column(ctx, 520, 700, 420, 50, "#7a655c", seed=32, a=0.45, lean=0.5)
    reichstag(ctx, 1500, 720, 520, "#8a7468")
    skyline(ctx, 725, 40, 120, "#8e776a", seed=34, broken=0.9)
    brandenburg(ctx, 1110, 812, 440, "#3a3032")
    rnd = random.Random(40)
    berlin_house(ctx, -40, 820, 380, 420, "#2f2829", 0.12, rnd)
    berlin_house(ctx, 1620, 820, 360, 380, "#2f2829", 0.1, rnd)
    ruined_block(ctx, 330, 820, 160, 260, "#2f2829", rnd, windows=True, broken=1.0)
    # street: amber reflections so the legs stay readable
    vgrad(ctx, 808, H, [(0, "#9a7558"), (0.3, "#4a3a33"), (1, "#1c1616")])
    for y in range(826, H, 26):
        line(ctx, [(0, y), (W, y)], "#2a2020", 1.5, 0.5)
    # lamp posts
    for lx, s in ((560, 1.0), (1760, 1.15)):
        line(ctx, [(lx, GY + 10), (lx, GY - 330 * s)], "#1a1414", 10 * s)
        fill_poly(ctx, [(lx - 16 * s, GY - 330 * s), (lx - 22 * s, GY - 375 * s), (lx, GY - 390 * s),
                        (lx + 22 * s, GY - 375 * s), (lx + 16 * s, GY - 330 * s)], "#1a1414")
        rect(ctx, lx - 14 * s, GY - 60 * s, 28 * s, 70 * s, "#1a1414")
        glow(ctx, lx, GY - 360 * s, 50 * s, "#ffd9a0", 0.22)
    main_figure(ctx, phase, fig)
    # rubble foreground
    rnd = random.Random(44)
    for cx, cw in ((120, 360), (1700, 420)):
        pts = [(cx - cw / 2, H)]
        for i in range(12):
            pts.append((cx - cw / 2 + cw * i / 11, H - 40 - rnd.uniform(0, 110) * math.sin(math.pi * i / 11)))
        pts.append((cx + cw / 2, H))
        fill_poly(ctx, pts, "#0c0a0a")
    embers(ctx, t, 45, n=int(40 + 60 * intensity))


# ============================================================ 3. Japanese warship deck
def pagoda_mast(ctx, x, base, s, c):
    """Yamato-style pagoda tower with raked funnel behind it."""
    u = s
    # raked funnel (aft = left), leaning back
    fill_poly(ctx, [(x - 0.42 * u, base - 0.1 * u), (x - 0.5 * u, base - 0.44 * u), (x - 0.7 * u, base - 0.42 * u),
                    (x - 0.64 * u, base - 0.1 * u)], c)
    fill_poly(ctx, [(x - 0.49 * u, base - 0.45 * u), (x - 0.52 * u, base - 0.49 * u), (x - 0.72 * u, base - 0.46 * u),
                    (x - 0.71 * u, base - 0.425 * u)], c)
    # superstructure block
    fill_poly(ctx, [(x - 0.8 * u, base + 5), (x - 0.74 * u, base - 0.12 * u), (x + 0.24 * u, base - 0.12 * u),
                    (x + 0.32 * u, base + 5)], c)
    # tower core, tapering upward
    core = lambda y: 0.12 * u - 0.075 * u * (base - 0.12 * u - y) / (0.74 * u)
    fill_poly(ctx, [(x - core(base - 0.12 * u), base - 0.12 * u), (x - core(base - 0.86 * u), base - 0.86 * u),
                    (x + core(base - 0.86 * u), base - 0.86 * u), (x + core(base - 0.12 * u), base - 0.12 * u)], c)
    rnd = random.Random(7)
    y = base - 0.16 * u
    while y > base - 0.82 * u:
        w = 2 * core(y) + rnd.uniform(0.05, 0.14) * u
        hh = rnd.uniform(0.02, 0.04) * u
        off = rnd.uniform(-0.02, 0.03) * u
        fill_poly(ctx, [(x - w / 2 + off, y), (x - w / 2 + off - 0.01 * u, y - hh), (x + w / 2 + off + 0.02 * u, y - hh),
                        (x + w / 2 + off, y)], c)
        if rnd.random() < 0.5:   # searchlight / AA tubs hanging off the sides
            circle(ctx, x + (w / 2 + 0.015 * u) * rnd.choice((-1, 1)), y - hh / 2, 0.013 * u, c)
        y -= hh + rnd.uniform(0.035, 0.06) * u
    # rangefinder arms + top
    rect(ctx, x - 0.2 * u, base - 0.9 * u, 0.4 * u, 0.022 * u, c)
    ellipse(ctx, x - 0.2 * u, base - 0.889 * u, 0.02 * u, 0.02 * u, c)
    ellipse(ctx, x + 0.2 * u, base - 0.889 * u, 0.02 * u, 0.02 * u, c)
    rect(ctx, x - 0.045 * u, base - 0.97 * u, 0.09 * u, 0.08 * u, c)
    line(ctx, [(x, base - 0.97 * u), (x, base - 1.12 * u)], c, 0.01 * u)
    line(ctx, [(x - 0.08 * u, base - 1.05 * u), (x + 0.08 * u, base - 1.05 * u)], c, 0.006 * u)


def turret(ctx, x, base, s, c, elev=-0.18):
    u = s
    for dy in (-0.05, 0.0, 0.05):
        ctx.save(); ctx.translate(x + 0.25 * u, base - 0.2 * u + dy * u); ctx.rotate(elev)
        fill_poly(ctx, [(0, -0.024 * u), (1.1 * u, -0.016 * u), (1.1 * u, 0.016 * u), (0, 0.024 * u)], c)
        ctx.restore()
    fill_poly(ctx, [(x - 0.5 * u, base - 0.08 * u), (x - 0.42 * u, base - 0.3 * u), (x + 0.2 * u, base - 0.32 * u),
                    (x + 0.45 * u, base - 0.14 * u), (x + 0.48 * u, base - 0.08 * u)], c)
    rect(ctx, x - 0.4 * u, base - 0.1 * u, 0.8 * u, 0.1 * u, c)


def warship(ctx, t=0.0, phase=0.0, fig=None, intensity=0.0):
    fig = fig or {"kind": "sol"}
    vgrad(ctx, 0, 640, [(0, "#4a1820"), (0.45, "#b0433a"), (0.8, "#ec8c55"), (1, "#f6c27d")])
    circle(ctx, 1010, 585, 150, "#ffe0a8", 0.95)
    glow(ctx, 1010, 585, 420, "#ffcf8a", 0.35)
    # sea
    vgrad(ctx, 630, H, [(0, "#8e3a30"), (0.4, "#5a2226"), (1, "#2a1016")])
    rnd = random.Random(50)
    for i in range(46):
        y = 640 + (i / 46) ** 1.6 * 220
        w = rnd.uniform(40, 260) * (1 - i / 60)
        x = 1010 + rnd.uniform(-160, 160) * (1 + i / 30) + math.sin(t * 2 + i) * 6
        line(ctx, [(x - w / 2, y), (x + w / 2, y)], "#ffcf8a", 3, 0.75 * (1 - i / 50))
    # distant fleet
    for sx, ss in ((260, 0.9), (1560, 0.7), (1740, 0.55)):
        fill_poly(ctx, [(sx - 110 * ss, 632), (sx - 95 * ss, 640), (sx + 110 * ss, 640), (sx + 125 * ss, 628)], "#6a2a2c")
        rect(ctx, sx - 20 * ss, 596, 26 * ss, 34, "#6a2a2c")
        rect(ctx, sx - 50 * ss, 614, 24 * ss, 16, "#6a2a2c")
    # our ship
    pagoda_mast(ctx, 1330, 800, 660, "#30161a")
    turret(ctx, 1700, 812, 360, "#24101a", elev=-0.08)
    # railing
    for x in range(-20, W + 40, 90):
        line(ctx, [(x, 800), (x, 872)], "#1a0c10", 5)
    line(ctx, [(-20, 800), (W + 20, 800)], "#1a0c10", 5)
    line(ctx, [(-20, 836), (W + 20, 836)], "#1a0c10", 3)
    # AA gun on the left
    ctx.arc(190, 872, 70, math.pi, 2 * math.pi); src(ctx, "#1a0c10"); ctx.fill()
    for k in (-12, 0, 12):
        ctx.save(); ctx.translate(200, 820); ctx.rotate(-0.75)
        ctx.rectangle(0, k - 3, 200, 6); src(ctx, "#1a0c10"); ctx.fill(); ctx.restore()
    rect(ctx, 150, 790, 90, 40, "#1a0c10")
    # deck
    fill_poly(ctx, [(-10, 870), (W + 10, 862), (W + 10, H), (-10, H)], "#120709")
    for x in range(0, W, 140):
        line(ctx, [(x, 900), (x - 60, H)], "#1f0e11", 2)
    birds(ctx, 700, 260, 6, "#3a1418", seed=52, s=12)
    main_figure(ctx, phase, fig)


# ============================================================ 4. Trench charge (climax)
def trench(ctx, t=0.0, phase=0.0, fig=None, intensity=1.0):
    fig = fig or {"kind": "sol", "run": 1.0, "charge": True}
    vgrad(ctx, 0, 820, [(0, "#2a0f10"), (0.5, "#8a2e20"), (0.85, "#e0612f"), (1, "#ff9a45")])
    # smoke banks
    smoke_column(ctx, 300, 820, 700, 120, "#5a2016", seed=60, a=0.75, lean=0.35)
    smoke_column(ctx, 1500, 820, 760, 140, "#4a1a14", seed=61, a=0.8, lean=0.25)
    smoke_column(ctx, 950, 820, 420, 90, "#6a2618", seed=62, a=0.6, lean=0.5)
    explosion(ctx, 1320, 640, 70 + 25 * math.sin(t * 7), seed=63)
    rnd = random.Random(64)
    for _ in range(40):   # flying debris
        a = rnd.uniform(-2.8, -0.3); d = rnd.uniform(60, 330)
        x, y = 1320 + math.cos(a) * d, 640 + math.sin(a) * d
        fill_poly(ctx, [(x, y), (x + rnd.uniform(4, 14), y + rnd.uniform(-6, 6)), (x + rnd.uniform(-4, 6), y + rnd.uniform(4, 12))], "#1a0806")
    # far no-man's land
    ridge(ctx, 780, 12, "#7a2a1e", seed=65, freq=1.3)
    for x, h in ((150, 180), (620, 140), (1780, 220), (1100, 110)):
        dead_tree(ctx, x, 790, h, "#5a1e16", seed=int(x), w=9)
    # tracers
    for i in range(7):
        y0 = rnd.uniform(420, 700); x0 = rnd.uniform(1200, 1900)
        L = rnd.uniform(120, 260)
        line(ctx, [(x0, y0), (x0 - L, y0 + L * 0.12)], "#ffe6a0", 2.5, 0.85)
    # far & mid charging soldiers
    for x, s, c, ph in ((1010, 150, "#6a2419", 0.1), (1230, 140, "#6a2419", 0.6), (1550, 170, "#6a2419", 0.35),
                        (1700, 150, "#6a2419", 0.85)):
        figure(ctx, x, 800, s, ph + t * 1.75, "sol", run=1.0, charge=True, c=c)
    ridge(ctx, 820, 8, "#4a1812", seed=66, freq=1.6)
    barbed_wire(ctx, -20, W + 20, 850, 70, "#2a0c0a", seed=67, w=2.5)
    for x, s, ph in ((360, 300, 0.45), (1180, 330, 0.2), (1500, 280, 0.7)):
        figure(ctx, x, 880, s, ph + t * 1.75, "sol", run=1.0, charge=True, c="#2a0c0a")
    # trench parapet (sandbags)
    fill_poly(ctx, [(-10, 872), (W + 10, 868), (W + 10, H), (-10, H)], "#0a0404")
    x = -30
    while x < W + 30:
        w = rnd.uniform(70, 100)
        ellipse(ctx, x + w / 2, 872 + rnd.uniform(-4, 4), w / 2 + 6, 22, "#0a0404")
        x += w
    main_figure(ctx, phase, fig)
    # soldier climbing out of the trench, bottom-left
    figure(ctx, 190, 1060, 470, 0.15 + t * 1.75, "sol", run=1.0, charge=True, c="#000000")
    fill_poly(ctx, [(-10, 960), (420, 975), (440, H), (-10, H)], "#000000")
    embers(ctx, t, 68, n=140, c="#ffc070")


# ============================================================ 5. Air battle
def airbattle(ctx, t=0.0, phase=0.0, fig=None, intensity=1.0):
    fig = fig or {"kind": "sol", "run": 0.0}
    vgrad(ctx, 0, 820, [(0, "#3a1830"), (0.4, "#a0413c"), (0.8, "#f08a4a"), (1, "#ffd27a")])
    # flat cloud bands
    for y, c, a, sd in ((520, "#ffb070", 0.5, 70), (430, "#d06a50", 0.55, 71), (300, "#8a3a44", 0.45, 72)):
        rnd = random.Random(sd)
        for _ in range(9):
            cx = (rnd.uniform(-200, W + 200) - t * 30) % (W + 400) - 200
            ellipse(ctx, cx, y + rnd.uniform(-30, 30), rnd.uniform(160, 360), rnd.uniform(18, 34), c, a)
    # bomber formation (far, upper right)
    for dx, dy in ((0, 0), (-80, -45), (-80, 45), (-160, -90), (-160, 90), (-240, 0)):
        bomber(ctx, 760 + dx + t * 40, 150 + dy, 90, "#5a2230", ang=0.0)
    # flak bursts around them
    rnd = random.Random(73)
    for _ in range(12):
        flak(ctx, rnd.uniform(380, 980), rnd.uniform(40, 300), rnd.uniform(12, 22), "#2a1018", seed=rnd.randint(0, 999), a=0.85)
    # burning fighter falling on the left
    fx, fy = 330 - t * 60, 470 + t * 90
    smoke_column(ctx, fx + 30, fy - 10, 330, 16, "#2a1018", seed=74, a=0.75, lean=-0.6)
    fighter(ctx, fx, fy, 120, "#1e0c14", ang=2.2, elliptical=False)
    glow(ctx, fx, fy, 45, "#ffb040", 0.8)
    # two fighters diving overhead, speed streaks trail behind the wingtips
    for (x, y, s_, ang) in ((1380 + t * 900, 260, 340, 0.2), (1080 + t * 900, 440, 230, 0.25)):
        d = (math.cos(ang), math.sin(ang)); n = (-d[1], d[0])
        for off in (-0.56, 0.56):
            p0 = (x + n[0] * off * s_ + d[0] * 0.1 * s_, y + n[1] * off * s_ + d[1] * 0.1 * s_)
            line(ctx, [p0, (p0[0] - d[0] * s_ * 1.6, p0[1] - d[1] * s_ * 1.6)], "#ffe8c0", 2, 0.45)
        fighter(ctx, x, y, s_, "#140810", ang=ang, elliptical=True)
        for k in (-0.3, 0.3):   # guns firing
            g0 = (x + n[0] * k * s_ + d[0] * 0.3 * s_, y + n[1] * k * s_ + d[1] * 0.3 * s_)
            line(ctx, [(g0[0] + d[0] * 60, g0[1] + d[1] * 60), (g0[0] + d[0] * 180, g0[1] + d[1] * 180)], "#fff0b0", 3, 0.9)
    # land
    ridge(ctx, 800, 18, "#8a3440", seed=75, freq=0.6)
    # bumpy treeline, a church steeple and a haystack
    rnd = random.Random(77)
    ctx.push_group()
    for x in range(-20, W + 40, 26):
        circle(ctx, x, 845 - 25 * math.sin(x * 0.011) - rnd.uniform(0, 22), rnd.uniform(24, 40), "#4a1a26")
    rect(ctx, -20, 840, W + 40, 60, "#4a1a26")
    fill_poly(ctx, [(1300, 840), (1300, 700), (1318, 640), (1336, 700), (1336, 840)], "#4a1a26")
    ctx.pop_group_to_source(); ctx.paint()
    for x in (260, 1560):
        ellipse(ctx, x, 850, 40, 30, "#3a1420")
    fill_poly(ctx, [(-10, 872), (W + 10, 866), (W + 10, H), (-10, H)], "#0b0508")
    rnd = random.Random(76)
    for x in range(-10, W + 10, 9):     # grass blades along the ground edge
        h = rnd.uniform(10, 38)
        line(ctx, [(x, 875), (x + rnd.uniform(-8, 8), 875 - h)], "#0b0508", 3)
    main_figure(ctx, phase, fig)


# ============================================================ 6. Ending: sunrise over ruins
def dawn(ctx, t=0.0, phase=0.0, fig=None, intensity=0.0):
    fig = fig or {"kind": "civ", "suitcase": True}
    vgrad(ctx, 0, 880, [(0, "#5e6f98"), (0.4, "#b89aae"), (0.68, "#f2c3a4"), (0.85, "#fde6bc"), (1, "#fde6bc")])
    circle(ctx, 1260, 760, 170, "#fff1cf", 0.95)
    glow(ctx, 1260, 720, 700, "#ffe2a8", 0.4)
    for i in range(12):   # soft sun rays
        a = -math.pi / 2 + (i - 5.5) * 0.16
        fill_poly(ctx, [(1260, 720), (1260 + 1600 * math.cos(a - 0.02), 720 + 1600 * math.sin(a - 0.02)),
                        (1260 + 1600 * math.cos(a + 0.02), 720 + 1600 * math.sin(a + 0.02))], "#fff4d8", 0.07)
    skyline(ctx, 800, 60, 220, "#c6a3a6", seed=80, broken=0.9, windows=True)
    smoke_column(ctx, 520, 740, 360, 26, "#c9aab0", seed=81, a=0.35, lean=0.7)
    rnd = random.Random(82)
    for x, w, h in ((-40, 280, 380), (260, 130, 200), (1560, 220, 300), (1780, 200, 420)):
        ruined_block(ctx, x, 880, w, h, "#6f5866", rnd, windows=True, broken=1.0)
    dead_tree(ctx, 1480, 875, 300, "#4a3a46", seed=83, w=12)
    fill_poly(ctx, [(-10, 872), (W + 10, 868), (W + 10, H), (-10, H)], "#0b0809")
    for _ in range(40):   # bricks
        x = rnd.uniform(0, W); y = rnd.uniform(865, 900)
        rect(ctx, x, y - 12, rnd.uniform(14, 30), 12, "#0b0809")
    # a small sprout in the rubble
    sx = 1180
    line(ctx, [(sx, 872), (sx + 4, 830), (sx + 2, 800)], "#0b0809", 5)
    ellipse(ctx, sx + 20, 812, 18, 8, "#0b0809", rot=-0.5)
    ellipse(ctx, sx - 14, 826, 15, 7, "#0b0809", rot=0.5)
    birds(ctx, 1100, 360, 7, "#5a4a5e", seed=84, s=13, spread=220)
    main_figure(ctx, phase, fig)


SCENES = {
    "stalingrad": stalingrad, "berlin": berlin, "warship": warship,
    "trench": trench, "airbattle": airbattle, "dawn": dawn,
}
