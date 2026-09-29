"""Drawing primitives for the WW2 silhouette video (pycairo, flat illustration style)."""
import math, random
import cairo
import numpy as np

W, H = 1920, 1080
GY = 870          # ground line the main figure walks on
FIG_X = 720       # main figure x (left of centre, walking right)
FIG_H = 430       # main figure height


# ---------------------------------------------------------------- colour helpers
def hx(s, a=None):
    s = s.lstrip("#")
    c = tuple(int(s[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return c if a is None else c + (a,)


def mix(c1, c2, t):
    c1, c2 = hx(c1) if isinstance(c1, str) else c1, hx(c2) if isinstance(c2, str) else c2
    return tuple(a + (b - a) * t for a, b in zip(c1, c2))


def src(ctx, c, a=1.0):
    c = hx(c) if isinstance(c, str) else c
    ctx.set_source_rgba(c[0], c[1], c[2], a if len(c) == 3 else c[3] * a)


# ---------------------------------------------------------------- basic shapes
def poly(ctx, pts, close=True):
    ctx.move_to(*pts[0])
    for p in pts[1:]:
        ctx.line_to(*p)
    if close:
        ctx.close_path()


def fill_poly(ctx, pts, c, a=1.0):
    poly(ctx, pts); src(ctx, c, a); ctx.fill()


def rect(ctx, x, y, w, h, c, a=1.0):
    ctx.rectangle(x, y, w, h); src(ctx, c, a); ctx.fill()


def circle(ctx, x, y, r, c, a=1.0):
    ctx.arc(x, y, r, 0, 2 * math.pi); src(ctx, c, a); ctx.fill()


def ellipse(ctx, x, y, rx, ry, c, a=1.0, rot=0.0):
    ctx.save(); ctx.translate(x, y); ctx.rotate(rot); ctx.scale(rx, ry)
    ctx.arc(0, 0, 1, 0, 2 * math.pi); ctx.restore(); src(ctx, c, a); ctx.fill()


def line(ctx, pts, c, w, a=1.0, cap=cairo.LINE_CAP_ROUND):
    poly(ctx, pts, close=False)
    ctx.set_line_width(w); ctx.set_line_cap(cap); ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    src(ctx, c, a); ctx.stroke()


def vgrad(ctx, y0, y1, stops, x0=0, x1=W):
    """Vertical gradient fill of rect [x0,x1]x[y0,y1]; stops = [(t, colour), ...]."""
    g = cairo.LinearGradient(0, y0, 0, y1)
    for t, c in stops:
        g.add_color_stop_rgb(t, *hx(c))
    ctx.rectangle(x0, y0, x1 - x0, y1 - y0); ctx.set_source(g); ctx.fill()


def glow(ctx, x, y, r, c, a=1.0, r0=0.0):
    g = cairo.RadialGradient(x, y, r0, x, y, r)
    cc = hx(c)
    g.add_color_stop_rgba(0, *cc, a)
    g.add_color_stop_rgba(0.35, *cc, a * 0.45)
    g.add_color_stop_rgba(1, *cc, 0)
    ctx.arc(x, y, r, 0, 2 * math.pi); ctx.set_source(g); ctx.fill()


def ridge(ctx, y, amp, c, seed, freq=1.0, x0=-50, x1=W + 50, bottom=H, a=1.0):
    """Rolling hill/terrain band."""
    rnd = random.Random(seed)
    comps = [(rnd.uniform(0.6, 1.4) * freq * k, rnd.uniform(0, 6.28), amp / k) for k in (1, 2.3, 5.1)]
    pts = [(x0, bottom)]
    for x in range(int(x0), int(x1) + 1, 12):
        yy = y + sum(A * math.sin(x / 300 * f + p) for f, p, A in comps)
        pts.append((x, yy))
    pts.append((x1, bottom))
    fill_poly(ctx, pts, c, a)


# ---------------------------------------------------------------- buildings
def ruined_block(ctx, x, base, w, h, c, rnd, windows=True, broken=0.6, a=1.0):
    """Building with a jagged broken top and window holes (holes show what is behind)."""
    top = base - h
    pts = [(x, base), (x, top + rnd.uniform(0, h * 0.1))]
    if rnd.random() < broken:
        n = rnd.randint(3, 6)
        for i in range(1, n):
            px = x + w * i / n + rnd.uniform(-w * 0.05, w * 0.05)
            pts.append((px, top + rnd.uniform(0, h * 0.45)))
    pts += [(x + w, top + rnd.uniform(0, h * 0.25)), (x + w, base)]
    ctx.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
    poly(ctx, pts)
    if windows:
        cols = max(2, int(w / 38)); rows = max(2, int(h / 55))
        ww, wh = w / cols * 0.42, h / rows * 0.42
        for i in range(cols):
            for j in range(rows):
                wx = x + (i + 0.5) * w / cols - ww / 2
                wy = top + h * 0.12 + (j + 0.3) * (h * 0.85) / rows
                if wy < top + h * 0.5 and rnd.random() < 0.35:
                    continue
                if rnd.random() < 0.75:
                    ctx.rectangle(wx, wy, ww, wh)
    src(ctx, c, a); ctx.fill()
    ctx.set_fill_rule(cairo.FILL_RULE_WINDING)


def skyline(ctx, base, hmin, hmax, c, seed, x0=-40, x1=W + 40, wmin=60, wmax=160, broken=0.5, windows=False, a=1.0):
    rnd = random.Random(seed)
    x = x0
    while x < x1:
        w = rnd.uniform(wmin, wmax)
        ruined_block(ctx, x, base + 5, w + 2, rnd.uniform(hmin, hmax), c, rnd, windows=windows, broken=broken, a=a)
        x += w


def chimney(ctx, x, base, w, h, c, broken=False):
    top = base - h
    pts = [(x, base), (x + w * 0.1, top), (x + w * 0.9, top + (h * 0.08 if broken else 0)), (x + w, base)]
    fill_poly(ctx, pts, c)


def smoke_column(ctx, x, base, h, width, c, seed, a=0.85, lean=0.25):
    """Billowing smoke drawn as one flat merged shape."""
    rnd = random.Random(seed)
    n = 16
    ctx.push_group()
    for i in range(n):
        t = i / (n - 1)
        cx = x + lean * h * t ** 1.4 + rnd.uniform(-12, 12)
        cy = base - h * t
        r = width * (0.35 + 0.9 * t) * rnd.uniform(0.8, 1.15)
        circle(ctx, cx, cy, r, c)
        circle(ctx, cx + r * 0.5, cy + r * 0.2, r * 0.7, c)
    ctx.pop_group_to_source(); ctx.paint_with_alpha(a)


def czech_hedgehog(ctx, x, base, s, c):
    """Soviet anti-tank 'hedgehog' (three crossed beams)."""
    w = s * 0.12
    for ang in (-0.75, 0.75):
        ctx.save(); ctx.translate(x, base - s * 0.42); ctx.rotate(ang)
        ctx.rectangle(-w / 2, -s * 0.6, w, s * 1.2); ctx.restore()
    ctx.rectangle(x - w * 0.6, base - s * 0.95, w * 1.2, s * 0.95)
    src(ctx, c); ctx.fill()


def barbed_wire(ctx, x0, x1, base, h, c, seed, w=2.2):
    rnd = random.Random(seed)
    x = x0
    posts = []
    while x < x1:
        posts.append(x); x += rnd.uniform(90, 150)
    for px in posts:
        line(ctx, [(px, base), (px + rnd.uniform(-8, 8), base - h * rnd.uniform(0.85, 1.1))], c, w * 2.2)
    # coils
    ctx.set_line_width(w)
    pts = []
    xx = x0
    while xx < x1:
        pts.append((xx, base - h * 0.5 + h * 0.42 * math.sin(xx * 0.09) + rnd.uniform(-4, 4)))
        xx += 4
    line(ctx, pts, c, w)
    pts2 = [(p[0], base - h * 0.85 + h * 0.12 * math.sin(p[0] * 0.05 + 1)) for p in pts[::3]]
    line(ctx, pts2, c, w)


def dead_tree(ctx, x, base, h, c, seed, w=14):
    rnd = random.Random(seed)
    top = (x + rnd.uniform(-20, 20), base - h)
    line(ctx, [(x, base), ((x + top[0]) / 2 + rnd.uniform(-8, 8), base - h / 2), top], c, w, cap=cairo.LINE_CAP_BUTT)
    fill_poly(ctx, [(top[0] - w / 2, top[1]), (top[0] + 3, top[1] - h * 0.08), (top[0] + w / 2, top[1] + 6)], c)
    for _ in range(rnd.randint(2, 4)):
        t = rnd.uniform(0.35, 0.85)
        bx, by = x + (top[0] - x) * t, base - h * t
        side = rnd.choice((-1, 1))
        L = h * rnd.uniform(0.15, 0.3)
        line(ctx, [(bx, by), (bx + side * L * 0.8, by - L * 0.6)], c, w * 0.45)


def birds(ctx, x, y, n, c, seed, s=10, spread=180):
    rnd = random.Random(seed)
    for _ in range(n):
        bx, by = x + rnd.uniform(-spread, spread), y + rnd.uniform(-spread * 0.35, spread * 0.35)
        ss = s * rnd.uniform(0.6, 1.2)
        line(ctx, [(bx - ss, by - ss * 0.35), (bx, by + ss * 0.1), (bx + ss, by - ss * 0.35)], c, max(1.5, ss * 0.22))


# ---------------------------------------------------------------- vehicles / aircraft
def t34(ctx, x, base, s, c, tilt=0.0, snow=None):
    """Side-view T-34 style tank facing right, s = hull length."""
    ctx.save(); ctx.translate(x, base); ctx.rotate(tilt)
    u = s
    ctx.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
    # tracks + hull
    poly(ctx, [(-0.5 * u, -0.02 * u), (-0.55 * u, -0.12 * u), (-0.46 * u, -0.2 * u), (0.47 * u, -0.2 * u),
               (0.56 * u, -0.12 * u), (0.5 * u, -0.02 * u)])
    poly(ctx, [(-0.5 * u, -0.2 * u), (-0.44 * u, -0.3 * u), (0.3 * u, -0.3 * u), (0.52 * u, -0.2 * u)])
    # turret
    poly(ctx, [(-0.22 * u, -0.3 * u), (-0.18 * u, -0.43 * u), (0.12 * u, -0.43 * u), (0.2 * u, -0.3 * u)])
    src(ctx, c); ctx.fill()
    ctx.set_fill_rule(cairo.FILL_RULE_WINDING)
    # gun
    line(ctx, [(0.15 * u, -0.385 * u), (0.72 * u, -0.40 * u)], c, 0.035 * u, cap=cairo.LINE_CAP_BUTT)
    # road wheels as lighter holes
    for i in range(5):
        wx = -0.38 * u + i * 0.19 * u
        ctx.arc(wx, -0.105 * u, 0.07 * u, 0, 2 * math.pi)
        src(ctx, mix(c, "#ffffff", 0.12)); ctx.fill()
        ctx.arc(wx, -0.105 * u, 0.025 * u, 0, 2 * math.pi); src(ctx, c); ctx.fill()
    if snow:
        fill_poly(ctx, [(-0.44 * u, -0.3 * u), (-0.4 * u, -0.33 * u), (0.26 * u, -0.33 * u), (0.3 * u, -0.3 * u)], snow)
        fill_poly(ctx, [(-0.18 * u, -0.43 * u), (-0.14 * u, -0.46 * u), (0.1 * u, -0.46 * u), (0.12 * u, -0.43 * u)], snow)
    ctx.restore()


def fighter(ctx, x, y, s, c, ang=0.0, elliptical=True):
    """Fighter plane seen from below (planform). Nose points along +x before rotation."""
    ctx.save(); ctx.translate(x, y); ctx.rotate(ang); u = s
    # fuselage
    poly(ctx, [(0.5 * u, 0), (0.44 * u, -0.05 * u), (0.1 * u, -0.06 * u), (-0.38 * u, -0.025 * u),
               (-0.5 * u, -0.012 * u), (-0.5 * u, 0.012 * u), (-0.38 * u, 0.025 * u), (0.1 * u, 0.06 * u), (0.44 * u, 0.05 * u)])
    src(ctx, c); ctx.fill()
    # wings
    if elliptical:
        ctx.save(); ctx.translate(0.12 * u, 0); ctx.scale(0.13 * u, 0.56 * u); ctx.arc(0, 0, 1, 0, 2 * math.pi); ctx.restore()
        src(ctx, c); ctx.fill()
    else:
        fill_poly(ctx, [(0.22 * u, -0.05 * u), (0.14 * u, -0.55 * u), (0.04 * u, -0.55 * u), (0.0, -0.05 * u),
                        (0.0, 0.05 * u), (0.04 * u, 0.55 * u), (0.14 * u, 0.55 * u), (0.22 * u, 0.05 * u)], c)
    # tailplane
    ctx.save(); ctx.translate(-0.42 * u, 0); ctx.scale(0.06 * u, 0.2 * u); ctx.arc(0, 0, 1, 0, 2 * math.pi); ctx.restore()
    src(ctx, c); ctx.fill()
    # prop disc
    ellipse(ctx, 0.51 * u, 0, 0.012 * u, 0.14 * u, c, 0.35)
    ctx.restore()


def bomber(ctx, x, y, s, c, ang=0.0):
    ctx.save(); ctx.translate(x, y); ctx.rotate(ang); u = s
    fill_poly(ctx, [(0.5 * u, 0), (0.45 * u, -0.045 * u), (-0.45 * u, -0.025 * u), (-0.5 * u, 0),
                    (-0.45 * u, 0.025 * u), (0.45 * u, 0.045 * u)], c)
    fill_poly(ctx, [(0.16 * u, -0.04 * u), (0.08 * u, -0.62 * u), (-0.02 * u, -0.62 * u), (0.0, -0.04 * u),
                    (0.0, 0.04 * u), (-0.02 * u, 0.62 * u), (0.08 * u, 0.62 * u), (0.16 * u, 0.04 * u)], c)
    for e in (-0.42, -0.2, 0.2, 0.42):
        ellipse(ctx, 0.16 * u, e * u, 0.07 * u, 0.028 * u, c)
    fill_poly(ctx, [(-0.36 * u, -0.02 * u), (-0.44 * u, -0.2 * u), (-0.49 * u, -0.2 * u), (-0.48 * u, 0),
                    (-0.49 * u, 0.2 * u), (-0.44 * u, 0.2 * u), (-0.36 * u, 0.02 * u)], c)
    ctx.restore()


def flak(ctx, x, y, r, c, seed, a=0.9):
    rnd = random.Random(seed)
    ctx.push_group()
    for _ in range(6):
        circle(ctx, x + rnd.uniform(-r, r) * 0.7, y + rnd.uniform(-r, r) * 0.5, r * rnd.uniform(0.4, 0.75), c)
    ctx.pop_group_to_source(); ctx.paint_with_alpha(a)


def explosion(ctx, x, y, r, seed, core="#fff4d0", mid="#ffb347", outer="#e2542a"):
    glow(ctx, x, y, r * 3.2, outer, 0.55)
    rnd = random.Random(seed)
    # spiky burst
    n = 22
    pts = []
    for i in range(n):
        a = i / n * 2 * math.pi
        rr = r * (1.0 if i % 2 == 0 else rnd.uniform(0.45, 0.7)) * rnd.uniform(0.8, 1.3)
        pts.append((x + math.cos(a) * rr, y + math.sin(a) * rr * 0.85))
    fill_poly(ctx, pts, mid)
    glow(ctx, x, y, r * 0.9, core, 1.0)


# ---------------------------------------------------------------- the walker
def _pt(p, ang, L):
    return (p[0] + L * math.sin(ang), p[1] + L * math.cos(ang))


def limb(ctx, p0, p1, w0, w1, c):
    """Tapered limb segment with rounded joints."""
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    L = math.hypot(dx, dy) or 1
    nx, ny = -dy / L, dx / L
    fill_poly(ctx, [(p0[0] + nx * w0 / 2, p0[1] + ny * w0 / 2), (p1[0] + nx * w1 / 2, p1[1] + ny * w1 / 2),
                    (p1[0] - nx * w1 / 2, p1[1] - ny * w1 / 2), (p0[0] - nx * w0 / 2, p0[1] - ny * w0 / 2)], c)
    circle(ctx, p0[0], p0[1], w0 / 2, c)
    circle(ctx, p1[0], p1[1], w1 / 2, c)


def figure(ctx, x, gy, h, phase, kind="civ", run=0.0, c="#000000", charge=False, suitcase=True):
    """Side-view silhouette walking to the right.

    phase: 0..1 per stride (two steps). A heel lands at phase 0.0 and 0.5.
    kind : 'civ' (trench coat, fedora, suitcase) or 'sol' (helmet, pack, rifle).
    run  : 0 = walk, 1 = run.   charge: rifle levelled forward (soldier only).
    """
    u = h
    tau = 2 * math.pi
    A = 0.34 + 0.28 * run
    lean = 0.04 + 0.2 * run + (0.08 if charge else 0)
    L1, L2 = 0.25 * u, 0.245 * u

    legs = []
    for s in (0, 1):
        ph = tau * phase + s * math.pi + math.pi / 2
        thigh = A * math.sin(ph) + lean * 0.35
        flex = 0.07 + (0.8 + 0.9 * run) * max(0.0, math.cos(ph - 0.5)) ** 2
        legs.append((thigh, thigh - flex, ph))

    def foot_low(th, sh):
        k = _pt((0, 0), th, L1); an = _pt(k, sh, L2)
        return an[1] + 0.028 * u
    low = max(foot_low(th, sh) for th, sh, _ in legs)
    hip = (x, gy - low)

    shoulder = (hip[0] + math.sin(lean) * 0.3 * u, hip[1] - math.cos(lean) * 0.3 * u)
    head = (shoulder[0] + 0.03 * u + lean * 0.08 * u, shoulder[1] - 0.1 * u)

    def draw_leg(th, sh):
        k = _pt(hip, th, L1); an = _pt(k, sh, L2)
        limb(ctx, hip, k, 0.1 * u, 0.068 * u, c)
        limb(ctx, k, an, 0.066 * u, 0.045 * u, c)
        fa = math.pi / 2 + sh * 0.5
        rot = math.atan2(math.cos(fa), math.sin(fa))
        ctx.save(); ctx.translate(*an); ctx.rotate(rot)
        fill_poly(ctx, [(-0.035 * u, -0.022 * u), (0.02 * u, -0.022 * u), (0.075 * u, 0.0), (0.09 * u, 0.018 * u),
                        (0.085 * u, 0.028 * u), (-0.035 * u, 0.028 * u)], c)
        ctx.restore()

    def arm(side_ph, swing, w=0.056):
        a_up = -swing * math.sin(side_ph) + lean * 0.5
        el = _pt(shoulder, a_up, 0.16 * u)
        fore = a_up + 0.18 + (0.25 + 0.6 * run) * max(0, math.sin(side_ph))
        hand = _pt(el, fore, 0.15 * u)
        limb(ctx, (shoulder[0], shoulder[1] + 0.02 * u), el, w * u, w * 0.85 * u, c)
        limb(ctx, el, hand, w * 0.85 * u, w * 0.7 * u, c)
        circle(ctx, hand[0], hand[1], 0.03 * u, c)

    for th, sh, _ in legs:
        draw_leg(th, sh)

    # head + neck
    limb(ctx, (shoulder[0] + 0.01 * u, shoulder[1] + 0.02 * u), (head[0] - 0.012 * u, head[1] + 0.03 * u), 0.07 * u, 0.055 * u, c)
    circle(ctx, head[0], head[1], 0.06 * u, c)

    if kind == "civ":
        hem_y = hip[1] + 0.2 * u
        f_leg = max(legs, key=lambda l: l[0])[0]
        b_leg = min(legs, key=lambda l: l[0])[0]
        coat = [(shoulder[0] - 0.085 * u, shoulder[1] + 0.03 * u),
                (shoulder[0] - 0.05 * u, shoulder[1] - 0.012 * u),
                (shoulder[0] + 0.035 * u, shoulder[1] - 0.015 * u),
                (shoulder[0] + 0.075 * u, shoulder[1] + 0.03 * u),
                (hip[0] + 0.085 * u, hip[1] - 0.06 * u),
                (hip[0] + 0.1 * u + 0.18 * u * max(0, f_leg), hem_y - 0.01 * u),
                (hip[0] - 0.02 * u, hem_y + 0.012 * u),
                (hip[0] - 0.11 * u + 0.18 * u * min(0, b_leg), hem_y),
                (hip[0] - 0.095 * u, hip[1] - 0.06 * u)]
        fill_poly(ctx, coat, c)
        circle(ctx, shoulder[0] - 0.035 * u, shoulder[1] + 0.03 * u, 0.05 * u, c)
        # fedora
        hb = (head[0] - 0.005 * u, head[1] - 0.03 * u)
        fill_poly(ctx, [(hb[0] - 0.1 * u, hb[1] + 0.012 * u), (hb[0] - 0.08 * u, hb[1] - 0.004 * u),
                        (hb[0] + 0.08 * u, hb[1] - 0.012 * u), (hb[0] + 0.105 * u, hb[1] - 0.002 * u),
                        (hb[0] + 0.08 * u, hb[1] + 0.008 * u)], c)
        fill_poly(ctx, [(hb[0] - 0.06 * u, hb[1]), (hb[0] - 0.052 * u, hb[1] - 0.075 * u),
                        (hb[0] - 0.005 * u, hb[1] - 0.064 * u), (hb[0] + 0.05 * u, hb[1] - 0.078 * u),
                        (hb[0] + 0.058 * u, hb[1] - 0.006 * u)], c)
        arm(legs[0][2], 0.42)
        if suitcase:
            sw = 0.05 * math.sin(legs[1][2])
            el2 = _pt(shoulder, 0.05 + sw, 0.16 * u)
            hand2 = _pt(el2, 0.02 + sw, 0.15 * u)
            limb(ctx, (shoulder[0], shoulder[1] + 0.02 * u), el2, 0.058 * u, 0.05 * u, c)
            limb(ctx, el2, hand2, 0.05 * u, 0.04 * u, c)
            bw, bh = 0.21 * u, 0.135 * u
            ctx.save(); ctx.translate(hand2[0], hand2[1]); ctx.rotate(-sw * 0.6)
            rect(ctx, -bw / 2, 0.02 * u, bw, bh, c)
            ctx.restore()
        else:
            arm(legs[1][2], 0.42)
    else:
        belt_y = hip[1] + 0.04 * u
        tunic = [(shoulder[0] - 0.08 * u, shoulder[1] + 0.025 * u), (shoulder[0] - 0.04 * u, shoulder[1] - 0.012 * u),
                 (shoulder[0] + 0.07 * u, shoulder[1] + 0.02 * u),
                 (hip[0] + 0.08 * u, hip[1] - 0.03 * u), (hip[0] + 0.09 * u, belt_y + 0.05 * u),
                 (hip[0] - 0.085 * u, belt_y + 0.05 * u), (hip[0] - 0.09 * u, hip[1] - 0.05 * u)]
        fill_poly(ctx, tunic, c)
        # backpack with rolled blanket, rotated with the lean
        ctx.save(); ctx.translate(shoulder[0], shoulder[1]); ctx.rotate(-lean)
        ctx.new_path()
        ctx.move_to(-0.07 * u, 0.02 * u); ctx.line_to(-0.155 * u, 0.04 * u); ctx.line_to(-0.165 * u, 0.2 * u)
        ctx.line_to(-0.07 * u, 0.22 * u); ctx.close_path(); src(ctx, c); ctx.fill()
        ellipse(ctx, -0.11 * u, 0.02 * u, 0.06 * u, 0.028 * u, c)
        ctx.restore()
        ellipse(ctx, hip[0] - 0.08 * u, hip[1] + 0.035 * u, 0.028 * u, 0.042 * u, c)   # canteen
        rect(ctx, hip[0] + 0.02 * u, belt_y - 0.01 * u, 0.06 * u, 0.04 * u, c)          # ammo pouch
        # helmet
        ctx.save(); ctx.translate(head[0] - 0.005 * u, head[1] - 0.018 * u); ctx.rotate(lean * 0.5)
        ctx.arc(0, 0, 0.082 * u, math.pi, 2 * math.pi); src(ctx, c); ctx.fill()
        fill_poly(ctx, [(-0.105 * u, 0.012 * u), (-0.08 * u, -0.004 * u), (0.08 * u, -0.004 * u),
                        (0.11 * u, 0.01 * u), (0.08 * u, 0.02 * u), (-0.08 * u, 0.022 * u)], c)
        ctx.restore()
        if charge:
            grip = (hip[0] + 0.06 * u, hip[1] - 0.1 * u)
            ang = -0.28 - 0.05 * math.sin(tau * phase * 2)
            d = (math.cos(ang), math.sin(ang))
            butt = (grip[0] - d[0] * 0.12 * u, grip[1] - d[1] * 0.12 * u)
            muzzle = (grip[0] + d[0] * 0.5 * u, grip[1] + d[1] * 0.5 * u)
            fore = (grip[0] + d[0] * 0.26 * u, grip[1] + d[1] * 0.26 * u)
            limb(ctx, butt, grip, 0.05 * u, 0.034 * u, c)
            line(ctx, [grip, muzzle], c, 0.024 * u)
            line(ctx, [muzzle, (muzzle[0] + d[0] * 0.14 * u, muzzle[1] + d[1] * 0.14 * u)], c, 0.01 * u,
                 cap=cairo.LINE_CAP_BUTT)
            sh0 = (shoulder[0], shoulder[1] + 0.02 * u)
            for tgt, w in ((fore, 0.052), (grip, 0.056)):
                mx, my = (sh0[0] + tgt[0]) / 2, (sh0[1] + tgt[1]) / 2 + 0.05 * u
                limb(ctx, sh0, (mx, my), w * u, w * 0.85 * u, c)
                limb(ctx, (mx, my), tgt, w * 0.85 * u, w * 0.7 * u, c)
                circle(ctx, tgt[0], tgt[1], 0.028 * u, c)
        else:
            # rifle slung on back: butt near hip, muzzle above shoulder
            ctx.save(); ctx.translate(shoulder[0], shoulder[1]); ctx.rotate(-lean)
            butt = (-0.13 * u, 0.36 * u); muzzle = (-0.03 * u, -0.25 * u)
            line(ctx, [butt, muzzle], c, 0.022 * u)
            fill_poly(ctx, [(butt[0] - 0.028 * u, butt[1] + 0.01 * u), (butt[0] + 0.03 * u, butt[1] + 0.02 * u),
                            (butt[0] + 0.035 * u, butt[1] - 0.14 * u), (butt[0] + 0.01 * u, butt[1] - 0.14 * u)], c)
            ctx.restore()
            arm(legs[0][2], 0.4)
            # near arm holds the sling at the chest
            el2 = _pt(shoulder, 0.3, 0.15 * u)
            hand2 = (shoulder[0] + 0.05 * u, shoulder[1] + 0.05 * u)
            limb(ctx, (shoulder[0], shoulder[1] + 0.02 * u), el2, 0.058 * u, 0.05 * u, c)
            limb(ctx, el2, hand2, 0.05 * u, 0.04 * u, c)
    return hip


# ---------------------------------------------------------------- post
def post(surface, seed=0, grain=7.0, vignette=0.32, warm=None):
    buf = surface.get_data()
    a = np.ndarray((H, W, 4), np.uint8, buf).copy()
    img = a[:, :, [2, 1, 0]].astype(np.float32)
    rng = np.random.default_rng(seed)
    n = rng.normal(0, grain, (H // 2, W // 2)).astype(np.float32)
    n = np.repeat(np.repeat(n, 2, 0), 2, 1)
    img += n[:, :, None]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = ((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2
    img *= (1 - vignette * np.clip(d - 0.25, 0, 1.4) / 1.4)[:, :, None]
    return np.clip(img, 0, 255).astype(np.uint8)


def new_canvas():
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(s)
    ctx.set_antialias(cairo.ANTIALIAS_BEST)
    return s, ctx
