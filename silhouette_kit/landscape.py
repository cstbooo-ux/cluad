"""English countryside + sky elements: oast houses, a signature oak, hedgerows, fields, flat cumulus clouds,
foreground grass. All flat fills; pass colours already graded for the scene."""
import math, random
import cairo
from .core import hx, mix, src, poly, fill_poly, rect, circle, ellipse, line, glow, W, H

TAU = 2 * math.pi


def _grp(ctx):
    ctx.push_group()


def _paint(ctx, a=1.0):
    ctx.pop_group_to_source(); ctx.paint_with_alpha(a)


def oast_house(ctx, x, base, s, c, cowl=None, t=0.0, a=1.0):
    """Kentish oast house: round kiln with a steep conical roof and a white tilted cowl, plus a barn."""
    u = s
    _grp(ctx)
    # barn (stowage) to the right with a pitched roof
    rect(ctx, x + 0.18 * u, base - 0.55 * u, 0.9 * u, 0.55 * u, c)
    fill_poly(ctx, [(x + 0.14 * u, base - 0.53 * u), (x + 0.35 * u, base - 0.85 * u), (x + 1.02 * u, base - 0.85 * u),
                    (x + 1.14 * u, base - 0.53 * u)], c)
    # round kiln + cone
    rect(ctx, x - 0.22 * u, base - 0.75 * u, 0.44 * u, 0.75 * u, c)
    fill_poly(ctx, [(x - 0.25 * u, base - 0.74 * u), (x - 0.05 * u, base - 1.42 * u), (x + 0.05 * u, base - 1.42 * u),
                    (x + 0.25 * u, base - 0.74 * u)], c)
    _paint(ctx, a)
    # cowl: white hood with a vane, turned by the wind
    cc = cowl or c
    sw = 0.03 * math.sin(t * 0.7)
    fill_poly(ctx, [(x - 0.07 * u, base - 1.41 * u), (x - 0.08 * u, base - 1.55 * u), (x + (0.02 + sw) * u, base - 1.6 * u),
                    (x + (0.12 + sw) * u, base - 1.52 * u), (x + 0.07 * u, base - 1.41 * u)], cc, a)
    line(ctx, [(x + (0.06 + sw) * u, base - 1.54 * u), (x + (0.2 + sw) * u, base - 1.6 * u)], cc, max(1.5, 0.012 * u), a)


def oak_tree(ctx, x, base, h, c, seed=3, t=0.0, wind=1.0, a=1.0, lean=0.0):
    """Broad English oak: short thick trunk, a few big limbs, a wide lumpy crown that sways a little."""
    rnd = random.Random(seed)
    _grp(ctx)
    tw = h * 0.09
    sway = 0.006 * h * wind * math.sin(t * 1.3)
    fill_poly(ctx, [(x - tw * 1.3, base + 2), (x - tw * 0.55, base - h * 0.25), (x - tw * 0.5 + lean * h, base - h * 0.45),
                    (x + tw * 0.5 + lean * h, base - h * 0.45), (x + tw * 0.6, base - h * 0.25), (x + tw * 1.4, base + 2)], c)
    for ang, L in ((-0.9, 0.35), (-0.4, 0.3), (0.35, 0.32), (0.85, 0.36), (0.05, 0.28)):
        x0, y0 = x + lean * h, base - h * 0.42
        x1, y1 = x0 + math.sin(ang) * h * L, y0 - math.cos(ang) * h * L * 0.8
        line(ctx, [(x0, y0), ((x0 + x1) / 2 + sway, (y0 + y1) / 2), (x1 + sway, y1)], c, tw * 0.45)
    # crown: clusters of circles, wider than tall, flat-ish underside
    cx, cy = x + lean * h + sway * 2, base - h * 0.68
    for _ in range(46):
        ang = rnd.uniform(0, TAU)
        rr = rnd.uniform(0.0, 1.0) ** 0.6
        px = cx + math.cos(ang) * rr * h * 0.62
        py = cy + math.sin(ang) * rr * h * 0.3 - h * 0.02
        r = h * rnd.uniform(0.1, 0.17)
        if py > cy + h * 0.2:
            py = cy + h * 0.2
        circle(ctx, px + sway * rnd.uniform(0.5, 1.5), py, r, c)
    _paint(ctx, a)
    # a few leaves flutter off the edge (dotted) - silhouette detail
    for k in range(10):
        ang = rnd.uniform(0, TAU)
        px = cx + math.cos(ang) * h * 0.75 + sway * 3
        py = cy + math.sin(ang) * h * 0.36
        ellipse(ctx, px, py, h * 0.018, h * 0.01, c, a, rot=ang + t)


