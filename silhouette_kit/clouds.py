"""High-quality cumulus sprites.

Offline: `generate()` builds a small library of cloud sprites. Each sprite is a 2-D density field made of
hierarchical puffs (big domes -> smaller billows -> tiny bumps = cauliflower cumulus), eroded at the edges with
fractal noise, with a lumpy, softly dissolving underside. Lighting is computed by marching toward the sun through
the density (Beer-Lambert transmittance) plus a powder term, an ambient term that darkens toward the base, and
forward-scatter at thin edges (silver lining). Sprites store luminance + alpha only (8-bit LA PNG).

At render time `draw(ctx, x, base_y, width, tones, idx)` colourises a sprite with the scene palette
(shadow, body, lit, highlight) and draws it with its flat base on `base_y`. Coloured sprites are cached per process.
"""
import math, os, random
from collections import OrderedDict
import numpy as np
import cairo

D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "clouds")
SW, SH = 1280, 760          # sprite size
BASE = 640                  # base line inside the sprite
KINDS = ["cumulus"] * 8 + ["tower"] * 4 + ["flat"] * 4


# ------------------------------------------------------------------ generation (numpy only)
def _value_noise(shape, cell, rng):
    gy, gx = shape[0] // cell + 3, shape[1] // cell + 3
    g = rng.random((gy, gx)).astype(np.float32)
    y = np.arange(shape[0], dtype=np.float32) / cell
    x = np.arange(shape[1], dtype=np.float32) / cell
    y0, x0 = y.astype(int), x.astype(int)
    fy, fx = y - y0, x - x0
    fy = fy * fy * (3 - 2 * fy); fx = fx * fx * (3 - 2 * fx)
    a = g[y0][:, x0]; b = g[y0][:, x0 + 1]; c = g[y0 + 1][:, x0]; d = g[y0 + 1][:, x0 + 1]
    return (a * (1 - fx) + b * fx) * (1 - fy)[:, None] + (c * (1 - fx) + d * fx) * fy[:, None]


def fbm(shape, rng, base_cell=160, octaves=5, billow=False):
    out = np.zeros(shape, np.float32)
    amp, tot, cell = 1.0, 0.0, base_cell
    for _ in range(octaves):
        n = _value_noise(shape, max(2, int(cell)), rng)
        if billow:
            n = np.abs(n * 2 - 1)
        out += n * amp
        tot += amp
        amp *= 0.5
        cell /= 2
    return out / tot


