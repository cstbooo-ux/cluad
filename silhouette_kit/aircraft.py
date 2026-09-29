"""Aircraft silhouettes (side / banked / planform / tail-on) + the paper plane.

Local units: 1.0 = aircraft length, x = forward (nose at +0.5), y = up.
`place(ctx, shape, x, y, size, pitch, ...)` puts a shape on screen: `size` = length in px,
`pitch` = nose-up angle in radians (screen is y-down, handled here).
All shapes use the smooth-outline convention of figure.py: (x, y) smooth, (x, y, True) corner.
"""
import math
import cairo
from .figure import smooth_path

TAU = 2 * math.pi
C = True

# ---------------------------------------------------------------- side profiles
SPITFIRE = [
    (0.50, 0.004), (0.488, 0.03), (0.458, 0.044, C), (0.40, 0.052), (0.25, 0.058), (0.12, 0.062),
    (0.088, 0.064, C), (-0.10, 0.07, C), (-0.20, 0.064), (-0.32, 0.048), (-0.37, 0.044, C), (-0.40, 0.11),
    (-0.432, 0.162), (-0.468, 0.178), (-0.494, 0.158), (-0.508, 0.102), (-0.508, 0.038), (-0.50, 0.0, C),
    (-0.47, -0.01), (-0.40, -0.011), (-0.25, -0.018), (-0.10, -0.028), (-0.06, -0.032, C), (-0.07, -0.058),
    (0.03, -0.062), (0.06, -0.037, C), (0.15, -0.036), (0.30, -0.032), (0.42, -0.024), (0.47, -0.016),
    (0.492, -0.008)]
SPITFIRE_CANOPY = [(0.088, 0.064, C), (0.06, 0.097), (0.03, 0.108), (-0.03, 0.11), (-0.072, 0.1), (-0.10, 0.07, C)]
SPITFIRE_WING_EDGE = [(0.195, -0.024), (0.12, -0.014), (-0.03, -0.024), (-0.075, -0.036, C), (0.06, -0.043),
                      (0.175, -0.036)]
SPITFIRE_TAILPLANE = [(-0.40, 0.02), (-0.45, 0.027), (-0.505, 0.023, C), (-0.50, 0.011), (-0.42, 0.011)]

BF109 = [
    (0.50, 0.0), (0.485, 0.032), (0.452, 0.046, C), (0.38, 0.054), (0.20, 0.06), (0.092, 0.062, C),
    (-0.102, 0.068, C), (-0.20, 0.06), (-0.34, 0.044), (-0.38, 0.042, C), (-0.405, 0.115), (-0.435, 0.15),
    (-0.478, 0.158), (-0.498, 0.13), (-0.506, 0.055), (-0.50, 0.0, C), (-0.46, -0.012), (-0.30, -0.02),
    (-0.10, -0.03), (0.05, -0.038), (0.20, -0.036), (0.30, -0.036, C), (0.318, -0.052, C), (0.382, -0.052, C),
    (0.40, -0.034, C), (0.46, -0.021), (0.49, -0.01)]
BF109_CANOPY = [(0.092, 0.062, C), (0.07, 0.094, C), (0.05, 0.1, C), (-0.08, 0.098, C), (-0.102, 0.068, C)]
BF109_WING_EDGE = [(0.20, -0.026), (0.13, -0.018), (-0.04, -0.026, C), (-0.05, -0.034, C), (0.18, -0.036)]
BF109_TAILPLANE = [(-0.40, 0.026), (-0.508, 0.028, C), (-0.508, 0.017, C), (-0.40, 0.017)]

