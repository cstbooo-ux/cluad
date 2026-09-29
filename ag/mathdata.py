"""Precompute the exact geometry the video shows: the 27 lines on the Clebsch
cubic and the singular points (nodes) of each surface in the singularity race.
Writes data.json next to this file."""
import json, os, itertools
import numpy as np
import sympy as sp
from scipy.optimize import root

D = os.path.dirname(os.path.abspath(__file__))
x, y, z = sp.symbols("x y z", real=True)
phi = (1 + sp.sqrt(5)) / 2

# ---- Clebsch diagonal cubic: sum x_i = 0, sum x_i^3 = 0 in P^4, affine chart x3 - x4 = 1
C0 = np.array([0, 0, 0, 0.5, -0.5])
E = np.array([[1, -1, 0, 0, 0], [1, 1, -2, 0, 0], [1, 1, 1, -1.5, -1.5]], float)
E /= np.linalg.norm(E, axis=1)[:, None]
X5 = [sp.Rational(0)] * 5
for i in range(5):
    X5[i] = sp.nsimplify(C0[i]) + x * sp.nsimplify(E[0, i], [sp.sqrt(2), sp.sqrt(6), sp.sqrt(30)]) \
        + y * sp.nsimplify(E[1, i], [sp.sqrt(2), sp.sqrt(6), sp.sqrt(30)]) \
        + z * sp.nsimplify(E[2, i], [sp.sqrt(2), sp.sqrt(6), sp.sqrt(30)])
clebsch = sp.expand(sum(v ** 3 for v in X5))

SURF = {
    "clebsch": clebsch,
    "cayley": 4 * (x**2 + y**2 + z**2) + 16 * x * y * z - 1,
    "kummer": None,
    "barth6": 4 * (phi**2 * x**2 - y**2) * (phi**2 * y**2 - z**2) * (phi**2 * z**2 - x**2)
              - (1 + 2 * phi) * (x**2 + y**2 + z**2 - 1) ** 2,
    "barth10": 8 * (x**2 - phi**4 * y**2) * (y**2 - phi**4 * z**2) * (z**2 - phi**4 * x**2)
               * (x**4 + y**4 + z**4 - 2 * x**2 * y**2 - 2 * x**2 * z**2 - 2 * y**2 * z**2)
               + (3 + 5 * phi) * (x**2 + y**2 + z**2 - 1) ** 2 * (x**2 + y**2 + z**2 - (2 - phi)) ** 2,
}
mu2 = sp.Rational(13, 10)
lam = (3 * mu2 - 1) / (3 - mu2)
s2 = sp.sqrt(2)
p, q, r, s = 1 - z - s2 * x, 1 - z + s2 * x, 1 + z + s2 * y, 1 + z - s2 * y
SURF["kummer"] = (x**2 + y**2 + z**2 - mu2) ** 2 - lam * p * q * r * s

CLIP = {"clebsch": 2.6, "cayley": 1.9, "kummer": 2.4, "barth6": 1.9, "barth10": 2.0}


def nodes(name, n_starts=200000, seed=5):
    F = SURF[name]
    g = [sp.diff(F, v) for v in (x, y, z)]
    Hm = [[sp.diff(gi, v) for v in (x, y, z)] for gi in g]
    fF = sp.lambdify((x, y, z), F, "numpy")
    fg = sp.lambdify((x, y, z), g, "numpy")
    fH = sp.lambdify((x, y, z), Hm, "numpy")
    R = CLIP[name]
    rng = np.random.default_rng(seed)
    P = rng.uniform(-R, R, (n_starts, 3))
    P = P[np.linalg.norm(P, axis=1) < R]
    # vectorised Newton on grad F = 0
    for _ in range(60):
        G = np.array([np.broadcast_to(v, len(P)) for v in fg(*P.T)], float).T
        Hs = np.array([[np.broadcast_to(v, len(P)) for v in row] for row in fH(*P.T)], float)
        Hs = np.moveaxis(Hs, 2, 0)
        try:
            step = np.linalg.solve(Hs + 1e-12 * np.eye(3), G[..., None])[..., 0]
        except np.linalg.LinAlgError:
            step = np.zeros_like(P)
        step = np.clip(step, -0.3, 0.3)
        P = P - step
        P = P[np.all(np.isfinite(P), axis=1)]
    G = np.array([np.broadcast_to(v, len(P)) for v in fg(*P.T)], float).T
    ok = (np.linalg.norm(G, axis=1) < 1e-9) & (np.abs(fF(*P.T)) < 1e-9) & (np.linalg.norm(P, axis=1) < R)
    P = P[ok]
    out = []
    for v in P:
        if all(np.linalg.norm(v - w) > 1e-6 for w in out):
            out.append(v)
    return np.array(out)


def clebsch_lines():
    """27 lines as (point, unit direction) found by Newton in random charts."""
    fF = sp.lambdify((x, y, z), SURF["clebsch"], "numpy")
    rng = np.random.default_rng(3)
    found = []
    for trial in range(6):
        Q, _ = np.linalg.qr(rng.normal(size=(3, 3)))
        a, b, c, d, t = sp.symbols("a b c d t")
        pt = sp.Matrix(Q) * sp.Matrix([a * t + b, c * t + d, t])
        poly = sp.Poly(sp.expand(SURF["clebsch"].subs({x: pt[0], y: pt[1], z: pt[2]})), t)
        co = poly.all_coeffs()
        co = [0] * (4 - len(co)) + co
        fco = sp.lambdify((a, b, c, d), co, "numpy")
        J = sp.lambdify((a, b, c, d), sp.Matrix(co).jacobian([a, b, c, d]), "numpy")
        for _ in range(3000):
            v = rng.normal(size=4) * rng.choice([0.3, 1, 3])
            sol = root(lambda u: np.array(fco(*u), float), v, jac=lambda u: np.array(J(*u), float), method="hybr")
            if not sol.success or np.max(np.abs(fco(*sol.x))) > 1e-10:
                continue
            A, B, Cc, Dd = sol.x
            p0 = Q @ np.array([B, Dd, 0.0])
            dv = Q @ np.array([A, Cc, 1.0])
            dv /= np.linalg.norm(dv)
            p0 = p0 - dv * np.dot(p0, dv)  # closest point to origin
            if any(np.linalg.norm(p0 - p1) < 1e-6 and abs(abs(np.dot(dv, d1)) - 1) < 1e-9 for p1, d1 in found):
                continue
            # sanity: whole line lies on the surface
            ts = np.linspace(-5, 5, 11)
            assert np.max(np.abs(fF(*(p0[:, None] + dv[:, None] * ts)))) < 1e-7
            found.append((p0, dv))
        if len(found) >= 27:
            break
    return found


if __name__ == "__main__":
    out = {"nodes": {}, "lines": []}
    for name in ["cayley", "kummer", "barth6", "barth10"]:
        N = nodes(name)
        print(name, "real nodes inside clip ball:", len(N), "max |p|:", np.linalg.norm(N, axis=1).max())
        out["nodes"][name] = N.tolist()
    L = clebsch_lines()
    print("clebsch lines:", len(L), "min dist to origin:", min(np.linalg.norm(p0) for p0, _ in L),
          "max:", max(np.linalg.norm(p0) for p0, _ in L))
    out["lines"] = [[p0.tolist(), dv.tolist()] for p0, dv in L]
    out["clebsch_poly"] = str(SURF["clebsch"])
    json.dump(out, open(os.path.join(D, "data.json"), "w"))
