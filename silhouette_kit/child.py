"""A 1930s English country boy (flat cap, shirt, shorts, knee socks), side view facing right.

child(ctx, x, ground_y, height, phase, run=1.0, throw=None, c=...) -> dict(hand=(x, y), hand_ang=a, hip=(x, y))
  phase : 0..1 per stride (feet land at 0.0 and 0.5)
  run   : 0 walk .. 1 run
  throw : None, or 0..1 throwing motion of the near arm (0 wind-up, ~0.5 release, 1 follow-through)
Built on the same outline helpers as figure.py, with child proportions (bigger head, shorter limbs).
"""
import math
from .figure import Frame, bone_pt, bone_outline, ang_of, smooth_path, ik

TAU = 2 * math.pi
C = True

# head in head units (1 = crown-to-chin), x forward, y DOWN: rounder skull, small nose, soft chin
CHILD_HEAD = [(0.0, -0.5), (0.26, -0.44), (0.38, -0.28), (0.41, -0.1), (0.4, -0.04, C), (0.44, 0.04),
              (0.47, 0.1), (0.45, 0.15, C), (0.42, 0.17, C), (0.43, 0.22), (0.44, 0.25, C), (0.41, 0.28, C),
              (0.42, 0.32), (0.38, 0.4), (0.3, 0.46), (0.12, 0.44), (0.0, 0.38), (-0.2, 0.3, C), (-0.38, 0.22),
              (-0.47, 0.02), (-0.46, -0.2), (-0.34, -0.4), (-0.18, -0.48)]
FLAT_CAP = [(-0.5, -0.12, C), (-0.44, -0.3), (-0.3, -0.5), (0.0, -0.6), (0.3, -0.56), (0.48, -0.44),
            (0.62, -0.3), (0.7, -0.26, C), (0.66, -0.2), (0.44, -0.2, C), (0.4, -0.2), (-0.1, -0.16), (-0.46, -0.08)]
SHOE = [(-0.03, -0.022), (-0.04, 0.0), (-0.042, 0.028, C), (-0.04, 0.034, C), (0.07, 0.034), (0.095, 0.022),
        (0.09, 0.006), (0.05, -0.006), (0.02, -0.02)]
FIST = [(-0.005, 0.03), (0.035, 0.036), (0.06, 0.03), (0.07, 0.012), (0.066, -0.014), (0.05, -0.03),
        (0.015, -0.032), (-0.005, -0.028)]
# leg profiles (t along bone, front, back) in units of height
THIGH = [(0, 0.06, 0.07), (0.35, 0.062, 0.066), (0.55, 0.058, 0.06, ), (0.58, 0.04, 0.042), (1.0, 0.033, 0.034)]
SHIN = [(0, 0.033, 0.034), (0.12, 0.034, 0.038), (0.16, 0.037, 0.042), (0.45, 0.034, 0.042), (0.85, 0.028, 0.03),
        (1.0, 0.027, 0.028)]
UPPER = [(0, 0.04, 0.042), (0.5, 0.034, 0.034), (0.55, 0.028, 0.028), (1.0, 0.024, 0.024)]
FORE = [(0, 0.024, 0.024), (1.0, 0.02, 0.02)]


def _rgb(c):
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) / 255 for i in (0, 2, 4))


