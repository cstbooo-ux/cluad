"""Detailed flat-silhouette props: architecture, landmarks, vehicles, aircraft, vegetation."""
import math, random
import cairo
from lib import hx, mix, src, poly, fill_poly, rect, circle, ellipse, line, W, H

TAU = 2 * math.pi


def _group(ctx):
    ctx.push_group()


def _paint(ctx, a=1.0):
    ctx.pop_group_to_source()
    ctx.paint_with_alpha(a)


def _clear(ctx):
    ctx.set_operator(cairo.OPERATOR_CLEAR)


def _over(ctx):
    ctx.set_operator(cairo.OPERATOR_OVER)


# ================================================================ architecture
def facade(ctx, x, base, w, h, c, rnd, roof="mansard", damage=0.0, lit=0.0, lit_c="#f2a65a",
           holes=True, floors=None, a=1.0, chimneys=True):
    """European city block: cornices, roof (mansard/gable/flat), dormers, chimneys,
    window holes, optional lit windows and war damage (jagged top + shell holes)."""
    _group(ctx)
    top = base - h
    floors = floors or max(2, int(h / 78))
    fh = h * 0.9 / floors
    rect(ctx, x, top, w, h, c)
    # cornice + string course
    rect(ctx, x - 7, top - 4, w + 14, 10, c)
    rect(ctx, x - 5, top + 6, w + 10, 4, c)
    rect(ctx, x - 4, base - fh * 1.05, w + 8, 6, c)
    if roof == "mansard":
        rh = min(80, h * 0.22)
        fill_poly(ctx, [(x - 2, top - 4), (x + 16, top - rh), (x + w - 16, top - rh), (x + w + 2, top - 4)], c)
        for k in range(max(1, int(w / 70))):
            dx = x + 30 + k * (w - 60) / max(1, int(w / 70) - 1 or 1)
            if dx > x + w - 30:
                break
            fill_poly(ctx, [(dx - 11, top - 8), (dx - 11, top - rh * 0.62), (dx, top - rh * 0.8), (dx + 11, top - rh * 0.62),
                            (dx + 11, top - 8)], c)
        rtop = top - rh
    elif roof == "gable":
        rh = min(w * 0.35, 110)
        fill_poly(ctx, [(x - 8, top - 2), (x + w / 2, top - rh), (x + w + 8, top - 2)], c)
        rtop = top - rh * 0.6
    else:
        for k in range(int(w / 16) + 1):     # balustrade
            rect(ctx, x + k * 16, top - 16, 7, 14, c)
        rect(ctx, x - 4, top - 20, w + 8, 5, c)
        rtop = top - 18
    if chimneys:
        for _ in range(rnd.randint(1, 3)):
            cx = x + rnd.uniform(0.1, 0.85) * w
            ch = rnd.uniform(28, 55)
            rect(ctx, cx, rtop - ch + 12, 16, ch, c)
            rect(ctx, cx - 3, rtop - ch + 10, 22, 6, c)
    # windows
    cols = max(2, int(w / 46))
    wins = []
    for j in range(floors):
        for i in range(cols):
            ww, wh = w / cols * 0.42, fh * 0.52
            wx = x + (i + 0.5) * w / cols - ww / 2
            wy = top + 22 + j * fh + fh * 0.18
            if wy + wh > base - 4:
                continue
            wins.append((wx, wy, ww, wh))
    for wx, wy, ww, wh in wins:
        if rnd.random() < lit:
            rect(ctx, wx, wy, ww, wh, lit_c)
            rect(ctx, wx + ww / 2 - 1, wy, 2, wh, c)              # mullion
            rect(ctx, wx, wy + wh * 0.4, ww, 2, c)
        elif holes:
            _clear(ctx); ctx.rectangle(wx, wy, ww, wh); ctx.fill(); _over(ctx)
            rect(ctx, wx + ww / 2 - 1, wy, 2, wh, c)
            rect(ctx, wx, wy + wh * 0.4, ww, 2, c)
        rect(ctx, wx - 3, wy + wh, ww + 6, 4, c)                   # sill
    # damage: bite the top off + shell holes
    if damage > 0:
        _clear(ctx)
        pts = [(x - 20, top - 200)]
        n = rnd.randint(4, 7)
        for i in range(n + 1):
            px = x - 10 + (w + 20) * i / n
            py = top - 200 + 200 + rnd.uniform(0, h * 0.55 * damage) * (0.3 + 0.7 * rnd.random())
            pts.append((px, py))
            if rnd.random() < 0.5:
                pts.append((px + rnd.uniform(4, 14), py + rnd.uniform(-30, 30)))
        pts.append((x + w + 20, top - 200))
        poly(ctx, pts); ctx.fill()
        for _ in range(int(3 * damage)):
            hx_, hy_ = x + rnd.uniform(0.15, 0.85) * w, top + rnd.uniform(0.2, 0.7) * h
            r = rnd.uniform(12, 30)
            pts = [(hx_ + math.cos(k / 9 * TAU) * r * rnd.uniform(0.6, 1.2),
                    hy_ + math.sin(k / 9 * TAU) * r * rnd.uniform(0.6, 1.2)) for k in range(9)]
            poly(ctx, pts); ctx.fill()
        _over(ctx)
        # rebar / broken beams sticking out
        for _ in range(int(4 * damage)):
            bx = x + rnd.uniform(0, w)
            by = top + rnd.uniform(0.1, 0.45) * h
            line(ctx, [(bx, by + 30), (bx + rnd.uniform(-18, 18), by - rnd.uniform(10, 30))], c, 2.5)
    _paint(ctx, a)


