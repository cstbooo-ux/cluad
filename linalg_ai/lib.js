// Drawing primitives in the 3Blue1Brown idiom: number planes, vectors, formulas, subtitles.
const W = 1920, H = 1080;
const cv = document.getElementById('c'), ctx = cv.getContext('2d');
const C = {
  bg: '#0c0e13', panel: '#10141b', blue: '#58C4DD', blueD: '#29ABCA', green: '#83C167', red: '#FC6255',
  yellow: '#F4D345', gold: '#F0AC5F', teal: '#5CD0B3', purple: '#B189C6', pink: '#F28DBA', grey: '#8A8F98',
  light: '#C9CCD2', white: '#ECECEC',
};
const SANS = '"Noto Sans SC", sans-serif', SERIF = '"Noto Serif SC", serif';
let GA = 1;                 // scene-level alpha multiplier, set by renderFrame
let COLLECT = null;         // when a Set, text() only records characters (font preloading)

// ---------------------------------------------------------------- maths helpers
const clamp = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x));
const smooth = x => { x = clamp(x); return x * x * x * (x * (x * 6 - 15) + 10); };
const lin = (t, a, b) => clamp((t - a) / (b - a));
const prog = (t, a, b) => smooth(lin(t, a, b));
const lerp = (a, b, k) => a + (b - a) * k;
const lerp2 = (p, q, k) => [lerp(p[0], q[0], k), lerp(p[1], q[1], k)];
// 1 inside [a, b], ramping over f seconds at both ends (ramps lie inside the interval)
const fadeIO = (t, a, b, f = 0.35) => Math.min(lin(t, a, a + f), 1 - lin(t, b - f, b));
const there = (t, a, f = 0.5) => prog(t, a, a + f);
// piecewise smooth interpolation through keyframes [[t, v], ...]
function keys(t, ks) {
  if (t <= ks[0][0]) return ks[0][1];
  for (let i = 1; i < ks.length; i++) if (t <= ks[i][0]) return lerp(ks[i - 1][1], ks[i][1], prog(t, ks[i - 1][0], ks[i][0]));
  return ks[ks.length - 1][1];
}
function rng(seed) { // mulberry32
  return () => { seed |= 0; seed = seed + 0x6D2B79F5 | 0; let t = Math.imul(seed ^ seed >>> 15, 1 | seed);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; };
}
function gauss(r) { return Math.sqrt(-2 * Math.log(1 - r())) * Math.cos(2 * Math.PI * r()); }

// ---------------------------------------------------------------- colour helpers
function hex(h) { h = h.replace('#', ''); return [0, 2, 4].map(i => parseInt(h.slice(i, i + 2), 16)); }
function rgba(h, a = 1) { const [r, g, b] = hex(h); return `rgba(${r},${g},${b},${a})`; }
function mix(h1, h2, k, a = 1) {
  const p = hex(h1), q = hex(h2); k = clamp(k);
  return `rgba(${Math.round(lerp(p[0], q[0], k))},${Math.round(lerp(p[1], q[1], k))},${Math.round(lerp(p[2], q[2], k))},${a})`;
}
// diverging cell colour for matrix entries in [-1, 1]
const cellColor = (v, a = 1) => v >= 0 ? mix('#161b24', C.blue, Math.min(1, v), a) : mix('#161b24', C.red, Math.min(1, -v), a);

// ---------------------------------------------------------------- canvas helpers
function withAlpha(a, fn) { if (a * GA <= 0.003) return; ctx.save(); ctx.globalAlpha = clamp(a * GA); fn(); ctx.restore(); }
function rr(x, y, w, h, r) { ctx.beginPath(); ctx.roundRect(x, y, w, h, r); }
function line(x0, y0, x1, y1, color, width = 2, alpha = 1, dash = null) {
  withAlpha(alpha, () => {
    ctx.strokeStyle = color; ctx.lineWidth = width; ctx.lineCap = 'round';
    if (dash) ctx.setLineDash(dash);
    ctx.beginPath(); ctx.moveTo(x0, y0); ctx.lineTo(x1, y1); ctx.stroke();
  });
}
function dot(x, y, r, color, alpha = 1) {
  withAlpha(alpha, () => { ctx.fillStyle = color; ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.fill(); });
}
function panel(x, y, w, h, alpha = 1, r = 14) {
  withAlpha(alpha, () => { ctx.fillStyle = rgba(C.bg, 0.86); rr(x, y, w, h, r); ctx.fill(); });
}

