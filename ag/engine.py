"""Rendering core: software-OpenGL raymarcher for implicit surfaces, a mesh
renderer, 2D glow helpers, typography and the HDR post chain."""
import os, io, functools
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont

D = os.path.dirname(os.path.abspath(__file__))
W, H, FPS = 1920, 1080, 30
FONT = {k: os.path.join(D, "fonts", f"NotoSerifSC-{k}.otf") for k in ("Light", "Regular", "Bold", "Black")}
LATIN = os.path.join(D, "fonts", "CormorantGaramond.ttf")
LATIN_I = os.path.join(D, "fonts", "CormorantGaramond-Italic.ttf")


def ss(a, b, x):
    x = np.clip((x - a) / (b - a), 0.0, 1.0)
    return x * x * (3 - 2 * x)


def ease_out(x, k=3):
    return 1 - (1 - np.clip(x, 0, 1)) ** k


def ease_io(x):
    x = np.clip(x, 0, 1)
    return np.where(x < 0.5, 4 * x**3, 1 - (-2 * x + 2) ** 3 / 2) if np.ndim(x) else (4 * x**3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2)


# =============================================================== camera
class Cam:
    def __init__(self, pos, target, focal=2.0, up=(0, 0, 1)):
        self.ro = np.array(pos, float)
        fw = np.array(target, float) - self.ro
        self.fw = fw / np.linalg.norm(fw)
        rt = np.cross(self.fw, np.array(up, float))
        self.rt = rt / np.linalg.norm(rt)
        self.up = np.cross(self.rt, self.fw)
        self.focal = focal

    @staticmethod
    def orbit(target, dist, az, el, focal=2.0):
        target = np.array(target, float)
        pos = target + dist * np.array([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)])
        return Cam(pos, target, focal)

    def project(self, P, w, h):
        """world points (N,3) -> pixel coords (N,2), distance along ray (N,)"""
        v = P - self.ro
        zc = v @ self.fw
        xs = (v @ self.rt) / zc * self.focal
        ys = (v @ self.up) / zc * self.focal
        px = xs * h + 0.5 * w
        py = 0.5 * h - ys * h
        return np.stack([px, py], 1), np.linalg.norm(v, axis=1), zc


# =============================================================== GL
_ctx = None


def ctx():
    global _ctx
    if _ctx is None:
        import moderngl
        _ctx = moderngl.create_standalone_context(require=330)
    return _ctx


QUAD_VS = """#version 330
in vec2 p; void main(){ gl_Position = vec4(p, 0.0, 1.0); }"""

