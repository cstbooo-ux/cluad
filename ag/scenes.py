"""The eleven scenes. Each scene is a pure function scene(t, txt=True) -> HDR float image (H, W, 3)."""
import os, json, functools, colorsys
import numpy as np, cv2
from scipy.interpolate import CubicSpline
from engine import *
from timeline import *

SS = float(os.environ.get("AG_SS", "1.5"))
QUAL = float(os.environ.get("AG_Q", "1.0"))
SW, SH = int(W * SS), int(H * SS)
DATA = json.load(open(os.path.join(D, "data.json")))

GOLD = np.array([1.0, 0.72, 0.32], np.float32)
CYAN = np.array([0.35, 0.75, 1.0], np.float32)
MAG = np.array([0.95, 0.35, 0.75], np.float32)
WHITE = np.array([1.0, 1.0, 1.0], np.float32)
PAL = np.array([[1.0, 0.72, 0.32], [1.0, 0.45, 0.35], [0.95, 0.35, 0.75], [0.55, 0.42, 1.0], [0.3, 0.75, 1.0]], np.float32)


def pal(u):
    u = np.clip(np.asarray(u, np.float32), 0, 1) * (len(PAL) - 1)
    i = np.minimum(np.floor(u).astype(int), len(PAL) - 2)
    f = (u - i)[..., None]
    return PAL[i] * (1 - f) + PAL[i + 1] * f


def add(img, layer, color, k=1.0):
    img += layer[..., None] * (np.asarray(color, np.float32) * k)


def ring(v, px, py, r, w=1.5):
    return np.exp(-((np.hypot((v.X - v.cx) * v.s + W / 2 - px, -(v.Y - v.cy) * v.s + H / 2 - py) - r) / w) ** 2)


def formula(img, tex, cx, cy, size, op=1.0, color=(1, 1, 1), glow=0.25, scale=1.0, blur=0.0):
    if op > 0.003:
        paste(img, math_img(tex, size), cx, cy, color, opacity=op, glow=glow, scale=scale, blur=blur, scrim=0.5)


def label(img, text, cx, cy, size, op=1.0, color=(1, 1, 1), italic=False, anchor="c", weight="Regular", tracking=0.0):
    if op > 0.003:
        paste(img, text_img(text, size, weight, latin=True, italic=italic, tracking=tracking), cx, cy, color,
              opacity=op, anchor=anchor, scrim=0.4)


def zh(img, text, cx, cy, size, op=1.0, color=(1, 1, 1), weight="Regular", anchor="c", tracking=0.0, glow=0.0,
       scale=1.0, blur=0.0):
    if op > 0.003:
        paste(img, text_img(text, size, weight, tracking=tracking), cx, cy, color, opacity=op, anchor=anchor,
              glow=glow, scale=scale, blur=blur, scrim=0.45)


def pulse(t, t0, tau=0.15):
    return float(np.exp(-(t - t0) / tau)) if t >= t0 else 0.0


# ======================================================================= 1. intro
_rng = np.random.default_rng(5)
INTRO_ON = _rng.uniform(0, 2 * np.pi, 110)
INTRO_OFF = np.stack([_rng.uniform(-3.3, 3.3, 900), _rng.uniform(-1.85, 1.85, 900)], 1)
INTRO_OFF = INTRO_OFF[np.abs(np.hypot(INTRO_OFF[:, 0], INTRO_OFF[:, 1]) - 1) > 0.06]
INTRO_TA = _rng.uniform(2.75, 3.6, 1100)


def intro(t, txt=True):
    img = background(t, star_amt=ss(0, 2.2, t), neb_amt=ss(0.3, 3.5, t))
    v = View2D(0, 0, 300)
    ax = ss(1.0, 2.6, t) * 0.12
    if ax > 0:
        dax = np.minimum(np.abs(v.X), np.abs(v.Y)) * v.s
        add(img, np.exp(-(dax / 0.8) ** 2) * ax, (0.5, 0.65, 1.0))
    # candidate points: those off the circle fade away, the solutions remain
    if t > 2.7:
        n_off = len(INTRO_OFF)
        a_off = np.array([ss(INTRO_TA[i], INTRO_TA[i] + 0.2, t) for i in range(n_off)])
        a_off *= 1 - ss(3.9 + (INTRO_TA[:n_off] - 2.75) * 0.6, 4.5 + (INTRO_TA[:n_off] - 2.75) * 0.6, t)
        if a_off.max() > 0:
            drift = INTRO_OFF * (1 + 0.04 * ss(3.9, 4.8, t))
            img += glow_points(v.to_px(drift), a_off * 1.2, (0.55, 0.65, 1.0), sigmas=((1.0, 1.0), (4, 0.3)))
        on = np.stack([np.cos(INTRO_ON), np.sin(INTRO_ON)], 1)
        a_on = np.array([ss(INTRO_TA[-1 - i], INTRO_TA[-1 - i] + 0.2, t) for i in range(len(on))])
        a_on *= 1 + 2.5 * ss(3.9, 4.5, t)
        img += glow_points(v.to_px(on), a_on * 1.4, GOLD, sigmas=((1.2, 1.0), (5, 0.4)))
    # the circle, traced
    prog = ease_io(ss(4.2, 5.9, t)) * 2 * np.pi
    if prog > 0:
        r = np.hypot(v.X, v.Y)
        d = np.abs(r - 1) * v.s
        ang = np.mod(np.arctan2(v.Y, v.X), 2 * np.pi)
        m = np.clip((prog - ang) / 0.02, 0, 1) if prog < 2 * np.pi - 1e-3 else 1.0
        boost = 1 + 2.5 * np.exp(-np.clip(prog - ang, 0, None) / 0.5) * (1 - ss(5.9, 6.6, t))
        breathe = 1 + 0.15 * np.sin((t - 6) * 3) * ss(6, 6.5, t)
        add(img, line_glow(d, 1.7, 2.3, 0.35, 9) * m * boost * breathe, GOLD)
        if prog < 2 * np.pi - 1e-3:
            hp = v.to_px(np.array([[np.cos(prog), np.sin(prog)]]))
            img += glow_points(hp, np.array([6.0]), (1, 0.9, 0.7))
    if txt:
        # formula: slams in at 2.5, then rises to the top
        k = ease_io(ss(3.5, 4.3, t))
        cy = H / 2 * (1 - k) + 0.13 * H * k
        sc = (1 + 0.15 * np.exp(-(t - 2.5) * 8)) * (1 - 0.36 * k)
        formula(img, r"x^2 + y^2 = 1", W / 2, cy, 110, ss(2.45, 2.58, t), scale=sc, glow=0.5 * (1 - k) + 0.2)
        caption(img, t, 5.2, 7.2, "满足方程的点，连成了一个形状", "THE SOLUTIONS OF AN EQUATION FORM A SHAPE")
    return img


# ======================================================================= 2. conics
def conic_view(t):
    k = ease_io(ss(7.5, 9.8, t))
    return View2D(0.9 * k, 0, 300 - 80 * k)