def hedgerow(ctx, y, x0, x1, c, seed, h=40, a=1.0, trees=True):
    rnd = random.Random(seed)
    _grp(ctx)
    x = x0
    while x < x1:                                        # lumpy, overlapping bushes (not a string of beads)
        r = rnd.uniform(0.35, 1.05) * h
        circle(ctx, x, y - r * rnd.uniform(0.3, 0.7), r, c)
        if rnd.random() < 0.5:
            circle(ctx, x + r * 0.4, y - r * rnd.uniform(0.6, 1.1), r * rnd.uniform(0.4, 0.7), c)
        x += r * rnd.uniform(0.45, 0.85)
    rect(ctx, x0 - h, y - h * 0.3, x1 - x0 + 2 * h, h * 0.3 + 4, c)
    if trees:                                            # standard trees poking out of the hedge
        x = x0 + rnd.uniform(100, 400)
        while x < x1:
            th = h * rnd.uniform(2.5, 4.5)
            for _ in range(8):
                circle(ctx, x + rnd.uniform(-th * 0.3, th * 0.3), y - th * rnd.uniform(0.5, 0.9), th * rnd.uniform(0.18, 0.28), c)
            rect(ctx, x - h * 0.08, y - th * 0.5, h * 0.16, th * 0.5, c)
            x += rnd.uniform(350, 800)
    _paint(ctx, a)


def rolling_field(ctx, y, amp, c, seed, x0=-200, x1=W + 200, bottom=H + 50, freq=1.0, a=1.0, tilt=0.0):
    rnd = random.Random(seed)
    comps = [(rnd.uniform(0.6, 1.4) * freq * k, rnd.uniform(0, TAU), amp / k) for k in (1, 2.2, 4.7)]
    pts = [(x0, bottom)]
    for xx in range(int(x0), int(x1) + 1, 16):
        yy = y + sum(A * math.sin(xx / 320 * f + p) for f, p, A in comps) + tilt * (xx - W / 2)
        pts.append((xx, yy))
    pts.append((x1, bottom))
    fill_poly(ctx, pts, c, a)


def field_stripes(ctx, y0, y1, c, a=0.18, n=7, tilt=0.0):
    """Ploughed / mown stripes converging slightly - gives the ground a sense of perspective."""
    for k in range(n):
        yy = y0 + (y1 - y0) * (k / n) ** 1.6
        line(ctx, [(-100, yy + tilt * (-100 - W / 2)), (W + 100, yy + tilt * (W + 100 - W / 2))], c, 2 + k * 1.5, a)


def cumulus(ctx, x, y, w, c, seed, a=1.0, flat=True, shade=None):
    """Flat stylised cumulus: lumpy top, flat base. Optional darker shade band along the base."""
    rnd = random.Random(seed)
    _grp(ctx)
    n = max(5, int(w / 40))
    for i in range(n):
        tt = i / (n - 1)
        bump = math.sin(math.pi * tt) ** 0.7
        r = w * (0.08 + 0.16 * bump) * rnd.uniform(0.8, 1.2)
        circle(ctx, x - w / 2 + w * tt, y - r * 0.55 - bump * w * 0.08, r, c)
    if flat:
        ctx.set_operator(cairo.OPERATOR_CLEAR)
        rect(ctx, x - w, y, 2 * w, w, "#000000")
        ctx.set_operator(cairo.OPERATOR_OVER)
    if shade:
        g = cairo.LinearGradient(0, y - w * 0.22, 0, y)
        sc = hx(shade)
        g.add_color_stop_rgba(0, *sc, 0.0); g.add_color_stop_rgba(1, *sc, 0.85)
        ctx.save(); ctx.set_operator(cairo.OPERATOR_ATOP)
        ctx.rectangle(x - w, y - w * 0.22, 2 * w, w * 0.22); ctx.set_source(g); ctx.fill()
        ctx.restore()
    _paint(ctx, a)


def cloud_bank(ctx, y, c, seed, t=0.0, speed=20.0, scale=1.0, a=1.0, shade=None, count=7, spread=None):
    rnd = random.Random(seed)
    span = W + 900
    for i in range(count):
        w = rnd.uniform(260, 620) * scale
        x = (rnd.uniform(0, span) - t * speed * rnd.uniform(0.8, 1.2)) % span - 450
        cumulus(ctx, x, y + rnd.uniform(-40, 40) * scale, w, c, seed * 13 + i, a, shade=shade)


def grass(ctx, y, x0, x1, h, c, seed, t=0.0, wind=1.0, density=7, a=1.0):
    """Foreground grass blades swaying in the wind."""
    rnd = random.Random(seed)
    _grp(ctx)
    x = x0
    while x < x1:
        hh = h * rnd.uniform(0.4, 1.0)
        lean = rnd.uniform(-0.2, 0.35) + 0.12 * wind * math.sin(t * 2.2 + x * 0.013)
        tip = (x + math.sin(lean) * hh, y - math.cos(lean) * hh)
        fill_poly(ctx, [(x - 3, y + 2), ((x + tip[0]) / 2 + lean * 6, (y + tip[1]) / 2), tip, (x + 3, y + 2)], c)
        x += rnd.uniform(0.5, 1.5) * density
    rect(ctx, x0, y, x1 - x0, H - y + 20, c)
    _paint(ctx, a)