HE111 = [
    (0.40, 0.064), (0.20, 0.066), (0.0, 0.066, C), (-0.012, 0.086), (-0.07, 0.084, C), (-0.09, 0.064, C),
    (-0.30, 0.046), (-0.36, 0.043, C), (-0.40, 0.12), (-0.44, 0.17), (-0.482, 0.17), (-0.502, 0.13),
    (-0.506, 0.04), (-0.49, 0.0, C), (-0.45, -0.016), (-0.30, -0.03), (-0.10, -0.038, C), (-0.085, -0.066),
    (0.08, -0.07), (0.12, -0.042, C), (0.30, -0.044), (0.40, -0.04, C)]
HE111_NOSE = [(0.40, 0.064, C), (0.45, 0.058), (0.487, 0.036), (0.5, 0.004), (0.485, -0.026), (0.44, -0.04),
              (0.40, -0.04, C)]
HE111_WING_EDGE = [(0.22, 0.0), (0.12, 0.012), (-0.08, 0.003, C), (-0.09, -0.01, C), (0.2, -0.014)]
HE111_NACELLE = [(0.33, -0.01), (0.30, 0.016), (0.20, 0.022), (0.02, 0.014), (-0.04, 0.0, C), (0.02, -0.024),
                 (0.20, -0.032), (0.30, -0.028)]
HE111_TAILPLANE = [(-0.40, 0.026), (-0.51, 0.031, C), (-0.51, 0.017, C), (-0.40, 0.015)]

# ---------------------------------------------------------------- planforms (x forward, z = half-span, right wing)
def _ellipse_wing(x_qc, c0, span, n=16):
    """Elliptical wing (Spitfire): straight quarter-chord line."""
    le, te = [], []
    for i in range(n + 1):
        z = span * i / n
        c = c0 * math.sqrt(max(0.0, 1 - (z / span) ** 2))
        le.append((x_qc + 0.25 * c, z))
        te.append((x_qc - 0.75 * c, z))
    return le + te[::-1]


def _taper_wing(root_le, root_te, tip_le, tip_te, span, tip_round=0.3):
    return [(root_le, 0.0), (tip_le, span * (1 - tip_round * 0.3)), (tip_le - (tip_le - tip_te) * 0.2, span),
            (tip_te + (tip_le - tip_te) * 0.2, span), (tip_te, span * (1 - tip_round * 0.2)), (root_te, 0.0)]


PLANFORM = {
    "spitfire": dict(wing=_ellipse_wing(0.14, 0.27, 0.615), tail=_ellipse_wing(-0.43, 0.09, 0.19, 8),
                     width=0.055),
    "bf109": dict(wing=_taper_wing(0.21, -0.02, 0.15, 0.06, 0.56), tail=_taper_wing(-0.40, -0.50, -0.43, -0.49, 0.18),
                  width=0.05),
    "he111": dict(wing=_ellipse_wing(0.12, 0.30, 0.69), tail=_ellipse_wing(-0.43, 0.11, 0.26, 8), width=0.06),
}
SIDE = {"spitfire": (SPITFIRE, SPITFIRE_WING_EDGE, SPITFIRE_TAILPLANE),
        "bf109": (BF109, BF109_WING_EDGE, BF109_TAILPLANE),
        "he111": (HE111, HE111_WING_EDGE, HE111_TAILPLANE)}
GLASS = {"spitfire": SPITFIRE_CANOPY, "bf109": BF109_CANOPY, "he111": HE111_NOSE}


# ---------------------------------------------------------------- placement
def _xf(x, y, size, pitch, flip=False):
    ca, sa = math.cos(pitch), math.sin(pitch)
    fx = -1 if flip else 1

    def f(p):
        lx, ly = p[0] * fx, p[1]
        return (x + size * (lx * ca - ly * sa * fx), y - size * (lx * sa * fx + ly * ca)) + tuple(p[2:])
    return f


def _fill(ctx, pts, c, a=1.0):
    smooth_path(ctx, pts)
    ctx.set_source_rgba(*c, a) if len(c) == 3 else ctx.set_source_rgba(*c)
    ctx.fill()