def child(ctx, x, gy, h, phase, run=1.0, throw=None, c="#000000"):
    u = h
    shapes = []
    add = lambda pts: shapes.append(("p", pts))
    dot = lambda p, r: shapes.append(("c", p[0], p[1], r))
    L1, L2 = 0.215 * u, 0.205 * u
    A = 0.36 + 0.3 * run
    lean = 0.05 + 0.2 * run
    if throw is not None:                         # plant the feet and rock the body for the throw
        k = throw
        lean = -0.12 + 0.5 * max(0.0, min(1.0, (k - 0.3) / 0.4)) if k < 0.7 else 0.38 - 0.1 * (k - 0.7)
        A = 0.28
    hip = (x, 0.0)
    legs = []
    for s in (0, 1):
        ph = TAU * phase + s * math.pi + math.pi / 2
        sn = math.sin(ph)
        if throw is None:
            thigh = A * sn + lean * 0.3
            flex = 0.08 + (0.9 + 0.9 * run) * max(0.0, math.cos(ph - 0.5)) ** 2
        else:                                      # stride stance: front leg forward, back leg behind
            thigh = (0.32 if s == 0 else -0.3) + lean * 0.2
            flex = 0.1 if s == 0 else 0.35
        shin = thigh - flex
        pitch = 0.5 * max(0.0, -sn) ** 3 if throw is None else (0.0 if s == 0 else 0.5)
        knee = bone_pt(hip, thigh, L1, 0); ankle = bone_pt(knee, shin, L2, 0)
        legs.append((thigh, shin, knee, ankle, pitch))
    shoe_pts = []
    for thigh, shin, knee, ankle, pitch in legs:
        add(bone_outline(hip, thigh, L1, THIGH, u))
        dot(knee, 0.03 * u)
        add(bone_outline(knee, shin, L2, SHIN, u))
        sp = Frame(ankle[0], ankle[1], pitch, u).pts([(p[0], -p[1]) + tuple(p[2:]) for p in SHOE])
        shoe_pts += sp
        add(sp)
    ground = max(p[1] for p in shoe_pts)
    bob = 0.01 * u * abs(math.sin(TAU * phase * 2)) * run if throw is None else 0.0
    T = Frame(hip[0], hip[1] - bob, lean, u)
    # shirt + shorts waist
    add(T.pts([(-0.075, 0.25, C), (-0.03, 0.27), (0.03, 0.265), (0.07, 0.24, C), (0.08, 0.14), (0.075, 0.04),
               (0.08, -0.03, C), (-0.08, -0.03, C), (-0.085, 0.06), (-0.085, 0.16)]))
    # head, neck, cap
    hc = T(0.025 + 0.04 * lean, 0.34)
    HH = 0.17 * u
    nod = lean * 0.5
    Hf = Frame(hc[0], hc[1], nod, HH)
    hp = lambda lst: Hf.pts([(p[0], -p[1]) + tuple(p[2:]) for p in lst])
    add([T(-0.03, 0.24), Hf(-0.3, -0.25), Hf(0.1, -0.42), Hf(0.15, -0.5), T(0.035, 0.25)])
    add(hp(CHILD_HEAD))
    add(hp(FLAT_CAP))
    # arms
    shoulder = T(-0.005, 0.235)
    La, Lf = 0.14 * u, 0.13 * u

    def arm(el, fore_ang, fist=True):
        a_up = ang_of(shoulder, el)
        wrist = bone_pt(el, fore_ang, Lf, 0)
        add(bone_outline(shoulder, a_up, La, UPPER, u))
        dot(shoulder, 0.036 * u); dot(el, 0.022 * u)
        add(bone_outline(el, fore_ang, Lf, FORE, u))
        add([bone_pt(wrist, fore_ang, p[0] * u, p[1] * u) + tuple(p[2:]) for p in FIST])
        return wrist

    far_ph = TAU * phase + math.pi / 2
    swing = 0.35 + 0.45 * run
    bend = 0.5 + 0.9 * run
    a_up = -swing * math.sin(far_ph) + lean * 0.4
    el = bone_pt(shoulder, a_up, La, 0)
    arm(el, a_up + bend + 0.2 * max(0.0, math.sin(far_ph)))
    if throw is None:
        near_ph = far_ph + math.pi
        a_up = -swing * math.sin(near_ph) + lean * 0.4
        el = bone_pt(shoulder, a_up, La, 0)
        fore = a_up + bend + 0.2 * max(0.0, math.sin(near_ph))
    else:
        k = throw
        # keyed arm angles (0 = down, + forward): wind-up behind the head -> release up/forward -> follow down
        keys = [(0.0, -2.4, -2.9), (0.35, -2.6, -3.3), (0.5, 3.1, 2.7), (0.58, 2.4, 2.3), (1.0, 1.0, 1.1)]
        for (k0, u0, f0), (k1, u1, f1) in zip(keys[:-1], keys[1:]):
            if k0 <= k <= k1:
                q = (k - k0) / (k1 - k0)
                q = q * q * (3 - 2 * q)
                d = (u1 - u0 + math.pi) % TAU - math.pi
                df = (f1 - f0 + math.pi) % TAU - math.pi
                a_up = u0 + d * q
                fore = f0 + df * q
                break
        el = bone_pt(shoulder, a_up, La, 0)
    wrist = arm(el, fore)
    hand = bone_pt(wrist, fore, 0.04 * u, 0)

    ctx.save()
    ctx.translate(0, gy - ground)
    col = _rgb(c) if isinstance(c, str) else c
    ctx.set_source_rgb(*col)
    for sh in shapes:
        if sh[0] == "p":
            smooth_path(ctx, sh[1])
        else:
            ctx.new_sub_path(); ctx.arc(sh[1], sh[2], sh[3], 0, TAU)
        ctx.fill()
    ctx.restore()
    dy = gy - ground
    return {"hand": (hand[0], hand[1] + dy), "hand_ang": fore, "hip": (hip[0], hip[1] + dy)}