def ruin_wall(ctx, x, base, w, h, c, rnd, a=1.0):
    """Free-standing shell of a bombed building: arched window holes, jagged edges."""
    _group(ctx)
    pts = [(x, base)]
    n = 7
    for i in range(n + 1):
        pts.append((x + w * i / n + rnd.uniform(-6, 6), base - h * rnd.uniform(0.45, 1.0) if 0 < i < n else base - h * rnd.uniform(0.5, 0.8)))
    pts.append((x + w, base))
    fill_poly(ctx, pts, c)
    _clear(ctx)
    cols = max(2, int(w / 60))
    for j in range(2):
        for i in range(cols):
            ww = w / cols * 0.45
            wx = x + (i + 0.5) * w / cols - ww / 2
            wy = base - h * (0.38 + 0.3 * j)
            ctx.rectangle(wx, wy, ww, h * 0.18)
            ctx.arc(wx + ww / 2, wy, ww / 2, math.pi, TAU)
            ctx.fill()
    _over(ctx)
    _paint(ctx, a)


def rubble(ctx, x0, x1, base, hmax, c, seed, bricks=True, beams=True):
    rnd = random.Random(seed)
    pts = [(x0, base + 40)]
    n = max(4, int((x1 - x0) / 30))
    for i in range(n + 1):
        t = i / n
        env = max(0.0, math.sin(math.pi * t)) ** 0.7
        pts.append((x0 + (x1 - x0) * t, base - hmax * env * rnd.uniform(0.55, 1.0)))
    pts.append((x1, base + 40))
    fill_poly(ctx, pts, c)
    if bricks:
        for _ in range(n):
            bx = rnd.uniform(x0, x1); t = (bx - x0) / (x1 - x0)
            by = base - hmax * max(0.0, math.sin(math.pi * t)) ** 0.7 * 0.8
            ctx.save(); ctx.translate(bx, by); ctx.rotate(rnd.uniform(-0.6, 0.6))
            rect(ctx, -9, -7, 18, 9, c); ctx.restore()
    if beams:
        for _ in range(max(1, n // 5)):
            bx = rnd.uniform(x0 + 20, x1 - 20); t = (bx - x0) / (x1 - x0)
            by = base - hmax * max(0.0, math.sin(math.pi * t)) ** 0.7 * 0.7
            ang = rnd.uniform(-1.1, 1.1)
            L = rnd.uniform(60, 130)
            line(ctx, [(bx, by), (bx + math.sin(ang) * L, by - math.cos(ang) * L)], c, rnd.uniform(5, 9), cap=cairo.LINE_CAP_BUTT)


def street_lamp(ctx, x, base, s, c, lit=None, t=0.0):
    rect(ctx, x - 9 * s, base - 30 * s, 18 * s, 30 * s, c)
    line(ctx, [(x, base - 20 * s), (x, base - 300 * s)], c, 7 * s)
    line(ctx, [(x, base - 270 * s), (x + 14 * s, base - 282 * s), (x, base - 300 * s)], c, 3 * s)
    fill_poly(ctx, [(x - 15 * s, base - 300 * s), (x - 20 * s, base - 340 * s), (x, base - 355 * s),
                    (x + 20 * s, base - 340 * s), (x + 15 * s, base - 300 * s)], c)
    if lit:
        from lib import glow
        fill_poly(ctx, [(x - 11 * s, base - 305 * s), (x - 14 * s, base - 336 * s), (x + 14 * s, base - 336 * s),
                        (x + 11 * s, base - 305 * s)], lit)
        glow(ctx, x, base - 322 * s, 70 * s, lit, 0.3 + 0.03 * math.sin(t * 20))


def telegraph_poles(ctx, x0, x1, base, h, gap, c, sag=26):
    xs = []
    x = x0
    while x < x1 + gap:
        xs.append(x); x += gap
    for px in xs:
        line(ctx, [(px, base), (px, base - h)], c, 6, cap=cairo.LINE_CAP_BUTT)
        line(ctx, [(px - 30, base - h + 12), (px + 30, base - h + 12)], c, 4)
        line(ctx, [(px - 22, base - h + 30), (px + 22, base - h + 30)], c, 3)
    for dy, dx in ((12, -26), (12, 26), (30, -18), (30, 18)):
        for a_, b_ in zip(xs[:-1], xs[1:]):
            pts = [(a_ + dx + (b_ - a_) * k / 12, base - h + dy + sag * math.sin(math.pi * k / 12)) for k in range(13)]
            line(ctx, pts, c, 1.4)


# ---------------------------------------------------------------- landmarks
def eiffel(ctx, cx, base, h, c, a=1.0):
    _group(ctx)
    L = []
    prof = [(0.0, 0.2), (0.06, 0.165), (0.12, 0.135), (0.18, 0.118), (0.26, 0.09), (0.38, 0.062), (0.5, 0.04),
            (0.65, 0.026), (0.8, 0.017), (0.86, 0.014)]
    left = [(cx - w * h, base - y * h) for y, w in prof]
    right = [(cx + w * h, base - y * h) for y, w in reversed(prof)]
    fill_poly(ctx, left + right, c)
    # platforms
    for y, w, th in ((0.18, 0.14, 0.022), (0.38, 0.075, 0.016), (0.86, 0.022, 0.018)):
        rect(ctx, cx - w * h, base - y * h - th * h, 2 * w * h, th * h, c)
    rect(ctx, cx - 0.01 * h, base - 0.95 * h, 0.02 * h, 0.08 * h, c)
    line(ctx, [(cx, base - 0.95 * h), (cx, base - 1.0 * h)], c, 0.006 * h)
    # arches + lattice
    _clear(ctx)
    ctx.move_to(cx - 0.135 * h, base + 2)
    ctx.curve_to(cx - 0.13 * h, base - 0.1 * h, cx + 0.13 * h, base - 0.1 * h, cx + 0.135 * h, base + 2)
    ctx.close_path(); ctx.fill()
    ctx.move_to(cx - 0.07 * h, base - 0.2 * h)
    ctx.curve_to(cx - 0.06 * h, base - 0.3 * h, cx + 0.06 * h, base - 0.3 * h, cx + 0.07 * h, base - 0.2 * h)
    ctx.close_path(); ctx.fill()
    ctx.save()
    ctx.rectangle(cx - h, base - 0.8 * h, 2 * h, 0.58 * h); ctx.rectangle(cx - h, base - 0.175 * h, 2 * h, 0.17 * h)
    ctx.clip()
    ctx.set_line_width(max(1.2, 0.0035 * h))
    for k in range(-40, 40):
        x0 = cx + k * 0.012 * h
        ctx.move_to(x0, base - 0.02 * h); ctx.line_to(x0 + 0.4 * h, base - 0.62 * h)
        ctx.move_to(x0, base - 0.02 * h); ctx.line_to(x0 - 0.4 * h, base - 0.62 * h)
    ctx.stroke(); ctx.restore()
    _over(ctx)
    # re-seal the outer edges
    line(ctx, left, c, 0.008 * h); line(ctx, right, c, 0.008 * h)
    _paint(ctx, a)


def big_ben(ctx, x, base, h, c, clock_c=None, a=1.0):
    _group(ctx)
    w = 0.12 * h
    rect(ctx, x - w / 2, base - 0.62 * h, w, 0.62 * h, c)
    for k in range(6):                       # vertical buttress lines
        rect(ctx, x - w / 2 - 3, base - 0.62 * h + k * 0.1 * h, w + 6, 4, c)
    rect(ctx, x - w * 0.58, base - 0.76 * h, w * 1.16, 0.14 * h, c)
    rect(ctx, x - w * 0.62, base - 0.765 * h, w * 1.24, 0.012 * h, c)
    rect(ctx, x - w * 0.5, base - 0.82 * h, w, 0.055 * h, c)
    fill_poly(ctx, [(x - w * 0.55, base - 0.82 * h), (x, base - 1.0 * h), (x + w * 0.55, base - 0.82 * h)], c)
    for dx in (-0.55, 0.55, -0.3, 0.3):
        fill_poly(ctx, [(x + dx * w - 4, base - 0.82 * h), (x + dx * w, base - 0.88 * h), (x + dx * w + 4, base - 0.82 * h)], c)
    line(ctx, [(x, base - 1.0 * h), (x, base - 1.05 * h)], c, 3)
    if clock_c:
        circle(ctx, x, base - 0.69 * h, 0.04 * h, clock_c)
        line(ctx, [(x, base - 0.69 * h), (x + 0.02 * h, base - 0.7 * h)], c, 2.5)
        line(ctx, [(x, base - 0.69 * h), (x - 0.004 * h, base - 0.72 * h)], c, 2.5)
    else:
        _clear(ctx); ctx.arc(x, base - 0.69 * h, 0.04 * h, 0, TAU); ctx.fill(); _over(ctx)
        circle(ctx, x, base - 0.69 * h, 0.028 * h, c)
    _paint(ctx, a)


def parliament(ctx, x0, x1, base, h, c, a=1.0):
    _group(ctx)
    rect(ctx, x0, base - h, x1 - x0, h, c)
    k = x0
    while k < x1:
        fill_poly(ctx, [(k - 4, base - h), (k, base - h - 34), (k + 4, base - h)], c)
        rect(ctx, k - 3, base - h - 14, 6, 14, c)
        k += 36
    for k in range(int(x0) + 20, int(x1) - 20, 26):
        _clear(ctx); ctx.rectangle(k, base - h * 0.75, 9, h * 0.35); ctx.arc(k + 4.5, base - h * 0.75, 4.5, math.pi, TAU)
        ctx.fill(); _over(ctx)
    _paint(ctx, a)


def dome_church(ctx, cx, base, s, c, a=1.0):
    """St Paul's style: portico block, drum with columns, dome, lantern."""
    _group(ctx)
    rect(ctx, cx - 0.9 * s, base - 0.45 * s, 1.8 * s, 0.45 * s, c)
    rect(ctx, cx - 0.5 * s, base - 0.7 * s, 1.0 * s, 0.26 * s, c)
    for side in (-1, 1):                     # west towers
        tx = cx + side * 0.75 * s
        rect(ctx, tx - 0.1 * s, base - 0.95 * s, 0.2 * s, 0.5 * s, c)
        ellipse(ctx, tx, base - 0.95 * s, 0.1 * s, 0.14 * s, c)
        line(ctx, [(tx, base - 1.08 * s), (tx, base - 1.18 * s)], c, 0.02 * s)
    rect(ctx, cx - 0.36 * s, base - 0.98 * s, 0.72 * s, 0.3 * s, c)
    ctx.save(); ctx.translate(cx, base - 0.98 * s); ctx.scale(0.36 * s, 0.4 * s)
    ctx.arc(0, 0, 1, math.pi, TAU); ctx.restore(); src(ctx, c); ctx.fill()
    rect(ctx, cx - 0.05 * s, base - 1.5 * s, 0.1 * s, 0.14 * s, c)
    circle(ctx, cx, base - 1.52 * s, 0.04 * s, c)
    line(ctx, [(cx, base - 1.52 * s), (cx, base - 1.64 * s)], c, 0.015 * s)
    _clear(ctx)
    for k in range(7):
        ctx.rectangle(cx - 0.3 * s + k * 0.1 * s, base - 0.95 * s, 0.035 * s, 0.2 * s)
    ctx.fill(); _over(ctx)
    _paint(ctx, a)


def barrage_balloon(ctx, x, y, s, c, cable_to=None, a=1.0):
    _group(ctx)
    ellipse(ctx, x, y, s, s * 0.36, c)
    fill_poly(ctx, [(x - s * 0.6, y - s * 0.15), (x - s * 1.2, y - s * 0.55), (x - s * 1.05, y - s * 0.1)], c)
    fill_poly(ctx, [(x - s * 0.6, y + s * 0.15), (x - s * 1.2, y + s * 0.55), (x - s * 1.05, y + s * 0.1)], c)
    fill_poly(ctx, [(x - s * 0.7, y), (x - s * 1.15, y - s * 0.05), (x - s * 1.15, y + s * 0.05)], c)
    if cable_to:
        line(ctx, [(x + s * 0.1, y + s * 0.34), (cable_to, H)], c, 1.5)
    _paint(ctx, a)


def onion_tower(ctx, cx, base, w, h, c, dome_w=None):
    """Drum + onion dome + tip (St Basil's style)."""
    dw = dome_w or w * 1.35
    rect(ctx, cx - w / 2, base - h, w, h, c)
    rect(ctx, cx - w * 0.6, base - h, w * 1.2, 6, c)
    y0 = base - h
    ctx.move_to(cx - w * 0.45, y0)
    ctx.curve_to(cx - dw * 0.75, y0 - dw * 0.35, cx - dw * 0.55, y0 - dw * 0.8, cx, y0 - dw * 1.25)
    ctx.curve_to(cx + dw * 0.55, y0 - dw * 0.8, cx + dw * 0.75, y0 - dw * 0.35, cx + w * 0.45, y0)
    ctx.close_path(); src(ctx, c); ctx.fill()
    line(ctx, [(cx, y0 - dw * 1.2), (cx, y0 - dw * 1.55)], c, max(2, w * 0.06))
    line(ctx, [(cx - dw * 0.12, y0 - dw * 1.45), (cx + dw * 0.12, y0 - dw * 1.45)], c, max(1.5, w * 0.04))


def st_basil(ctx, cx, base, s, c, a=1.0):
    _group(ctx)
    rect(ctx, cx - 0.8 * s, base - 0.3 * s, 1.6 * s, 0.3 * s, c)
    rect(ctx, cx - 0.6 * s, base - 0.42 * s, 1.2 * s, 0.14 * s, c)
    # central tent spire
    rect(ctx, cx - 0.1 * s, base - 0.8 * s, 0.2 * s, 0.4 * s, c)
    fill_poly(ctx, [(cx - 0.12 * s, base - 0.8 * s), (cx, base - 1.35 * s), (cx + 0.12 * s, base - 0.8 * s)], c)
    onion_tower(ctx, cx, base - 1.3 * s, 0.03 * s, 0.02 * s, c, dome_w=0.07 * s)
    for dx, hh, w in ((-0.6, 0.55, 0.13), (-0.33, 0.72, 0.15), (0.33, 0.7, 0.15), (0.62, 0.5, 0.12), (-0.18, 0.5, 0.1),
                      (0.2, 0.52, 0.1)):
        onion_tower(ctx, cx + dx * s, base, w * s, hh * s, c)
    line(ctx, [(cx + 0.95 * s, base), (cx + 0.95 * s, base - 0.9 * s)], c, 0.05 * s, cap=cairo.LINE_CAP_BUTT)
    fill_poly(ctx, [(cx + 0.9 * s, base - 0.9 * s), (cx + 0.95 * s, base - 1.1 * s), (cx + 1.0 * s, base - 0.9 * s)], c)
    _paint(ctx, a)


def kremlin_wall(ctx, x0, x1, base, h, c):
    rect(ctx, x0, base - h, x1 - x0, h, c)
    k = x0
    while k < x1:                         # swallow-tail merlons
        fill_poly(ctx, [(k, base - h), (k, base - h - 26), (k + 7, base - h - 18), (k + 14, base - h - 26),
                        (k + 14, base - h)], c)
        k += 24


def pyramid(ctx, cx, base, w, h, lit_c, shade_c):
    fill_poly(ctx, [(cx - w / 2, base), (cx, base - h), (cx + w * 0.12, base)], lit_c)
    fill_poly(ctx, [(cx + w * 0.12, base), (cx, base - h), (cx + w / 2, base)], shade_c)


def palm(ctx, x, base, h, c, seed, lean=0.25, t=0.0, wind=1.0):
    rnd = random.Random(seed)
    top = (x + lean * h, base - h)
    ctrl = (x + lean * h * 0.15, base - h * 0.55)
    pts = []
    for k in range(13):
        tt = k / 12
        px = (1 - tt) ** 2 * x + 2 * (1 - tt) * tt * ctrl[0] + tt * tt * top[0]
        py = (1 - tt) ** 2 * base + 2 * (1 - tt) * tt * ctrl[1] + tt * tt * top[1]
        pts.append((px, py))
    for k in range(12):
        wdt = h * (0.05 - 0.025 * k / 12)
        line(ctx, [pts[k], pts[k + 1]], c, wdt, cap=cairo.LINE_CAP_BUTT)
        circle(ctx, pts[k][0], pts[k][1], wdt * 0.58, c)      # ring notches
    n = rnd.randint(7, 9)
    for i in range(n):
        ang = -math.pi + i / (n - 1) * math.pi + rnd.uniform(-0.15, 0.15) + 0.06 * wind * math.sin(t * 3 + i)
        L = h * rnd.uniform(0.38, 0.55)
        droop = 0.45 + 0.35 * abs(math.cos(ang))
        p0 = top
        p1 = (top[0] + math.cos(ang) * L * 0.55, top[1] + math.sin(ang) * L * 0.55 - L * 0.12)
        p2 = (top[0] + math.cos(ang) * L, top[1] + math.sin(ang) * L * 0.6 + L * droop)
        spine = []
        for k in range(11):
            tt = k / 10
            spine.append(((1 - tt) ** 2 * p0[0] + 2 * (1 - tt) * tt * p1[0] + tt * tt * p2[0],
                          (1 - tt) ** 2 * p0[1] + 2 * (1 - tt) * tt * p1[1] + tt * tt * p2[1]))
        up, dn = [], []
        for k, p in enumerate(spine):
            tt = k / 10
            ww = L * 0.09 * math.sin(math.pi * min(1, tt * 1.1)) + 1
            if k < 10:
                dx, dy = spine[k + 1][0] - p[0], spine[k + 1][1] - p[1]
            d = math.hypot(dx, dy) or 1
            nx, ny = -dy / d, dx / d
            jag = 1.0 if k % 2 else 0.55
            up.append((p[0] + nx * ww * jag, p[1] + ny * ww * jag))
            dn.append((p[0] - nx * ww * jag, p[1] - ny * ww * jag))
        fill_poly(ctx, up + dn[::-1], c)
    for i in range(3):
        circle(ctx, top[0] + rnd.uniform(-10, 10), top[1] + rnd.uniform(4, 16), h * 0.022, c)


def cypress(ctx, x, base, h, c):
    w = h * 0.13
    ctx.move_to(x, base)
    ctx.curve_to(x - w, base - h * 0.3, x - w * 0.8, base - h * 0.75, x, base - h)
    ctx.curve_to(x + w * 0.8, base - h * 0.75, x + w, base - h * 0.3, x, base)
    src(ctx, c); ctx.fill()


def leafy_tree(ctx, x, base, h, c, seed):
    rnd = random.Random(seed)
    line(ctx, [(x, base), (x + rnd.uniform(-8, 8), base - h * 0.45)], c, h * 0.06, cap=cairo.LINE_CAP_BUTT)
    _group(ctx)
    for _ in range(14):
        circle(ctx, x + rnd.uniform(-0.3, 0.3) * h, base - h * rnd.uniform(0.45, 0.9), h * rnd.uniform(0.12, 0.2), c)
    _paint(ctx)


def windmill(ctx, x, base, h, c, t=0.0):
    fill_poly(ctx, [(x - 0.16 * h, base), (x - 0.1 * h, base - 0.7 * h), (x + 0.1 * h, base - 0.7 * h), (x + 0.16 * h, base)], c)
    fill_poly(ctx, [(x - 0.12 * h, base - 0.7 * h), (x, base - 0.85 * h), (x + 0.12 * h, base - 0.7 * h)], c)
    hub = (x + 0.02 * h, base - 0.74 * h)
    for k in range(4):
        a_ = t * 0.8 + k * math.pi / 2
        tip = (hub[0] + math.cos(a_) * 0.55 * h, hub[1] + math.sin(a_) * 0.55 * h)
        line(ctx, [hub, tip], c, 0.02 * h)
        n = (-math.sin(a_), math.cos(a_))
        fill_poly(ctx, [(hub[0] + math.cos(a_) * 0.15 * h, hub[1] + math.sin(a_) * 0.15 * h),
                        (tip[0], tip[1]), (tip[0] + n[0] * 0.08 * h, tip[1] + n[1] * 0.08 * h),
                        (hub[0] + math.cos(a_) * 0.15 * h + n[0] * 0.08 * h, hub[1] + math.sin(a_) * 0.15 * h + n[1] * 0.08 * h)], c, 0.85)


def farmhouse(ctx, x, base, s, c, lit=None):
    rect(ctx, x, base - 0.5 * s, s, 0.5 * s, c)
    fill_poly(ctx, [(x - 0.08 * s, base - 0.48 * s), (x + 0.5 * s, base - 0.95 * s), (x + 1.08 * s, base - 0.48 * s)], c)
    rect(ctx, x + 0.7 * s, base - 0.95 * s, 0.1 * s, 0.25 * s, c)
    if lit:
        rect(ctx, x + 0.2 * s, base - 0.36 * s, 0.14 * s, 0.14 * s, lit)
        rect(ctx, x + 0.62 * s, base - 0.36 * s, 0.14 * s, 0.14 * s, lit)


def abbey(ctx, cx, base, s, c):
    """Monte Cassino style hilltop monastery."""
    _group(ctx)
    rect(ctx, cx - s, base - 0.28 * s, 2 * s, 0.28 * s, c)
    rect(ctx, cx - 0.3 * s, base - 0.42 * s, 0.6 * s, 0.16 * s, c)
    fill_poly(ctx, [(cx - 0.33 * s, base - 0.42 * s), (cx, base - 0.52 * s), (cx + 0.33 * s, base - 0.42 * s)], c)
    rect(ctx, cx + 0.4 * s, base - 0.6 * s, 0.1 * s, 0.34 * s, c)
    fill_poly(ctx, [(cx + 0.39 * s, base - 0.6 * s), (cx + 0.45 * s, base - 0.68 * s), (cx + 0.51 * s, base - 0.6 * s)], c)
    _clear(ctx)
    for row in range(3):
        for k in range(22):
            ctx.rectangle(cx - 0.95 * s + k * 0.087 * s, base - 0.24 * s + row * 0.07 * s, 0.025 * s, 0.035 * s)
    ctx.fill(); _over(ctx)
    _paint(ctx)


# ================================================================ vehicles
def sherman(ctx, x, base, s, c, t=0.0, a=1.0):
    """US M4 side view facing right; s = hull length."""
    u = s
    _group(ctx)
    fill_poly(ctx, [(-0.5 * u + x, base - 0.1 * u), (-0.47 * u + x, base - 0.33 * u), (0.22 * u + x, base - 0.34 * u),
                    (0.5 * u + x, base - 0.22 * u), (0.52 * u + x, base - 0.1 * u)], c)
    ctx.move_to(x - 0.2 * u, base - 0.33 * u)
    ctx.curve_to(x - 0.2 * u, base - 0.52 * u, x + 0.18 * u, base - 0.55 * u, x + 0.2 * u, base - 0.33 * u)
    src(ctx, c); ctx.fill()
    rect(ctx, x - 0.08 * u, base - 0.56 * u, 0.1 * u, 0.04 * u, c)
    line(ctx, [(x + 0.15 * u, base - 0.44 * u), (x + 0.58 * u, base - 0.45 * u)], c, 0.03 * u, cap=cairo.LINE_CAP_BUTT)
    rect(ctx, x + 0.56 * u, base - 0.465 * u, 0.04 * u, 0.03 * u, c)
    line(ctx, [(x - 0.12 * u, base - 0.54 * u), (x - 0.14 * u, base - 0.78 * u)], c, 0.006 * u)   # antenna
    # tracks + bogies
    ctx.move_to(x - 0.5 * u, base - 0.06 * u)
    ctx.line_to(x + 0.52 * u, base - 0.06 * u)
    ctx.set_line_width(0.1 * u); ctx.set_line_cap(cairo.LINE_CAP_ROUND); src(ctx, c); ctx.stroke()
    _clear(ctx)
    for k in range(6):
        wx = x - 0.36 * u + k * 0.14 * u
        ctx.arc(wx, base - 0.07 * u, 0.042 * u, 0, TAU); ctx.fill()
    _over(ctx)
    for k in range(6):
        wx = x - 0.36 * u + k * 0.14 * u
        circle(ctx, wx, base - 0.07 * u, 0.018 * u, c)
        ctx.save(); ctx.translate(wx, base - 0.07 * u); ctx.rotate(-t * 8)
        rect(ctx, -0.04 * u, -0.005 * u, 0.08 * u, 0.01 * u, c); ctx.restore()
    _paint(ctx, a)


def panzer(ctx, x, base, s, c, t=0.0, a=1.0):
    """Boxy German-style medium tank with side skirts, long gun (no markings)."""
    u = s
    _group(ctx)
    fill_poly(ctx, [(x - 0.5 * u, base - 0.12 * u), (x - 0.5 * u, base - 0.3 * u), (x + 0.42 * u, base - 0.3 * u),
                    (x + 0.52 * u, base - 0.2 * u), (x + 0.5 * u, base - 0.1 * u)], c)
    fill_poly(ctx, [(x - 0.22 * u, base - 0.3 * u), (x - 0.2 * u, base - 0.46 * u), (x + 0.16 * u, base - 0.46 * u),
                    (x + 0.22 * u, base - 0.3 * u)], c)
    rect(ctx, x - 0.14 * u, base - 0.51 * u, 0.1 * u, 0.05 * u, c)
    line(ctx, [(x + 0.18 * u, base - 0.4 * u), (x + 0.82 * u, base - 0.41 * u)], c, 0.022 * u, cap=cairo.LINE_CAP_BUTT)
    rect(ctx, x + 0.8 * u, base - 0.425 * u, 0.05 * u, 0.03 * u, c)
    # side skirts with gaps
    for k in range(6):
        rect(ctx, x - 0.44 * u + k * 0.145 * u, base - 0.29 * u, 0.135 * u, 0.13 * u, c)
    line(ctx, [(x - 0.5 * u, base - 0.06 * u), (x + 0.5 * u, base - 0.06 * u)], c, 0.1 * u)
    _clear(ctx)
    for k in range(8):
        ctx.arc(x - 0.38 * u + k * 0.105 * u, base - 0.07 * u, 0.034 * u, 0, TAU); ctx.fill()
    _over(ctx)
    for k in range(8):
        circle(ctx, x - 0.38 * u + k * 0.105 * u, base - 0.07 * u, 0.014 * u, c)
    _paint(ctx, a)


def truck(ctx, x, base, s, c, a=1.0):
    u = s
    _group(ctx)
    rect(ctx, x - 0.5 * u, base - 0.42 * u, 0.62 * u, 0.3 * u, c)            # canvas back
    ctx.save(); ctx.rectangle(x - 0.5 * u, base - 0.6 * u, 0.62 * u, 0.2 * u); ctx.clip()
    ellipse(ctx, x - 0.19 * u, base - 0.42 * u, 0.31 * u, 0.14 * u, c); ctx.restore()
    fill_poly(ctx, [(x + 0.14 * u, base - 0.12 * u), (x + 0.14 * u, base - 0.5 * u), (x + 0.3 * u, base - 0.5 * u),
                    (x + 0.33 * u, base - 0.32 * u), (x + 0.5 * u, base - 0.3 * u), (x + 0.52 * u, base - 0.12 * u)], c)
    _clear(ctx); ctx.rectangle(x + 0.18 * u, base - 0.46 * u, 0.1 * u, 0.1 * u); ctx.fill(); _over(ctx)
    for wx in (-0.35, -0.15, 0.36):
        circle(ctx, x + wx * u, base - 0.08 * u, 0.08 * u, c)
    _paint(ctx, a)


def locomotive(ctx, x, base, s, c, t=0.0, a=1.0):
    """Steam locomotive facing right with tender; s = loco length."""
    u = s
    _group(ctx)
    rect(ctx, x - 0.5 * u, base - 0.2 * u, 1.02 * u, 0.06 * u, c)                   # frame
    rect(ctx, x - 0.3 * u, base - 0.5 * u, 0.72 * u, 0.3 * u, c)                   # boiler
    circle(ctx, x + 0.42 * u, base - 0.35 * u, 0.15 * u, c)                        # smokebox
    rect(ctx, x + 0.3 * u, base - 0.72 * u, 0.08 * u, 0.24 * u, c)                 # chimney
    rect(ctx, x + 0.28 * u, base - 0.74 * u, 0.12 * u, 0.04 * u, c)
    ellipse(ctx, x + 0.1 * u, base - 0.52 * u, 0.06 * u, 0.06 * u, c)              # steam dome
    ellipse(ctx, x - 0.08 * u, base - 0.51 * u, 0.045 * u, 0.045 * u, c)
    rect(ctx, x - 0.52 * u, base - 0.66 * u, 0.24 * u, 0.46 * u, c)                # cab
    rect(ctx, x - 0.56 * u, base - 0.69 * u, 0.32 * u, 0.04 * u, c)
    rect(ctx, x + 0.52 * u, base - 0.26 * u, 0.05 * u, 0.1 * u, c)                 # buffer beam
    for by in (-0.24, -0.16):
        rect(ctx, x + 0.56 * u, base + by * u, 0.05 * u, 0.025 * u, c)
    fill_poly(ctx, [(x + 0.5 * u, base - 0.14 * u), (x + 0.62 * u, base - 0.02 * u), (x + 0.5 * u, base - 0.02 * u)], c)
    # tender
    rect(ctx, x - 1.02 * u, base - 0.5 * u, 0.46 * u, 0.34 * u, c)
    rect(ctx, x - 1.04 * u, base - 0.53 * u, 0.5 * u, 0.04 * u, c)
    ellipse(ctx, x - 0.8 * u, base - 0.53 * u, 0.2 * u, 0.05 * u, c)
    _clear(ctx)
    ctx.rectangle(x - 0.48 * u, base - 0.6 * u, 0.12 * u, 0.12 * u); ctx.fill()   # cab window
    wheels = [(x - 0.22 * u, 0.13), (x + 0.07 * u, 0.13), (x + 0.36 * u, 0.13), (x - 0.92 * u, 0.07), (x - 0.7 * u, 0.07)]
    for wx, r in wheels:
        ctx.arc(wx, base - r * u, r * u, 0, TAU); ctx.fill()
    _over(ctx)
    for wx, r in wheels:
        ctx.arc(wx, base - r * u, r * u - 3, 0, TAU); ctx.set_line_width(5); src(ctx, c); ctx.stroke()
        for k in range(8 if r > 0.1 else 6):
            a_ = -t * 6 + k * math.pi / (4 if r > 0.1 else 3)
            line(ctx, [(wx, base - r * u), (wx + math.cos(a_) * r * u, base - r * u + math.sin(a_) * r * u)], c, 3)
        circle(ctx, wx, base - r * u, 0.025 * u, c)
    crank = (math.cos(-t * 6) * 0.07 * u, math.sin(-t * 6) * 0.07 * u)
    line(ctx, [(x - 0.22 * u + crank[0], base - 0.13 * u + crank[1]), (x + 0.36 * u + crank[0], base - 0.13 * u + crank[1])], c, 0.025 * u)
    line(ctx, [(x + 0.07 * u + crank[0], base - 0.13 * u + crank[1]), (x + 0.48 * u, base - 0.17 * u)], c, 0.02 * u)
    _paint(ctx, a)


def landing_craft(ctx, x, base, s, c, ramp=0.0, helmets=5, a=1.0):
    """Higgins boat, bow (ramp) to the right. ramp 0 = up, 1 = down."""
    u = s
    _group(ctx)
    fill_poly(ctx, [(x - 0.5 * u, base - 0.3 * u), (x - 0.5 * u, base - 0.05 * u), (x - 0.42 * u, base + 0.02 * u),
                    (x + 0.36 * u, base + 0.02 * u), (x + 0.36 * u, base - 0.3 * u)], c)
    rect(ctx, x - 0.45 * u, base - 0.4 * u, 0.12 * u, 0.1 * u, c)
    ang = -ramp * 1.3
    ctx.save(); ctx.translate(x + 0.36 * u, base + 0.02 * u); ctx.rotate(-ang)
    rect(ctx, 0, -0.34 * u, 0.06 * u, 0.34 * u, c); ctx.restore()
    for k in range(helmets):
        hx_ = x - 0.28 * u + k * 0.12 * u
        ctx.arc(hx_, base - 0.3 * u, 0.045 * u, math.pi, TAU); src(ctx, c); ctx.fill()
    _paint(ctx, a)


# ================================================================ aircraft (side views)
def fighter_side(ctx, x, y, s, c, ang=0.0, prop_t=0.0, a=1.0):
    """Single-engine fighter, side view facing +x before rotation."""
    u = s
    ctx.save(); ctx.translate(x, y); ctx.rotate(ang)
    _group(ctx)
    ctx.move_to(0.5 * u, 0.0)
    ctx.curve_to(0.48 * u, -0.07 * u, 0.3 * u, -0.08 * u, 0.1 * u, -0.075 * u)
    ctx.curve_to(0.05 * u, -0.15 * u, -0.08 * u, -0.15 * u, -0.12 * u, -0.07 * u)         # canopy
    ctx.line_to(-0.42 * u, -0.035 * u)
    ctx.line_to(-0.46 * u, -0.2 * u); ctx.line_to(-0.52 * u, -0.2 * u); ctx.line_to(-0.52 * u, 0.0)   # fin
    ctx.line_to(-0.4 * u, 0.03 * u)
    ctx.curve_to(0.0, 0.07 * u, 0.3 * u, 0.08 * u, 0.5 * u, 0.02 * u)
    ctx.close_path(); src(ctx, c); ctx.fill()
    fill_poly(ctx, [(0.22 * u, 0.02 * u), (0.26 * u, 0.06 * u), (-0.02 * u, 0.07 * u), (-0.04 * u, 0.04 * u)], c)  # wing
    fill_poly(ctx, [(-0.36 * u, -0.02 * u), (-0.5 * u, -0.03 * u), (-0.5 * u, 0.0), (-0.38 * u, 0.0)], c)
    ellipse(ctx, 0.51 * u, 0.0, 0.012 * u, 0.16 * u, c, 0.35 + 0.1 * math.sin(prop_t * 40))
    _paint(ctx, a)
    ctx.restore()


def bomber_side(ctx, x, y, s, c, ang=0.0, a=1.0):
    u = s
    ctx.save(); ctx.translate(x, y); ctx.rotate(ang)
    _group(ctx)
    ctx.move_to(0.5 * u, 0.0)
    ctx.curve_to(0.5 * u, -0.05 * u, 0.4 * u, -0.07 * u, 0.3 * u, -0.07 * u)
    ctx.line_to(0.25 * u, -0.1 * u); ctx.line_to(0.18 * u, -0.1 * u); ctx.line_to(0.15 * u, -0.07 * u)
    ctx.line_to(-0.3 * u, -0.05 * u)
    ctx.line_to(-0.38 * u, -0.24 * u); ctx.curve_to(-0.45 * u, -0.26 * u, -0.5 * u, -0.2 * u, -0.5 * u, -0.02 * u)
    ctx.line_to(-0.35 * u, 0.02 * u)
    ctx.curve_to(0.0, 0.05 * u, 0.3 * u, 0.06 * u, 0.5 * u, 0.02 * u)
    ctx.close_path(); src(ctx, c); ctx.fill()
    fill_poly(ctx, [(0.12 * u, 0.0), (0.16 * u, 0.03 * u), (-0.1 * u, 0.035 * u), (-0.12 * u, 0.01 * u)], c)
    for ex in (0.14, 0.02):
        ellipse(ctx, ex * u, 0.035 * u, 0.06 * u, 0.02 * u, c)
    fill_poly(ctx, [(-0.38 * u, -0.02 * u), (-0.52 * u, -0.03 * u), (-0.52 * u, 0.0), (-0.4 * u, 0.0)], c)
    _clear(ctx); ellipse(ctx, 0.46 * u, -0.01 * u, 0.025 * u, 0.02 * u, c); _over(ctx)
    _paint(ctx, a)
    ctx.restore()


# ================================================================ naval
def carrier_island(ctx, x, deck, s, c):
    """Carrier island: stepped bridge with window strip, upright funnel, tripod mast + radar."""
    u = s
    _group(ctx)
    rect(ctx, x - 0.22 * u, deck - 0.26 * u, 0.44 * u, 0.26 * u, c)
    rect(ctx, x - 0.17 * u, deck - 0.38 * u, 0.36 * u, 0.13 * u, c)
    fill_poly(ctx, [(x + 0.19 * u, deck - 0.38 * u), (x + 0.26 * u, deck - 0.36 * u), (x + 0.24 * u, deck - 0.31 * u),
                    (x + 0.19 * u, deck - 0.3 * u)], c)                                 # bridge wing
    rect(ctx, x - 0.13 * u, deck - 0.46 * u, 0.26 * u, 0.09 * u, c)
    rect(ctx, x - 0.2 * u, deck - 0.48 * u, 0.4 * u, 0.02 * u, c)
    rect(ctx, x - 0.2 * u, deck - 0.62 * u, 0.16 * u, 0.2 * u, c)                  # funnel
    rect(ctx, x - 0.22 * u, deck - 0.64 * u, 0.2 * u, 0.025 * u, c)
    for dx in (0.02, 0.1):                                                          # tripod mast
        line(ctx, [(x + dx * u, deck - 0.47 * u), (x + 0.06 * u, deck - 0.9 * u)], c, 0.012 * u)
    rect(ctx, x - 0.04 * u, deck - 0.8 * u, 0.2 * u, 0.06 * u, c)                  # radar
    line(ctx, [(x + 0.06 * u, deck - 0.9 * u), (x + 0.06 * u, deck - 1.0 * u)], c, 0.006 * u)
    for k in range(6):                                                              # AA tubs
        circle(ctx, x - 0.2 * u + k * 0.08 * u, deck - 0.26 * u, 0.02 * u, c)
    _clear(ctx)
    for k in range(7):
        ctx.rectangle(x - 0.15 * u + k * 0.045 * u, deck - 0.36 * u, 0.028 * u, 0.03 * u)
    ctx.fill(); _over(ctx)
    _paint(ctx)


def parked_plane(ctx, x, deck, s, c):
    """Carrier fighter on deck, side view with landing gear, facing right."""
    fighter_side(ctx, x, deck - 0.2 * s, s, c, ang=-0.12)
    line(ctx, [(x + 0.12 * s, deck - 0.15 * s), (x + 0.14 * s, deck - 0.04 * s)], c, 0.018 * s)
    circle(ctx, x + 0.14 * s, deck - 0.04 * s, 0.04 * s, c)
    circle(ctx, x - 0.44 * s, deck - 0.12 * s, 0.018 * s, c)


def hangar(ctx, x, base, w, h, c, door_c=None):
    ctx.save(); ctx.translate(x + w / 2, base); ctx.scale(w / 2, h)
    ctx.arc(0, 0, 1, math.pi, TAU); ctx.restore(); src(ctx, c); ctx.fill()
    if door_c:
        rect(ctx, x + w * 0.22, base - h * 0.62, w * 0.56, h * 0.62, door_c)


def control_tower(ctx, x, base, s, c, lit=None):
    u = s
    rect(ctx, x - 0.25 * u, base - 0.6 * u, 0.5 * u, 0.6 * u, c)
    rect(ctx, x - 0.32 * u, base - 0.63 * u, 0.64 * u, 0.04 * u, c)
    rect(ctx, x - 0.2 * u, base - 0.85 * u, 0.4 * u, 0.22 * u, c)
    rect(ctx, x - 0.24 * u, base - 0.88 * u, 0.48 * u, 0.04 * u, c)
    for k in range(9):
        line(ctx, [(x - 0.3 * u + k * 0.075 * u, base - 0.63 * u), (x - 0.3 * u + k * 0.075 * u, base - 0.7 * u)], c, 2)
    line(ctx, [(x - 0.32 * u, base - 0.7 * u), (x + 0.32 * u, base - 0.7 * u)], c, 2)
    if lit:
        rect(ctx, x - 0.16 * u, base - 0.82 * u, 0.32 * u, 0.1 * u, lit)
    line(ctx, [(x + 0.1 * u, base - 0.88 * u), (x + 0.1 * u, base - 1.2 * u)], c, 4)


def windsock(ctx, x, base, h, c, t=0.0):
    line(ctx, [(x, base), (x, base - h)], c, 5)
    fl = 0.12 * math.sin(t * 6)
    fill_poly(ctx, [(x, base - h - 14), (x + 0.5 * h, base - h - 4 + fl * 40), (x + 0.5 * h, base - h + 4 + fl * 40),
                    (x, base - h + 14)], c)