def wildflowers(ctx, y, x0, x1, c, seed, n=20, t=0.0):
    rnd = random.Random(seed)
    for _ in range(n):
        x = rnd.uniform(x0, x1)
        hh = rnd.uniform(20, 60)
        sw = 3 * math.sin(t * 2 + x)
        line(ctx, [(x, y), (x + sw, y - hh)], c, 2)
        circle(ctx, x + sw, y - hh, rnd.uniform(4, 7), c)


# ---------------------------------------------------------------- richer skies
CLOUD_TONES = {
    # shadow, body, lit, highlight
    "gold": ("#a89e98", "#dcd0c0", "#f7ebd6", "#fffbf0"),
    "red": ("#34161f", "#6e2d30", "#c46246", "#ffb46e"),
    "dusk": ("#6a3a3a", "#a86a5a", "#dca080", "#f6d0a8"),
}


def tones_mix(a, b, t):
    return tuple(mix(x, y, t) for x, y in zip(CLOUD_TONES[a], CLOUD_TONES[b]))


def cumulus_rich(ctx, x, y, w, tones, seed, a=1.0, light=(0.55, -0.85), tower=0.6, t=0.0):
    """Realistic cumulus from the pre-rendered sprite library (silhouette_kit/clouds.py): flat base on y, w wide,
    coloured with tones = (shadow, body, lit, highlight). The sun is on the right; light[0] < 0 mirrors it."""
    from . import clouds
    clouds.draw(ctx, x, y, w * 1.1, tones, clouds.pick(seed, tower), a, flip=light[0] < 0)


def cumulus_cel(ctx, x, y, w, tones, seed, a=1.0, light=(0.55, -0.85), tower=0.6, t=0.0):
    """Cel-shaded cumulus (the old flat look): one puffy mass (optional tower) with a flat base. The whole mass is lit as a unit:
    a lit crescent on the side facing `light`, a thin hot rim inside it, and a shadowed underside.
    tones = (shadow, body, lit, highlight)."""
    rnd = random.Random(seed)
    sh, body, lit, hi = [hx(c) if isinstance(c, str) else c for c in tones]
    puffs = []
    n = max(7, int(w / 26))
    for i in range(n):
        tt = i / (n - 1)
        dome = math.sin(math.pi * tt) ** 0.8
        tw = tower * math.exp(-((tt - 0.45) / 0.18) ** 2)
        r = w * (0.06 + 0.11 * dome + 0.07 * tw) * rnd.uniform(0.85, 1.15)
        cy = y - r * 0.45 - dome * w * 0.07 - tw * w * 0.22
        puffs.append((x - w / 2 + w * tt + rnd.uniform(-w * 0.015, w * 0.015), cy, r))
        if tw > 0.25 or rnd.random() < 0.3:
            puffs.append((puffs[-1][0] + rnd.uniform(-r, r) * 0.5, cy - r * rnd.uniform(0.55, 0.85),
                          r * rnd.uniform(0.55, 0.75)))

    def mass(dx=0.0, dy=0.0, k=1.0):
        for px, py, r in puffs:
            ctx.new_sub_path(); ctx.arc(px + dx, py + dy, r * k, 0, TAU)

    lx, ly = light
    d = w * 0.09
    ctx.push_group()
    mass(); ctx.set_source_rgb(*lit); ctx.fill()                              # lit everywhere ...
    ctx.set_operator(cairo.OPERATOR_ATOP)
    mass(-lx * d, -ly * d); ctx.set_source_rgb(*body); ctx.fill()            # ... except away from the light
    ctx.set_operator(cairo.OPERATOR_OVER)
    ctx.save()
    mass(); ctx.clip()
    ctx.push_group()                                                          # thin hot rim on the lit edge
    mass(); ctx.set_source_rgb(*hi); ctx.fill()
    ctx.set_operator(cairo.OPERATOR_DEST_OUT)
    mass(-lx * d * 0.22, -ly * d * 0.22); ctx.set_source_rgb(0, 0, 0); ctx.fill()
    ctx.set_operator(cairo.OPERATOR_OVER)
    ctx.pop_group_to_source(); ctx.paint_with_alpha(0.7)
    g = cairo.LinearGradient(0, y - w * 0.26, 0, y)                           # shadowed underside
    g.add_color_stop_rgba(0, *sh, 0.0); g.add_color_stop_rgba(0.75, *sh, 0.7); g.add_color_stop_rgba(1, *sh, 0.95)
    ctx.rectangle(x - w, y - w * 0.26, 2 * w, w * 0.26); ctx.set_source(g); ctx.fill()
    ctx.restore()
    ctx.set_operator(cairo.OPERATOR_CLEAR)
    rect(ctx, x - w, y, 2 * w, w * 2, "#000000")                              # flat base
    ctx.set_operator(cairo.OPERATOR_OVER)
    for k in range(3):                                                        # torn wisps under the base
        wx = x + rnd.uniform(-0.45, 0.45) * w
        ellipse(ctx, wx + 20 * math.sin(t * 0.3 + k), y + w * 0.006, w * rnd.uniform(0.1, 0.22), w * 0.01, sh, 0.5)
    ctx.pop_group_to_source(); ctx.paint_with_alpha(a)