def _puffs(kind, rng):
    """Hierarchical 3-D sphere list (cx, cy, cz, r): big domes, billows sitting on their surface, small bumps on
    those (cauliflower cumulus). cz is depth toward the viewer, so child billows really sit on the parent surface."""
    P = []
    x0, x1 = 200, SW - 200
    if kind == "flat":
        x0, x1 = 110, SW - 110
    n = rng.randint(5, 7) if kind != "flat" else rng.randint(8, 11)
    for i in range(n):
        t = i / (n - 1)
        dome = math.sin(math.pi * t) ** 0.7
        if kind == "flat":
            r = math.exp(rng.uniform(math.log(50), math.log(95))) * (0.6 + 0.5 * dome)
            cy = BASE - r * 0.3 - dome * r * 0.2
        else:
            r = math.exp(rng.uniform(math.log(90), math.log(160))) * (0.55 + 0.6 * dome)
            cy = BASE - r * 0.3 - dome * r * 0.45
        P.append((x0 + (x1 - x0) * t + rng.uniform(-40, 40), cy, rng.uniform(-40, 40), r))
    if kind == "tower":
        cx = rng.uniform(0.42, 0.58) * SW
        y, r = BASE - 240, 150
        while y > 150:
            P.append((cx + rng.uniform(-55, 55), y, rng.uniform(-20, 30), r))
            y -= r * rng.uniform(0.6, 0.8)
            r *= rng.uniform(0.8, 0.92)
    gens = ((9, (0.3, 0.55), 0.45), (6, (0.3, 0.5), 0.45), (4, (0.3, 0.45), 0.4))
    level = P
    for g, (k, rs, dd) in enumerate(gens):
        new = []
        for cx, cy, cz, r in level:
            for _ in range(rng.randint(k // 2 + 1, k)):
                down = rng.random() < 0.28
                a = rng.uniform(0.35, math.pi - 0.35) if down else rng.uniform(-math.pi * 1.12, 0.3)
                phi = rng.uniform(0.45 if g == 0 else 0.75, 1.5)    # angle away from the view axis
                rr = r * math.exp(rng.uniform(math.log(rs[0]), math.log(rs[1]))) * (0.8 if down else 1.0)
                d = r - rr * (1 - dd)                               # child pokes out of the parent surface
                new.append((cx + math.cos(a) * math.sin(phi) * d, cy + math.sin(a) * math.sin(phi) * d,
                            cz + math.cos(phi) * d, rr))
        P += new
        level = new
    return P


def _render_fields(kind, seed):
    """Height (toward viewer), thickness and analytic normals of the sphere union, with an irregular, soft underside."""
    from scipy import ndimage
    rng = random.Random(seed)
    nr = np.random.default_rng(seed)
    H = np.full((SH, SW), -1e4, np.float32)
    T = np.zeros((SH, SW), np.float32)
    NX = np.zeros((SH, SW), np.float32); NY = np.zeros_like(NX); NZ = np.ones_like(NX)
    for cx, cy, cz, r in _puffs(kind, rng):
        x0, x1 = int(max(0, cx - r - 1)), int(min(SW, cx + r + 2))
        y0, y1 = int(max(0, cy - r - 1)), int(min(SH, cy + r + 2))
        if x1 <= x0 or y1 <= y0:
            continue
        yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        q = r * r - (xx - cx) ** 2 - (yy - cy) ** 2
        inside = q > 0
        h = np.sqrt(np.clip(q, 0, None))
        z = np.where(inside, cz + h, -1e4)
        win = z > H[y0:y1, x0:x1]
        H[y0:y1, x0:x1] = np.where(win, z, H[y0:y1, x0:x1])
        NX[y0:y1, x0:x1] = np.where(win, (xx - cx) / r, NX[y0:y1, x0:x1])
        NY[y0:y1, x0:x1] = np.where(win, (yy - cy) / r, NY[y0:y1, x0:x1])
        NZ[y0:y1, x0:x1] = np.where(win, h / r, NZ[y0:y1, x0:x1])
        T[y0:y1, x0:x1] = np.maximum(T[y0:y1, x0:x1], 2 * h)
    # gentle domain warp -> the outline is turbulent, not a stack of perfect circles
    wx = (fbm((SH, SW), nr, 60, 3) - 0.5) * 22
    wy = (fbm((SH, SW), nr, 60, 3) - 0.5) * 18
    yy, xx = np.mgrid[0:SH, 0:SW].astype(np.float32)
    coords = [yy + wy, xx + wx]
    inside = (H > -1e3).astype(np.float32)
    H = np.where(H > -1e3, H, 0)
    warp = lambda f, o=1: ndimage.map_coordinates(f, coords, order=o, mode="constant")
    H, T, inside = warp(H), warp(T), warp(inside)
    NX, NY, NZ = warp(NX), warp(NY), warp(NZ)
    # fine billow bumps perturb the normals (small-scale cauliflower texture)
    bump = fbm((SH, SW), nr, 34, 3, billow=True)
    gy, gx = np.gradient(ndimage.gaussian_filter(bump, 1.0) * 28)
    NX, NY = NX - gx * 0.15, NY - gy * 0.15
    NX, NY, NZ = [ndimage.gaussian_filter(v, 3.0) for v in (NX, NY, NZ)]
    nl = np.sqrt(NX * NX + NY * NY + NZ * NZ) + 1e-6
    NX, NY, NZ = NX / nl, NY / nl, NZ / nl
    # thickness -> density; ragged fbm erosion eats the thinnest edges
    ero = fbm((SH, SW), nr, 40, 4)
    T = np.clip(T * inside - 22 * (ero - 0.35), 0, None)
    # irregular underside: a lumpy, uneven lower edge that dissolves softly (no ruler-flat base)
    rag = (fbm((1, SW), nr, 170, 2)[0] - 0.5) * 150 + (fbm((1, SW), nr, 45, 3)[0] - 0.5) * 50 + 30
    wisp = fbm((SH, SW), nr, 30, 3)
    cut = np.clip((BASE + rag[None, :] - yy) / 45.0 + (wisp - 0.5) * 0.8, 0, 1)
    T *= cut
    return H, T, (NX, NY, NZ), ero


def _shift(a, dx, dy):
    out = np.zeros_like(a)
    h, w = a.shape
    xs0, xs1 = max(0, dx), min(w, w + dx)
    ys0, ys1 = max(0, dy), min(h, h + dy)
    out[ys0:ys1, xs0:xs1] = a[ys0 - dy:ys1 - dy, xs0 - dx:xs1 - dx]
    return out


def _light(H, T, N, ero, sun=(0.62, -0.62, 0.48)):
    """Sunlit cumulus: per-billow lambert (analytic sphere normals), billows shadowing each other (height-field
    march toward the sun), volumetric attenuation through the mass, crevice occlusion, dark flat base, bright
    translucent silver edges on the sun side."""
    from scipy import ndimage
    NX, NY, NZ = N
    sl = math.sqrt(sum(v * v for v in sun))
    sx, sy, sz = [v / sl for v in sun]
    lam = NX * sx + NY * sy + NZ * sz
    lam = np.clip((lam + 0.5) / 1.5, 0, 1) ** 1.3
    # height-field shadows (billow on billow)
    sxy = math.hypot(sx, sy)
    dx, dy, rise = sx / sxy, sy / sxy, sz / sxy
    occ = np.zeros_like(H)
    vol = np.zeros_like(H)
    Tb = ndimage.gaussian_filter(T, 3)
    for k in range(1, 61):
        d = k * 5
        Hs = _shift(H, int(round(-dx * d)), int(round(-dy * d)))
        occ += np.clip((Hs - (H + d * rise)) / 45.0, 0, 1) * (1.0 / (1 + k * 0.05))
        vol += _shift(Tb, int(round(-dx * d)), int(round(-dy * d))) * 5
    hshadow = np.exp(-occ * 0.45)
    vshadow = np.exp(-vol * 0.0000085)
    shadow = ndimage.gaussian_filter(hshadow, 4.5) * (0.35 + 0.65 * ndimage.gaussian_filter(vshadow, 4))
    # crevice occlusion
    ao = ndimage.gaussian_filter(np.clip(1 - (ndimage.gaussian_filter(H, 18) - H) / 90.0, 0.45, 1), 3)
    yy = np.arange(SH, dtype=np.float32)[:, None]
    height = np.clip((BASE - yy) / 420.0, 0, 1)
    basedark = 0.55 + 0.45 * np.clip((BASE - yy) / 150.0, 0, 1) ** 0.8
    sky = 0.12 + 0.16 * height + 0.12 * np.clip(-NY, 0, 1)             # sky light from above
    thin = np.exp(-T / 45.0)
    edge_sun = np.clip(NX * sx + NY * sy, 0, 1)
    L = (sky * ao + 1.05 * lam * shadow) * basedark + 0.5 * thin * (0.3 + edge_sun) * shadow
    L = L * (0.94 + 0.12 * ero)
    L = 0.45 * L + 0.55 * ndimage.gaussian_filter(L * (T > 1), 12) / np.maximum(ndimage.gaussian_filter((T > 1) * 1.0, 12), 1e-3)
    inside = T > 8
    lo, hi = np.percentile(L[inside], 0.5), np.percentile(L[inside], 99.7)
    return np.clip((L - lo) / (hi - lo), 0, 1)


def _largest_parts(A, keep=0.08):
    from scipy import ndimage
    lab, n = ndimage.label(A > 0.12)
    if n <= 1:
        return A
    sizes = ndimage.sum(np.ones_like(A), lab, range(1, n + 1))
    good = np.isin(lab, [i + 1 for i, sz in enumerate(sizes) if sz >= keep * sizes.max()])
    mask = ndimage.gaussian_filter(ndimage.binary_dilation(good, iterations=6).astype(np.float32), 3)
    return A * np.clip(mask, 0, 1)


def _alpha(T, seed):
    from scipy import ndimage
    nr = np.random.default_rng(seed + 7)
    A = 1 - np.exp(-T / 20.0)
    A = ndimage.gaussian_filter(A, 1.6)
    fuzz = fbm((SH, SW), nr, 12, 2)
    A = np.clip(A - 1.2 * (0.55 - fuzz) * A * (1 - A), 0, 1)          # wispy fringe, solid core
    return _largest_parts(A)


def generate(n=len(KINDS)):
    os.makedirs(D, exist_ok=True)
    from PIL import Image
    for i in range(n):
        kind = KINDS[i % len(KINDS)]
        H, T, N, ero = _render_fields(kind, 1000 + i * 17)
        L = _light(H, T, N, ero)
        A = _alpha(T, 1000 + i * 17)
        img = np.stack([(L * 255).astype(np.uint8), (A * 255).astype(np.uint8)], -1)
        Image.fromarray(img, "LA").save(os.path.join(D, f"cloud_{i:02d}_{kind}.png"), optimize=True)
        print("cloud", i, kind)


# ------------------------------------------------------------------ runtime
_RAW = {}
_COL = OrderedDict()


def _hx(c):
    if isinstance(c, str):
        c = c.lstrip("#")
        return tuple(int(c[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return tuple(c)[:3]


def _raw(idx):
    if idx not in _RAW:
        from PIL import Image
        files = _files()
        im = np.asarray(Image.open(os.path.join(D, files[idx % len(files)])).convert("LA")).astype(np.float32) / 255
        _RAW[idx] = (im[..., 0], im[..., 1], files[idx % len(files)])
    return _RAW[idx]


def count():
    return len([f for f in os.listdir(D) if f.endswith(".png")])


_FILES = []


def _files():
    if not _FILES:
        _FILES.extend(sorted(f for f in os.listdir(D) if f.endswith(".png")))
    return _FILES


def pick(seed, tower=0.5):
    """Sprite index for a seed; high `tower` prefers towering cumulus."""
    files = _files()
    rnd = random.Random(seed)
    if tower > 0.7:
        pool = [i for i, f in enumerate(files) if "tower" in f]
    elif tower < 0.25:
        pool = [i for i, f in enumerate(files) if "flat" in f]
    else:
        pool = [i for i, f in enumerate(files) if "cumulus" in f]
    return rnd.choice(pool or list(range(len(files))))


def _surface(idx, tones):
    key = (idx, tuple(tuple(round(v * 40) for v in _hx(c)) for c in tones))
    s = _COL.get(key)
    if s is not None:
        _COL.move_to_end(key)
        return s
    L, Al, _ = _raw(idx)
    sh, bo, li, hi = [np.array(_hx(c), np.float32) for c in tones]
    # piecewise gradient shadow(0) -> body(0.42) -> lit(0.78) -> highlight(1)
    t = L[..., None]
    c = np.where(t < 0.42, sh + (bo - sh) * (t / 0.42),
                 np.where(t < 0.78, bo + (li - bo) * ((t - 0.42) / 0.36), li + (hi - li) * ((t - 0.78) / 0.22)))
    c = np.clip(c, 0, 1)
    a = Al[..., None]
    bgra = np.empty((SH, SW, 4), np.uint8)
    bgra[..., 0] = (c[..., 2] * a[..., 0] * 255).astype(np.uint8)
    bgra[..., 1] = (c[..., 1] * a[..., 0] * 255).astype(np.uint8)
    bgra[..., 2] = (c[..., 0] * a[..., 0] * 255).astype(np.uint8)
    bgra[..., 3] = (a[..., 0] * 255).astype(np.uint8)
    surf = cairo.ImageSurface.create_for_data(bytearray(bgra.tobytes()), cairo.FORMAT_ARGB32, SW, SH, SW * 4)
    _COL[key] = surf
    while len(_COL) > 110:                    # ~4 MB each
        _COL.popitem(last=False)
    return surf


def draw(ctx, x, base_y, width, tones, idx, a=1.0, flip=False, stretch=1.0):
    """Draw sprite `idx`, centred on x, base on base_y, `width` px wide (content ~ 80% of the sprite).
    `stretch` scales the height (variety from a small library: < 1 flatter, > 1 taller)."""
    surf = _surface(idx, tones)
    s = width / (SW * 0.8)
    ctx.save()
    ctx.translate(x, base_y)
    ctx.scale(-s if flip else s, s * stretch)
    ctx.translate(-SW / 2, -BASE)
    ctx.set_source_surface(surf, 0, 0)
    ctx.get_source().set_filter(cairo.FILTER_GOOD)
    ctx.rectangle(0, 0, SW, SH)
    ctx.clip()
    ctx.paint_with_alpha(a)
    ctx.restore()


if __name__ == "__main__":
    generate()