def conics(t, txt=True):
    img = background(t)
    v = conic_view(t)
    e = 1.8 * ease_io(ss(8.0, 12.2, t))
    X, Y = v.X, v.Y
    r2 = X * X + Y * Y
    add(img, np.exp(-((np.minimum(np.abs(X), np.abs(Y)) * v.s) / 0.8) ** 2) * 0.1, (0.5, 0.65, 1.0))
    for kk in range(1, 19):
        ek = 0.1 * kk
        if ek > e - 0.03:
            break
        d = pix_dist(r2 - (1 + ek * X) ** 2)
        add(img, line_glow(d, 1.1, 0.55, 0.12, 5), pal(ek / 1.8), 0.9)
    d = pix_dist(r2 - (1 + e * X) ** 2)
    add(img, line_glow(d, 1.7, 2.4, 0.4, 9), pal(e / 1.8))
    # focus + directrix
    img += glow_points(v.to_px(np.array([[0.0, 0.0]])), np.array([3.0]), WHITE)
    if e > 0.05:
        xd = -1 / e
        dd = np.abs(X - xd) * v.s
        dash = (np.sin(Y * v.s / 7) > 0).astype(np.float32)
        add(img, np.exp(-(dd / 0.9) ** 2) * dash * 0.35 * ss(0.05, 0.3, e), (0.6, 0.7, 1.0))
    if txt:
        formula(img, r"x^2 + y^2 = 1", W / 2, 0.13 * H, 110, 1 - ss(7.5, 7.8, t), scale=0.64)
        formula(img, r"x^2 + y^2 = (1 + e\,x)^2", W / 2, 0.13 * H, 70, ss(7.6, 8.0, t))
        formula(img, r"e = %.2f" % e, W / 2, 0.215 * H, 44, ss(7.8, 8.2, t) * 0.9, color=pal(e / 1.8))
        names = [("圆", "circle", 1 - ss(0.005, 0.02, e)), ("椭圆", "ellipse", ss(0.02, 0.035, e) * (1 - ss(0.965, 0.98, e))),
                 ("抛物线", "parabola", ss(0.985, 0.995, e) * (1 - ss(1.005, 1.015, e))), ("双曲线", "hyperbola", ss(1.02, 1.035, e))]
        for zname, en, w in names:
            o = w * ss(7.8, 8.2, t)
            zh(img, zname, W / 2 - 8, 0.285 * H, 40, o, pal(e / 1.8), anchor="r")
            label(img, en, W / 2 + 10, 0.29 * H, 36, o * 0.85, (0.75, 0.8, 1.0), italic=True, anchor="l")
        caption(img, t, 8.6, 12.2, "圆、椭圆、抛物线、双曲线——同一个方程", "CIRCLE · ELLIPSE · PARABOLA · HYPERBOLA — ONE EQUATION")
    return img


# ======================================================================= 3. cubic + group law
def ec_add(P, Q, a=-1.0):
    (x1, y1), (x2, y2) = P, Q
    if abs(x1 - x2) < 1e-12 and abs(y1 + y2) < 1e-12:
        return None
    m = (3 * x1 * x1 + a) / (2 * y1) if abs(x1 - x2) < 1e-12 else (y2 - y1) / (x2 - x1)
    x3 = m * m - x1 - x2
    return (x3, m * (x1 - x3) - y1)


GP = (-0.9, np.sqrt(0.171))
GQ = (1.3, np.sqrt(2.197 - 1.3))
GS = ec_add(GP, GQ)
GR = (GS[0], -GS[1])
MULT = [GS]
for _ in range(15):
    MULT.append(ec_add(MULT[-1], GS) if MULT[-1] is not None else None)


def cubic_view():
    return View2D(0.25, 0, 250)


def cubic(t, txt=True):
    img = background(t)
    v = cubic_view()
    X, Y = v.X, v.Y
    f = Y * Y - X ** 3 + X
    gy, gx = np.gradient(f)
    gm = np.sqrt(gx * gx + gy * gy) + 1e-12
    # A: flowing contour field
    fa = ss(12.5, 13.0, t) * (1 - ss(15.0, 15.9, t))
    if fa > 0:
        dl = 0.35
        phase = dl * ((0.55 * min(t - 15.0, 0.0)) % 1.0)
        g = (f - phase) / dl
        k = np.round(g)
        d = np.abs(g - k) * dl / gm
        c = k * dl + phase
        col = pal((c + 2.8) / 5.6)
        spacing = dl / gm
        inten = (np.exp(-(d / 1.0) ** 2) * 0.9 + np.exp(-d / 4) * 0.1) * fa * ss(5, 16, spacing) * (np.abs(c) < 3.2)
        img += inten[..., None] * col
    d0 = np.abs(f) / gm
    main = ss(15.0, 15.25, t)
    if main > 0:
        fade_mid = 1 - 0.45 * ss(22.5, 23.2, t) * 0
        add(img, line_glow(d0, 1.7, 2.5, 0.4, 9) * main * fade_mid, GOLD)
    # C: group law
    pts, vals, cols = [], [], []

    def dot(P, t0, col, big=1.0):
        if t >= t0 and P is not None:
            pts.append(P)
            vals.append((14 + 40 * pulse(t, t0, 0.2)) * big)
            cols.append(col)

    fade_c = 1 - ss(22.5, 23.1, t)
    dot(GP, GL["P"], CYAN)
    dot(GQ, GL["Q"], CYAN)
    if t >= GL["R"]:
        dot(GR, GL["R"], WHITE, 0.8 * fade_c + 0.2)
    dot(GS, GL["S"], GOLD, 1.5)
    # chord
    if t >= GL["line0"]:
        g = ease_out(ss(GL["line0"], GL["line1"], t))
        P, Q = np.array(GP), np.array(GQ)
        dv = (Q - P) / np.linalg.norm(Q - P)
        mid = (P + Q) / 2
        a = mid - dv * 3.2 * g
        b = mid + dv * 3.2 * g
        ds = seg_dist(X, Y, a, b) * v.s
        add(img, line_glow(ds, 1.2, 1.3, 0.2, 6) * fade_c, (0.75, 0.85, 1.0))
    if t >= GL["refl0"]:
        g = ease_out(ss(GL["refl0"], GL["refl1"], t))
        a = np.array(GR)
        b = a + (np.array(GS) - a) * g
        ds = seg_dist(X, Y, a, b) * v.s
        dash = (np.sin(Y * v.s / 6) > 0).astype(np.float32)
        add(img, line_glow(ds, 1.1, 1.2, 0.15, 5) * dash * fade_c, (1.0, 0.85, 0.6))
    for t0, P, cc in ((GL["P"], GP, CYAN), (GL["Q"], GQ, CYAN), (GL["R"], GR, WHITE), (GL["S"], GS, GOLD)):
        if t >= t0:
            px = v.to_px(np.array([P]))[0]
            k = ss(t0, t0 + 0.15, t) * (fade_c if P is GR else 1.0) * (1 - 0.5 * ss(22.5, 23.1, t))
            add(img, ring(v, px[0], px[1], 13, 1.5) * 1.6 * k, cc)
    for t0, P in ((GL["P"], GP), (GL["Q"], GQ), (GL["S"], GS)):
        if t >= t0:
            dt = t - t0
            px = v.to_px(np.array([P]))[0]
            add(img, ring(v, px[0], px[1], 8 + 90 * ease_out(dt / 0.6), 2.0) * np.exp(-dt * 4) * 1.5, (1, 0.9, 0.7))
    # D: multiples of P+Q hopping around
    for i, (tm, P) in enumerate(zip(MULT_T, MULT)):
        if t < tm or P is None or abs(P[0] - 0.25) > 3.7 or abs(P[1]) > 2.1:
            continue
        dot(P, tm, pal(0.3 + 0.7 * i / 16), 0.7)
        if i > 0 and MULT[i - 1] is not None:
            fl = pulse(t, tm, 0.18)
            if fl > 0.02:
                ds = seg_dist(X, Y, np.array(MULT[i - 1]), np.array(P)) * v.s
                add(img, line_glow(ds, 1.0, 0.8, 0.1, 5) * fl, (0.8, 0.8, 1.0))
    if pts:
        pp = v.to_px(np.array(pts))
        for p_, val, col in zip(pp, vals, cols):
            img += glow_points(p_[None], np.array([val]), col, sigmas=((2.2, 1.0), (6, 0.5), (18, 0.3)))
            img += glow_points(p_[None], np.array([val * 0.35]), WHITE, sigmas=((1.2, 1.0),))
    if txt:
        formula(img, r"y^2 = x^3 - x + c", W / 2, 0.12 * H, 70, ss(12.6, 13.0, t) * (1 - ss(14.8, 15.0, t)))
        formula(img, r"y^2 = x^3 - x", W / 2, 0.12 * H, 70, ss(15.0, 15.1, t), glow=0.3 + 0.8 * pulse(t, 15.0, 0.3))
        caption(img, t, 15.3, 17.4, "椭圆曲线", "ELLIPTIC CURVE", size=72, weight="Bold", stagger=0.08)
        for t0, P, tex, off in ((GL["P"], GP, "P", (-34, -30)), (GL["Q"], GQ, "Q", (30, -30)),
                                (GL["R"], GR, "R", (-10, -34)), (GL["S"], GS, r"P \oplus Q", (-12, 40))):
            if t >= t0:
                px = v.to_px(np.array([P]))[0]
                op = ss(t0, t0 + 0.2, t) * (fade_c if tex == "R" else 1.0)
                formula(img, tex, px[0] + off[0], px[1] + off[1], 40, op, color=(1, 0.95, 0.85), glow=0.2)
        caption(img, t, 18.8, 22.3, "曲线上的点，竟然可以相加", "POINTS ON THIS CURVE CAN BE ADDED")
        caption(img, t, 22.6, 24.8, "它们构成一个「群」——代数与几何在此相遇", "THEY FORM A GROUP: ALGEBRA MEETS GEOMETRY")
    return img