def _rgb(c):
    if isinstance(c, str):
        c = c.lstrip("#")
        return tuple(int(c[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return c


# 1940 liveries, deliberately dark so they still read as silhouettes against the sky
LIVERY = {
    "raf": dict(top="#343a26", top2="#46392a", under="#7d8c80", spinner="#1a1a1a",
                marks=("roundel", "#2d3a66", "#cfcabb", "#8e2b25", "#b89a3a")),
    "luftwaffe": dict(top="#373d36", top2="#4d534c", under="#7a8da0", spinner="#c8a232", nose="#c8a232",
                      rudder="#c8a232", marks=("cross", "#141414", "#d8d8d0")),
    "bomber": dict(top="#2e372b", top2="#3a4234", under="#7a8da0", spinner="#2a2a2a",
                   marks=("cross", "#141414", "#d8d8d0")),
    None: dict(top="#000000", top2="#000000", under="#000000", spinner="#000000", marks=None),
}
DEFAULT_LIVERY = {"spitfire": "raf", "bf109": "luftwaffe", "he111": "bomber"}


def _mix(c1, c2, t):
    return tuple(a + (b - a) * t for a, b in zip(c1, c2))


def _toner(light=None, light_amt=0.0, haze=None, haze_amt=0.0):
    lc = _rgb(light) if light else None
    hc = _rgb(haze) if haze else None

    def tone(c):
        c = _rgb(c)
        if lc and light_amt:
            c = _mix(c, tuple(a * b for a, b in zip(c, lc)), light_amt)     # multiply-ish tint
            c = _mix(c, lc, light_amt * 0.12)
        if hc and haze_amt:
            c = _mix(c, hc, haze_amt)
        return c
    return tone


def _clip_fill(ctx, clip_pts, fill_pts, color):
    ctx.save()
    smooth_path(ctx, clip_pts); ctx.clip()
    ctx.new_path(); ctx.move_to(*fill_pts[0][:2])
    for q in fill_pts[1:]:
        ctx.line_to(*q[:2])
    ctx.close_path(); ctx.set_source_rgb(*color); ctx.fill()
    ctx.restore()


def aircraft(ctx, kind, x, y, size, pitch=0.0, bank=0.0, c=None, flip=False, prop_t=0.0,
             markings=True, damage=0.0, a=1.0, livery="auto", light=None, light_amt=0.0, haze=None, haze_amt=0.0):
    """Side view of `kind` ('spitfire' | 'bf109' | 'he111').

    livery: 'auto' (by type) | 'raf' | 'luftwaffe' | 'bomber' | None (pure silhouette, or colour `c`)
    bank: roll angle in radians. 0 = pure side view (wing edge-on); non-zero shows the wing planforms.
    light / light_amt: scene light tint (e.g. red sky); haze / haze_amt: fade distant aircraft into the sky.
    damage: 0..1 punches holes in wing / tail.
    """
    lv = LIVERY[DEFAULT_LIVERY[kind] if livery == "auto" else livery]
    tone = _toner(light, light_amt, haze, haze_amt)
    if c is not None and livery in (None,):
        lv = dict(LIVERY[None]); lv.update(top=c, top2=c, under=c, spinner=c)
    top, top2, under = tone(lv["top"]), tone(lv["top2"]), tone(lv["under"])
    T = _xf(x, y, size, pitch, flip)
    body, wing_edge, tailplane = SIDE[kind]
    body_pts = [T(p) for p in body]
    ctx.push_group()
    pl = PLANFORM[kind]
    sb = math.sin(bank)
    if abs(sb) > 0.02:
        yw = -0.03 if kind != "he111" else 0.0
        for side, k in ((-1, 0.72), (1, 1.0)):
            pts = [(px, yw - side * pz * sb * k) for px, pz in pl["wing"]]
            # we see the top of the wing that rises and the underside of the one that drops
            _fill(ctx, [T(p) for p in pts], top if side * sb < 0 else under)
        for side, k in ((-1, 0.72), (1, 1.0)):
            tp = [(px, 0.02 - side * pz * sb * 0.9 * k) for px, pz in pl["tail"]]
            _fill(ctx, [T(p) for p in tp], top if side * sb < 0 else under)
    _fill(ctx, body_pts, top)
    # lighter underside below the waterline, darker disruptive patch on the upper fuselage
    _clip_fill(ctx, body_pts, [T(p) for p in [(0.6, -0.004), (-0.6, 0.012), (-0.6, -0.3), (0.6, -0.3)]], under)
    _clip_fill(ctx, body_pts, [T(p) for p in [(0.3, 0.07), (0.18, 0.02), (-0.05, 0.03), (-0.25, 0.01),
                                              (-0.33, 0.06), (-0.05, 0.2), (0.3, 0.2)]], top2)
    if lv.get("nose"):
        _clip_fill(ctx, body_pts, [T(p) for p in [(0.6, 0.2), (0.4, 0.2), (0.4, -0.2), (0.6, -0.2)]], tone(lv["nose"]))
    if lv.get("rudder"):
        _clip_fill(ctx, body_pts, [T(p) for p in [(-0.46, 0.3), (-0.6, 0.3), (-0.6, 0.02), (-0.46, 0.04)]],
                   tone(lv["rudder"]))
    _fill(ctx, [T(p) for p in wing_edge], under)
    _fill(ctx, [T(p) for p in tailplane], top)
    if kind == "spitfire" and markings:                   # fin flash
        for i, cc in enumerate(("#8e2b25", "#cfcabb", "#2d3a66")):
            x0 = -0.40 - i * 0.022
            _clip_fill(ctx, body_pts, [T(p) for p in [(x0, 0.12), (x0 - 0.022, 0.12), (x0 - 0.022, 0.05),
                                                      (x0, 0.05)]], tone(cc))
    glass = GLASS[kind]
    _fill(ctx, [T(p) for p in glass], top, 0.45)
    ctx.set_source_rgb(*top); ctx.set_line_width(max(1.0, size * 0.005))
    smooth_path(ctx, [T(p) for p in glass]); ctx.stroke()
    frames = {"spitfire": [(0.06, 0.066, 0.06, 0.097), (-0.035, 0.07, -0.03, 0.11)],
              "bf109": [(0.05, 0.064, 0.05, 0.1), (0.0, 0.065, 0.0, 0.099), (-0.045, 0.066, -0.045, 0.098),
                        (0.07, 0.083, -0.09, 0.083)],
              "he111": [(0.44, 0.058, 0.44, -0.04), (0.47, 0.048, 0.47, -0.03), (0.40, 0.03, 0.495, 0.02),
                        (0.40, 0.0, 0.5, 0.0)]}[kind]
    for x0, y0, x1, y1 in frames:
        ctx.new_path(); ctx.move_to(*T((x0, y0))[:2]); ctx.line_to(*T((x1, y1))[:2]); ctx.stroke()
    if kind in ("spitfire", "bf109"):                     # pilot's head + helmet inside the canopy
        hx_, hy_ = (-0.012, 0.086) if kind == "spitfire" else (-0.02, 0.082)
        cx, cy = T((hx_, hy_))[:2]
        ctx.new_path(); ctx.arc(cx, cy, size * 0.019, 0, TAU); ctx.set_source_rgb(*tone("#0c0c0c")); ctx.fill()
    if kind == "he111":
        _fill(ctx, [T(p) for p in HE111_NACELLE], top)
        _clip_fill(ctx, [T(p) for p in HE111_NACELLE], [T(p) for p in [(0.4, -0.005), (-0.1, -0.005), (-0.1, -0.1),
                                                                         (0.4, -0.1)]], under)
        if abs(sb) > 0.05:
            _fill(ctx, [T((p[0], p[1] - 0.25 * sb)) for p in HE111_NACELLE], top)
    if kind == "bf109":                                   # tailplane strut
        ctx.new_path(); ctx.move_to(*T((-0.445, 0.02))[:2]); ctx.line_to(*T((-0.425, -0.008))[:2])
        ctx.set_line_width(max(1.0, size * 0.004)); ctx.set_source_rgb(*under); ctx.stroke()
    if kind in ("spitfire", "bf109"):                     # aerial mast
        ctx.new_path(); ctx.move_to(*T((-0.11, 0.066))[:2]); ctx.line_to(*T((-0.13, 0.125))[:2])
        ctx.set_line_width(max(1.0, size * 0.005)); ctx.set_source_rgb(*top); ctx.stroke()
    # spinner colour
    sp = {"spitfire": [(0.5, 0.004), (0.488, 0.03), (0.458, 0.044, C), (0.458, -0.02, C), (0.49, -0.008)],
          "bf109": [(0.5, 0.0), (0.485, 0.032), (0.452, 0.046, C), (0.452, -0.028, C), (0.49, -0.01)]}.get(kind)
    if sp:
        _fill(ctx, [T(p) for p in sp], tone(lv["spinner"]))
    # propeller disc(s): faint blur
    discs = [(0.505, 0.004)] if kind != "he111" else [(0.335, -0.008)]
    for px, py in discs:
        cx, cy = T((px, py))[:2]
        ctx.save(); ctx.translate(cx, cy); ctx.rotate(-pitch if not flip else pitch)
        ctx.scale(size * 0.01, size * 0.18 if kind != 'he111' else size * 0.1); ctx.arc(0, 0, 1, 0, TAU); ctx.restore()
        ctx.set_source_rgba(*top, 0.28 + 0.06 * math.sin(prop_t * 50)); ctx.fill()
    if damage > 0:
        ctx.set_operator(cairo.OPERATOR_CLEAR)
        for k, (hx, hy, r) in enumerate(((-0.02, -0.05, 0.012), (0.05, -0.03, 0.009), (-0.3, 0.03, 0.008),
                                          (-0.44, 0.12, 0.014), (0.1, -0.06, 0.01))):
            if k < int(1 + damage * 5):
                cx, cy = T((hx, hy))[:2]
                ctx.arc(cx, cy, r * size, 0, TAU); ctx.fill()
        ctx.set_operator(cairo.OPERATOR_OVER)
    if markings and lv["marks"]:
        mx, my = T((-0.22 if kind != "he111" else -0.2, 0.018))[:2]
        r = size * (0.03 if kind != "he111" else 0.022)
        m = lv["marks"]
        if m[0] == "roundel":
            for rr, cc in ((1.0, m[4]), (0.86, m[1]), (0.58, m[2]), (0.3, m[3])):
                ctx.new_path(); ctx.arc(mx, my, r * rr, 0, TAU); ctx.set_source_rgb(*tone(cc)); ctx.fill()
        else:
            ctx.save(); ctx.translate(mx, my); ctx.rotate(-pitch if not flip else pitch)
            for scale_, cc in ((1.0, m[2]), (0.72, m[1])):
                w = r * 0.34 * scale_ + (r * 0.12 if scale_ == 1.0 else 0)
                L = r * scale_
                ctx.rectangle(-L, -w / 2, 2 * L, w); ctx.rectangle(-w / 2, -L, w, 2 * L)
                ctx.set_source_rgb(*tone(cc)); ctx.fill()
            ctx.restore()
    ctx.pop_group_to_source(); ctx.paint_with_alpha(a)


def planform(ctx, kind, x, y, size, heading=0.0, c=None, a=1.0, prop=True, view="below", livery="auto",
             light=None, light_amt=0.0, haze=None, haze_amt=0.0):
    """Seen from directly above or below. heading = direction of the nose (radians, screen, 0 = right)."""
    lv = LIVERY[DEFAULT_LIVERY[kind] if livery == "auto" else livery]
    tone = _toner(light, light_amt, haze, haze_amt)
    col = _rgb(c) if c else tone(lv["under"] if view == "below" else lv["top"])
    pl = PLANFORM[kind]
    ca, sa = math.cos(heading), math.sin(heading)

    def T(p, side=1):
        lx, lz = p[0], p[1] * side
        return (x + size * (lx * ca - lz * sa), y + size * (lx * sa + lz * ca))
    ctx.push_group()
    for side in (1, -1):
        _fill(ctx, [T(p, side) for p in pl["wing"]], col)
        _fill(ctx, [T(p, side) for p in pl["tail"]], col)
    w = pl["width"]
    fus = [(0.5, 0.0), (0.46, w * 0.7), (0.2, w), (-0.1, w * 0.8), (-0.45, w * 0.25), (-0.5, 0.0)]
    _fill(ctx, [T(p) for p in fus] + [T(p, -1) for p in fus[::-1]], col)
    if kind == "he111":
        for side in (1, -1):
            nac = [(0.33, 0.20), (0.3, 0.24), (0.05, 0.24), (-0.05, 0.22), (0.05, 0.16), (0.3, 0.16)]
            _fill(ctx, [T(p, side) for p in nac], col)
    if lv.get("nose") and c is None:
        _fill(ctx, [T(p) for p in [(0.5, 0.0), (0.46, w * 0.7), (0.4, w * 0.85), (0.4, -w * 0.85), (0.46, -w * 0.7)]],
              tone(lv["nose"]))
    if lv["marks"] and c is None:                         # wing markings
        m = lv["marks"]
        for side in (1, -1):
            span = max(q[1] for q in pl["wing"])
            mx, my = T((0.08 if kind != "he111" else 0.05, span * 0.62), side)
            r = size * 0.035
            if m[0] == "roundel":
                for rr, cc in ((1.0, m[1]), (0.66, m[2]), (0.33, m[3])):
                    ctx.new_path(); ctx.arc(mx, my, r * rr, 0, TAU); ctx.set_source_rgb(*tone(cc)); ctx.fill()
            else:
                ctx.save(); ctx.translate(mx, my); ctx.rotate(heading)
                for sc, cc in ((1.0, m[2]), (0.72, m[1])):
                    ww = r * 0.34 * sc + (r * 0.12 if sc == 1.0 else 0); L = r * sc
                    ctx.rectangle(-L, -ww / 2, 2 * L, ww); ctx.rectangle(-ww / 2, -L, ww, 2 * L)
                    ctx.set_source_rgb(*tone(cc)); ctx.fill()
                ctx.restore()
    ctx.pop_group_to_source(); ctx.paint_with_alpha(a)


def tail_on(ctx, kind, x, y, span, roll=0.0, c=None, a=1.0, prop_t=0.0, livery="auto",
            light=None, light_amt=0.0, haze=None, haze_amt=0.0):
    """Seen from behind (e.g. through a gunsight). span = wingspan in px."""
    lv = LIVERY[DEFAULT_LIVERY[kind] if livery == "auto" else livery]
    tone = _toner(light, light_amt, haze, haze_amt)
    col = _rgb(c) if c else tone(lv["top"])
    s = span / 1.1
    ca, sa = math.cos(roll), math.sin(roll)

    def T(p):
        return (x + s * (p[0] * ca - p[1] * sa), y - s * (p[0] * sa + p[1] * ca))
    ctx.push_group()
    dih = 0.06 if kind != "bf109" else 0.045
    half = 0.55 if kind != "he111" else 0.62
    wing = [(-half, dih + 0.012), (0, 0.022), (half, dih + 0.012), (half, dih - 0.006), (0, -0.018),
            (-half, dih - 0.006)]
    _fill(ctx, [T(p) for p in wing], col)
    tp = 0.17 if kind != "he111" else 0.24
    _fill(ctx, [T(p) for p in [(-tp, 0.062), (tp, 0.062), (tp, 0.05), (-tp, 0.05)]], col)
    fin = [(-0.008, 0.06), (-0.004, 0.21), (0.004, 0.21), (0.008, 0.06)]
    _fill(ctx, [T(p) for p in fin], tone(lv["rudder"]) if (lv.get("rudder") and not c) else col)
    fus = [(0.0, 0.07), (0.05, 0.05), (0.06, 0.0), (0.045, -0.05), (0.0, -0.065), (-0.045, -0.05), (-0.06, 0.0),
           (-0.05, 0.05)]
    _fill(ctx, [T(p) for p in fus], col)
    _fill(ctx, [T(p) for p in [(0.0, 0.115), (0.03, 0.095), (0.035, 0.06, C), (-0.035, 0.06, C), (-0.03, 0.095)]], col)
    if kind == "bf109":
        for sx in (-0.2, 0.2):                            # underwing radiators
            _fill(ctx, [T(p) for p in [(sx - 0.04, 0.02, C), (sx + 0.04, 0.02, C), (sx + 0.035, -0.02, C),
                                        (sx - 0.035, -0.02, C)]], col)
        for sx in (-0.13, 0.13):                          # tailplane struts
            ctx.new_path(); ctx.move_to(*T((sx, 0.052))); ctx.line_to(*T((sx * 0.3, 0.0)))
            ctx.set_line_width(max(1.0, s * 0.006)); ctx.set_source_rgb(*col); ctx.stroke()
    if kind == "he111":
        for sx in (-0.2, 0.2):
            _fill(ctx, [T(p) for p in [(sx, 0.07), (sx + 0.05, 0.04), (sx + 0.05, -0.02), (sx, -0.05),
                                        (sx - 0.05, -0.02), (sx - 0.05, 0.04)]], col)
    cx, cy = T((0, 0))
    ctx.new_path(); ctx.arc(cx, cy, s * 0.17, 0, TAU)
    ctx.set_source_rgba(*col, 0.16 + 0.05 * math.sin(prop_t * 40)); ctx.fill()
    ctx.pop_group_to_source(); ctx.paint_with_alpha(a)


# ---------------------------------------------------------------- paper plane
PAPER_TOP = [(0.5, 0.0, C), (-0.5, 0.2, C), (-0.46, 0.02, C)]            # near wing top surface (rolled to camera)
PAPER_KEEL = [(0.5, 0.0, C), (-0.46, 0.02, C), (-0.5, -0.12, C)]          # folded keel under the wings
PAPER_FAR = [(0.5, 0.0, C), (-0.44, 0.24, C), (-0.5, 0.2, C)]             # far wing edge peeking above


def paper_plane(ctx, x, y, size, pitch=0.0, flip=False, white="#f7f3ea", shade="#d8d2c4", fold="#b8b0a2", a=1.0):
    """Classic dart, same nose position / length convention as the aircraft (nose at +0.5)."""
    T = _xf(x, y, size, pitch, flip)
    ctx.push_group()
    for pts, c in ((PAPER_FAR, shade), (PAPER_KEEL, shade), (PAPER_TOP, white)):
        ctx.new_path()
        p = [T(q) for q in pts]
        ctx.move_to(*p[0][:2])
        for q in p[1:]:
            ctx.line_to(*q[:2])
        ctx.close_path()
        ctx.set_source_rgb(*_rgb(c)); ctx.fill()
    ctx.new_path()
    ctx.move_to(*T((0.5, 0.0))[:2]); ctx.line_to(*T((-0.46, 0.02))[:2])
    ctx.set_line_width(max(1.0, size * 0.006)); ctx.set_source_rgb(*_rgb(fold)); ctx.stroke()
    ctx.pop_group_to_source(); ctx.paint_with_alpha(a)
