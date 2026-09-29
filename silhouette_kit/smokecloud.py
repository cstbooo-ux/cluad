"""Particle (smoke-style) clouds.

A cloud is an emitter: a cumulus-shaped volume (a few big lobes plus billows, irregular top AND bottom) that
continuously emits soft smoke puffs. Every puff is born at a point in the volume, slowly billows outward and
upward while it grows, then fades and is re-emitted, so the cloud keeps its overall shape but churns like smoke.

Each puff is a small noisy ball with its own light and shadow (bright toward the sun, darker underneath); on top of
that every puff gets a light value from its place in the cloud: self-shadowing by the puffs between it and the sun
(precomputed per cloud), sky light from above, dark underside. Puffs are drawn far-to-near.

    cloud(ctx, x, base_y, width, tones, seed, T, a=1.0, tower=0.5, churn=1.0)
tones = (shadow, body, lit, highlight); base_y is the cloud's mean underside, x its centre.
"""
import math, random
import numpy as np
import cairo

SUN = (0.62, -0.62, 0.48)
TEX = 128
NTEX = 8
_TEX = []
_CLOUDS = {}


def _hx(c):
    if isinstance(c, str):
        c = c.lstrip("#")
        return tuple(int(c[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return tuple(c)[:3]


def _noise(n, cell, rng):
    g = rng.random((n // cell + 3, n // cell + 3)).astype(np.float32)
    t = np.arange(n, dtype=np.float32) / cell
    i = t.astype(int); f = t - i; f = f * f * (3 - 2 * f)
    a = g[i][:, i]; b = g[i][:, i + 1]; c = g[i + 1][:, i]; d = g[i + 1][:, i + 1]
    return (a * (1 - f) + b * f) * (1 - f)[:, None] + (c * (1 - f) + d * f) * f[:, None]


def _surf(arr):
    """Single-channel float array -> A8 cairo surface (used as a mask)."""
    h, w = arr.shape
    stride = cairo.ImageSurface.format_stride_for_width(cairo.FORMAT_A8, w)
    buf = np.zeros((h, stride), np.uint8)
    buf[:, :w] = (np.clip(arr, 0, 1) * 255).astype(np.uint8)
    return cairo.ImageSurface.create_for_data(bytearray(buf.tobytes()), cairo.FORMAT_A8, w, h, stride)


def _textures():
    """Puff textures: (alpha mask, lit mask). Soft noisy balls; the lit mask is the sunward, upper part."""
    if _TEX:
        return _TEX
    rng = np.random.default_rng(7)
    yy, xx = (np.mgrid[0:TEX, 0:TEX].astype(np.float32) + 0.5) / TEX * 2 - 1
    for k in range(NTEX):
        n = 0.55 * _noise(TEX, 16, rng) + 0.3 * _noise(TEX, 8, rng) + 0.15 * _noise(TEX, 4, rng)
        warp = (n - 0.5) * 0.45
        r = np.sqrt(xx * xx + yy * yy) + warp
        alpha = np.clip(1 - r, 0, 1) ** 0.9
        alpha = np.clip(alpha * 1.6, 0, 1) * (0.75 + 0.35 * n)
        nz = np.sqrt(np.clip(1 - np.clip(r, 0, 1) ** 2, 0, 1))
        sl = math.sqrt(sum(v * v for v in SUN))
        lam = (xx * SUN[0] + yy * SUN[1] + nz * SUN[2]) / sl + (n - 0.5) * 0.5
        lit = np.clip(lam * 0.55 + 0.45, 0, 1) ** 1.6
        _TEX.append((_surf(alpha), _surf(alpha * lit)))
    return _TEX


def _lobes(rnd, width, tower):
    """Cumulus volume as lobes (cx, cy, cz, r) in units of width, y up is negative, base around 0."""
    L = []
    n = rnd.randint(4, 6)
    for i in range(n):
        t = i / (n - 1)
        dome = math.sin(math.pi * t) ** 0.8
        r = rnd.uniform(0.09, 0.15) * (0.6 + 0.7 * dome)
        L.append((-0.42 + 0.84 * t + rnd.uniform(-0.04, 0.04), -r * 0.55 - dome * 0.06 + rnd.uniform(-0.03, 0.05),
                  rnd.uniform(-0.05, 0.05), r))
    if rnd.random() < tower:
        cx, y, r = rnd.uniform(-0.15, 0.15), -0.22, 0.14
        while y > -0.62:
            L.append((cx + rnd.uniform(-0.05, 0.05), y, rnd.uniform(-0.03, 0.04), r))
            y -= r * rnd.uniform(0.5, 0.7)
            r = max(0.075, r * rnd.uniform(0.8, 0.92))
    for cx, cy, cz, r in list(L):                      # billows on the lobes, also hanging below
        for _ in range(rnd.randint(3, 5)):
            a = rnd.uniform(-math.pi, math.pi)
            rr = max(0.05, r * rnd.uniform(0.4, 0.65))
            d = r * rnd.uniform(0.55, 0.85)
            L.append((cx + math.cos(a) * d, cy + math.sin(a) * d * 0.8, cz + rnd.uniform(-0.3, 0.6) * r, rr))
    return L


def _build(seed, tower, count):
    rnd = random.Random(seed)
    L = _lobes(rnd, 1.0, tower)
    w = np.array([l[3] ** 2 for l in L]); w /= w.sum()
    P = []
    for _ in range(count):
        cx, cy, cz, r = L[rnd.choices(range(len(L)), w)[0]]
        u = rnd.random() ** 0.6                        # a little biased toward the lobe surface
        th, ph = rnd.uniform(0, 2 * math.pi), math.acos(rnd.uniform(-1, 1))
        px = cx + r * u * math.sin(ph) * math.cos(th)
        py = cy + r * u * math.sin(ph) * math.sin(th) * 0.85
        pz = cz + r * u * math.cos(ph)
        pr = max(0.04, r * rnd.uniform(0.45, 0.75) * (1.2 - 0.4 * u))
        # outward direction from the lobe centre: puffs billow out of the cloud as they age
        dx, dy = px - cx, py - cy
        dl = math.hypot(dx, dy) + 1e-6
        P.append([px, py, pz, pr, dx / dl, dy / dl - 0.6, rnd.random(), rnd.uniform(0.7, 1.3), rnd.randrange(NTEX)])
    P = np.array(P, np.float32)
    # self-shadow: how much of the cloud lies between each puff and the sun (cylinder toward the sun)
    s = np.array(SUN, np.float32); s /= np.linalg.norm(s)
    pos, rad = P[:, :3], P[:, 3]
    d = pos[None, :, :] - pos[:, None, :]              # j - i
    along = d @ s
    perp = np.linalg.norm(d - along[..., None] * s[None, None, :], axis=2)
    occ = ((along > 0) * np.clip(1 - perp / (rad[None, :] * 1.3 + 1e-6), 0, 1) * (rad[None, :] / 0.05)).sum(1)
    shadow = np.exp(-occ * 0.09)
    height = np.clip(-pos[:, 1] / 0.35, -0.3, 1)
    light = 0.18 + 0.2 * height + 0.62 * shadow
    light = light - 0.18 * np.clip(pos[:, 1] / 0.05, 0, 1)          # underside darker
    order = np.argsort(pos[:, 2])                                   # far to near
    return P[order], np.clip(light[order], 0, 1)


def _tone(tones, t):
    sh, bo, li, hi = [np.array(_hx(c)) for c in tones]
    if t < 0.42:
        return sh + (bo - sh) * (t / 0.42)
    if t < 0.78:
        return bo + (li - bo) * ((t - 0.42) / 0.36)
    return li + (hi - li) * min(1.0, (t - 0.78) / 0.22)


def cloud(ctx, x, base_y, width, tones, seed, T=0.0, a=1.0, tower=0.5, churn=1.0, detail=1.0):
    """Draw one particle cloud centred on x with its underside around base_y, `width` px wide.
    churn scales how fast the puffs billow (0 = frozen)."""
    tex = _textures()
    count = int(max(40, min(260, width * 0.26 * detail)))
    key = (seed, round(tower, 1), count)
    if key not in _CLOUDS:
        if len(_CLOUDS) > 400:
            _CLOUDS.clear()
        _CLOUDS[key] = _build(seed, tower, count)
    P, light = _CLOUDS[key]
    # quantised palette lookups (cheap)
    lut = [_tone(tones, q / 31) for q in range(32)]
    for (px, py, pz, pr, ox, oy, ph, sp, ti), lv in zip(P, light):
        age = (T * 0.045 * churn * sp + ph) % 1.0
        fade = min(1.0, age / 0.2, (1 - age) / 0.25)
        grow = 0.8 + 0.45 * age
        bx = x + (px + ox * pr * 0.35 * age) * width
        by = base_y + (py + oy * pr * 0.25 * age) * width
        rad = pr * grow * width
        al = a * fade
        if al <= 0.01 or rad < 1:
            continue
        k = rad * 2 / TEX
        A_, Lm = tex[int(ti)]
        c0 = lut[int(min(31, lv * 0.62 * 31))]
        c1 = lut[int(min(31, (0.42 + 0.62 * lv) * 31))]
        ctx.save()
        ctx.translate(bx - rad, by - rad)
        ctx.scale(k, k)
        ctx.set_source_rgba(c0[0], c0[1], c0[2], al)
        ctx.mask_surface(A_, 0, 0)
        ctx.set_source_rgba(c1[0], c1[1], c1[2], al * (0.25 + 0.55 * lv))
        ctx.mask_surface(Lm, 0, 0)
        ctx.restore()