# ======================================================================= 4. complex torus
_mesh = None


def mesh():
    global _mesh
    if _mesh is None:
        _mesh = Mesh()
    return _mesh


TL = 2.6


def torus_geom(t, nu=180, nv=100):
    u, vv, idx = grid_mesh(nu, nv)
    k1 = ease_io(ss(26.6, 28.4, t))
    k2 = ease_io(ss(28.2, 30.2, t))
    Lv = TL
    Lu = TL + (2 * np.pi * 1.25 - TL) * k2
    s1 = (vv - 0.5) * Lv
    if k1 < 1e-4:
        yp, zp = s1, np.zeros_like(s1)
    else:
        r1 = Lv / (2 * np.pi * k1)
        yp, zp = r1 * np.sin(s1 / r1), r1 * (1 - np.cos(s1 / r1))
    s2 = (u - 0.5) * Lu
    if k2 < 1e-4:
        Xp, Zp = s2, zp
        C = np.array([0, 0, 0.0])
    else:
        r2 = Lu / (2 * np.pi * k2)
        ph = s2 / r2
        Xp = (r2 + zp) * np.sin(ph)
        Zp = (r2 + zp) * np.cos(ph) - r2
        C = np.array([0, 0, -r2])
    P = np.stack([Xp, yp, Zp], -1)
    if t > 30.2:  # spin about the torus axis (parallel to y)
        a = 0.45 * (t - 30.2) ** 1.2
        Q = P - C
        c, s = np.cos(a), np.sin(a)
        P = np.stack([c * Q[..., 0] + s * Q[..., 2], Q[..., 1], -s * Q[..., 0] + c * Q[..., 2]], -1) + C
    return P, u, vv, idx, k1, k2


def torus(t, txt=True):
    img = background(t)
    P, u, vv, idx, k1, k2 = torus_geom(t)
    N = grid_normals(P)
    cen = P.reshape(-1, 3).mean(0)
    # camera: from above the sheet, drifting to a 3/4 view of the ring
    az = -np.pi / 2 + 0.3 * np.sin(0.22 * (t - 25))
    el = 1.05 - 0.62 * ease_io(ss(27.0, 31.0, t))
    dist = 9.0 + 2.6 * ease_io(ss(27.5, 30.5, t))
    cam = Cam.orbit(cen + np.array([0, 0, -0.35]), dist, az, el, focal=2.0)
    nu, nv = P.shape[:2]
    base = np.array([0.03, 0.08, 0.25])
    col = np.broadcast_to(base, P.shape).reshape(-1, 3)
    # uv swapped on purpose: the shader's "band" (real locus) runs along u = 0, 1/2, 1 -> two meridian circles
    uvs = np.stack([vv, u], -1).reshape(-1, 2)
    c, a, dep = mesh().render(cam, SW, SH, P.reshape(-1, 3), N.reshape(-1, 3), col, uvs, idx,
                              gridA=0.5, gridN=8, gridM=8, bandA=2.6, bandCol=(1.0, 0.55, 0.12), gloss=0.7,
                              uedgeA=1.4, uedgeCol=tuple(MAG * 1.2 * (1 - k1)), emis=0.05)
    c = downsample(c)
    a = downsample(a)
    img = img * (1 - a[..., None]) + c
    # lattice of periods around the sheet (flat phase only)
    la = 1 - ss(26.2, 26.9, t)
    if la > 0:
        g = np.arange(-4, 5)
        L = np.array([[TL * (i + 0.5), TL * (j + 0.5), 0.0] for i in g for j in g])
        px, dd, zc = cam.project(L, W, H)
        ok = zc > 0.1
        img += glow_points(px[ok], np.full(ok.sum(), 3.0) * la * ss(25.0, 25.6, t), CYAN)
        # faint lattice lines
        ss_ = np.linspace(-4.5 * TL, 4.5 * TL, 1600)
        lines = []
        for i in g:
            x0 = TL * (i + 0.5)
            lines.append(np.stack([np.full_like(ss_, x0), ss_, 0 * ss_], 1))
            lines.append(np.stack([ss_, np.full_like(ss_, x0), 0 * ss_], 1))
        Lp = np.concatenate(lines)
        px, dd, zc = cam.project(Lp, W, H)
        ok = zc > 0.1
        img += glow_points(px[ok], np.full(ok.sum(), 0.12) * la * ss(25.0, 25.8, t), (0.5, 0.7, 1.0),
                           sigmas=((0.8, 1.0), (3, 0.3)))
    if txt:
        formula(img, r"y^2 = x^3 - x,\quad x,\,y \in \mathbb{C}", W / 2, 0.11 * H, 62, ss(25.3, 25.8, t))
        caption(img, t, 25.4, 28.9, "如果让 x 和 y 取复数……", "WHAT IF x AND y ARE COMPLEX NUMBERS?")
        caption(img, t, 30.6, 34.6, "椭圆曲线，原来是一个环面", "OVER THE COMPLEX NUMBERS, AN ELLIPTIC CURVE IS A TORUS")
        zh(img, "金色的两个圆 = 我们熟悉的实曲线", W * 0.5, H * 0.945, 26, ss(31.4, 32.0, t) * (1 - ss(34.4, 34.9, t)) * 0.8,
           (1.0, 0.8, 0.5))
    return img


