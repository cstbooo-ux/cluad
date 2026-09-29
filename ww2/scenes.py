"""Scene library.

Each scene is  fn(ctx, S)  where S is a Shot state:
  S.t      seconds since the shot started (drives weather, smoke, planes)
  S.phase  walk-cycle phase of the hero (continuous over the whole video)
  S.fig    dict(kind='civ'|'sol', run=0..1, charge=bool)
  S.B      0 = calm (part A), 1 = battle (part B)
  S.scroll pixels the ground has moved since the shot started (parallax)
  S.var    integer variant (moves explosions / planes between repeats)
  S.post   dict the scene can fill for post effects (e.g. heat shimmer)
Layers are painted back to front; the hero is painted by the scene so
weather and foreground can go on top of it.
"""
import math, random
import cairo
from contextlib import contextmanager
from lib import (W, H, GY, FIG_X, FIG_H, hx, mix, src, poly, fill_poly, rect, circle, ellipse, line, vgrad,
                 glow, ridge, skyline, ruined_block, chimney, czech_hedgehog, barbed_wire, dead_tree, birds, t34,
                 fighter, bomber, flak, figure)
import props as P
import fx

TAU = 2 * math.pi


@contextmanager
def lay(ctx, S, f):
    """Parallax layer: f = 0 static sky, 1 = moves with the ground."""
    ctx.save(); ctx.translate(-S.scroll * f, 0)
    try:
        yield
    finally:
        ctx.restore()


def contact_shadow(ctx, x, y, w, a=0.45):
    g = cairo.RadialGradient(0, 0, 0, 0, 0, 1)
    g.add_color_stop_rgba(0, 0, 0, 0, a); g.add_color_stop_rgba(0.6, 0, 0, 0, a * 0.5); g.add_color_stop_rgba(1, 0, 0, 0, 0)
    ctx.save(); ctx.translate(x, y); ctx.scale(w, w * 0.09)
    ctx.arc(0, 0, 1, 0, TAU); ctx.restore(); ctx.set_source(g); ctx.fill()


def hero(ctx, S):
    f = S.fig
    contact_shadow(ctx, FIG_X + 15, GY + 3, 120)
    figure(ctx, FIG_X, GY, FIG_H, S.phase, f.get("kind", "civ"), run=f.get("run", 0.0),
           charge=f.get("charge", False), suitcase=f.get("suitcase", True))
    foreground(ctx, S)


FGC = "#040304"


def foreground(ctx, S):
    """Closest parallax layer (moves 1.7x the ground) that sweeps across in front of the hero."""
    sc, B, t = S.scene, S.B, S.t
    c = FGC
    with lay(ctx, S, 1.7):
        if sc == "prologue":
            P.grass_clump(ctx, 140, H + 10, 340, c, 1, t)
            P.fence_post(ctx, 1200, H + 40, 440, c, span=520)
            P.grass_clump(ctx, 1800, H + 10, 380, c, 2, t)
        elif sc == "paris":
            P.street_lamp(ctx, 1220, H + 60, 1.9, c)
            P.bollard(ctx, 200, H + 30, 260, c)
        elif sc == "station":
            P.pillar(ctx, 1260, 300, 90, c)
            P.luggage(ctx, 170, H + 20, 340, c)
        elif sc == "london":
            ctx.save(); ctx.translate(-80, H + 20); ctx.scale(1.8, 1.8)
            P.sandbags(ctx, 0, 0, 380, 4, c); ctx.restore()
            P.street_lamp(ctx, 1340, H + 60, 1.9, c)
        elif sc == "berlin":
            P.rubble(ctx, 960, 1560, H + 40, 320, c, seed=201)
        elif sc == "stalingrad":
            P.fence_post(ctx, 1150, H + 40, 420, c, span=500)
        elif sc == "moscow":
            czech_hedgehog(ctx, 1260, H + 90, 480, c)
            P.boulder(ctx, 130, H + 40, 300, "#dfe6ea", 202)
        elif sc == "warship":
            P.bollard(ctx, 1170, H + 20, 280, c)
            P.rope_coil(ctx, 240, H + 10, 360, c)
        elif sc == "carrier":
            P.drum(ctx, 1170, H + 20, 250, c); P.drum(ctx, 1330, H + 20, 250, c)
            P.crate(ctx, 200, H + 20, 320, c)
        elif sc == "desert":
            P.jerrycan(ctx, 1150, H + 20, 230, c); P.jerrycan(ctx, 1320, H + 20, 230, c)
            P.boulder(ctx, 150, H + 40, 300, c, 203)
            P.grass_clump(ctx, 1840, H + 10, 300, c, 3, t)
        elif sc == "jungle":
            P.fern(ctx, 1180, H + 60, 560, c, t)
            P.fern(ctx, 80, H + 60, 480, c, t)
        elif sc == "normandy":
            czech_hedgehog(ctx, 1260, H + 120, 540, c)
            line(ctx, [(260, H + 40), (400, H - 330)], c, 26)
        elif sc == "mountains":
            P.boulder(ctx, 1200, H + 40, 280, c, 204)
            P.grass_clump(ctx, 180, H + 10, 360, c, 4, t)
        elif sc == "airfield":
            for k in range(3):
                P.drum(ctx, 1120 + k * 165, H + 20, 240, c)
            P.grass_clump(ctx, 1840, H + 10, 340, c, 5, t)
        elif sc == "trench":
            ctx.save(); ctx.translate(1300, H + 20); ctx.scale(1.8, 1.8)
            P.sandbags(ctx, 0, 0, 420, 3, c); ctx.restore()
            if not B:
                P.fence_post(ctx, 1060, H + 40, 420, c, span=460)
        elif sc == "airbattle":
            P.grass_clump(ctx, 180, H + 10, 360, c, 6, t)
            P.fence_post(ctx, 1180, H + 40, 420, c, span=500)
        elif sc == "dawn":
            P.rubble(ctx, 1500, 2100, H + 40, 230, c, seed=205)