SURF_FS = """#version 330
layout(location=0) out vec4 oc;
layout(location=1) out vec4 od;
uniform vec2 R;
uniform vec3 ro, fw, rt, up;
uniform float focal, clipR, steps, scan, scanW, iso, gloss, shellA;
uniform vec3 colOut, colIn, scanCol, scanAx, keyDir;
uniform float T;
float F(vec3 q_){
  float x=q_.x, y=q_.y, z=q_.z;
  %s
}
vec3 G(vec3 p){
  float e = 2e-4*max(1.0, clipR);
  return vec3(F(p+vec3(e,0,0))-F(p-vec3(e,0,0)), F(p+vec3(0,e,0))-F(p-vec3(0,e,0)), F(p+vec3(0,0,e))-F(p-vec3(0,0,e)));
}
bool ok(vec3 p){ return dot(p, scanAx) < scan; }
void main(){
  vec2 uv = (gl_FragCoord.xy - 0.5*R) / R.y;
  vec3 rd = normalize(fw*focal + uv.x*rt + uv.y*up);
  float b = dot(ro, rd), c = dot(ro, ro) - clipR*clipR, h = b*b - c;
  oc = vec4(0.0); od = vec4(1e9, 0.0, 0.0, 0.0);
  // faint glass shell outline
  float dmin = sqrt(max(dot(ro,ro) - b*b, 0.0));
  float ring = exp(-pow((dmin - clipR)/(0.012*clipR), 2.0)) * shellA;
  if (h < 0.0) { oc = vec4(vec3(0.35,0.55,1.0)*ring, 0.0); return; }
  h = sqrt(h);
  float t0 = max(-b - h, 0.0), t1 = -b + h;
  float dt = (t1 - t0) / steps;
  float t = t0;
  float fprev = F(ro + rd*t);
  bool okprev = ok(ro + rd*t);
  float thit = -1.0;
  for (int i = 0; i < 2000; i++) {
    if (float(i) >= steps) break;
    float tn = t + dt;
    vec3 pn = ro + rd*tn;
    float fn = F(pn);
    bool okn = ok(pn);
    if (okn && okprev && sign(fn) != sign(fprev)) {
      float a = t, bb = tn, fa = fprev;
      for (int k = 0; k < 14; k++) {
        float m = 0.5*(a + bb); float fm = F(ro + rd*m);
        if (sign(fm) == sign(fa)) { a = m; fa = fm; } else { bb = m; }
      }
      thit = 0.5*(a + bb); break;
    }
    fprev = fn; okprev = okn; t = tn;
  }
  vec3 shell = vec3(0.35,0.55,1.0)*ring;
  if (thit < 0.0) { oc = vec4(shell, 0.0); return; }
  vec3 p = ro + rd*thit;
  vec3 g = G(p);
  vec3 n = normalize(g);
  bool inside = dot(n, rd) > 0.0;
  if (inside) n = -n;
  vec3 base = inside ? colIn : colOut;
  vec3 L1 = normalize(keyDir);
  vec3 L2 = normalize(vec3(-L1.x, -L1.y, 0.3));
  vec3 V = -rd;
  float d1 = max(dot(n, L1), 0.0), d2 = max(dot(n, L2), 0.0);
  vec3 H1 = normalize(L1 + V);
  float sp = pow(max(dot(n, H1), 0.0), 90.0) * gloss;
  float sp2 = pow(max(dot(n, normalize(L2 + V)), 0.0), 30.0) * gloss * 0.25;
  float fr = pow(1.0 - max(dot(n, V), 0.0), 3.0);
  // ambient occlusion from the field itself
  float gl = length(g) / (4e-4*max(1.0, clipR));
  float ao = 0.0;
  for (int k = 1; k <= 4; k++) {
    float dk = 0.06 * float(k) * max(1.0, clipR*0.5);
    float est = abs(F(p + n*dk)) / max(gl, 1e-6);
    ao += max(dk - est, 0.0) / dk * (1.0 / float(k));
  }
  ao = clamp(1.0 - 0.55*ao, 0.25, 1.0);
  vec3 col = base * (0.035 + 1.05*pow(d1, 1.3) + 0.22*d2) * ao;
  col += (sp + sp2) * vec3(1.0, 0.95, 0.88);
  col += fr * mix(vec3(0.35,0.6,1.0), base, 0.35) * 1.1 * (0.5 + 0.5*ao);
  // iso lines on the surface (radial shells)
  if (iso > 0.0) {
    float r = length(p) * iso;
    float li = exp(-pow((fract(r) - 0.5) / 0.035, 2.0));
    col += li * base * 0.35;
  }
  // rim where surface meets the clipping sphere
  float edge = exp(-pow((clipR - length(p)) / (0.012*clipR), 2.0));
  col += edge * vec3(1.0, 0.85, 0.6) * 1.6;
  // scanning front
  float sf = exp(-pow((scan - dot(p, scanAx)) / scanW, 2.0));
  col += sf * scanCol * 3.0;
  oc = vec4(col + shell*0.3, 1.0);
  od = vec4(thit, 0.0, 0.0, 0.0);
}"""


class Surface:
    def __init__(self, glsl_body):
        c = ctx()
        self.prog = c.program(vertex_shader=QUAD_VS, fragment_shader=SURF_FS % glsl_body)
        vbo = c.buffer(np.array([-1, -1, 1, -1, -1, 1, 1, 1], "f4"))
        self.vao = c.vertex_array(self.prog, [(vbo, "2f", "p")])
        self.fbos = {}

    def _fbo(self, w, h):
        if (w, h) not in self.fbos:
            c = ctx()
            t0 = c.texture((w, h), 4, dtype="f4")
            t1 = c.texture((w, h), 4, dtype="f4")
            self.fbos[(w, h)] = (c.framebuffer([t0, t1]), t0, t1)
        return self.fbos[(w, h)]

    def render(self, cam, w, h, clipR=2.0, steps=400, colOut=(0.2, 0.55, 1.0), colIn=(1.0, 0.6, 0.2),
               scan=1e9, scanW=0.03, scanCol=(0.6, 0.9, 1.0), scanAx=(0, 0, 1), iso=0.0, gloss=0.8,
               keyDir=(0.5, -0.4, 0.8), shellA=0.35, T=0.0):
        fbo, t0, t1 = self._fbo(w, h)
        fbo.use()
        u = self.prog
        vals = dict(R=(w, h), ro=tuple(cam.ro), fw=tuple(cam.fw), rt=tuple(cam.rt), up=tuple(cam.up), focal=cam.focal,
                    clipR=clipR, steps=float(steps), colOut=colOut, colIn=colIn, scan=scan, scanW=scanW,
                    scanCol=scanCol, scanAx=tuple(np.array(scanAx) / np.linalg.norm(scanAx)), iso=iso, gloss=gloss,
                    keyDir=keyDir, shellA=shellA, T=T)
        for k, v in vals.items():
            if k in u:
                u[k].value = v
        import moderngl
        self.vao.render(moderngl.TRIANGLE_STRIP)
        col = np.frombuffer(t0.read(), "f4").reshape(h, w, 4)[::-1]
        dep = np.frombuffer(t1.read(), "f4").reshape(h, w, 4)[::-1, :, 0]
        return col[..., :3].copy(), col[..., 3].copy(), dep.copy()