# ======================================================================= surfaces
GLSL = {
    "clebsch": """float a=x*0.70710678, b=y*0.40824829, c=z*0.36514837;
  float X0=a+b+c, X1=-a+b+c, X2=-2.0*b+c, X3=0.5-1.5*c, X4=-0.5-1.5*c;
  return X0*X0*X0+X1*X1*X1+X2*X2*X2+X3*X3*X3+X4*X4*X4;""",
    "cayley": "return 4.0*(x*x+y*y+z*z) + 16.0*x*y*z - 1.0;",
    "kummer": """float s2=1.41421356, mu2=1.3, lam=1.70588235;
  float p=1.0-z-s2*x, q=1.0-z+s2*x, r=1.0+z+s2*y, s=1.0+z-s2*y;
  float a=x*x+y*y+z*z-mu2; return a*a - lam*p*q*r*s;""",
    "barth6": """float P2=2.6180340; float x2=x*x, y2=y*y, z2=z*z; float r=x2+y2+z2-1.0;
  return 4.0*(P2*x2-y2)*(P2*y2-z2)*(P2*z2-x2) - 4.2360680*r*r;""",
    "barth10": """float P4=6.8541020; float x2=x*x, y2=y*y, z2=z*z; float r2=x2+y2+z2;
  float a=8.0*(x2-P4*y2)*(y2-P4*z2)*(z2-P4*x2)*(x2*x2+y2*y2+z2*z2-2.0*x2*y2-2.0*x2*z2-2.0*y2*z2);
  float b=(r2-1.0)*(r2-0.3819660);
  return a + 11.0901699*b*b;""",
}
_surf = {}


def surf(name):
    if name not in _surf:
        _surf[name] = Surface(GLSL[name])
    return _surf[name]


def lookup_depth(dep, pxs):
    xi = np.clip(np.round(pxs[:, 0] - 0.5).astype(int), 0, dep.shape[1] - 1)
    yi = np.clip(np.round(pxs[:, 1] - 0.5).astype(int), 0, dep.shape[0] - 1)
    # min over a 3x3 neighbourhood would be safer at silhouettes; the centre sample is enough here
    return dep[yi, xi]


def visible(cam, dep, P, tol=0.035):
    pxs, dist, zc = cam.project(P, SW, SH)
    d = lookup_depth(dep, pxs)
    vis = (dist <= d * (1 + tol)) & (zc > 0)
    inside = (pxs[:, 0] >= 0) & (pxs[:, 0] < SW) & (pxs[:, 1] >= 0) & (pxs[:, 1] < SH)
    return pxs / SS, np.where(vis, 1.0, 0.08) * inside


def flare(pts, vals, color, length=60):
    """cross-shaped lens streaks for bright pops"""
    acc = splat(np.zeros((H, W), np.float32), pts, vals.astype(np.float32))
    k = cv2.getGaussianKernel(2 * length + 1, length / 2.5).astype(np.float32)
    hz = cv2.sepFilter2D(acc, -1, k, np.array([[1.0]], np.float32))
    vt = cv2.sepFilter2D(acc, -1, np.array([[1.0]], np.float32), k)
    return (hz + vt)[..., None] * np.asarray(color, np.float32) * 6


def surface_frame(t, name, cam, clipR, colOut, colIn, scan, scanAx, steps, dim=1.0, iso=2.5, gloss=0.8, shellA=0.3):
    col, mask, dep = surf(name).render(cam, SW, SH, clipR=clipR, steps=int(steps * QUAL), colOut=colOut,
                                       colIn=colIn, scan=scan, scanAx=scanAx, iso=iso, gloss=gloss,
                                       scanW=0.03 * clipR, shellA=shellA)
    img = background(t)
    c = downsample(col) * dim
    a = downsample(mask)
    return img * (1 - a[..., None]) + c, dep


# ======================================================================= 5. Clebsch + 27 lines
LINES = [(np.array(p), np.array(d)) for p, d in DATA["lines"]]
LINE_ORDER = np.random.default_rng(27).permutation(27)


def clebsch_cam(t):
    u = t - 35
    az = 0.55 + 0.085 * u
    el = 0.42 + 0.1 * np.sin(0.25 * u)
    dist = 13.6 - 1.2 * ease_io(ss(35, 45, t)) + 1.0 * ease_io(ss(45, 50, t))
    return Cam.orbit((0, 0, -0.35), dist, az, el, focal=2.0)


def clebsch(t, txt=True):
    R = 2.6
    cam = clebsch_cam(t)
    scan = -R - 0.1 + (2 * R + 0.4) * ease_out(ss(35.0, 36.5, t), 2)
    dim = 1 - 0.3 * ss(39.5, 41.0, t)
    img, dep = surface_frame(t, "clebsch", cam, R, (0.1, 0.32, 0.9), (1.0, 0.42, 0.08), scan, (0.2, 0.1, 1), 320, dim)
    n_shown = 0
    allp, allv = [], []
    flares, fv = [], []
    for j, k in enumerate(LINE_ORDER):
        tk = LINE_T[j]
        if t < tk:
            continue
        n_shown += 1
        p0, dv = LINES[k]
        smax = np.sqrt(max(R * R - p0 @ p0, 0))
        g = ease_out(ss(tk, tk + 0.35, t))
        s = np.linspace(-smax * g, smax * g, 2600)
        P = p0[None] + s[:, None] * dv[None]
        pts, vis = visible(cam, dep, P)
        inten = 0.32 + 2.0 * pulse(t, tk, 0.25) + 1.2 * pulse(t, 45.0, 0.5)
        allp.append(pts)
        allv.append(vis * inten)
        if t - tk < 0.4:
            flares.append(cam.project(p0[None], W, H)[0][0])
            fv.append(3.0 * pulse(t, tk, 0.12))
    if allp:
        img += glow_points(np.concatenate(allp), np.concatenate(allv), (1.0, 0.82, 0.5),
                           sigmas=((0.75, 1.0), (2.5, 0.35), (9, 0.15)))
    if flares:
        img += flare(np.array(flares), np.array(fv), (1.0, 0.9, 0.7))
    if txt:
        formula(img, r"x_0^3 + x_1^3 + x_2^3 + x_3^3 + x_4^3 = 0,\qquad x_0 + x_1 + x_2 + x_3 + x_4 = 0",
                W / 2, 0.1 * H, 50, ss(35.8, 36.4, t) * (1 - ss(39.2, 39.6, t)))
        caption(img, t, 36.0, 39.3, "克莱布什对角三次曲面", "THE CLEBSCH DIAGONAL CUBIC SURFACE")
        caption(img, t, 39.7, 44.7, "每一个光滑的三次曲面上，都恰好有 27 条直线",
                "EVERY SMOOTH CUBIC SURFACE CONTAINS EXACTLY 27 LINES")
        caption(img, t, 45.3, 49.7, "凯莱与萨蒙，1849 年", "CAYLEY & SALMON, 1849")
        if t > 39.8:
            last = max([LINE_T[j] for j in range(n_shown)] or [0])
            pop = 1 + 0.25 * pulse(t, last, 0.08) + 0.2 * pulse(t, 45.0, 0.3)
            op = ss(39.8, 40.2, t) * (1 - ss(49.4, 49.9, t))
            zh(img, str(n_shown), 0.865 * W, 0.44 * H, 170, op, (1.0, 0.9, 0.72), weight="Black", scale=pop,
               glow=0.4 + 1.2 * pulse(t, 45.0, 0.4))
            zh(img, "条直线", 0.865 * W, 0.57 * H, 34, op * 0.9, (1, 1, 1))
            label(img, "LINES", 0.865 * W, 0.615 * H, 22, op * 0.7, (0.65, 0.75, 0.95), tracking=0.3)
    return img