def ground(ctx, S, c, y=GY, kind="plain", seed=0, detail_c=None):
    rect(ctx, -10, y, W + 20, H - y + 10, c)
    dc = detail_c or c
    if kind == "plain":
        off = S.scroll % 300
        for k in range(-1, 9):
            rr = random.Random(seed * 17 + (k + int(S.scroll // 300)) * 13)
            for _ in range(4):
                ellipse(ctx, k * 300 - off + rr.uniform(0, 300), y + rr.uniform(6, 60), rr.uniform(4, 12), rr.uniform(2, 4),
                        mix(c, "#ffffff", 0.06))
    if kind == "rubble":
        off = S.scroll % 400
        for k in range(-1, 7):
            x = k * 400 - off
            rr = random.Random(seed * 31 + (k + int(S.scroll // 400)) * 7)
            for _ in range(6):
                bx = x + rr.uniform(0, 400)
                ctx.save(); ctx.translate(bx, y + rr.uniform(-4, 6)); ctx.rotate(rr.uniform(-0.5, 0.5))
                rect(ctx, -10, -8, rr.uniform(14, 26), rr.uniform(7, 11), dc); ctx.restore()
    elif kind == "grass":
        for x in range(-20, W + 20, 8):
            xx = x - (S.scroll % 8)
            wx = xx + S.scroll
            hh = 12 + 18 * abs(math.sin(wx * 0.37)) + 10 * abs(math.sin(wx * 0.051))
            line(ctx, [(xx, y + 3), (xx + 3 * math.sin(wx * 0.2), y - hh)], dc, 2.5)
    elif kind == "cobble":
        for row in range(6):
            yy = y + 8 + row * 18 * (1 + row * 0.3)
            line(ctx, [(0, yy), (W, yy)], dc, 1.4, 0.5)
            step = 34 + row * 10
            o = (S.scroll * (1 + row * 0.12)) % step
            for x in range(-step, W + step, step):
                xx = x - o + (row % 2) * step / 2
                line(ctx, [(xx, yy), (xx, yy + 14 + row * 5)], dc, 1.2, 0.4)
    elif kind == "sleepers":
        for x in range(-80, W + 80, 60):
            rect(ctx, x - S.scroll % 60, y + 6, 36, 8, dc)
        line(ctx, [(0, y + 4), (W, y + 4)], dc, 4)


# ============================================================ 0. prologue: quiet countryside
def prologue(ctx, S):
    vgrad(ctx, 0, GY, [(0, "#2d3b5c"), (0.45, "#8c6a78"), (0.78, "#e39a6a"), (1, "#f6cf8c")])
    circle(ctx, 1320, 700, 90, "#ffe8b8", 0.95)
    glow(ctx, 1320, 700, 420, "#ffcf8a", 0.4)
    rnd = random.Random(1)
    for _ in range(5):
        ellipse(ctx, rnd.uniform(0, W), rnd.uniform(120, 420), rnd.uniform(180, 340), rnd.uniform(10, 22), "#f2b48a", 0.35)
    with lay(ctx, S, 0.08):
        ridge(ctx, 740, 22, "#8a5a66", seed=2, freq=0.5, x1=W + 300)
    with lay(ctx, S, 0.2):
        ridge(ctx, 790, 16, "#5e3e4c", seed=3, freq=0.8, x1=W + 400)
        P.windmill(ctx, 1560, 790, 170, "#5e3e4c", t=S.t)
        P.farmhouse(ctx, 330, 795, 120, "#4e3240", lit="#ffcf7a")
        P.leafy_tree(ctx, 520, 800, 150, "#4e3240", seed=4)
        P.leafy_tree(ctx, 1840, 800, 190, "#4e3240", seed=5)
    with lay(ctx, S, 0.55):
        ridge(ctx, 845, 8, "#3a2530", seed=6, freq=1.2, x1=W + 900)
        P.telegraph_poles(ctx, -200, W + 900, 860, 330, 520, "#2a1a22")
    ground(ctx, S, "#150d10", kind="grass")
    birds(ctx, 980 - S.t * 30, 330, 7, "#4a3040", seed=7, s=12, spread=200)
    hero(ctx, S)


# ============================================================ 1. Paris
def paris(ctx, S):
    B = S.B
    if B:
        vgrad(ctx, 0, GY, [(0, "#2a1414"), (0.5, "#8a3a26"), (0.85, "#e07a3a"), (1, "#f2a55a")])
    else:
        vgrad(ctx, 0, GY, [(0, "#161a2a"), (0.55, "#3d3d55"), (0.85, "#7a6a78"), (1, "#a08a8a")])
    with lay(ctx, S, 0.05):
        glow(ctx, 1380, 520, 420, "#b8a8c8" if not B else "#ff9050", 0.25)
        P.eiffel(ctx, 1380, 820, 720, "#6a6488" if not B else "#6a2a20")
        if B:
            fx.smoke(ctx, 1050, 780, 560, 70, "#4a1c14", seed=10 + S.var, t=S.t, a=0.75, lean=0.4)
    with lay(ctx, S, 0.3):
        rnd = random.Random(11)
        x = -60
        while x < W + 700:
            w = rnd.uniform(200, 290); h = rnd.uniform(330, 440)
            if not (1150 < x < 1600):
                P.facade(ctx, x, 850, w, h, "#24212e" if not B else "#2a120e", rnd, roof="mansard",
                         damage=(rnd.uniform(0.2, 0.8) if B else 0), lit=(0.25 if not B else 0.05),
                         lit_c="#f5b76a", holes=bool(B))
            x += w + rnd.uniform(0, 30)
        if B:
            P.sherman(ctx, 1450, 870, 330, "#140806", t=S.t)
            fx.flames(ctx, 360, 600, 140, 160, S.t, seed=12)
            fx.flames(ctx, 1820, 540, 160, 150, S.t, seed=13)
    rect(ctx, -10, 850, W + 20, H - 840, "#1b1822" if not B else "#1f0e0a")     # wet street
    with lay(ctx, S, 1.0):
        for lx in range(200, W + 900, 620):
            P.street_lamp(ctx, lx, GY + 6, 1.05, "#0e0c12", lit=None if B else "#ffd9a0", t=S.t)
            if not B:
                g = cairo.LinearGradient(0, 876, 0, H)
                g.add_color_stop_rgba(0, *hx("#ffd9a0"), 0.35); g.add_color_stop_rgba(1, *hx("#ffd9a0"), 0.0)
                ctx.new_path(); poly(ctx, [(lx - 10, 876), (lx + 10, 876), (lx + 26, H), (lx - 26, H)])
                ctx.set_source(g); ctx.fill()
        ax = 1100                                                              # cafe awning
        fill_poly(ctx, [(ax, 640), (ax + 260, 640), (ax + 290, 700), (ax - 30, 700)], "#0e0c12")
        for k in range(9):
            fill_poly(ctx, [(ax - 30 + k * 35, 700), (ax - 13 + k * 35, 722), (ax + 5 + k * 35, 700)], "#0e0c12")
        rect(ctx, ax - 20, 700, 8, 170, "#0e0c12")
        for tx in (ax + 40, ax + 180):
            rect(ctx, tx - 22, 800, 44, 6, "#0e0c12"); rect(ctx, tx - 3, 800, 6, 70, "#0e0c12")
    if B:
        fx.explosion(ctx, 900 + 300 * (S.var % 3), 760, 80, S.t, seed=14 + S.var)
    hero(ctx, S)
    if B:
        fx.embers(ctx, S.t, 15, n=110)
        fx.tracers(ctx, S.t, 16 + S.var, n=6, x0=W + 50, y0=560, spread=160)
    else:
        fx.rain(ctx, S.t, 17, n=300, ground=880)


# ============================================================ 2. London Blitz
def london(ctx, S):
    B = S.B
    vgrad(ctx, 0, GY, [(0, "#0c1022"), (0.55, "#26294a"), (0.85, "#5a4660" if not B else "#a0402a"),
                       (1, "#7a5a6a" if not B else "#ff8a3a")])
    fx.searchlights(ctx, S.t, [(260, 820, -0.25, 0.12, 0.7), (980, 820, 0.18, 0.1, 0.9), (1700, 820, -0.05, 0.14, 0.6)])
    with lay(ctx, S, 0.03):
        for bx, by, s in ((300, 250, 55), (820, 180, 40), (1500, 300, 50), (1850, 200, 36)):
            P.barrage_balloon(ctx, bx, by + 6 * math.sin(S.t + bx), s, "#3a3a52" if not B else "#4a2426", cable_to=bx + 30)
    if B:
        for k in range(3):
            P.bomber_side(ctx, 300 + k * 260 + S.t * 90, 150 + k * 40, 180, "#1a1020", ang=0.02)
    with lay(ctx, S, 0.08):
        P.dome_church(ctx, 520, 790, 190, "#3c3a58" if not B else "#4a2020")
        skyline(ctx, 800, 30, 110, "#3c3a58" if not B else "#4a2020", seed=20, x1=W + 300, broken=0.3 if not B else 0.9)
        if B:
            fx.smoke(ctx, 700, 780, 600, 80, "#2a1010", seed=21, t=S.t, a=0.8, lean=0.35)
            fx.smoke(ctx, 1600, 780, 520, 70, "#2a1010", seed=22, t=S.t, a=0.75, lean=0.3)
    with lay(ctx, S, 0.2):
        P.parliament(ctx, 820, 1520, 840, 150, "#22223a" if not B else "#200c0c")
        P.big_ben(ctx, 1620, 845, 640, "#22223a" if not B else "#200c0c", clock_c="#ffe7b0")
        if B:
            fx.flames(ctx, 1000, 700, 220, 120, S.t, seed=23)
            fx.flames(ctx, 1350, 700, 160, 100, S.t, seed=24)
    rect(ctx, -10, 840, W + 20, 40, "#15152a" if not B else "#170808")        # river + embankment
    fx.sea_glints(ctx, S.t, 25, 1600, 848, 866, 200, "#ffe7b0" if not B else "#ffb060", a=0.5, n=14)
    with lay(ctx, S, 1.0):
        rect(ctx, -10, GY - 40, W + 1200, 12, "#0b0b16")
        for x in range(0, W + 1200, 70):
            rect(ctx, x, GY - 40, 10, 44, "#0b0b16")
        for lx in range(420, W + 1200, 700):
            P.street_lamp(ctx, lx, GY + 4, 1.0, "#0b0b16")
    ground(ctx, S, "#0b0b16" if not B else "#0e0505", kind="cobble", detail_c="#20203a" if not B else "#2a0e0a")
    if B:
        fx.explosion(ctx, 1200 + 250 * (S.var % 2), 700, 90, S.t, seed=26 + S.var)
    hero(ctx, S)
    if B:
        fx.embers(ctx, S.t, 27, n=120)
        fx.ash(ctx, S.t, 28, n=60)
    else:
        fx.ash(ctx, S.t, 29, n=25, c="#8a8aa0")


# ============================================================ 3. Berlin
def brandenburg(ctx, cx, base, s, c):
    u = s
    rect(ctx, cx - 0.5 * u, base - 0.06 * u, u, 0.06 * u, c)
    for i in range(6):
        x = cx - 0.46 * u + i * 0.184 * u
        rect(ctx, x, base - 0.62 * u, 0.07 * u, 0.58 * u, c)
        rect(ctx, x - 0.01 * u, base - 0.07 * u, 0.09 * u, 0.02 * u, c)
        rect(ctx, x - 0.01 * u, base - 0.63 * u, 0.09 * u, 0.02 * u, c)
    rect(ctx, cx - 0.53 * u, base - 0.72 * u, 1.06 * u, 0.1 * u, c)
    rect(ctx, cx - 0.55 * u, base - 0.73 * u, 1.1 * u, 0.02 * u, c)
    rect(ctx, cx - 0.36 * u, base - 0.86 * u, 0.72 * u, 0.14 * u, c)
    for k in range(5):
        rect(ctx, cx - 0.36 * u + k * 0.18 * u - 0.01 * u, base - 0.88 * u, 0.02 * u, 0.02 * u, c)
    rect(ctx, cx - 0.2 * u, base - 0.9 * u, 0.4 * u, 0.05 * u, c)
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
    for side in (-1, 1):
        x0 = cx + side * 0.66 * u
        rect(ctx, x0 - 0.12 * u, base - 0.42 * u, 0.24 * u, 0.42 * u, c)
        rect(ctx, x0 - 0.13 * u, base - 0.44 * u, 0.26 * u, 0.03 * u, c)


def reichstag(ctx, cx, base, s, c):
    u = s
    rect(ctx, cx - 0.5 * u, base - 0.3 * u, u, 0.3 * u, c)
    for dx in (-0.5, 0.38):
        rect(ctx, cx + dx * u, base - 0.42 * u, 0.12 * u, 0.42 * u, c)
    fill_poly(ctx, [(cx - 0.14 * u, base - 0.3 * u), (cx, base - 0.4 * u), (cx + 0.14 * u, base - 0.3 * u)], c)
    rect(ctx, cx - 0.14 * u, base - 0.44 * u, 0.28 * u, 0.1 * u, c)
    ctx.new_path()
    ctx.arc(cx, base - 0.44 * u, 0.2 * u, math.pi, TAU)
    ctx.set_line_width(0.012 * u); src(ctx, c); ctx.stroke()
    for i in range(7):
        k = -1 + i / 3
        line(ctx, [(cx + 0.2 * u * k, base - 0.44 * u),
                   (cx + 0.1 * u * k, base - 0.44 * u - 0.18 * u * math.sqrt(max(0, 1 - k * k))), (cx, base - 0.64 * u)],
             c, 0.008 * u)


def berlin(ctx, S):
    B = S.B
    if B:
        vgrad(ctx, 0, GY, [(0, "#1a0c10"), (0.45, "#6a2420"), (0.8, "#d8602c"), (1, "#ff9a48")])
    else:
        vgrad(ctx, 0, GY, [(0, "#34353e"), (0.42, "#6e6560"), (0.78, "#c89468"), (1, "#f0bb80")])
    fx.searchlights(ctx, S.t, [(300, 760, -0.35, 0.05, 1.0), (1000, 760, 0.25, 0.06, 0.8), (1650, 760, -0.1, 0.05, 1.2)],
                    a=0.12 if not B else 0.08)
    glow(ctx, 1500, 760, 560, "#ff9a4a", 0.35 + 0.35 * B)
    with lay(ctx, S, 0.06):
        fx.smoke(ctx, 1380, 740, 560, 70, "#7a655c" if not B else "#3a1410", seed=31, t=S.t, a=0.6 + 0.2 * B, lean=0.4)
        fx.smoke(ctx, 520, 740, 460, 50, "#7a655c" if not B else "#3a1410", seed=32, t=S.t, a=0.45 + 0.3 * B, lean=0.5)
        reichstag(ctx, 1500, 760, 520, "#8a7468" if not B else "#5a2a22")
        skyline(ctx, 770, 40, 120, "#8e776a" if not B else "#5e2c22", seed=34, broken=0.9, x1=W + 300)
    with lay(ctx, S, 0.15):
        brandenburg(ctx, 1110, 830, 440, "#3a3032" if not B else "#2a1210")
    with lay(ctx, S, 0.35):
        rnd = random.Random(40)
        hc = "#2f2829" if not B else "#1c0c0a"
        P.facade(ctx, -40, 840, 380, 430, hc, rnd, roof="mansard", lit=0.12 * (1 - B), damage=0.3 + 0.5 * B)
        P.facade(ctx, 330, 840, 170, 280, hc, rnd, roof="flat", damage=1.0, lit=0)
        P.facade(ctx, 1640, 840, 380, 390, hc, rnd, roof="mansard", lit=0.1 * (1 - B), damage=0.2 + 0.6 * B)
        P.facade(ctx, 2080, 840, 300, 330, hc, rnd, roof="gable", lit=0.1 * (1 - B), damage=0.8)
        if B:
            fx.flames(ctx, 150, 480, 180, 150, S.t, seed=41)
            fx.flames(ctx, 1800, 520, 150, 130, S.t, seed=42)
            t34(ctx, 1380 - 20 * S.t, 858, 340, "#120606")
    vgrad(ctx, 836, H, [(0, "#9a7558" if not B else "#a0502a"), (0.3, "#4a3a33" if not B else "#3a160e"), (1, "#1c1616")])
    with lay(ctx, S, 1.0):
        for lx in (560, 1760, 2400):
            P.street_lamp(ctx, lx, GY + 8, 1.1, "#1a1414", lit="#ffd9a0" if not B else None, t=S.t)
        P.rubble(ctx, -60, 260, H - 40, 110, "#0c0a0a", seed=44)
        P.rubble(ctx, 1560, 2000, H - 30, 130, "#0c0a0a", seed=45)
    if B:
        fx.explosion(ctx, 1000 + 400 * (S.var % 2), 740, 90, S.t, seed=46 + S.var)
    hero(ctx, S)
    fx.embers(ctx, S.t, 47, n=int(40 + 110 * B))


# ============================================================ 4. Stalingrad
def stalingrad(ctx, S):
    B = S.B
    vgrad(ctx, 0, GY, [(0, "#6f7c8a" if not B else "#4a4a56"), (0.6, "#aab4bc" if not B else "#8a8088"),
                       (1, "#dde2e3" if not B else "#d0a890")])
    glow(ctx, 1460, 300, 260, "#f4f1e8", 0.45)
    circle(ctx, 1460, 300, 58, "#f1efe7", 0.9 - 0.4 * B)
    far = "#a4aeb6" if not B else "#8a8490"
    with lay(ctx, S, 0.05):
        skyline(ctx, 670, 50, 150, far, seed=11, broken=0.9, x1=W + 300)
        ruined_block(ctx, 1180, 675, 110, 250, "#97a2ab" if not B else "#7a7480", random.Random(3), windows=False, broken=0.9)
        for i in range(6):
            rect(ctx, 1188 + i * 17, 480, 12, 200, "#97a2ab" if not B else "#7a7480")
        fx.smoke(ctx, 400, 650, 380, 55, "#8e98a2" if not B else "#3a3438", seed=4, t=S.t, a=0.55 + 0.3 * B, lean=0.5)
        fx.smoke(ctx, 1600, 650, 300, 45, "#8e98a2" if not B else "#3a3438", seed=5, t=S.t, a=0.5 + 0.3 * B, lean=0.6)
    mid = "#5d6873" if not B else "#3e3a42"
    with lay(ctx, S, 0.3):
        rnd = random.Random(21)
        for x, w, h in ((-30, 230, 330), (230, 150, 210), (1010, 170, 260), (1700, 260, 360), (2150, 220, 300)):
            P.facade(ctx, x, 725, w, h, mid, rnd, roof="flat", damage=1.0, lit=0, chimneys=False)
        chimney(ctx, 1560, 725, 36, 330, mid, broken=True)
        chimney(ctx, 1625, 725, 30, 250, mid)
        if B:
            fx.flames(ctx, 1100, 560, 120, 120, S.t, seed=22)
    vgrad(ctx, 705, H, [(0, "#e3e8eb"), (1, "#c6d0d7")])
    with lay(ctx, S, 0.5):
        ridge(ctx, 720, 10, "#d3dbe0", seed=7, freq=1.2, x1=W + 900)
        t34(ctx, 1380, 800, 330, "#2a3139", tilt=-0.06, snow="#eef2f4")
        czech_hedgehog(ctx, 330, 795, 90, "#39424b")
        czech_hedgehog(ctx, 470, 780, 60, "#4a545e")
        if B:
            for x, s, ph in ((1000, 190, 0.2), (1180, 170, 0.7), (1620, 200, 0.45), (1850, 180, 0.9)):
                figure(ctx, x + S.t * 120, 800, s, ph + S.t * 1.75, "sol", run=1.0, charge=True, c="#3a424a")
    with lay(ctx, S, 1.0):
        ridge(ctx, 780, 8, "#e8edf0", seed=8, freq=0.8, x1=W + 1400)
        for i in range(1, 16):
            ellipse(ctx, FIG_X - 60 - i * 95 + S.scroll, GY + 14 + (i % 2) * 10, 16, 5, "#9aa7b2", 0.8)
    ellipse(ctx, FIG_X + 10, GY + 18, 90, 10, "#9aa7b2", 0.55)
    if B:
        fx.explosion(ctx, 1150 + 300 * (S.var % 2), 760, 85, S.t, seed=23 + S.var, dark="#3a3a40")
    hero(ctx, S)
    with lay(ctx, S, 1.6):
        czech_hedgehog(ctx, 1790, 1110, 300, "#12161a")
    fx.snow(ctx, S.t, 99, n=300 + 250 * B, blizzard=0.6 * B)


# ============================================================ 5. Moscow / Red Square
def moscow(ctx, S):
    B = S.B
    vgrad(ctx, 0, GY, [(0, "#4c5670"), (0.6, "#9aa2b4"), (1, "#d8d8dc" if not B else "#c8a8a0")])
    far = "#6a7082" if not B else "#5a4a52"
    with lay(ctx, S, 0.06):
        P.st_basil(ctx, 1380, 780, 300, far)
        for x, h in ((380, 420), (900, 360)):          # Kremlin towers with tent roofs
            rect(ctx, x - 40, 780 - h * 0.7, 80, h * 0.7, far)
            rect(ctx, x - 30, 780 - h * 0.85, 60, h * 0.16, far)
            fill_poly(ctx, [(x - 34, 780 - h * 0.85), (x, 780 - h * 1.12), (x + 34, 780 - h * 0.85)], far)
            line(ctx, [(x, 780 - h * 1.12), (x, 780 - h * 1.2)], far, 4)
        P.kremlin_wall(ctx, -40, W + 300, 790, 90, "#5a6072" if not B else "#4a3e46")
    vgrad(ctx, 790, H, [(0, "#e9edf0"), (1, "#cfd6dc")])
    with lay(ctx, S, 0.45):
        for k in range(10):
            czech_hedgehog(ctx, 100 + k * 260, 830, 70, "#3a414c")
        if B:
            for k in range(3):
                t34(ctx, 900 + k * 420 + S.t * 110, 860, 300, "#1c2026", snow="#e8eef2")
            fx.explosion(ctx, 1500 + 150 * (S.var % 2), 800, 70, S.t, seed=50 + S.var, dark="#3a3a40")
    with lay(ctx, S, 1.0):
        for k in range(10):
            ellipse(ctx, FIG_X - 70 - k * 95 + S.scroll, GY + 16 + (k % 2) * 9, 15, 5, "#a4afb8", 0.8)
    hero(ctx, S)
    fx.snow(ctx, S.t, 51, n=420 + 200 * B, blizzard=0.3 + 0.7 * B, big=18)


# ============================================================ 6. Japanese warship deck
def pagoda_mast(ctx, x, base, s, c):
    u = s
    fill_poly(ctx, [(x - 0.42 * u, base - 0.1 * u), (x - 0.5 * u, base - 0.44 * u), (x - 0.7 * u, base - 0.42 * u),
                    (x - 0.64 * u, base - 0.1 * u)], c)
    fill_poly(ctx, [(x - 0.49 * u, base - 0.45 * u), (x - 0.52 * u, base - 0.49 * u), (x - 0.72 * u, base - 0.46 * u),
                    (x - 0.71 * u, base - 0.425 * u)], c)
    fill_poly(ctx, [(x - 0.8 * u, base + 5), (x - 0.74 * u, base - 0.12 * u), (x + 0.24 * u, base - 0.12 * u),
                    (x + 0.32 * u, base + 5)], c)
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
        if rnd.random() < 0.5:
            circle(ctx, x + (w / 2 + 0.015 * u) * rnd.choice((-1, 1)), y - hh / 2, 0.013 * u, c)
        y -= hh + rnd.uniform(0.035, 0.06) * u
    rect(ctx, x - 0.2 * u, base - 0.9 * u, 0.4 * u, 0.022 * u, c)
    ellipse(ctx, x - 0.2 * u, base - 0.889 * u, 0.02 * u, 0.02 * u, c)
    ellipse(ctx, x + 0.2 * u, base - 0.889 * u, 0.02 * u, 0.02 * u, c)
    rect(ctx, x - 0.045 * u, base - 0.97 * u, 0.09 * u, 0.08 * u, c)
    line(ctx, [(x, base - 0.97 * u), (x, base - 1.12 * u)], c, 0.01 * u)
    line(ctx, [(x - 0.08 * u, base - 1.05 * u), (x + 0.08 * u, base - 1.05 * u)], c, 0.006 * u)


def turret(ctx, x, base, s, c, elev=-0.18, recoil=0.0):
    u = s
    for dy in (-0.05, 0.0, 0.05):
        ctx.save(); ctx.translate(x + 0.25 * u - recoil * 0.08 * u, base - 0.2 * u + dy * u); ctx.rotate(elev)
        fill_poly(ctx, [(0, -0.024 * u), (1.1 * u, -0.016 * u), (1.1 * u, 0.016 * u), (0, 0.024 * u)], c)
        ctx.restore()
    fill_poly(ctx, [(x - 0.5 * u, base - 0.08 * u), (x - 0.42 * u, base - 0.3 * u), (x + 0.2 * u, base - 0.32 * u),
                    (x + 0.45 * u, base - 0.14 * u), (x + 0.48 * u, base - 0.08 * u)], c)
    rect(ctx, x - 0.4 * u, base - 0.1 * u, 0.8 * u, 0.1 * u, c)


def warship(ctx, S):
    B = S.B
    vgrad(ctx, 0, 640, [(0, "#4a1820"), (0.45, "#b0433a"), (0.8, "#ec8c55"), (1, "#f6c27d")])
    circle(ctx, 1010, 585, 150, "#ffe0a8", 0.95)
    glow(ctx, 1010, 585, 420, "#ffcf8a", 0.35)
    vgrad(ctx, 630, H, [(0, "#8e3a30"), (0.4, "#5a2226"), (1, "#2a1016")])
    fx.sea_glints(ctx, S.t, 50, 1010, 640, 860, 160, "#ffcf8a")
    fx.waves(ctx, S.t, 700, "#7a2e2a", a=0.5, amp=4)
    with lay(ctx, S, 0.03):
        for sx, ss in ((260, 0.9), (1560, 0.7), (1740, 0.55)):
            fill_poly(ctx, [(sx - 110 * ss, 632), (sx - 95 * ss, 640), (sx + 110 * ss, 640), (sx + 125 * ss, 628)], "#6a2a2c")
            rect(ctx, sx - 20 * ss, 596, 26 * ss, 34, "#6a2a2c")
            rect(ctx, sx - 50 * ss, 614, 24 * ss, 16, "#6a2a2c")
    if B:
        for k in range(3):                               # dive bombers
            P.fighter_side(ctx, 300 + k * 380 + S.t * 500, 120 + k * 70 + S.t * 260, 150, "#2a0e12", ang=0.5, prop_t=S.t)
        for k in range(5):                               # water columns from near misses
            age = S.t + k * 0.13 - (S.var % 3) * 0.05
            if age > 0:
                water_column(ctx, 250 + k * 360, 640, age, "#f2d0b0", seed=k)
        fx.tracers(ctx, S.t, 52 + S.var, n=10, x0=1500, y0=620, ang=-math.pi / 2 - 0.5, spread=60)
        for k in range(7):
            flak(ctx, 300 + k * 230, 150 + 60 * math.sin(k * 2.1), 18, "#2a1016", seed=k + S.var, a=0.8)
    with lay(ctx, S, 0.25):
        pagoda_mast(ctx, 1330, 800, 660, "#30161a")
        turret(ctx, 1700, 812, 360, "#24101a", elev=-0.08 - 0.25 * B, recoil=B * max(0, 1 - S.t * 4))
        if B:
            fx.muzzle_flash(ctx, 2020, 610, S.t, 53, s=60)
            fx.smoke(ctx, 1200, 700, 480, 60, "#1e0a0c", seed=54, t=S.t, a=0.75, lean=-0.4)
    with lay(ctx, S, 1.0):
        for x in range(-20, W + 1200, 90):
            line(ctx, [(x, 800), (x, 872)], "#1a0c10", 5)
        line(ctx, [(-20, 800), (W + 1200, 800)], "#1a0c10", 5)
        line(ctx, [(-20, 836), (W + 1200, 836)], "#1a0c10", 3)
        ctx.new_path(); ctx.arc(190, 872, 70, math.pi, TAU); src(ctx, "#1a0c10"); ctx.fill()
        for k in (-12, 0, 12):
            ctx.save(); ctx.translate(200, 820); ctx.rotate(-0.75 - 0.2 * B * math.sin(S.t * 20))
            ctx.rectangle(0, k - 3, 200, 6); src(ctx, "#1a0c10"); ctx.fill(); ctx.restore()
        rect(ctx, 150, 790, 90, 40, "#1a0c10")
    fill_poly(ctx, [(-10, 870), (W + 10, 862), (W + 10, H), (-10, H)], "#120709")
    with lay(ctx, S, 1.0):
        for x in range(0, W + 1400, 140):
            line(ctx, [(x, 900), (x - 60, H)], "#1f0e11", 2)
    if not B:
        birds(ctx, 700 - S.t * 40, 260, 6, "#3a1418", seed=55, s=12)
    hero(ctx, S)
    fx.spray(ctx, S.t, 56, 870, c="#f2c8a0", n=30 + 40 * B, a=0.5)
    if B:
        fx.embers(ctx, S.t, 57, n=70)


def water_column(ctx, x, base, age, c, seed=0, hmax=280):
    """Geyser from a near miss: narrow stem, spray crown, falling droplets."""
    if age <= 0 or age > 1.6:
        return
    rnd = random.Random(seed)
    k = min(1.0, age * 3.5)
    fade = max(0.0, 1 - age / 1.6)
    h = hmax * k * (1 - 0.3 * max(0, age - 0.6))
    w = 18 + 30 * age
    pts = [(x - w, base)]
    for i in range(9):
        tt = i / 8
        pts.append((x - w * (1 + tt * 1.8) + rnd.uniform(-6, 6), base - h * tt))
    for i in range(7):
        a_ = math.pi + i / 6 * math.pi
        pts.append((x + math.cos(a_) * w * 2.8 * rnd.uniform(0.8, 1.2), base - h + math.sin(a_) * h * 0.18 * rnd.uniform(0.6, 1.3)))
    for i in range(8, -1, -1):
        tt = i / 8
        pts.append((x + w * (1 + tt * 1.8) + rnd.uniform(-6, 6), base - h * tt))
    pts.append((x + w, base))
    fill_poly(ctx, pts, c, 0.85 * fade)
    for _ in range(14):
        a_ = rnd.uniform(-2.6, -0.5)
        d = rnd.uniform(0.4, 1.0) * h * 0.7
        px = x + math.cos(a_) * d * 1.2
        py = base - h * 0.8 + math.sin(a_) * d * 0.4 + 500 * max(0, age - 0.3) ** 2
        circle(ctx, px, py, rnd.uniform(2, 5), c, 0.8 * fade)


# ============================================================ 7. Aircraft carrier
def carrier(ctx, S):
    B = S.B
    vgrad(ctx, 0, 660, [(0, "#3a5a80"), (0.6, "#8aaac0"), (1, "#e8e0c8")] if not B else
          [(0, "#2a2030"), (0.6, "#8a5048"), (1, "#f0a060")])
    for k in range(6):
        ellipse(ctx, (200 + k * 360 - S.t * 20) % (W + 400) - 200, 200 + 50 * (k % 3), 220, 26,
                "#f2f0e6" if not B else "#c88068", 0.55)
    vgrad(ctx, 650, H, [(0, "#4a6a84" if not B else "#5a3030"), (1, "#16202c" if not B else "#200c0c")])
    fx.waves(ctx, S.t, 690, "#dfe8ee" if not B else "#e0a080", a=0.35, amp=3, n=4, speed=100)
    shipc = "#1c2632" if not B else "#1c0c0c"
    with lay(ctx, S, 0.03):
        for sx in (300, 1650):
            fill_poly(ctx, [(sx - 90, 652), (sx + 100, 652), (sx + 110, 640), (sx - 100, 642)], "#34485a" if not B else "#4a2424")
            rect(ctx, sx - 10, 616, 24, 28, "#34485a" if not B else "#4a2424")
    with lay(ctx, S, 0.6):
        P.carrier_island(ctx, 1450, 866, 560, shipc)
        for px in (1860, 2140, 2420, 380):
            P.parked_plane(ctx, px, 866, 210, shipc)
        if B:
            fx.smoke(ctx, 1300, 800, 520, 70, "#150808", seed=60, t=S.t, a=0.8, lean=-0.5)
            fx.flames(ctx, 1320, 830, 180, 110, S.t, seed=61)
    if B:
        P.fighter_side(ctx, 1900 - S.t * 900, 300 + S.t * 180, 220, "#140606", ang=math.pi + 0.4, prop_t=S.t)
        fx.tracers(ctx, S.t, 62 + S.var, n=10, x0=1400, y0=820, ang=-math.pi / 2 + 0.35, spread=80)
        fx.explosion(ctx, 1600 + 200 * (S.var % 2), 790, 90, S.t, seed=63 + S.var)
    else:
        tt = S.t
        P.fighter_side(ctx, 900 + tt * 700, 790 - tt * tt * 120, 220, shipc, ang=-0.06 - tt * 0.12, prop_t=tt)
    ground(ctx, S, "#0c1118" if not B else "#0c0505", y=864)
    with lay(ctx, S, 1.0):
        for x in range(0, W + 1400, 200):
            rect(ctx, x, 880, 110, 5, "#e8e0c8" if not B else "#a06040", 0.55)
        for x in range(0, W + 1400, 36):                  # deck-edge gallery railing
            rect(ctx, x, 850, 3, 16, "#0c1118" if not B else "#0c0505")
        rect(ctx, -10, 850, W + 1420, 3, "#0c1118" if not B else "#0c0505")
    hero(ctx, S)
    fx.dust(ctx, S.t, 64, n=40, c="#ffffff" if not B else "#ffb070", y0=100, y1=H, speed=900, a=0.3)


# ============================================================ 8. North African desert
def desert(ctx, S):
    B = S.B
    vgrad(ctx, 0, GY, [(0, "#3e7fb8" if not B else "#8a5a3a"), (0.55, "#a8c8d8" if not B else "#d89a5a"),
                       (0.85, "#f4e0b0"), (1, "#fbeccc")])
    circle(ctx, 1500, 210, 80, "#fffbe8")
    glow(ctx, 1500, 210, 420, "#fff4c8", 0.55)
    with lay(ctx, S, 0.04):
        P.pyramid(ctx, 1250, 760, 560, 330, "#e0b87a", "#b88a56")
        P.pyramid(ctx, 1620, 760, 380, 220, "#d8b074", "#b08450")
        P.pyramid(ctx, 1010, 760, 240, 140, "#d8b074", "#b08450")
    with lay(ctx, S, 0.15):
        ridge(ctx, 770, 20, "#d9a864", seed=70, freq=0.6, x1=W + 600)
        for k in range(4):                             # column on the horizon
            (P.panzer if B else P.truck)(ctx, 200 + k * 180 + S.t * 20, 772, 120, "#8a6038")
        if B:
            fx.smoke(ctx, 520, 760, 300, 40, "#3a2410", seed=71, t=S.t, a=0.7, lean=0.6)
    with lay(ctx, S, 0.45):
        ridge(ctx, 820, 26, "#c48a48", seed=72, freq=0.9, x1=W + 1000)
        P.palm(ctx, 260, 830, 300, "#5a3a1c", seed=73, lean=0.2, t=S.t)
        P.palm(ctx, 380, 830, 230, "#5a3a1c", seed=74, lean=-0.25, t=S.t)
        if B:
            P.panzer(ctx, 1480, 860, 360, "#2a1808", t=S.t)
            P.sherman(ctx, 2100, 860, 320, "#2a1808", t=S.t)
            fx.explosion(ctx, 1250 + 150 * (S.var % 2), 800, 95, S.t, seed=75 + S.var, dark="#6a4424")
        else:
            P.panzer(ctx, 1560, 860, 340, "#6a4424")                   # abandoned wreck half in sand
            ridge(ctx, 866, 14, "#b07a3c", seed=76, freq=1.5, x0=1300, x1=1850)
    vgrad(ctx, GY - 4, H, [(0, "#9a6430"), (1, "#5a3414")])
    with lay(ctx, S, 1.0):
        for x in range(-40, W + 1400, 180):
            ellipse(ctx, x, GY + 40 + (x % 60), 60, 5, "#b07a40", 0.6)
    ellipse(ctx, FIG_X - 20, GY + 6, 110, 9, "#5a3414", 0.6)          # hard midday shadow
    hero(ctx, S)
    fx.dust(ctx, S.t, 77, n=180 + 220 * B, c="#f4d9a0", y0=420, speed=300 + 400 * B)
    S.post["heat"] = (560, 900)


# ============================================================ 9. Pacific jungle
def jungle(ctx, S):
    B = S.B
    vgrad(ctx, 0, GY, [(0, "#1e2a24" if not B else "#2a1410"), (0.6, "#4a6a58" if not B else "#8a4a2a"),
                       (1, "#9ab8a0" if not B else "#e08a40")])
    with lay(ctx, S, 0.05):
        ridge(ctx, 560, 60, "#5e7a68" if not B else "#7a3a22", seed=80, freq=0.4, x1=W + 400)
        fx.fog(ctx, 640, 90, "#b8cabc" if not B else "#e0a070", a=0.45, t=S.t, seed=81)
    pc = "#2e443a" if not B else "#3a1a10"
    with lay(ctx, S, 0.2):
        for k, x in enumerate(range(-100, W + 600, 150)):
            P.palm(ctx, x, 800, 260 + 60 * math.sin(k * 1.7), pc, seed=82 + k, lean=0.25 * math.sin(k * 2.3), t=S.t)
        rect(ctx, -10, 780, W + 900, 100, pc)
        if B:
            fx.flames(ctx, 1200, 800, 300, 200, S.t, seed=83)
            fx.smoke(ctx, 1250, 700, 500, 70, "#1a0a06", seed=84, t=S.t, a=0.8, lean=0.3)
    bc = "#162219" if not B else "#1e0c06"
    with lay(ctx, S, 0.5):
        rnd = random.Random(85)
        for k in range(7):                                         # big rainforest trunks + lianas
            x = -60 + k * 380 + rnd.uniform(-60, 60)
            w = rnd.uniform(30, 48)
            fill_poly(ctx, [(x - w * 2.2, 882), (x - w * 0.6, 820), (x - w * 0.5, -10), (x + w * 0.5, -10),
                            (x + w * 0.6, 820), (x + w * 2.4, 882)], bc)
            for j in range(3):
                x2 = x + rnd.uniform(80, 220)
                y0_ = rnd.uniform(-20, 60) + j * 90
                sag = rnd.uniform(140, 240)
                pts = [(x + (x2 - x) * q / 14, y0_ + sag * math.sin(math.pi * q / 14) + 4 * math.sin(S.t * 2 + q + j))
                       for q in range(15)]
                line(ctx, pts, bc, 4)
                for q in range(0, 15, 3):
                    ellipse(ctx, pts[q][0], pts[q][1] + 10, 12, 6, bc, rot=0.6)
        for k in range(16):                                        # fern clusters
            x = rnd.uniform(-100, W + 900)
            for j in range(9):
                ang = -math.pi / 2 + (j - 4) * 0.28
                L = rnd.uniform(90, 150)
                tip = (x + math.cos(ang) * L, 880 + math.sin(ang) * L * 0.8)
                mid = (x + math.cos(ang) * L * 0.5, 880 + math.sin(ang) * L * 0.55 - 12)
                fill_poly(ctx, [(x, 880), (mid[0] - 8, mid[1]), tip, (mid[0] + 8, mid[1] + 6)], bc)
        if B:
            for x, s_, ph in ((1350, 260, 0.1), (1650, 240, 0.6)):
                figure(ctx, x + S.t * 150, 880, s_, ph + S.t * 1.75, "sol", run=1.0, charge=True, c="#120806")
    fx.fog(ctx, 850, 60, "#9ab8a0" if not B else "#d08040", a=0.35, t=S.t, seed=86)
    ground(ctx, S, "#0a120d" if not B else "#0a0504", kind="grass")
    with lay(ctx, S, 1.4):                                           # hanging vines, foreground
        rnd = random.Random(86)
        for k in range(6):
            x = rnd.uniform(-100, W + 1200)
            L = rnd.uniform(120, 330)
            sw = 8 * math.sin(S.t * 1.5 + k)
            pts = [(x + sw * q / 10, -10 + L * q / 10) for q in range(11)]
            line(ctx, pts, "#050806", 5)
            for q in range(2, 11, 2):
                ellipse(ctx, pts[q][0] + 12, pts[q][1], 16, 7, "#050806", rot=0.5)
                ellipse(ctx, pts[q][0] - 12, pts[q][1] + 8, 16, 7, "#050806", rot=-0.5)
    if B:
        fx.explosion(ctx, 1000 + 300 * (S.var % 2), 760, 80, S.t, seed=87 + S.var)
        fx.tracers(ctx, S.t, 88 + S.var, n=8, x0=W + 50, y0=640, spread=160)
    hero(ctx, S)
    fx.rain(ctx, S.t, 89, n=380, angle=0.12, c="#cfe0d4" if not B else "#ffd0a0", a=0.4, ground=GY)


# ============================================================ 10. Normandy beach
def normandy(ctx, S):
    B = S.B
    vgrad(ctx, 0, 700, [(0, "#4a5460"), (0.6, "#8a949a"), (1, "#c8c8c0")] if not B else
          [(0, "#3a3034"), (0.6, "#8a6a60"), (1, "#d8a080")])
    with lay(ctx, S, 0.04):
        fill_poly(ctx, [(-40, 700), (-40, 560), (200, 540), (420, 580), (700, 600), (900, 660), (1100, 700)],
                  "#6a7278" if not B else "#5a4644")                                       # cliffs
        if B:
            for k in range(4):
                fx.muzzle_flash(ctx, 200 + k * 180, 575 + 10 * k, S.t + k * 0.1, 90 + k, s=16)
    vgrad(ctx, 690, 780, [(0, "#6a7a84" if not B else "#6a4a44"), (1, "#8a9894" if not B else "#8a6a5a")])
    fx.waves(ctx, S.t, 705, "#dfe6e6", a=0.5, amp=4, n=4, speed=50, wl=200)
    with lay(ctx, S, 0.12):
        for k in range(5):
            P.landing_craft(ctx, 1100 + k * 220, 720, 150, "#3a444c" if not B else "#2a1e1e", ramp=B * 1.0)
        if B:
            for k in range(3):
                P.bomber_side(ctx, 900 + k * 300 + S.t * 60, 140 + k * 30, 150, "#2a2226")
    vgrad(ctx, 780, H, [(0, "#b8ac94" if not B else "#9a8068"), (1, "#6a604e" if not B else "#4a3a2a")])
    with lay(ctx, S, 0.5):
        for k in range(10):
            x = 60 + k * 240
            czech_hedgehog(ctx, x, 850 - (k % 2) * 20, 90 - (k % 2) * 20, "#2a2a2a")
            line(ctx, [(x + 110, 860), (x + 150, 790)], "#2a2a2a", 8)                      # wooden stakes
        if B:
            for x, s, ph in ((950, 200, 0.2), (1200, 220, 0.75), (1480, 190, 0.4), (1750, 230, 0.9)):
                figure(ctx, x + S.t * 150, 860, s, ph + S.t * 1.75, "sol", run=1.0, charge=True, c="#241c18")
            for k in range(3):
                age = S.t + k * 0.18 - 0.05 * (S.var % 3)
                water_column(ctx, 700 + k * 450, 845, age, "#e6dccc", seed=10 + k, hmax=300)
    fx.fog(ctx, 760, 70, "#d0d0c8" if not B else "#c09080", a=0.35, t=S.t, seed=91)
    ground(ctx, S, "#2a2620" if not B else "#1a120c", kind="rubble", detail_c="#1a1814", seed=92)
    hero(ctx, S)
    fx.spray(ctx, S.t, 93, 780, n=50, a=0.6)
    if B:
        fx.tracers(ctx, S.t, 94 + S.var, n=10, x0=-50, y0=600, ang=0.12, spread=200)
    else:
        fx.rain(ctx, S.t, 95, n=120, angle=0.3, a=0.25)


# ============================================================ 11. Railway station / refugees
def station(ctx, S):
    B = S.B
    vgrad(ctx, 0, GY, [(0, "#3a3a44"), (0.6, "#8a8078"), (1, "#d8c0a0")] if not B else
          [(0, "#2a1010"), (0.6, "#9a4a2a"), (1, "#f09048")])
    with lay(ctx, S, 0.1):
        rnd = random.Random(100)
        for x in range(-50, W + 400, 260):
            P.facade(ctx, x, 780, 240, rnd.uniform(200, 300), "#6a625e" if not B else "#5a2a22", rnd, roof="gable",
                     lit=0.1 * (1 - B), damage=0.6 * B)
        if B:
            fx.smoke(ctx, 600, 740, 520, 70, "#2a0c08", seed=101, t=S.t, a=0.8)
    c = "#2a2628" if not B else "#1e0c0a"
    with lay(ctx, S, 0.3):
        for k in range(5):                                   # arched iron trainshed
            x = -100 + k * 520
            ctx.new_path()
            ctx.save(); ctx.translate(x + 260, 700); ctx.scale(290, 180)
            ctx.arc(0, 0, 1, math.pi, TAU); ctx.restore()
            ctx.set_line_width(12); src(ctx, c); ctx.stroke()
            for j in range(9):
                a_ = math.pi + j / 8 * math.pi
                line(ctx, [(x + 260 + 290 * math.cos(a_), 700 + 180 * math.sin(a_)),
                           (x + 260 + 250 * math.cos(a_), 700 + 150 * math.sin(a_))], c, 3)
            rect(ctx, x - 45, 700, 30, 170, c)
        line(ctx, [(-100, 700), (W + 2200, 700)], c, 10)
        line(ctx, [(900, 520), (900, 600)], c, 4)
        circle(ctx, 900, 630, 34, c); circle(ctx, 900, 630, 26, "#e8dcc0" if not B else "#f0a060")
        line(ctx, [(900, 630), (900, 610)], c, 3); line(ctx, [(900, 630), (914, 634)], c, 3)
    tc = "#161416" if not B else "#120606"
    with lay(ctx, S, 0.5):
        dx = -S.t * 40 if not B else 0
        P.locomotive(ctx, 1500 + dx, 868, 420, tc, t=S.t)
        for k in range(2):                                     # carriages
            x = 1500 - 420 * 1.1 - (k + 1) * 470 + dx
            rect(ctx, x - 200, 608, 440, 220, tc)
            fill_poly(ctx, [(x - 212, 612), (x - 190, 590), (x + 230, 590), (x + 252, 612)], tc)
            for j in range(6):
                rect(ctx, x - 180 + j * 70, 638, 44, 60, "#e8c890" if not B else "#ff9040", 0.8)
            for wx in (x - 150, x - 90, x + 130, x + 190):
                circle(ctx, wx, 844, 24, tc)
            rect(ctx, x - 240, 800, 40, 10, tc)                       # coupling
        fx.steam(ctx, 1500 + 0.34 * 420 + dx, 868 - 0.74 * 420, S.t, 102, c="#ece6da" if not B else "#4a2a24")
        for x, s, ph in ((250, 330, 0.3), (420, 300, 0.8), (1060, 320, 0.55)):
            figure(ctx, x + S.t * 60, 880, s, ph + S.t * 0.875, "civ", c="#1a181a" if not B else "#140606")
    ground(ctx, S, "#100e10" if not B else "#0c0404", kind="sleepers", detail_c="#1e1a1c")
    if B:
        fx.explosion(ctx, 1200 + 400 * (S.var % 2), 700, 110, S.t, seed=103 + S.var)
    hero(ctx, S)
    if B:
        fx.embers(ctx, S.t, 104, n=100)
    else:
        fx.fog(ctx, 860, 40, "#d8d0c4", a=0.25, t=S.t, seed=105)


# ============================================================ 12. Italian mountains (Monte Cassino)
def mountains(ctx, S):
    B = S.B
    vgrad(ctx, 0, GY, [(0, "#6a8ab0"), (0.6, "#c0c8d0"), (1, "#f2e4c8")] if not B else
          [(0, "#3a2a34"), (0.6, "#9a6a5a"), (1, "#e0a070")])
    with lay(ctx, S, 0.03):
        fill_poly(ctx, [(-50, 620), (200, 300), (380, 420), (620, 240), (900, 450), (1200, 330), (1500, 470), (1800, 280),
                        (2100, 420), (2300, 620)], "#9aaac0" if not B else "#7a5a60")
        fill_poly(ctx, [(560, 310), (620, 240), (690, 300), (650, 290), (620, 305)], "#f4f4f4")     # snow caps
        fill_poly(ctx, [(1740, 340), (1800, 280), (1860, 330), (1820, 322)], "#f4f4f4")
    hill = "#56647a" if not B else "#4a2a30"
    with lay(ctx, S, 0.1):
        ridge(ctx, 640, 60, "#6a7a8a" if not B else "#5a3a40", seed=110, freq=0.5, x1=W + 400)
        fill_poly(ctx, [(900, 700), (1150, 470), (1250, 440), (1400, 470), (1650, 700)], hill)
        P.abbey(ctx, 1260, 452, 140, hill)
        if B:
            fx.smoke(ctx, 1250, 440, 420, 70, "#2a1414", seed=111, t=S.t, a=0.8, lean=0.3)
            for k in range(4):
                fx.explosion(ctx, 1150 + k * 60, 440 + 10 * k, 45, S.t - k * 0.12, seed=112 + k + S.var)
    tree = "#223022" if not B else "#200c0c"
    with lay(ctx, S, 0.35):
        ridge(ctx, 780, 30, "#3a4a3a" if not B else "#3a1c1c", seed=113, freq=0.9, x1=W + 900)
        for k, x in enumerate(range(-50, W + 900, 170)):
            P.cypress(ctx, x + 40 * math.sin(k * 3.1), 800, 180 + 60 * math.sin(k * 1.3), tree)
        for k in range(6):                                  # supply column on the road
            P.truck(ctx, 300 + k * 200 + S.t * 30, 780, 90, tree)
    ground(ctx, S, "#121812" if not B else "#0c0505", kind="grass")
    if B:
        fx.tracers(ctx, S.t, 114 + S.var, n=6, x0=W, y0=500, spread=200)
    hero(ctx, S)
    if not B:
        birds(ctx, 500 + S.t * 30, 200, 3, "#4a5a70", seed=115, s=16, spread=100)
        fx.falling_leaves(ctx, S.t, 116, n=10, c="#1a2a1a")
    else:
        fx.ash(ctx, S.t, 117, n=60)


# ============================================================ 13. Airfield
def airfield(ctx, S):
    B = S.B
    vgrad(ctx, 0, GY, [(0, "#2c3a5a"), (0.55, "#a88aa0"), (0.85, "#f0b890"), (1, "#f8d8a8")] if not B else
          [(0, "#2a1822"), (0.55, "#9a4a40"), (1, "#f0a050")])
    circle(ctx, 400, 760, 110, "#fff0cc", 0.9)
    glow(ctx, 400, 760, 400, "#ffd8a0", 0.4)
    fc = "#5a4a60" if not B else "#4a2020"
    with lay(ctx, S, 0.08):
        ridge(ctx, 800, 10, "#7a6a80" if not B else "#6a3030", seed=120, freq=0.5, x1=W + 300)
        P.hangar(ctx, 1200, 805, 420, 170, fc, door_c="#2a2230")
        P.hangar(ctx, 1640, 805, 300, 130, fc, door_c="#2a2230")
        P.control_tower(ctx, 950, 805, 220, "#4a3c52" if not B else "#3a1818", lit="#ffd890")
        P.windsock(ctx, 1950, 805, 120, "#4a3c52", t=S.t)
    pc = "#22182a" if not B else "#1a0a0a"
    with lay(ctx, S, 0.35):
        for k in range(4):                                   # parked bombers
            bx = 300 + k * 560
            P.bomber_side(ctx, bx, 790, 420, pc, ang=-0.08)
            line(ctx, [(bx + 60, 800), (bx + 60, 845)], pc, 8); circle(ctx, bx + 60, 845, 18, pc)
            line(ctx, [(bx - 190, 815), (bx - 190, 835)], pc, 5); circle(ctx, bx - 190, 836, 9, pc)
    if B:
        for k in range(3):                                   # bombers climbing out overhead
            P.bomber_side(ctx, 200 + k * 420 + S.t * 400, 380 - k * 70 - S.t * 60, 300, "#140a10", ang=-0.1)
        fx.explosion(ctx, 1500 + 200 * (S.var % 2), 790, 90, S.t, seed=121 + S.var)
    fx.fog(ctx, 830, 50, "#f0d8c0" if not B else "#e09060", a=0.5, t=S.t, seed=122)
    ground(ctx, S, "#141018" if not B else "#0c0506", kind="grass")
    with lay(ctx, S, 1.0):
        for x in range(0, W + 1400, 260):                     # runway lights
            glow(ctx, x, GY + 30, 16, "#ffcf70", 0.7)
    hero(ctx, S)
    fx.dust(ctx, S.t, 123, n=60 + 100 * B, c="#e8d0b0", y0=780, speed=500, a=0.4)


# ============================================================ 14. Trench (A: the night before, B: the charge)
def trench_calm(ctx, S):
    vgrad(ctx, 0, 870, [(0, "#141a2a"), (0.55, "#3a4458"), (0.9, "#8a7a78"), (1, "#a08a80")])
    # a slowly falling flare lights the field
    fy = 180 + S.t * 40
    glow(ctx, 1250, fy, 520, "#fff0c8", 0.35)
    circle(ctx, 1250, fy, 7, "#fffbe8")
    line(ctx, [(1250, fy - 8), (1244, fy - 70)], "#c8c8d0", 2, 0.5)
    with lay(ctx, S, 0.05):
        fx.smoke(ctx, 500, 820, 360, 60, "#3a4050", seed=160, t=S.t, a=0.5, lean=0.5)
    with lay(ctx, S, 0.2):
        ridge(ctx, 790, 12, "#3a3a48", seed=65, freq=1.3, x1=W + 600)
        for x, h in ((150, 180), (620, 140), (1780, 220), (1100, 110), (2200, 160)):
            dead_tree(ctx, x, 800, h, "#2a2a36", seed=int(x), w=9)
    with lay(ctx, S, 0.5):
        ridge(ctx, 830, 8, "#22222c", seed=66, freq=1.6, x1=W + 1000)
        barbed_wire(ctx, -20, W + 1000, 855, 70, "#16161e", seed=67, w=2.5)
    fill_poly(ctx, [(-10, 872), (W + 10, 868), (W + 10, H), (-10, H)], "#07070a")
    with lay(ctx, S, 1.0):
        rnd = random.Random(68)
        x = -30
        while x < W + 1400:
            w = rnd.uniform(70, 100)
            ellipse(ctx, x + w / 2, 872 + rnd.uniform(-4, 4), w / 2 + 6, 22, "#07070a")
            x += w
        for k, x in enumerate(range(100, W + 1400, 330)):      # helmets waiting below the parapet
            ctx.new_path(); ctx.arc(x, 858, 20, math.pi, TAU); src(ctx, "#07070a"); ctx.fill()
            rect(ctx, x - 26, 856, 52, 5, "#07070a")
            line(ctx, [(x + 14, 856), (x + 44, 790 - 10 * (k % 2))], "#07070a", 4)   # rifle barrel
    hero(ctx, S)
    fx.rain(ctx, S.t, 161, n=140, angle=0.2, a=0.22, c="#b8c0d0")


def trench(ctx, S):
    if not S.B:
        return trench_calm(ctx, S)
    vgrad(ctx, 0, 820, [(0, "#2a0f10"), (0.5, "#8a2e20"), (0.85, "#e0612f"), (1, "#ff9a45")])
    with lay(ctx, S, 0.05):
        fx.smoke(ctx, 300, 820, 700, 120, "#5a2016", seed=60, t=S.t, a=0.75, lean=0.35)
        fx.smoke(ctx, 1500, 820, 760, 140, "#4a1a14", seed=61, t=S.t, a=0.8, lean=0.25)
        fx.smoke(ctx, 950, 820, 420, 90, "#6a2618", seed=62, t=S.t, a=0.6, lean=0.5)
    fx.explosion(ctx, 1320 - 200 * (S.var % 2), 640, 80, S.t, seed=63 + S.var)
    with lay(ctx, S, 0.2):
        ridge(ctx, 780, 12, "#7a2a1e", seed=65, freq=1.3, x1=W + 600)
        for x, h in ((150, 180), (620, 140), (1780, 220), (1100, 110), (2200, 160)):
            dead_tree(ctx, x, 790, h, "#5a1e16", seed=int(x), w=9)
    fx.tracers(ctx, S.t, 64 + S.var, n=8, x0=W + 50, y0=560, spread=160)
    with lay(ctx, S, 0.2):
        for x, s, c, ph in ((1010, 150, "#6a2419", 0.1), (1230, 140, "#6a2419", 0.6), (1550, 170, "#6a2419", 0.35),
                            (1700, 150, "#6a2419", 0.85)):
            figure(ctx, x + S.t * 90, 800, s, ph + S.t * 1.75, "sol", run=1.0, charge=True, c=c)
    with lay(ctx, S, 0.5):
        ridge(ctx, 820, 8, "#4a1812", seed=66, freq=1.6, x1=W + 1000)
        barbed_wire(ctx, -20, W + 1000, 850, 70, "#2a0c0a", seed=67, w=2.5)
        for x, s, ph in ((360, 300, 0.45), (1180, 330, 0.2), (1500, 280, 0.7)):
            figure(ctx, x + S.t * 160, 880, s, ph + S.t * 1.75, "sol", run=1.0, charge=True, c="#2a0c0a")
    fill_poly(ctx, [(-10, 872), (W + 10, 868), (W + 10, H), (-10, H)], "#0a0404")
    with lay(ctx, S, 1.0):
        rnd = random.Random(68)
        x = -30
        while x < W + 1400:
            w = rnd.uniform(70, 100)
            ellipse(ctx, x + w / 2, 872 + rnd.uniform(-4, 4), w / 2 + 6, 22, "#0a0404")
            x += w
    hero(ctx, S)
    with lay(ctx, S, 1.3):
        figure(ctx, 190, 1060, 470, 0.15 + S.t * 1.75, "sol", run=1.0, charge=True, c="#000000")
        fill_poly(ctx, [(-10, 960), (420, 975), (440, H + 10), (-10, H + 10)], "#000000")
    fx.embers(ctx, S.t, 69, n=140, c="#ffc070")


# ============================================================ 15. Air battle (B only)
def airbattle(ctx, S):
    t = S.t
    vgrad(ctx, 0, 820, [(0, "#3a1830"), (0.4, "#a0413c"), (0.8, "#f08a4a"), (1, "#ffd27a")])
    for y, c, a, sd in ((520, "#ffb070", 0.5, 70), (430, "#d06a50", 0.55, 71), (300, "#8a3a44", 0.45, 72)):
        rnd = random.Random(sd)
        for _ in range(9):
            cx = (rnd.uniform(-200, W + 200) - t * 30) % (W + 400) - 200
            ellipse(ctx, cx, y + rnd.uniform(-30, 30), rnd.uniform(160, 360), rnd.uniform(18, 34), c, a)
    for dx, dy in ((0, 0), (-80, -45), (-80, 45), (-160, -90), (-160, 90), (-240, 0)):
        bomber(ctx, 760 + dx + t * 40, 150 + dy, 90, "#5a2230", ang=0.0)
    rnd = random.Random(73 + S.var)
    for _ in range(12):
        flak(ctx, rnd.uniform(380, 980), rnd.uniform(40, 300), rnd.uniform(12, 22), "#2a1018", seed=rnd.randint(0, 999), a=0.85)
    px, py = 330 - t * 60, 470 + t * 90
    fx.smoke(ctx, px + 30, py - 10, 330, 16, "#2a1018", seed=74, t=t, a=0.75, lean=-0.6)
    fighter(ctx, px, py, 120, "#1e0c14", ang=2.2, elliptical=False)
    glow(ctx, px, py, 45, "#ffb040", 0.8)
    for (x, y, s_, ang) in ((1380 + t * 900, 260, 340, 0.2), (1080 + t * 900, 440, 230, 0.25)):
        d = (math.cos(ang), math.sin(ang)); n = (-d[1], d[0])
        for off in (-0.56, 0.56):
            p0 = (x + n[0] * off * s_ + d[0] * 0.1 * s_, y + n[1] * off * s_ + d[1] * 0.1 * s_)
            line(ctx, [p0, (p0[0] - d[0] * s_ * 1.6, p0[1] - d[1] * s_ * 1.6)], "#ffe8c0", 2, 0.45)
        fighter(ctx, x, y, s_, "#140810", ang=ang, elliptical=True)
        for k in (-0.3, 0.3):
            g0 = (x + n[0] * k * s_ + d[0] * 0.3 * s_, y + n[1] * k * s_ + d[1] * 0.3 * s_)
            line(ctx, [(g0[0] + d[0] * 60, g0[1] + d[1] * 60), (g0[0] + d[0] * 180, g0[1] + d[1] * 180)], "#fff0b0", 3, 0.9)
    with lay(ctx, S, 0.1):
        ridge(ctx, 800, 18, "#8a3440", seed=75, freq=0.6, x1=W + 300)
    with lay(ctx, S, 0.3):
        rnd = random.Random(77)
        ctx.push_group()
        for x in range(-20, W + 700, 26):
            circle(ctx, x, 845 - 25 * math.sin(x * 0.011) - rnd.uniform(0, 22), rnd.uniform(24, 40), "#4a1a26")
        rect(ctx, -20, 840, W + 720, 60, "#4a1a26")
        fill_poly(ctx, [(1300, 840), (1300, 700), (1318, 640), (1336, 700), (1336, 840)], "#4a1a26")
        ctx.pop_group_to_source(); ctx.paint()
    ground(ctx, S, "#0b0508", kind="grass")
    hero(ctx, S)


# ============================================================ 16. Outro: dawn over ruins
def dawn(ctx, S):
    vgrad(ctx, 0, 880, [(0, "#5e6f98"), (0.4, "#b89aae"), (0.68, "#f2c3a4"), (0.85, "#fde6bc"), (1, "#fde6bc")])
    circle(ctx, 1260, 760, 170, "#fff1cf", 0.95)
    glow(ctx, 1260, 760, 700, "#ffe2a8", 0.4)
    for i in range(12):
        a = -math.pi / 2 + (i - 5.5) * 0.16 + 0.01 * S.t
        fill_poly(ctx, [(1260, 760), (1260 + 1600 * math.cos(a - 0.02), 760 + 1600 * math.sin(a - 0.02)),
                        (1260 + 1600 * math.cos(a + 0.02), 760 + 1600 * math.sin(a + 0.02))], "#fff4d8", 0.07)
    with lay(ctx, S, 0.05):
        skyline(ctx, 800, 60, 220, "#c6a3a6", seed=80, broken=0.9, windows=True, x1=W + 300)
        fx.smoke(ctx, 520, 790, 360, 26, "#c9aab0", seed=81, t=S.t, a=0.35, lean=0.7)
    with lay(ctx, S, 0.25):
        rnd = random.Random(82)
        for x, w, h in ((-40, 280, 380), (260, 130, 200), (1560, 220, 300), (1780, 200, 420), (2100, 240, 340)):
            P.ruin_wall(ctx, x, 880, w, h, "#6f5866", rnd)
        dead_tree(ctx, 1480, 875, 300, "#4a3a46", seed=83, w=12)
    fill_poly(ctx, [(-10, 872), (W + 10, 868), (W + 10, H), (-10, H)], "#0b0809")
    with lay(ctx, S, 1.0):
        rnd = random.Random(84)
        for _ in range(60):
            x = rnd.uniform(0, W + 1400); y = rnd.uniform(865, 900)
            rect(ctx, x, y - 12, rnd.uniform(14, 30), 12, "#0b0809")
        sx = 1180
        line(ctx, [(sx, 872), (sx + 4, 830), (sx + 2, 800)], "#0b0809", 5)
        ellipse(ctx, sx + 20, 812, 18, 8, "#0b0809", rot=-0.5)
        ellipse(ctx, sx - 14, 826, 15, 7, "#0b0809", rot=0.5)
    birds(ctx, 1100 + S.t * 40, 360, 7, "#5a4a5e", seed=85, s=13, spread=220)
    hero(ctx, S)


SCENES = {
    "prologue": prologue, "paris": paris, "london": london, "berlin": berlin, "stalingrad": stalingrad,
    "moscow": moscow, "warship": warship, "carrier": carrier, "desert": desert, "jungle": jungle,
    "normandy": normandy, "station": station, "mountains": mountains, "airfield": airfield,
    "trench": trench, "airbattle": airbattle, "dawn": dawn,
}