MESH_VS = """#version 330
in vec3 pos; in vec3 nrm; in vec3 col; in vec2 uv;
uniform mat4 MVP;
out vec3 vp; out vec3 vn; out vec3 vc; out vec2 vu;
void main(){ vp = pos; vn = nrm; vc = col; vu = uv; gl_Position = MVP * vec4(pos, 1.0); }"""
MESH_FS = """#version 330
in vec3 vp; in vec3 vn; in vec3 vc; in vec2 vu;
layout(location=0) out vec4 oc;
layout(location=1) out vec4 od;
uniform vec3 ro; uniform vec3 keyDir; uniform float gridA, gridN, gridM, bandA, gloss, alpha, emis;
uniform vec3 bandCol; uniform float uedgeA; uniform vec3 uedgeCol;
void main(){
  vec3 V = normalize(ro - vp);
  vec3 n = normalize(vn);
  bool back = dot(n, V) < 0.0;
  if (back) n = -n;
  vec3 base = vc * (back ? 0.75 : 1.0);
  vec3 L1 = normalize(keyDir), L2 = normalize(vec3(-L1.x, -L1.y, 0.2));
  float d1 = max(dot(n, L1), 0.0), d2 = max(dot(n, L2), 0.0);
  vec3 Hh = normalize(L1 + V);
  float sp = pow(max(dot(n, Hh), 0.0), 60.0) * gloss;
  float fr = pow(1.0 - max(dot(n, V), 0.0), 3.0);
  vec3 col = base * (0.07 + 0.85*d1 + 0.3*d2) + sp + fr * mix(base, vec3(0.5,0.7,1.0), 0.4) * 0.55;
  col += base * emis;
  if (gridA > 0.0) {
    vec2 g = vec2(vu.x*gridN, vu.y*gridM);
    vec2 fw2 = fwidth(g);
    vec2 d = abs(fract(g - 0.5) - 0.5) / max(fw2, 1e-4);
    float line = 1.0 - min(min(d.x, d.y) / 1.2, 1.0);
    col += line * gridA * vec3(0.55, 0.8, 1.0);
  }
  if (bandA > 0.0) {
    float dv = min(min(abs(vu.y), abs(vu.y - 1.0)), abs(vu.y - 0.5));
    float fwv = fwidth(vu.y);
    float band = exp(-pow(dv / max(3.2*fwv, 1e-4), 2.0));
    col += band * bandA * bandCol;
  }
  if (uedgeA > 0.0) {
    float du = min(vu.x, 1.0 - vu.x);
    float e = exp(-pow(du / max(2.2*fwidth(vu.x), 1e-4), 2.0));
    col += e * uedgeA * uedgeCol;
  }
  oc = vec4(col * alpha, alpha);
  od = vec4(length(ro - vp), 0.0, 0.0, 0.0);
}"""