# ======================================================================= 6. the race for singularities
RACE_CFG = {
    "cayley": dict(R=1.55, out=(0.04, 0.5, 0.52), inn=(1.0, 0.32, 0.22), dist=7.4, az=0.7, el=0.5, steps=260,
                   ax=(0, 0, 1), zh="凯莱三次曲面", en="CAYLEY CUBIC", deg=3, N=4, iso=3.0),
    "kummer": dict(R=2.25, out=(0.42, 0.18, 0.95), inn=(1.0, 0.68, 0.18), dist=9.4, az=0.35, el=0.35, steps=320,
                   ax=(1, 0, 0.2), zh="库默尔曲面", en="KUMMER SURFACE", deg=4, N=16, iso=2.2),
    "barth6": dict(R=1.9, out=(0.3, 0.62, 1.0), inn=(1.0, 0.52, 0.12), dist=8.1, az=0.9, el=0.45, steps=380,
                   ax=(0, 1, 1), zh="巴特六次曲面", en="BARTH SEXTIC", deg=6, N=65, iso=2.6),
    "barth10": dict(R=2.0, out=(0.85, 0.1, 0.22), inn=(1.0, 0.82, 0.5), dist=8.6, az=0.4, el=0.62, steps=520,
                    ax=(1, 1, 0), zh="巴特十次曲面", en="BARTH DECIC", deg=10, N=345, iso=2.4),
}
RACE_TOP = {
    "cayley": ("一个 d 次曲面，最多能有多少个奇点？", "HOW MANY SINGULAR POINTS CAN A SURFACE OF DEGREE d HAVE?"),
    "kummer": ("四次曲面最多 16 个——库默尔，1864", "16 IS THE MAXIMUM FOR QUARTICS — KUMMER, 1864"),
    "barth6": ("六次曲面最多 65 个——直到 1997 年才被证明", "65 IS THE MAXIMUM FOR SEXTICS — PROVEN ONLY IN 1997"),
    "barth10": ("十次曲面：已知 345 个。真正的上限，至今无人知晓", "DEGREE 10: 345 KNOWN. THE TRUE MAXIMUM IS STILL UNKNOWN"),
}


def race_one(t, name, ts, txt=True):
    c = RACE_CFG[name]
    tau = t - ts
    az = c["az"] + 0.2 * tau
    el = c["el"] + 0.06 * np.sin(0.8 * tau)
    dist = c["dist"] * 1.12 * (1.1 - 0.1 * ease_out(tau / 5.0))
    cam = Cam.orbit((0, 0, -0.12 * c["R"]), dist, az, el, focal=2.0)
    R = c["R"]
    ax = np.array(c["ax"], float)
    ax /= np.linalg.norm(ax)
    scan = -R - 0.1 + (2 * R + 0.4) * ease_out(ss(0.0, 1.0, tau), 2)
    img, dep = surface_frame(t, name, cam, R, c["out"], c["inn"], scan, tuple(ax), c["steps"], 0.9, iso=c["iso"])
    nodes = np.array(DATA["nodes"][name])
    nv = len(nodes)
    order = np.random.default_rng(len(name)).permutation(nv)
    tk = 0.7 + 1.7 * (np.arange(nv) / max(nv - 1, 1)) ** 0.85
    popped = int(np.sum(tau >= tk))
    if popped:
        P = nodes[order[:popped]]
        pts, vis = visible(cam, dep, P, tol=0.02)
        dt = tau - tk[:popped]
        v = vis * (1.4 + 7.0 * np.exp(-dt / 0.15)) * (1 + 0.4 * np.sin(6 * t + np.arange(popped)))
        img += glow_points(pts, v, (0.85, 0.95, 1.0), sigmas=((1.3, 1.0), (4, 0.5), (14, 0.3)))
        fresh = dt < 0.5
        if fresh.any():
            img += flare(pts[fresh], vis[fresh] * np.exp(-dt[fresh] / 0.12) * 1.5, (0.8, 0.9, 1.0), 45)
    if txt:
        shown = int(round(c["N"] * popped / nv))
        tl = tk[popped - 1] if popped else 0
        pop = 1 + 0.18 * pulse(tau, tl, 0.07)
        op = ss(0.5, 0.8, tau) * (1 - ss(4.75, 5.0, tau))
        zh(img, str(shown), 0.865 * W, 0.44 * H, 170, op, (0.9, 0.96, 1.0), weight="Black", scale=pop,
           glow=0.3 + 0.8 * pulse(tau, tl, 0.2) * (popped == nv))
        zh(img, "个奇点", 0.865 * W, 0.57 * H, 34, op * 0.9)
        label(img, "SINGULAR POINTS", 0.865 * W, 0.615 * H, 20, op * 0.7, (0.65, 0.75, 0.95), tracking=0.25)
        lo = ss(0.3, 0.8, tau) * (1 - ss(4.75, 5.0, tau))
        zh(img, c["zh"], 0.07 * W, 0.8 * H, 46, lo, weight="Bold", anchor="l")
        label(img, f"{c['en']}  ·  DEGREE {c['deg']}", 0.07 * W, 0.862 * H, 22, lo * 0.8, (0.65, 0.75, 0.95),
              anchor="l", tracking=0.2)
        z, e = RACE_TOP[name]
        caption(img, t, ts + 0.3, ts + 4.6, z, e, y=0.085, size=40, en_size=19)
    return img


def race(t, txt=True):
    for name, ts, _ in reversed(RACE):
        if t >= ts:
            return race_one(t, name, ts, txt)
    return race_one(t, "cayley", 50.0, txt)


# ======================================================================= 7. Fermat
@functools.lru_cache(None)
def fermat_fields():
    v = View2D(0, 0, 300)
    out = {}
    for n in range(2, 19):
        f = np.power(v.X, n) + np.power(v.Y, n) - 1
        out[n] = pix_dist(f.astype(np.float32))
    fr = v.Y * v.Y - v.X ** 3 + v.X
    out["frey"] = pix_dist(fr)
    return v, out


def pythag(M=70):
    pts = []
    for m in range(2, M):
        for n in range(1, m):
            if (m - n) % 2 == 1 and np.gcd(m, n) == 1:
                a, b, c = m * m - n * n, 2 * m * n, m * m + n * n
                for sx in (1, -1):
                    for sy in (1, -1):
                        pts.append((sx * a / c, sy * b / c))
                        pts.append((sx * b / c, sy * a / c))
    return np.array(pts)


PYTH = pythag(34)
PYTH_T = 71.5 + np.random.default_rng(3).uniform(0, 1.0, len(PYTH)) ** 1.5