function text(s, x, y, o = {}) {
  if (COLLECT) { for (const ch of s) COLLECT.add(ch); return; }
  const { size = 40, color = C.white, weight = 500, align = 'center', base = 'middle', alpha = 1, font = SANS, ls = 0, glow = 0 } = o;
  withAlpha(alpha, () => {
    ctx.font = `${weight} ${size}px ${font}`; ctx.textAlign = align; ctx.textBaseline = base; ctx.fillStyle = color;
    ctx.letterSpacing = `${ls}px`;
    if (glow) { ctx.shadowColor = color; ctx.shadowBlur = glow; }
    ctx.fillText(s, x, y);
  });
}
function textWidth(s, size, weight = 500, font = SANS) { ctx.font = `${weight} ${size}px ${font}`; ctx.letterSpacing = '0px'; return ctx.measureText(s).width; }

// ---------------------------------------------------------------- formulas
const TEXIMG = {};
async function loadTex() {
  const data = await (await fetch('build/tex.json')).json();
  await Promise.all(Object.entries(data).map(([k, d]) => new Promise((res, rej) => {
    const img = new Image();
    img.onload = () => { TEXIMG[k] = { img, w: d.w, h: d.h }; res(); };
    img.onerror = () => rej(new Error('tex ' + k));
    img.src = 'data:image/svg+xml;base64,' + btoa(unescape(encodeURIComponent(d.svg)));
  })));
}
// draw formula `key` anchored at (x, y); wipe reveals it left to right
function tex(key, x, y, o = {}) {
  if (COLLECT) return;
  const f = TEXIMG[key]; if (!f) throw new Error('missing tex ' + key);
  const { alpha = 1, align = 'center', wipe = 1, bg = false, scale = 1, pad = 18 } = o;
  if (wipe <= 0) return;
  const w = f.w * scale, h = f.h * scale;
  const x0 = align === 'left' ? x : align === 'right' ? x - w : x - w / 2, y0 = y - h / 2;
  if (bg) panel(x0 - pad, y0 - pad * 0.8, w * Math.min(1, wipe * 1.15) + pad * 2, h + pad * 1.6, alpha);
  withAlpha(alpha, () => {
    ctx.beginPath(); ctx.rect(x0 - 4, y0 - 20, (w + 8) * wipe, h + 40); ctx.clip();
    ctx.drawImage(f.img, x0, y0, w, h);
  });
  return { x0, y0, w, h };
}
const texSize = key => TEXIMG[key] ? [TEXIMG[key].w, TEXIMG[key].h] : [0, 0];

// ---------------------------------------------------------------- number planes and vectors
class Plane {
  constructor(ox, oy, s) { this.ox = ox; this.oy = oy; this.s = s; }
  P(x, y) { return [this.ox + x * this.s, this.oy - y * this.s]; }
}
// Grid lines x = k and y = k mapped through f (unit space -> unit space). n = samples per line (2 is enough for linear maps).
function grid(pl, o = {}) {
  const { f = null, alpha = 1, xr = [-12, 12], yr = [-8, 8], color = C.blueD, sub = true, axes = true, n = 2, width = 2.2, ext = 0 } = o;
  if (alpha * GA <= 0.003) return;
  const map = f ? (x, y) => { const q = f(x, y); return pl.P(q[0], q[1]); } : (x, y) => pl.P(x, y);
  const poly = (pts) => { ctx.beginPath(); pts.forEach((p, i) => i ? ctx.lineTo(p[0], p[1]) : ctx.moveTo(p[0], p[1])); ctx.stroke(); };
  const vline = x => { const pts = []; for (let i = 0; i < n; i++) pts.push(map(x, lerp(yr[0] - ext, yr[1] + ext, i / (n - 1)))); return pts; };
  const hline = y => { const pts = []; for (let i = 0; i < n; i++) pts.push(map(lerp(xr[0] - ext, xr[1] + ext, i / (n - 1)), y)); return pts; };
  withAlpha(alpha, () => {
    ctx.lineCap = 'butt';
    if (sub) {
      ctx.strokeStyle = rgba(color, 0.28); ctx.lineWidth = 1;
      for (let x = Math.ceil(xr[0]) + 0.5; x < xr[1]; x++) poly(vline(x));
      for (let y = Math.ceil(yr[0]) + 0.5; y < yr[1]; y++) poly(hline(y));
    }
    ctx.strokeStyle = rgba(color, 0.8); ctx.lineWidth = width;
    for (let x = Math.ceil(xr[0]); x <= xr[1]; x++) if (x || !axes) poly(vline(x));
    for (let y = Math.ceil(yr[0]); y <= yr[1]; y++) if (y || !axes) poly(hline(y));
    if (axes) { ctx.strokeStyle = 'rgba(236,236,236,0.9)'; ctx.lineWidth = 2.6; poly(vline(0)); poly(hline(0)); }
  });
}
// screen-space arrow; grow in [0,1] draws it out from the tail
function arrow(x0, y0, x1, y1, o = {}) {
  const { color = C.yellow, width = 6, alpha = 1, head = 24, grow = 1 } = o;
  if (grow <= 0.001) return;
  x1 = lerp(x0, x1, grow); y1 = lerp(y0, y1, grow);
  const dx = x1 - x0, dy = y1 - y0, L = Math.hypot(dx, dy); if (L < 0.5) return;
  const ux = dx / L, uy = dy / L, hl = Math.min(head, L * 0.6), hw = hl * 0.55;
  withAlpha(alpha, () => {
    ctx.strokeStyle = color; ctx.fillStyle = color; ctx.lineWidth = width; ctx.lineCap = 'butt';
    ctx.beginPath(); ctx.moveTo(x0, y0); ctx.lineTo(x1 - ux * hl * 0.9, y1 - uy * hl * 0.9); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x1 - ux * hl - uy * hw, y1 - uy * hl + ux * hw);
    ctx.lineTo(x1 - ux * hl + uy * hw, y1 - uy * hl - ux * hw); ctx.closePath(); ctx.fill();
  });
}
function vec(pl, a, b, o = {}) { const p = pl.P(a[0], a[1]), q = pl.P(b[0], b[1]); arrow(p[0], p[1], q[0], q[1], o); }