class Mesh:
    def __init__(self):
        c = ctx()
        self.prog = c.program(vertex_shader=MESH_VS, fragment_shader=MESH_FS)
        self.fbos = {}

    def _fbo(self, w, h):
        if (w, h) not in self.fbos:
            c = ctx()
            t0 = c.texture((w, h), 4, dtype="f4")
            t1 = c.texture((w, h), 4, dtype="f4")
            db = c.depth_renderbuffer((w, h))
            self.fbos[(w, h)] = (c.framebuffer([t0, t1], db), t0, t1)
        return self.fbos[(w, h)]

    def render(self, cam, w, h, pos, nrm, col, uv, idx, near=0.05, far=100.0, keyDir=(0.5, -0.4, 0.8),
               gridA=0.0, gridN=8, gridM=8, bandA=0.0, bandCol=(1.0, 0.7, 0.3), gloss=0.6, alpha=1.0, emis=0.0,
               uedgeA=0.0, uedgeCol=(0.95, 0.35, 0.75)):
        import moderngl
        c = ctx()
        fbo, t0, t1 = self._fbo(w, h)
        fbo.use()
        fbo.clear(0, 0, 0, 0, depth=1.0)
        t1.write(np.full((h, w, 4), 1e9, "f4").tobytes())
        c.enable(moderngl.DEPTH_TEST)
        data = np.concatenate([pos, nrm, col, uv], 1).astype("f4")
        vbo = c.buffer(data.tobytes())
        ibo = c.buffer(idx.astype("i4").tobytes())
        vao = c.vertex_array(self.prog, [(vbo, "3f 3f 3f 2f", "pos", "nrm", "col", "uv")], ibo)
        # projection consistent with Cam.project
        V = np.eye(4)
        V[0, :3], V[1, :3], V[2, :3] = cam.rt, cam.up, -cam.fw
        V[:3, 3] = -V[:3, :3] @ cam.ro
        a = w / h
        P = np.zeros((4, 4))
        P[0, 0] = 2 * cam.focal / a
        P[1, 1] = 2 * cam.focal
        P[2, 2] = -(far + near) / (far - near)
        P[2, 3] = -2 * far * near / (far - near)
        P[3, 2] = -1
        M = (P @ V).T.astype("f4")
        u = self.prog
        vals = dict(MVP=M.tobytes(), ro=tuple(cam.ro), keyDir=keyDir, gridA=gridA, gridN=float(gridN),
                    gridM=float(gridM), bandA=bandA, bandCol=bandCol, gloss=gloss, alpha=alpha, emis=emis,
                    uedgeA=uedgeA, uedgeCol=uedgeCol)
        for k, v in vals.items():
            if k in u:
                if k == "MVP":
                    u[k].write(v)
                else:
                    u[k].value = v
        vao.render(moderngl.TRIANGLES)
        c.disable(moderngl.DEPTH_TEST)
        colr = np.frombuffer(t0.read(), "f4").reshape(h, w, 4)[::-1]
        dep = np.frombuffer(t1.read(), "f4").reshape(h, w, 4)[::-1, :, 0]
        vao.release(); vbo.release(); ibo.release()
        return colr[..., :3].copy(), colr[..., 3].copy(), dep.copy()


def grid_mesh(nu, nv):
    u, v = np.meshgrid(np.linspace(0, 1, nu), np.linspace(0, 1, nv), indexing="ij")
    i = np.arange(nu * nv).reshape(nu, nv)
    a, b, c, d = i[:-1, :-1], i[1:, :-1], i[1:, 1:], i[:-1, 1:]
    idx = np.stack([a, b, c, a, c, d], -1).reshape(-1, 3)
    return u, v, idx


def grid_normals(P):
    """P: (nu,nv,3) grid of points -> normals"""
    du = np.gradient(P, axis=0)
    dv = np.gradient(P, axis=1)
    n = np.cross(du, dv)
    return n / (np.linalg.norm(n, axis=-1, keepdims=True) + 1e-12)


def downsample(img, w=W, h=H):
    return cv2.resize(img, (w, h), interpolation=cv2.INTER_AREA)


# =============================================================== splats (points / lines with depth test)
def splat(acc, pts, vals, color=None):
    """bilinear splat of points into acc (h,w) or (h,w,3)"""
    h, w = acc.shape[:2]
    x, y = pts[:, 0] - 0.5, pts[:, 1] - 0.5
    x0, y0 = np.floor(x).astype(int), np.floor(y).astype(int)
    fx, fy = x - x0, y - y0
    for dx, dy, wt in ((0, 0, (1 - fx) * (1 - fy)), (1, 0, fx * (1 - fy)), (0, 1, (1 - fx) * fy), (1, 1, fx * fy)):
        xi, yi = x0 + dx, y0 + dy
        m = (xi >= 0) & (xi < w) & (yi >= 0) & (yi < h)
        if acc.ndim == 2:
            np.add.at(acc, (yi[m], xi[m]), (vals * wt)[m])
        else:
            np.add.at(acc, (yi[m], xi[m]), (vals * wt)[m][:, None] * (color if color is not None else 1))
    return acc