def fermat(t, txt=True):
    img = background(t)
    v, F = fermat_fields()
    dimf = 1 - 0.7 * ss(78.75, 79.4, t)
    c2 = ease_io(ss(71.3, 72.2, t))
    if c2 > 0:
        ang = np.mod(np.arctan2(v.Y, v.X) + np.pi / 2, 2 * np.pi)
        m = np.clip((c2 * 2 * np.pi - ang) / 0.03, 0, 1) if c2 < 1 - 1e-4 else 1.0
        add(img, line_glow(F[2], 1.6, 2.2, 0.35, 8) * m * dimf * (1 - 0.6 * ss(72.0, 72.8, t)), GOLD)
        on = PYTH_T <= t
        if on.any():
            vals = 2.2 + 8 * np.exp(-(t - PYTH_T[on]) / 0.2)
            img += glow_points(v.to_px(PYTH[on]), vals * dimf, (1.0, 0.92, 0.75), sigmas=((1.3, 1.0), (4, 0.4)))
    for i, n in enumerate(range(3, 19)):
        tn = FERMAT_T[i]
        if t < tn:
            break
        a = ss(tn, tn + 0.25, t)
        col = pal(0.25 + 0.75 * i / 15)
        add(img, line_glow(F[n], 1.2, 1.3 + 2.0 * pulse(t, tn, 0.2), 0.25, 6) * a * (0.85 - 0.02 * i) * dimf, col)
    triv = np.array([[1, 0], [0, 1], [-1, 0], [0, -1]], float)
    if t > 72.5:
        img += glow_points(v.to_px(triv), np.full(4, 3.5) * ss(72.5, 73.0, t), WHITE)
    if t > 78.75:
        add(img, line_glow(F["frey"], 1.7, 2.6, 0.4, 9) * ss(78.75, 79.1, t), GOLD, 1 + 1.5 * pulse(t, 78.75, 0.3))
    if txt:
        k = ease_io(ss(71.2, 72.0, t))
        cy = H * 0.47 * (1 - k) + 0.11 * H * k
        sc = (1 + 0.2 * np.exp(-(t - 70) * 7)) * (1 - 0.5 * k)
        formula(img, r"x^n + y^n = z^n", W / 2, cy, 150, ss(69.98, 70.05, t) * (1 - ss(78.6, 78.9, t)), scale=sc,
                glow=0.6 * (1 - k) + 0.2)
        formula(img, r"y^2 = x\,(x - a^n)(x + b^n)", W / 2, 0.11 * H, 62, ss(78.9, 79.3, t), color=(1, 0.88, 0.65))
        zh(img, "弗雷曲线", W / 2, 0.19 * H, 30, ss(79.2, 79.6, t) * 0.8, (1, 0.8, 0.5))
        caption(img, t, 72.6, 75.6, "n = 2 时有无穷多组整数解；n ≥ 3 时，一组也没有",
                "n = 2: INFINITELY MANY SOLUTIONS.   n ≥ 3: NONE AT ALL")
        caption(img, t, 75.95, 78.6, "费马，1637：「我有一个绝妙的证明，可惜空白太小，写不下」",
                "FERMAT, 1637: “THIS MARGIN IS TOO NARROW TO CONTAIN IT”", size=46)
        caption(img, t, 79.0, 82.3, "358 年后，怀尔斯证明了它——钥匙正是椭圆曲线",
                "WILES, 1995 — THE KEY WAS ELLIPTIC CURVES")
    return img


# ======================================================================= 8. Calabi-Yau (Hanson's Fermat quintic slice)
def calabi_geom(t, n=5, res=44):
    eta = 1.25 * ease_out(ss(82.5, 84.8, t), 2) + 1e-3
    xi, et = np.meshgrid(np.linspace(0, np.pi / 2, res), np.linspace(-eta, eta, res), indexing="ij")
    w = xi + 1j * et
    cw, sw = np.cos(w), np.sin(w)
    alpha = 0.55 + 0.11 * (t - 82.5)
    P, Nn, C, UV, I = [], [], [], [], []
    base_i = 0
    uu, vv, idx = grid_mesh(res, res)
    for k1 in range(n):
        for k2 in range(n):
            z1 = np.exp(2j * np.pi * k1 / n) * cw ** (2 / n)
            z2 = np.exp(2j * np.pi * k2 / n) * sw ** (2 / n)
            X = np.stack([z1.real, z2.real, np.cos(alpha) * z1.imag + np.sin(alpha) * z2.imag], -1)
            P.append(X.reshape(-1, 3))
            Nn.append(grid_normals(X).reshape(-1, 3))
            h = (0.58 + 0.42 * k1 / n + 0.05 * k2 / n) % 1.0
            rgb = colorsys.hsv_to_rgb(h, 0.82, 0.62)
            C.append(np.broadcast_to(np.array(rgb), (res * res, 3)))
            UV.append(np.stack([uu, vv], -1).reshape(-1, 2))
            I.append(idx + base_i)
            base_i += res * res
    return np.concatenate(P), np.concatenate(Nn), np.concatenate(C), np.concatenate(UV), np.concatenate(I)


def calabi(t, txt=True):
    img = background(t)
    P, Nn, C, UV, I = calabi_geom(t)
    u = t - 82.5
    cam = Cam.orbit((0, 0, 0.0), 10.4 - 0.9 * ease_io(ss(82.5, 92.5, t)), 0.4 + 0.12 * u, 0.5 + 0.12 * np.sin(0.3 * u),
                    focal=2.0)
    c, a, dep = mesh().render(cam, SW, SH, P, Nn, C, UV, I, gridA=0.16, gridN=6, gridM=6, gloss=0.9, emis=0.04)
    c = downsample(c)
    a = downsample(a)
    img = img * (1 - a[..., None]) + c * (1 + 0.8 * pulse(t, 82.5, 0.4))
    if txt:
        formula(img, r"z_1^5 + z_2^5 = 1", W / 2, 0.1 * H, 62, ss(83.0, 83.5, t))
        caption(img, t, 83.2, 87.2, "卡拉比–丘流形", "CALABI–YAU MANIFOLD", size=64, weight="Bold", stagger=0.08)
        caption(img, t, 87.55, 92.2, "弦理论中，宇宙隐藏的维度，也许就是这样的形状",
                "IN STRING THEORY, THE HIDDEN DIMENSIONS OF THE UNIVERSE MAY LOOK LIKE THIS")
    return img


# ======================================================================= 9. finite fields
@functools.lru_cache(None)
def fp_points(p):
    xs = np.arange(p)
    rhs = (xs ** 3 + 7) % p
    sq = {}
    for y in range(p):
        sq.setdefault(y * y % p, []).append(y)
    pts = [(x, y) for x in xs for y in sq.get(int(rhs[x]), [])]
    return np.array(pts, float)


FF_SIDE, FF_CY = 700, 0.44 * H


def ff_px(pts, p):
    x0 = W / 2 - FF_SIDE / 2
    y0 = FF_CY - FF_SIDE / 2
    return np.stack([x0 + (pts[:, 0] + 0.5) / p * FF_SIDE, y0 + FF_SIDE - (pts[:, 1] + 0.5) / p * FF_SIDE], 1)


@functools.lru_cache(None)
def real_curve_px():
    v = View2D(0.5, 0, 95)
    ys = np.linspace(-5.6, 5.6, 4000)
    xs = np.cbrt(ys * ys - 7)
    return v, v.to_px(np.stack([xs, ys], 1))


