"""Detailed side-profile silhouette of the walker (facing right).

All geometry is built in units of the figure height u, with the hip at (x, 0);
after building, the figure is dropped so the lowest shoe point sits on the ground.
Outline points are (x, y) for smooth Catmull-Rom points or (x, y, True) for corners.
"""
import math
import cairo

TAU = 2 * math.pi


# ---------------------------------------------------------------- geometry helpers
class Frame:
    """Local frame: x = forward, y = up. ang tilts 'up' toward +x (forward lean)."""

    def __init__(self, ox, oy, ang=0.0, s=1.0):
        self.o = (ox, oy); self.s = s
        self.f = (math.cos(ang), math.sin(ang))
        self.u = (math.sin(ang), -math.cos(ang))

    def __call__(self, x, y, *corner):
        s = self.s
        p = (self.o[0] + s * (x * self.f[0] + y * self.u[0]), self.o[1] + s * (x * self.f[1] + y * self.u[1]))
        return p + (True,) if corner and corner[0] else p

    def pts(self, lst):
        return [self(*p) for p in lst]


def bone_pt(p, a, s, w):
    """Point s along a bone hanging at angle a (0 = straight down, + = forward), w across (+ = front)."""
    return (p[0] + s * math.sin(a) + w * math.cos(a), p[1] + s * math.cos(a) - w * math.sin(a))


def bone_outline(p, a, L, prof, u):
    """prof = [(t, front, back), ...] in u; returns closed outline around a bone."""
    front = [bone_pt(p, a, t * L, f * u) for t, f, b in prof]
    back = [bone_pt(p, a, t * L, -b * u) for t, f, b in reversed(prof)]
    return front + back