// ---------------------------------------------------------------- matrices drawn as coloured cells
// vals: 2D array in [-1,1]; colorFn(v, i, j) optional; cellAlpha(i, j) optional (0..1)
function cells(x, y, vals, o = {}) {
  const { cw = 26, ch = 26, gx = 3, gy = gx, alpha = 1, colorFn = v => cellColor(v), cellAlpha = null, stroke = null } = o;
  withAlpha(alpha, () => {
    for (let i = 0; i < vals.length; i++) for (let j = 0; j < vals[i].length; j++) {
      const a = cellAlpha ? cellAlpha(i, j) : 1; if (a <= 0.003) continue;
      ctx.globalAlpha = clamp(alpha * GA * a);
      ctx.fillStyle = colorFn(vals[i][j], i, j);
      ctx.fillRect(x + j * (cw + gx), y + i * (ch + gy), cw, ch);
      if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = 1; ctx.strokeRect(x + j * (cw + gx) + .5, y + i * (ch + gy) + .5, cw - 1, ch - 1); }
    }
  });
}
function outline(x, y, w, h, color, alpha = 1, width = 3, r = 6) {
  withAlpha(alpha, () => { ctx.strokeStyle = color; ctx.lineWidth = width; rr(x, y, w, h, r); ctx.stroke(); });
}
function bracket(x, y, h, side, color = C.white, alpha = 1, w = 12) {
  const s = side === 'l' ? 1 : -1;
  withAlpha(alpha, () => {
    ctx.strokeStyle = color; ctx.lineWidth = 3; ctx.lineCap = 'square';
    ctx.beginPath(); ctx.moveTo(x + s * w, y); ctx.lineTo(x, y); ctx.lineTo(x, y + h); ctx.lineTo(x + s * w, y + h); ctx.stroke();
  });
}

// ---------------------------------------------------------------- background, section chip, subtitles
let BGIMG = null;
function background() {
  if (!BGIMG) {
    BGIMG = document.createElement('canvas'); BGIMG.width = W; BGIMG.height = H;
    const b = BGIMG.getContext('2d'), g = b.createRadialGradient(W / 2, H * 0.45, 100, W / 2, H * 0.5, W * 0.62);
    g.addColorStop(0, '#12161e'); g.addColorStop(1, '#07080b');
    b.fillStyle = g; b.fillRect(0, 0, W, H);
  }
  ctx.globalAlpha = 1; ctx.drawImage(BGIMG, 0, 0);
}
function section(num, title, alpha) {
  panel(40, 30, 96 + textWidth(title, 28), 60, alpha * 0.9, 30);
  text(num, 82, 61, { size: 28, weight: 700, color: C.blue, alpha });
  text(title, 118, 61, { size: 28, color: C.light, align: 'left', alpha });
}
function drawSubs(T) {
  for (const s of SUBS) {
    if (T < s.t0 || T > s.t1) continue;
    const a = fadeIO(T, s.t0, s.t1, 0.18);
    const w = textWidth(s.text, 40) + 64;
    panel(W / 2 - w / 2, 962, w, 70, a * 0.78, 12);
    text(s.text, W / 2, 998, { size: 40, color: '#F2F2F2', alpha: a });
  }
}