def finite(t, txt=True):
    img = background(t)
    v, cpx = real_curve_px()
    ra = 1 - ss(93.75, 94.3, t)
    if ra > 0:
        f = v.Y * v.Y - v.X ** 3 - 7
        add(img, line_glow(pix_dist(f), 1.7, 2.4, 0.4, 9) * ra * ss(92.5, 92.8, t), GOLD)
    fa = ss(93.9, 94.5, t)
    if fa > 0:  # square frame
        x0, y0 = W / 2 - FF_SIDE / 2, FF_CY - FF_SIDE / 2
        frame = np.zeros((H, W), np.float32)
        cv2.rectangle(frame, (int(x0), int(y0)), (int(x0 + FF_SIDE), int(y0 + FF_SIDE)), 1.0, 1, cv2.LINE_AA)
        img += frame[..., None] * np.array([0.35, 0.45, 0.7]) * fa
    for i, (tp, p) in enumerate(PRIMES_T):
        tnext = PRIMES_T[i + 1][0] if i + 1 < len(PRIMES_T) else 1e9
        if t < tp - 0.01 or t > tnext + 0.4:
            continue
        pts = fp_points(p)
        n = len(pts)
        tgt = ff_px(pts, p)
        rng = np.random.default_rng(p)
        delay = rng.uniform(0, 0.45, n)
        out = 1 - ss(tnext, tnext + 0.35, t)
        if i == 0:  # fly from the real curve
            src = cpx[rng.integers(0, len(cpx), n)]
            k = ease_io(np.clip((t - 93.75 - delay * 0.5) / 0.8, 0, 1))[:, None]
            pos = src * (1 - k) + tgt * k
            a = np.ones(n) * out
        else:
            pos = tgt
            a = ss(0, 0.15, t - tp - delay) * out
        fl = np.exp(-np.clip(t - tp - delay, 0, None) / 0.18) * (t - tp - delay > 0)
        sc = max(1.0, 14.0 / np.sqrt(p))
        vals = a * (1.5 + 4 * fl) * (1 + 0.2 * np.sin(5 * t + np.arange(n)))
        col = np.array([0.55, 0.85, 1.0]) if p < 1000 else np.array([0.7, 0.9, 1.0])
        img += glow_points(pos, vals * sc * 0.8, col, sigmas=((0.9 * sc, 1.0), (3 * sc, 0.4), (10, 0.12)))
        if p <= 61:  # lattice
            ga = (0.18 if p <= 13 else 0.1 if p <= 31 else 0.05) * a.mean() * fa
            grid = np.zeros((H, W), np.float32)
            x0, y0 = W / 2 - FF_SIDE / 2, FF_CY - FF_SIDE / 2
            for j in range(1, p):
                q = int(round(x0 + j / p * FF_SIDE))
                grid[int(y0):int(y0 + FF_SIDE), q] += 1
                q = int(round(y0 + j / p * FF_SIDE))
                grid[q, int(x0):int(x0 + FF_SIDE)] += 1
            img += grid[..., None] * np.array([0.4, 0.5, 0.9]) * ga
        if txt:
            lo = ss(tp, tp + 0.2, t) * (1 - ss(tnext - 0.12, tnext, t)) * fa
            if lo > 0.003:
                paste(img, math_img(r"p = %d" % p, 64), W / 2 - FF_SIDE / 2 - 50, FF_CY, (0.8, 0.9, 1.0), opacity=lo,
                      anchor="r", glow=0.2 + pulse(t, tp, 0.2), scrim=0.5)
    # symmetry axis y = p/2
    if fa > 0:
        yy = FF_CY
        dsh = (np.sin(np.arange(W) / 5.0) > 0).astype(np.float32)
        x0 = int(W / 2 - FF_SIDE / 2)
        img[int(yy), x0:x0 + FF_SIDE] += (dsh[x0:x0 + FF_SIDE, None] * np.array([0.3, 0.3, 0.5]) * 0.4 * fa)
    if txt:
        formula(img, r"y^2 = x^3 + 7", W / 2, 0.1 * H if t > 93.75 else 0.12 * H, 62, ss(92.6, 93.0, t) * (1 - ss(93.6, 93.75, t)))
        formula(img, r"y^2 \equiv x^3 + 7 \quad (\mathrm{mod}\ p)", W / 2, 0.06 * H, 50, ss(93.8, 94.2, t))
        if t > 98.0:
            paste(img, math_img(r"p = 2^{256} - 2^{32} - 977", 40), W / 2 + FF_SIDE / 2 + 40, FF_CY, (1.0, 0.85, 0.6),
                  opacity=ss(98.0, 98.6, t), anchor="l", glow=0.15)
            label(img, "secp256k1", W / 2 + FF_SIDE / 2 + 44, FF_CY + 56, 38, ss(98.3, 98.9, t) * 0.85,
                  (0.75, 0.8, 1.0), italic=True, anchor="l")
        caption(img, t, 94.0, 97.4, "在有限域上，曲线碎成了星尘", "OVER A FINITE FIELD, THE CURVE SHATTERS INTO STARDUST")
        caption(img, t, 97.7, 102.2, "比特币的每一笔签名，都建立在这条曲线上", "EVERY BITCOIN SIGNATURE IS BUILT ON THIS VERY CURVE")
    return img


# ======================================================================= 10. Spec Z[x]
FX = [0.085 * W + i * (0.76 * W / (len(SCHEME_PRIMES) - 1)) for i in range(len(SCHEME_PRIMES))]
GEN_X = 0.935 * W
FY0, FY1 = 0.2 * H, 0.72 * H
FMID, FH = (FY0 + FY1) / 2, FY1 - FY0


def centered(r, p):
    return r if r <= p / 2 else r - p


def sqrt2_roots(p):
    return [r for r in range(p) if (r * r - 2) % p == 0]


@functools.lru_cache(None)
def strands():
    up, lo, kinds = [], [], []
    for p in SCHEME_PRIMES:
        rs = sqrt2_roots(p)
        if len(rs) == 2:
            c = abs(centered(rs[0], p))
            up.append(FMID - c / p * FH)
            lo.append(FMID + c / p * FH)
            kinds.append("split")
        else:
            up.append(FMID)
            lo.append(FMID)
            kinds.append("ram" if p == 2 else "inert")
    xs = np.array(FX + [GEN_X])
    su = CubicSpline(xs, up + [FMID - 0.18 * FH], bc_type="natural")
    sl = CubicSpline(xs, lo + [FMID + 0.18 * FH], bc_type="natural")
    return su, sl, kinds