def glow_points(pts, vals, color, sigmas=((1.2, 1.0), (4, 0.5), (14, 0.25)), shape=(H, W)):
    acc = splat(np.zeros(shape, np.float32), pts, vals.astype(np.float32))
    out = np.zeros(shape, np.float32)
    for s, a in sigmas:
        out += cv2.GaussianBlur(acc, (0, 0), s) * a * (2 * np.pi * s * s) ** 0.5
    return out[..., None] * np.array(color, np.float32)


# =============================================================== 2D implicit curves
class View2D:
    def __init__(self, cx, cy, scale, w=W, h=H):
        self.cx, self.cy, self.s, self.w, self.h = cx, cy, scale, w, h
        xs = (np.arange(w, dtype=np.float32) + 0.5 - w / 2) / scale + cx
        ys = -(np.arange(h, dtype=np.float32) + 0.5 - h / 2) / scale + cy
        self.X, self.Y = np.meshgrid(xs, ys)

    def to_px(self, P):
        P = np.atleast_2d(P)
        return np.stack([(P[:, 0] - self.cx) * self.s + self.w / 2, -(P[:, 1] - self.cy) * self.s + self.h / 2], 1)


def pix_dist(f):
    """approximate pixel distance to the zero set of sampled field f"""
    gy, gx = np.gradient(f)
    return np.abs(f) / (np.sqrt(gx * gx + gy * gy) + 1e-12)


def line_glow(d, width=1.3, core=1.0, halo=0.35, halo_w=6.0):
    return core * np.exp(-(d / width) ** 2) + halo * np.exp(-d / halo_w)


def seg_dist(X, Y, a, b):
    ax, ay = a
    bx, by = b
    vx, vy = bx - ax, by - ay
    t = np.clip(((X - ax) * vx + (Y - ay) * vy) / (vx * vx + vy * vy + 1e-12), 0, 1)
    return np.hypot(X - ax - t * vx, Y - ay - t * vy)


# =============================================================== background
@functools.lru_cache(None)
def _bg_assets(seed=11):
    rng = np.random.default_rng(seed)
    n = 2600
    stars = np.stack([rng.uniform(-0.2, 1.2, n) * W, rng.uniform(-0.2, 1.2, n) * H], 1)
    mag = rng.pareto(2.2, n).clip(0, 12) * 0.06 + 0.01
    depth = rng.uniform(0.2, 1.0, n)
    tw = rng.uniform(0, 2 * np.pi, n)
    hue = rng.uniform(0, 1, n)
    # nebula: multi-octave smooth noise
    neb = np.zeros((H, W, 3), np.float32)
    for k, s in enumerate((120, 60, 30)):
        noise = rng.normal(size=neb.shape).astype(np.float32)
        neb += cv2.GaussianBlur(noise, (0, 0), s) * (1.0 / (k + 1))
    neb = neb / neb.std()
    return stars, mag, depth, tw, hue, neb