def ik(a, b, L1, L2, bend=1):
    """Two-bone IK: joint position between a and b. bend=+1 puts the joint below/behind the line."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    d = max(1e-6, min(math.hypot(dx, dy), L1 + L2 - 1e-6))
    x = (L1 * L1 - L2 * L2 + d * d) / (2 * d)
    h = math.sqrt(max(0.0, L1 * L1 - x * x))
    ux, uy = dx / d, dy / d
    return (a[0] + ux * x - uy * h * bend, a[1] + uy * x + ux * h * bend)


def ang_of(p0, p1):
    """Bone angle (0 = down, + = forward) of the segment p0 -> p1."""
    return math.atan2(p1[0] - p0[0], p1[1] - p0[1])


def smooth_path(ctx, pts, closed=True):
    n = len(pts)
    P = [(p[0], p[1]) for p in pts]
    C = [len(p) > 2 and p[2] for p in pts]

    def tan(i):
        if C[i % n] or (not closed and (i == 0 or i == n - 1)):
            return (0.0, 0.0)
        a, b = P[(i - 1) % n], P[(i + 1) % n]
        return ((b[0] - a[0]) / 6, (b[1] - a[1]) / 6)

    ctx.move_to(*P[0])
    segs = n if closed else n - 1
    for i in range(segs):
        p0, p1 = P[i], P[(i + 1) % n]
        t0, t1 = tan(i), tan(i + 1)
        ctx.curve_to(p0[0] + t0[0], p0[1] + t0[1], p1[0] - t1[0], p1[1] - t1[1], p1[0], p1[1])
    if closed:
        ctx.close_path()


# ---------------------------------------------------------------- part outlines
# head, in head units (1 = crown-to-chin), x forward, y DOWN, origin mid-skull
HEAD = [(0.0, -0.5), (0.24, -0.45), (0.35, -0.31), (0.39, -0.15), (0.39, -0.1), (0.375, -0.055, True),
        (0.42, 0.02), (0.47, 0.09), (0.505, 0.14), (0.51, 0.17), (0.48, 0.19), (0.44, 0.197, True), (0.435, 0.23),
        (0.45, 0.26, True), (0.42, 0.285, True), (0.435, 0.315, True), (0.395, 0.35, True), (0.41, 0.4),
        (0.39, 0.46), (0.32, 0.5), (0.18, 0.48), (0.04, 0.42), (-0.1, 0.33, True), (-0.3, 0.28), (-0.41, 0.12),
        (-0.44, -0.08), (-0.38, -0.3), (-0.22, -0.45)]
FEDORA = [(-0.66, -0.2, True), (-0.6, -0.15), (-0.5, -0.12), (-0.2, -0.13), (0.2, -0.13), (0.5, -0.12),
          (0.68, -0.09, True), (0.66, -0.15), (0.52, -0.2), (0.4, -0.23, True), (0.38, -0.3, True), (0.37, -0.32, True),
          (0.35, -0.55), (0.3, -0.63, True), (0.2, -0.66), (0.05, -0.61, True), (-0.1, -0.66), (-0.3, -0.64),
          (-0.38, -0.55), (-0.41, -0.32, True), (-0.42, -0.3, True), (-0.41, -0.25, True), (-0.5, -0.24)]
HELMET = [(0.52, -0.1, True), (0.46, -0.15), (0.41, -0.3), (0.3, -0.5), (0.1, -0.62), (-0.15, -0.63),
          (-0.36, -0.52), (-0.46, -0.32), (-0.5, -0.1), (-0.54, -0.03, True), (-0.42, -0.03, True), (-0.3, -0.12),
          (0.0, -0.15), (0.3, -0.14), (0.4, -0.12, True)]
OXFORD = [(-0.026, -0.024), (-0.036, 0.0), (-0.038, 0.029, True), (-0.036, 0.036, True), (-0.011, 0.036, True),
          (-0.009, 0.028, True), (0.03, 0.026), (0.048, 0.036, True), (0.09, 0.036), (0.106, 0.027), (0.103, 0.014),
          (0.083, 0.005), (0.05, -0.003), (0.022, -0.016), (0.013, -0.026)]
BOOT = [(-0.034, -0.03), (-0.042, 0.0), (-0.044, 0.03, True), (-0.042, 0.039, True), (-0.008, 0.039, True),
        (-0.006, 0.031, True), (0.03, 0.03), (0.046, 0.039, True), (0.094, 0.039), (0.11, 0.028), (0.107, 0.012),
        (0.082, 0.002), (0.046, -0.007), (0.028, -0.032)]
# hand along the forearm direction: (s along, w across; + = thumb/front side)
HAND = [(-0.005, 0.021), (0.02, 0.026), (0.034, 0.03), (0.052, 0.034), (0.058, 0.027, True), (0.04, 0.017, True),
        (0.066, 0.015), (0.083, 0.004), (0.08, -0.012), (0.05, -0.022), (0.02, -0.023), (-0.005, -0.021)]
FIST = [(-0.005, 0.022), (0.03, 0.03), (0.055, 0.03), (0.07, 0.018), (0.07, -0.01), (0.055, -0.024),
        (0.02, -0.024), (-0.005, -0.021)]
# rifle, in rifle units (u), x from butt to muzzle, y up = sight side
RIFLE = [(0.0, 0.014, True), (0.0, -0.036, True), (0.02, -0.034), (0.13, -0.012, True), (0.15, -0.018), (0.17, -0.02),
         (0.2, -0.013, True), (0.44, -0.009, True), (0.45, -0.004, True), (0.6, -0.003, True), (0.6, 0.004, True),
         (0.585, 0.004, True), (0.583, 0.012, True), (0.578, 0.012, True), (0.575, 0.004, True), (0.45, 0.005, True),
         (0.44, 0.009, True), (0.29, 0.01, True), (0.28, 0.016, True), (0.26, 0.016, True), (0.25, 0.011, True),
         (0.2, 0.012, True), (0.14, 0.011, True)]

LEG_PROF = {
    "civ": {"thigh": [(0, 0.05, 0.062), (0.3, 0.049, 0.054), (0.6, 0.044, 0.046), (1.0, 0.035, 0.035)],
            "shin": [(0, 0.035, 0.035), (0.3, 0.033, 0.037), (0.7, 0.032, 0.034), (0.97, 0.034, 0.035),
                     (1.07, 0.036, 0.03)]},
    "sol": {"thigh": [(0, 0.052, 0.064), (0.3, 0.054, 0.07), (0.65, 0.046, 0.054), (1.0, 0.034, 0.034)],
            "shin": [(0, 0.033, 0.035), (0.12, 0.037, 0.039), (0.16, 0.034, 0.041), (0.35, 0.032, 0.041),
                     (0.7, 0.029, 0.032), (1.0, 0.029, 0.03)]},
}
ARM_PROF = {
    "civ": {"up": [(0, 0.034, 0.038), (0.5, 0.032, 0.034), (1.0, 0.03, 0.03)],
            "fore": [(0, 0.03, 0.03), (0.6, 0.027, 0.028), (0.9, 0.027, 0.028), (0.92, 0.031, 0.032), (1.0, 0.03, 0.031)]},
    "sol": {"up": [(0, 0.031, 0.035), (0.5, 0.03, 0.031), (1.0, 0.027, 0.027)],
            "fore": [(0, 0.027, 0.027), (0.6, 0.025, 0.025), (1.0, 0.022, 0.022)]},
}


# ---------------------------------------------------------------- figure
def figure(ctx, x, gy, h, phase, kind="civ", run=0.0, c="#000000", charge=False, suitcase=True):
    """Side-view silhouette walking right. phase 0..1 per stride; heels land at 0.0 and 0.5."""
    from .core import hx
    u = h
    col = hx(c) if isinstance(c, str) else c
    shapes = []                     # ('p', pts) smooth outline | ('c', x, y, r)
    add = lambda pts: shapes.append(("p", pts))
    dot = lambda p, r: shapes.append(("c", p[0], p[1], r))

    A = 0.34 + 0.28 * run
    lean = 0.04 + 0.2 * run + (0.08 if charge else 0)
    L1, L2 = 0.25 * u, 0.245 * u
    hip = (x, 0.0)
    bob = 0.006 * u * math.cos(TAU * phase * 2)

    # ---- legs
    legs = leg_state(phase, u, run, charge, hip)
    prof = LEG_PROF["sol" if kind == "sol" else "civ"]
    shoe = BOOT if kind == "sol" else OXFORD
    shoe_pts = []
    for thigh, shin, knee, ankle, pitch in legs:
        add(bone_outline(hip, thigh, L1, prof["thigh"], u))
        dot(knee, 0.035 * u)
        add(bone_outline(knee, shin, L2, prof["shin"], u))
        sp = Frame(ankle[0], ankle[1], pitch, u).pts([(p[0], -p[1]) + tuple(p[2:]) for p in shoe])
        shoe_pts += sp
        add(sp)
    ground = max(p[1] for p in shoe_pts)

    # ---- torso
    T = Frame(hip[0], hip[1] - bob, lean, u)
    f_th = max(l[0] for l in legs); b_th = min(l[0] for l in legs)
    if kind == "civ":
        sw = math.sin(TAU * phase * 2)
        hf = 0.1 + 0.2 * max(0.0, f_th)
        hb = -0.12 + 0.2 * min(0.0, b_th)
        add(T.pts([(-0.04, 0.4, True), (-0.008, 0.405, True), (0.03, 0.375), (0.058, 0.34), (0.08, 0.3),
                   (0.088, 0.24), (0.08, 0.135), (0.086, 0.125, True), (0.086, 0.1, True), (0.08, 0.09, True),
                   (0.082, 0.02), (hf, -0.19), (hf + 0.006, -0.215, True), (0.0, -0.212 + 0.004 * sw),
                   (-0.015, -0.18, True), (-0.03, -0.212, True), (hb, -0.2 - 0.006 * sw, True), (-0.105, -0.06),
                   (-0.088, 0.09, True), (-0.094, 0.1, True), (-0.094, 0.125, True), (-0.088, 0.135, True),
                   (-0.1, 0.25), (-0.088, 0.325), (-0.06, 0.35)]))
    else:
        add(T.pts([(-0.035, 0.37, True), (-0.005, 0.378, True), (0.036, 0.352), (0.07, 0.315), (0.085, 0.25),
                   (0.078, 0.12), (0.087, 0.115, True), (0.087, 0.075, True), (0.08, 0.07, True), (0.086, -0.06, True),
                   (0.0, -0.07), (-0.088, -0.06, True), (-0.082, 0.07, True), (-0.092, 0.075, True),
                   (-0.092, 0.115, True), (-0.083, 0.12, True), (-0.092, 0.25), (-0.08, 0.32), (-0.06, 0.345)]))
        add(T.pts([(0.07, 0.108, True), (0.108, 0.105, True), (0.11, 0.05, True), (0.072, 0.048, True)]))   # pouches
        add(T.pts([(0.02, 0.108, True), (0.06, 0.106, True), (0.062, 0.055, True), (0.022, 0.056, True)]))
        add(T.pts([(-0.06, 0.07), (-0.12, 0.065), (-0.135, 0.0), (-0.12, -0.07), (-0.06, -0.075)]))       # bread bag
        add(T.pts([(-0.07, 0.31, True), (-0.14, 0.3), (-0.155, 0.27), (-0.155, 0.18), (-0.14, 0.16),
                   (-0.075, 0.165, True)]))                                                                # pack
        add(T.pts([(-0.06, 0.315), (-0.09, 0.345), (-0.145, 0.34), (-0.165, 0.315), (-0.15, 0.29), (-0.07, 0.295)]))  # roll

    # ---- head + neck
    nod = (lean * 0.6 if not charge else lean * 0.25) + 0.01 * math.sin(TAU * phase * 2)
    hc = T(0.022 + 0.05 * lean, 0.438)
    HH = 0.128 * u
    Hf = Frame(hc[0], hc[1], nod, HH)
    hpts = lambda lst: Hf.pts([(p[0], -p[1]) + tuple(p[2:]) for p in lst])
    add([T(-0.03, 0.34), Hf(-0.36, -0.3), Hf(-0.33, -0.22), Hf(-0.1, -0.3), Hf(0.15, -0.44), Hf(0.15, -0.54),
         Hf(0.18, -0.6, True), Hf(0.16, -0.66), T(0.045, 0.34)])
    add(hpts(HEAD))
    add(hpts(HELMET if kind == "sol" else FEDORA))

    # ---- arms
    ap = ARM_PROF["sol" if kind == "sol" else "civ"]
    shoulder = T(-0.008, 0.3)
    La, Lf = 0.165 * u, 0.145 * u

    def arm(el, hand_ang, hand=HAND):
        a_up = ang_of(shoulder, el)
        wrist = bone_pt(el, hand_ang, Lf, 0)
        add(bone_outline(shoulder, a_up, La, ap["up"], u))
        dot(shoulder, 0.037 * u)
        dot(el, 0.028 * u)
        add(bone_outline(el, hand_ang, Lf, ap["fore"], u))
        add([bone_pt(wrist, hand_ang, p[0] * u, p[1] * u) + tuple(p[2:]) for p in hand])
        return wrist

    def swing_arm(side_ph, amp):
        a_up = -amp * math.sin(side_ph) + lean * 0.5
        el = bone_pt(shoulder, a_up, La, 0)
        fore = a_up + 0.2 + (0.25 + 0.7 * run) * max(0.0, math.sin(side_ph))
        arm(el, fore)

    if kind == "civ":
        swing_arm(TAU * phase + math.pi / 2, 0.55)
        if suitcase:
            sw = 0.06 * math.sin(TAU * phase * 2 + 0.6)
            el = bone_pt(shoulder, 0.1 + sw, La, 0)
            wrist = arm(el, 0.06 + sw, FIST)
            grip = bone_pt(wrist, 0.06 + sw, 0.045 * u, 0)
            S = Frame(grip[0], grip[1], -sw * 0.8, u)
            bw, bh = 0.16, 0.125
            r_ = 0.012
            add(S.pts([(-bw + r_, -0.03, True), (bw - r_, -0.03, True), (bw, -0.03 - r_, True),
                       (bw, -0.03 - bh + r_, True), (bw - r_, -0.03 - bh, True), (-bw + r_, -0.03 - bh, True),
                       (-bw, -0.03 - bh + r_, True), (-bw, -0.03 - r_, True)]))
            add(S.pts([(-bw - 0.004, -0.075, True), (bw + 0.004, -0.075, True), (bw + 0.004, -0.085, True),
                       (-bw - 0.004, -0.085, True)]))                               # strap
            add(S.pts([(-0.035, -0.03, True), (-0.03, 0.005), (0.0, 0.015), (0.03, 0.005), (0.035, -0.03, True),
                       (0.02, -0.03, True), (0.018, -0.005), (0.0, 0.0), (-0.018, -0.005), (-0.02, -0.03, True)]))
        else:
            swing_arm(TAU * phase + math.pi * 1.5, 0.42)
    else:
        if charge:
            R = Frame(*T(-0.07, 0.07), -0.3 - lean * 0.2 + 0.04 * math.sin(TAU * phase * 2), u)
            rp = R.pts(RIFLE)
            add(rp)
            add([R(0.6, 0.0), R(0.73, 0.004), R(0.6, 0.008)])                 # bayonet
            for tgt, bend in ((R(0.37, -0.02), 1), (R(0.155, -0.03), 1)):
                el = ik(shoulder, tgt, La, Lf, bend)
                a_f = ang_of(el, tgt)
                arm(el, a_f, FIST)
        else:
            R = Frame(*T(-0.14, -0.13), -math.pi / 2 + 0.14 + lean, u)
            add(R.pts(RIFLE))
            swing_arm(TAU * phase + math.pi / 2, 0.4)
            tgt = T(0.045, 0.2)
            el = ik(shoulder, tgt, La, Lf, 1)
            arm(el, ang_of(el, tgt), FIST)

    # ---- draw, dropped onto the ground
    ctx.save()
    ctx.translate(0, gy - ground)
    ctx.set_source_rgb(*col[:3])
    for sh in shapes:
        if sh[0] == "p":
            smooth_path(ctx, sh[1])
        else:
            ctx.new_sub_path(); ctx.arc(sh[1], sh[2], sh[3], 0, TAU)
        ctx.fill()
    ctx.restore()
    return (hip[0], gy - ground)


def stride(u, run=0.0, charge=False):
    """Ground distance (px) covered per unit of phase, so the background can scroll without foot sliding."""
    A = 0.34 + 0.28 * run
    lean = 0.04 + 0.2 * run + (0.08 if charge else 0)
    L1, L2 = 0.25 * u, 0.245 * u

    def ankle_x(p):
        ph = TAU * p + math.pi / 2
        thigh = A * math.sin(ph) + lean * 0.35
        flex = 0.07 + (0.8 + 0.9 * run) * max(0.0, math.cos(ph - 0.5)) ** 2
        return L1 * math.sin(thigh) + L2 * math.sin(thigh - flex)
    return 2 * (ankle_x(0.0) - ankle_x(0.5))



def leg_state(phase, u, run=0.0, charge=False, hip=(0.0, 0.0)):
    """(thigh, shin, knee, ankle, pitch) for both legs, hip at `hip` (before dropping to the ground)."""
    A = 0.34 + 0.28 * run
    lean = 0.04 + 0.2 * run + (0.08 if charge else 0)
    L1, L2 = 0.25 * u, 0.245 * u
    legs = []
    for s in (0, 1):
        ph = TAU * phase + s * math.pi + math.pi / 2
        sn = math.sin(ph)
        thigh = A * sn + lean * 0.35
        flex = 0.07 + (0.8 + 0.9 * run) * max(0.0, math.cos(ph - 0.5)) ** 2
        shin = thigh - flex
        pitch = 0.6 * max(0.0, -sn) ** 3 * (1 if math.cos(ph) < 0.4 else 0.7) - 0.22 * max(0.0, sn) ** 4
        pitch += 0.25 * run * max(0.0, math.cos(ph))
        knee = bone_pt(hip, thigh, L1, 0); ankle = bone_pt(knee, shin, L2, 0)
        legs.append((thigh, shin, knee, ankle, pitch))
    return legs


def _shoes(phase, u, run, charge, kind):
    shoe = BOOT if kind == "sol" else OXFORD
    return [Frame(an[0], an[1], pitch, u).pts([(p[0], -p[1]) for p in shoe])
            for _, _, _, an, pitch in leg_state(phase, u, run, charge)]


_TRAVEL = {}


def travel(phase, u, run=0.0, charge=False, kind="civ"):
    """Cumulative ground distance at `phase`, derived from the sole point that is actually on the ground.

    Scrolling the ground by this amount keeps the planted foot still (heel strike -> roll -> toe off)
    instead of letting it slide, which is what made the walk look like it was floating.
    """
    key = (round(u, 3), run, charge, kind)
    if key not in _TRAVEL:
        N = 2000
        cum = [0.0]
        prev = _shoes(0.0, u, run, charge, kind)
        for i in range(1, N + 1):
            p = i / N
            cur = _shoes(p, u, run, charge, kind)
            low = max(max(q[1] for q in f) for f in prev)
            # contact foot + sole point = the lowest one in the previous step
            fi, j = max(((a, b) for a in range(2) for b in range(len(prev[a]))), key=lambda ab: prev[ab[0]][ab[1]][1])
            dx = prev[fi][j][0] - cur[fi][j][0]
            # vertical drop of the whole figure also changes which point is lowest; only count backward travel
            cum.append(cum[-1] + max(0.0, dx))
            prev = cur
        _TRAVEL[key] = cum
    cum = _TRAVEL[key]
    N = len(cum) - 1
    k = math.floor(phase)
    f = (phase - k) * N
    i = int(f)
    frac = f - i
    val = cum[i] + (cum[min(i + 1, N)] - cum[i]) * frac
    return k * cum[-1] + val