def scheme(t, txt=True):
    img = background(t)
    X = np.arange(W, dtype=np.float32)
    Yg = np.arange(H, dtype=np.float32)[:, None]
    lay = np.zeros((H, W), np.float32)
    dots, dv = [], []
    for i, p in enumerate(SCHEME_PRIMES):
        tf = FIBRE_T[i]
        if t < tf:
            continue
        g = ease_out(ss(tf, tf + 0.35, t))
        x = FX[i]
        half = FH / 2 * g
        seg = (np.abs(Yg - FMID) <= half).astype(np.float32)
        colm = np.exp(-((X - x) / 1.0) ** 2)
        lay += seg * colm[None, :] * 0.5
        for r in range(p):
            y = FMID - centered(r, p) / p * FH
            if abs(y - FMID) <= half:
                dots.append((x, y))
                dv.append(1.0 + 2.5 * pulse(t, tf, 0.2))
    img += lay[..., None] * np.array([0.45, 0.6, 1.0])
    if dots:
        sc = 1.0
        img += glow_points(np.array(dots), np.array(dv) * 0.9, (0.7, 0.85, 1.0), sigmas=((1.0, 1.0), (3, 0.4)))
    # generic fibre: a haze
    ga = ss(105.0, 105.8, t)
    if ga > 0:
        haze = np.exp(-((X - GEN_X) / 10) ** 2)[None, :] * np.exp(-((Yg - FMID) / (FH * 0.45)) ** 4)
        img += (haze * 0.25 * ga)[..., None] * np.array([0.6, 0.5, 1.0])
    # the curve Spec Z[sqrt 2] drawn left -> right
    su, sl, kinds = strands()
    xr = 0.05 * W + (GEN_X - 0.05 * W) * ease_io(ss(104.6, 106.8, t))
    if xr > 0.05 * W + 1:
        xs = np.linspace(FX[0] - 30, min(xr, GEN_X), 1500)
        for s in (su, sl):
            ys = s(xs)
            pts = np.stack([xs, ys], 1)
            img += glow_points(pts, np.full(len(pts), 0.9), GOLD, sigmas=((1.1, 1.0), (4, 0.4), (12, 0.15)))
        for i, p in enumerate(SCHEME_PRIMES):
            if FX[i] > xr:
                break
            if kinds[i] == "split":
                img += glow_points(np.array([[FX[i], su(FX[i])], [FX[i], sl(FX[i])]]), np.full(2, 5.0), (1, 0.85, 0.5))
            else:
                img += glow_points(np.array([[FX[i], FMID]]), np.array([9.0]), (1, 0.8, 0.45))
    # the rising sea
    sa = ss(109.7, 112.5, t)
    if sa > 0:
        lvl = H * (1.03 - 0.8 * ease_io(sa))
        wave = lvl + 14 * np.sin(X / 95 + 2.2 * t) + 7 * np.sin(X / 37 - 3.1 * t)
        dy = Yg - wave[None, :]
        crest = np.exp(-(dy / 2.2) ** 2) * 1.6 + np.exp(-np.abs(dy) / 18) * 0.25
        body = np.clip(dy / 300, 0, 1) ** 0.5 * (dy > 0) * (1 - 0.5 * np.clip(dy / 700, 0, 1))
        shimmer = (np.sin(X / 23 + 1.7 * t + np.sin(Yg / 31) * 2) * np.sin(X / 57 - t + Yg / 45)) ** 8 * (dy > 8)
        img += crest[..., None] * np.array([0.6, 0.85, 1.0])
        img += body[..., None] * np.array([0.006, 0.022, 0.05])
        img += (shimmer * 0.08 * np.exp(-np.clip(dy, 0, None) / 250))[..., None] * np.array([0.5, 0.8, 1.0])
        img *= 1 + 0.5 * (dy > 0)[..., None]
    if txt:
        formula(img, r"\mathrm{Spec}\ \mathbb{Z}[x]", W / 2, 0.09 * H, 58, ss(102.6, 103.2, t))
        for i, p in enumerate(SCHEME_PRIMES):
            if t >= FIBRE_T[i]:
                zh(img, str(p), FX[i], 0.775 * H, 26, ss(FIBRE_T[i], FIBRE_T[i] + 0.3, t) * 0.85, (0.8, 0.85, 1.0))
        formula(img, r"(0)", GEN_X, 0.775 * H, 32, ga * 0.85, (0.8, 0.75, 1.0))
        formula(img, r"x^2 = 2", FX[-1] + 30, su(FX[-1]) - 36, 36, ss(106.2, 106.8, t), (1, 0.85, 0.55), glow=0.1)
        caption(img, t, 102.8, 106.3, "格罗滕迪克：把数，也看成空间", "GROTHENDIECK: NUMBERS, TOO, ARE SPACES")
        caption(img, t, 106.65, 109.6, "每一个素数，都是这个空间里的一条「纤维」", "EVERY PRIME IS A FIBRE OF THIS SPACE")
        caption(img, t, 109.9, 112.4, "「海水无声上涨，坚硬的果壳终会自己裂开」", "“THE RISING SEA” — ALEXANDER GROTHENDIECK")
    return img


# ======================================================================= 11. finale
SHOTS = [("clebsch", 47.0), ("cubic", 14.0), ("calabi", 90.0), ("race", 63.2), ("finite", 101.9), ("torus", 33.5),
         ("race", 58.2), ("fermat", 75.2), ("scheme", 108.0), ("race", 68.3), ("conics", 11.6), ("clebsch", 44.6)]
_rng2 = np.random.default_rng(8)
FIN_P = _rng2.uniform(0, 2 * np.pi, 500)
FIN_R = _rng2.uniform(1.4, 3.2, 500)
FIN_D = _rng2.uniform(0, 0.8, 500)


def finale(t, txt=True):
    if t < 117.5:
        k = int(np.searchsorted(MONTAGE_T, t, side="right") - 1)
        k = max(0, min(k, len(SHOTS) - 1))
        name, ts = SHOTS[k]
        img = SCENE_FN[name](ts + (t - MONTAGE_T[k]) * 0.6, txt=False)
        dt = t - MONTAGE_T[k]
        s = 1.06 - 0.06 * ease_out(dt / 0.6)
        M = np.array([[s, 0, (1 - s) * W / 2], [0, s, (1 - s) * H / 2]], np.float32)
        img = cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        img = img + ss(116.6, 117.5, t) ** 2 * 3.0
        return img
    img = background(t, star_amt=0.8)
    v = View2D(0, 0, 380)
    cy = 0.46 * H
    v = View2D(0, (cy - H / 2) / 380, 380)
    prog = ease_io(ss(117.5, 118.5, t)) * 2 * np.pi
    r = np.hypot(v.X, v.Y)
    d = np.abs(r - 1) * v.s
    ang = np.mod(np.arctan2(v.Y, v.X) - np.pi / 2, 2 * np.pi)
    m = np.clip((prog - ang) / 0.02, 0, 1) if prog < 2 * np.pi - 1e-3 else 1.0
    add(img, line_glow(d, 1.6, 2.2, 0.3, 10) * m * (1 + 0.1 * np.sin(2 * t)), GOLD)
    # particles spiralling into the circle
    u = np.clip((t - 117.5 - FIN_D) / 2.2, 0, 1)
    rr = FIN_R * (1 - ease_out(u)) + 1.0 * ease_out(u)
    ph = FIN_P + 2.5 * ease_out(u)
    a = (u > 0) * (1 - ss(0.85, 1.0, u)) * (1 - ss(126, 128.5, t))
    pts = v.to_px(np.stack([rr * np.cos(ph), rr * np.sin(ph)], 1))
    img += glow_points(pts, a * 1.6, (1.0, 0.85, 0.6), sigmas=((1.0, 1.0), (4, 0.3)))
    if txt:
        k = ss(118.0, 119.2, t)
        paste(img, text_img("代数几何", 130, "Bold", tracking=0.22), W / 2, cy - 20, (1, 0.97, 0.92), opacity=k,
              blur=(1 - k) * 10, glow=0.35)
        k2 = ss(118.8, 119.8, t)
        label(img, "ALGEBRAIC GEOMETRY", W / 2, cy + 95, 30, k2 * 0.9, (0.8, 0.85, 1.0), tracking=0.45 - 0.1 * k2)
        caption(img, t, 120.6, 124.2, "方程与形状之间，藏着一整个宇宙", "BETWEEN EQUATIONS AND SHAPES LIES A WHOLE UNIVERSE", y=0.9)
        caption(img, t, 124.6, 128.4, "而这，只是开始。", "AND THIS IS ONLY THE BEGINNING.", y=0.9)
    return img


SCENE_FN = dict(intro=intro, conics=conics, cubic=cubic, torus=torus, clebsch=clebsch, race=race, fermat=fermat,
                calabi=calabi, finite=finite, scheme=scheme, finale=finale)


def render_frame(t, txt=True):
    name, a, b = scene_at(t)
    img = SCENE_FN[name](t, txt)
    flash, shake, ab, zoom = fx(t)
    bloom_amt = 0.28 if name in ("clebsch", "race", "calabi", "torus") else 0.4
    fade = ss(0.0, 0.4, t) * (1 - ss(128.6, 130.0, t))
    return post(img, flash=flash, shake=shake, aberr=ab, zoom=zoom, bloom_amt=bloom_amt, fade=fade)