def background(t, drift=(0.0, 0.0), neb_amt=1.0, star_amt=1.0, tint=(0.35, 0.45, 1.0), tint2=(0.8, 0.3, 0.7)):
    stars, mag, depth, tw, hue, neb = _bg_assets()
    img = np.empty((H, W, 3), np.float32)
    img[:] = (0.0025, 0.0035, 0.008)
    if neb_amt > 0:
        oy = int((drift[1] * 20 + t * 1.5) % (neb.shape[0] - H // 2))
        ox = int((drift[0] * 20 + t * 3.0) % (neb.shape[1] - W // 2))
        n = neb[oy:oy + H // 2, ox:ox + W // 2]
        n = cv2.resize(n, (W, H), interpolation=cv2.INTER_LINEAR)
        a = np.clip(n[..., 0] * 0.4 + 0.15, 0, None) ** 2 * 0.0055
        b = np.clip(n[..., 1] * 0.4 - 0.1, 0, None) ** 2 * 0.0035
        img += neb_amt * (a[..., None] * np.array(tint, np.float32) + b[..., None] * np.array(tint2, np.float32))
    if star_amt > 0:
        p = stars + np.array(drift) * depth[:, None] * 60 + np.array([t * 6, t * 1.5]) * depth[:, None]
        p[:, 0] = np.mod(p[:, 0] + 0.2 * W, 1.4 * W) - 0.2 * W
        v = mag * (0.75 + 0.25 * np.sin(t * 2.3 + tw)) * star_amt
        acc = splat(np.zeros((H, W), np.float32), p, v.astype(np.float32))
        acc = cv2.GaussianBlur(acc, (0, 0), 0.7) * 3.0
        img += acc[..., None] * np.array([0.8, 0.88, 1.0], np.float32)
    return img


# =============================================================== typography
@functools.lru_cache(maxsize=512)
def font(path, size):
    f = ImageFont.truetype(path, size)
    return f


@functools.lru_cache(maxsize=512)
def text_img(text, size, weight="Regular", latin=False, italic=False, tracking=0.0, crop=True):
    """white text on transparent -> float alpha array, plus width/height"""
    path = (LATIN_I if italic else LATIN) if latin else FONT[weight]
    f = font(path, size)
    if latin:
        try:
            f.set_variation_by_name("SemiBold" if weight in ("Bold", "Black") else ("Light" if weight == "Light" else "Medium"))
        except Exception:
            pass
    # per-glyph layout for tracking
    widths = [f.getlength(ch) for ch in text]
    tw = int(sum(widths) + tracking * size * max(len(text) - 1, 0)) + 4
    asc, desc = f.getmetrics()
    img = Image.new("L", (tw + size, asc + desc + size // 2), 0)
    dr = ImageDraw.Draw(img)
    xpos = size // 2
    for ch, wch in zip(text, widths):
        dr.text((xpos, size // 4), ch, font=f, fill=255)
        xpos += wch + tracking * size
    a = np.asarray(img, np.float32) / 255.0
    ys, xs = np.nonzero(a > 0.002)
    if len(xs) == 0:
        return np.zeros((1, 1), np.float32)
    # crop horizontally to ink, keep a vertical box from font metrics for stable baselines
    if crop:
        a = a[:, max(xs.min() - 2, 0): xs.max() + 3]
    return a


@functools.lru_cache(maxsize=128)
def math_img(tex, size):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    matplotlib.rcParams["mathtext.fontset"] = "cm"
    fig = plt.figure(figsize=(0.01, 0.01), dpi=100)
    fig.text(0, 0, f"${tex}$", fontsize=size * 0.72, color="white")
    buf = io.BytesIO()
    fig.savefig(buf, dpi=100, transparent=True, bbox_inches="tight", pad_inches=0.08)
    plt.close(fig)
    buf.seek(0)
    im = np.asarray(Image.open(buf).convert("RGBA"), np.float32) / 255.0
    return im[..., 3].copy()


def paste(img, alpha_map, cx, cy, color=(1, 1, 1), opacity=1.0, anchor="c", scale=1.0, blur=0.0, glow=0.0, scrim=0.0):
    """composite a monochrome alpha map (additive-over) centred at (cx, cy)."""
    if opacity <= 0.003:
        return img
    a = alpha_map
    if scale != 1.0:
        a = cv2.resize(a, None, fx=scale, fy=scale, interpolation=cv2.INTER_LINEAR if scale > 1 else cv2.INTER_AREA)
    if blur > 0.05:
        pad = int(blur * 3) + 2
        a = cv2.GaussianBlur(np.pad(a, pad), (0, 0), blur)
    h, w = a.shape
    if anchor == "c":
        x0, y0 = int(round(cx - w / 2)), int(round(cy - h / 2))
    elif anchor == "l":
        x0, y0 = int(round(cx)), int(round(cy - h / 2))
    else:  # right
        x0, y0 = int(round(cx - w)), int(round(cy - h / 2))
    col = np.array(color, np.float32)
    if glow > 0 or scrim > 0:
        P = 40
        ap = np.pad(a, P) * opacity
        gy0, gx0 = y0 - P, x0 - P
        gy1, gx1 = y0 + h + P, x0 + w + P
        cy0, cx0 = max(gy0, 0), max(gx0, 0)
        cy1, cx1 = min(gy1, img.shape[0]), min(gx1, img.shape[1])
        if cy1 > cy0 and cx1 > cx0:
            reg = img[cy0:cy1, cx0:cx1]
            if scrim > 0:
                sc = cv2.GaussianBlur(cv2.dilate(ap, np.ones((9, 9), np.uint8)), (0, 0), 10)
                reg *= (1 - np.clip(sc * scrim, 0, 0.85))[cy0 - gy0:cy1 - gy0, cx0 - gx0:cx1 - gx0, None]
            if glow > 0:
                g = cv2.GaussianBlur(ap, (0, 0), 12) * glow
                reg += g[cy0 - gy0:cy1 - gy0, cx0 - gx0:cx1 - gx0, None] * col
    X0, Y0 = max(x0, 0), max(y0, 0)
    X1, Y1 = min(x0 + w, img.shape[1]), min(y0 + h, img.shape[0])
    if X1 <= X0 or Y1 <= Y0:
        return img
    sub = a[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0] * opacity
    region = img[Y0:Y1, X0:X1]
    region *= (1 - sub[..., None] * 0.85)
    region += sub[..., None] * col
    return img


def caption(img, t, t0, t1, zh, en=None, y=0.82, size=54, en_size=25, color=(1, 1, 1), en_color=(0.65, 0.75, 0.95),
            weight="Regular", stagger=0.045, x=None, anchor="c"):
    """two-line caption: Chinese line with per-glyph fade/blur-in, small tracked English line under it."""
    if t < t0 - 0.05 or t > t1 + 0.3:
        return img
    out = 1 - ss(t1, t1 + 0.3, t)
    cx = W / 2 if x is None else x
    cy = H * y
    chars = list(zh)
    fimgs = [text_img(ch, size, weight, crop=False) if ch != " " else None for ch in chars]
    fo = font(FONT[weight], size)
    widths = [fo.getlength(ch) for ch in chars]
    total = sum(widths)
    xs = cx - total / 2 if anchor == "c" else cx
    for i, (ch, a, wch) in enumerate(zip(chars, fimgs, widths)):
        if a is not None:
            k = ss(t0 + i * stagger, t0 + i * stagger + 0.5, t)
            if k > 0:
                paste(img, a, xs + wch / 2, cy - (1 - k) * 10, color, opacity=k * out, blur=(1 - k) * 6, scrim=0.6)
        xs += wch
    if en:
        k = ss(t0 + 0.3, t0 + 1.1, t)
        a = text_img(en, en_size, "Regular", latin=True, tracking=0.22 - 0.06 * k)
        ex = cx if anchor == "c" else cx + a.shape[1] / 2
        paste(img, a, ex, cy + size * 0.95, en_color, opacity=k * out * 0.9, scrim=0.5)
    return img


# =============================================================== post
def aces(x):
    return np.clip((x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14), 0, 1)


@functools.lru_cache(None)
def _post_assets():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.hypot((xx - W / 2) / (W / 2), (yy - H / 2) / (H / 2))
    vig = (1 - 0.38 * ss(0.55, 1.5, r)).astype(np.float32)
    rng = np.random.default_rng(99)
    dither = (rng.random((H, W, 3)).astype(np.float32) - 0.5) / 255.0
    return vig, dither


def bloom(img, strength=0.35, thresh=0.0):
    src = np.maximum(img - thresh, 0) if thresh > 0 else img
    acc = np.zeros_like(img)
    lvl = src
    wts = (0.25, 0.3, 0.35, 0.4, 0.45, 0.5)
    for k, wt in enumerate(wts):
        lvl = cv2.pyrDown(lvl)
        b = cv2.GaussianBlur(lvl, (0, 0), 1.5)
        acc += cv2.resize(b, (img.shape[1], img.shape[0]), interpolation=cv2.INTER_LINEAR) * wt
    return img + acc * strength


def post(img, exposure=1.0, flash=0.0, bloom_amt=0.35, shake=(0.0, 0.0), aberr=0.0, fade=1.0, zoom=0.0):
    vig, dither = _post_assets()
    img = bloom(img, bloom_amt)
    if flash > 0:
        img = img + flash
    if aberr > 0.01 or abs(shake[0]) + abs(shake[1]) > 0.01 or zoom > 1e-4:
        out = np.empty_like(img)
        for c, s in zip(range(3), (1 + aberr * 0.004, 1.0, 1 - aberr * 0.004)):
            s = s * (1 + zoom)
            M = np.array([[s, 0, (1 - s) * W / 2 + shake[0]], [0, s, (1 - s) * H / 2 + shake[1]]], np.float32)
            out[..., c] = cv2.warpAffine(img[..., c], M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        img = out
    img = aces(img * exposure) * vig[..., None] * fade
    img = np.clip(img, 0, 1) ** (1 / 2.2) + dither
    return (np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)