def stratus(ctx, y, h, tone, seed, t=0.0, speed=10.0, a=0.6, n=10):
    """Long hazy bands (distant cloud layers)."""
    rnd = random.Random(seed)
    for _ in range(n):
        w = rnd.uniform(300, 900)
        x = (rnd.uniform(0, W + 1200) - t * speed) % (W + 1200) - 600
        ellipse(ctx, x, y + rnd.uniform(-h, h), w, h * rnd.uniform(0.25, 0.6), tone, a * rnd.uniform(0.5, 1.0))


def cirrus(ctx, y0, y1, tone, seed, t=0.0, a=0.35, n=14):
    """High thin streaks."""
    rnd = random.Random(seed)
    for _ in range(n):
        x = (rnd.uniform(0, W + 600) - t * 6) % (W + 600) - 300
        y = rnd.uniform(y0, y1)
        L = rnd.uniform(120, 420)
        pts = [(x + L * q / 8, y - 18 * math.sin(q / 8 * math.pi) + q * 1.5) for q in range(9)]
        line(ctx, pts, tone, rnd.uniform(2, 5), a * rnd.uniform(0.5, 1.0))


def cloud_deck(ctx, T, tones, seed=0, horizon=820, scroll=0.0, speed=1.0, haze=None, density=1.0, scale=1.0, a=1.0):
    """One continuous far cloud bank along the horizon: two rows of overlapping cumulus sprites (a hazier back row
    with towers, a front row of broad cumulus) that merge into a single mass, sitting on a soft haze floor.
    `scroll` is the horizontal camera offset in px (already scaled for distance); drift is slow."""
    from . import clouds
    rnd = random.Random(seed)
    span = W + 2000
    hz = haze or tones[2]
    rows = ((horizon - 40, (420, 900), 0.4, 0.5, 0.92, 0.6, 1.0),        # yb, widths, spacing, haze, alpha, tower, par
            (horizon + 25, (620, 980), 0.42, 0.25, 1.0, 0.45, 1.25))
    for r, (yb, (w0, w1), sp, hm, al, tw, par) in enumerate(rows):
        tn = tuple(mix(c, hz, hm) for c in tones) if haze else tones
        sp = sp + 0.25 * (1 - min(1.0, density))
        x, k = rnd.uniform(0, 300), 0
        items = []
        while x < span:
            wd = rnd.uniform(w0, w1) * scale
            items.append((x, wd, rnd.uniform(-14, 14) * scale, min(1.0, max(0.0, tw + rnd.uniform(-0.5, 0.5))), k))
            x += wd * sp * rnd.uniform(0.8, 1.15)
            k += 1
        off = scroll * par + T * speed * 4 * par
        for x0, wd, dy, twk, k in items:
            xx = (x0 - off) % span - 1000
            if -wd < xx < W + wd:
                clouds.draw(ctx, xx, yb + dy, wd, tn, clouds.pick(seed * 97 + r * 31 + k, twk), al * a, flip=False)
    # haze floor: the bases dissolve into the distant murk instead of ending on a hard line
    fl = mix(tones[1], hz, 0.6)
    g = cairo.LinearGradient(0, horizon - 30, 0, horizon + 420)
    g.add_color_stop_rgba(0, *fl, 0.0)
    g.add_color_stop_rgba(0.2, *fl, 0.85 * a)
    g.add_color_stop_rgba(1, *fl, 0.55 * a)
    ctx.rectangle(-200, horizon - 30, W + 400, 2000); ctx.set_source(g); ctx.fill()


def sky_clouds(ctx, T, tones, seed=0, scroll=0.0, speed=1.0, density=1.0, haze=None, horizon=820, scale=1.0):
    """Far cloudscape: high cirrus plus one continuous cumulus bank on the horizon (see cloud_deck)."""
    cirrus(ctx, 60, 260, tones[2], seed + 1, t=T, a=0.25)
    cloud_deck(ctx, T, tones, seed + 3, horizon=horizon, scroll=scroll, speed=speed, haze=haze, density=density,
               scale=scale)