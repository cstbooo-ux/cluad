'use strict';
// ---------------------------------------------------------------- basics
const W = 720, H = 1280, TAU = Math.PI * 2;
const clamp = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x));
const lerp = (a, b, k) => a + (b - a) * k;
const seg = (t, a, b) => clamp((t - a) / (b - a));
const sm = x => { x = clamp(x); return x * x * (3 - 2 * x); };
const eo = x => 1 - Math.pow(1 - clamp(x), 3);
const ei = x => Math.pow(clamp(x), 3);
const eback = x => { x = clamp(x); const c = 1.9; return 1 + (c + 1) * Math.pow(x - 1, 3) + c * Math.pow(x - 1, 2); };
const mod = (a, n) => ((a % n) + n) % n;
function rnd(seed) {
  let a = seed >>> 0;
  return () => { a = (a + 0x6D2B79F5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}
const hash = n => { const s = Math.sin(n * 127.1 + 311.7) * 43758.5453; return s - Math.floor(s); };
const noise1 = x => { const i = Math.floor(x), f = x - i; return lerp(hash(i), hash(i + 1), f * f * (3 - 2 * f)); };
function hex(c) { const n = parseInt(c.slice(1), 16); return [n >> 16 & 255, n >> 8 & 255, n & 255]; }
function mixc(a, b, k) { const x = hex(a), y = hex(b); return `rgb(${x.map((v, i) => Math.round(lerp(v, y[i], k))).join(',')})`; }
function rgba(c, a) { const x = hex(c); return `rgba(${x[0]},${x[1]},${x[2]},${a})`; }

const F_SANS = '"Noto Sans SC","WenQuanYi Zen Hei",sans-serif';
const F_SERIF = '"Noto Serif SC","Noto Sans SC",serif';
const F_FUN = '"ZCOOL KuaiLe","Noto Sans SC",sans-serif';
const F_BRUSH = '"Ma Shan Zheng","Noto Serif SC",serif';

function rr(ctx, x, y, w, h, r) {
  ctx.beginPath(); ctx.moveTo(x + r, y); ctx.arcTo(x + w, y, x + w, y + h, r); ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r); ctx.arcTo(x, y, x + w, y, r); ctx.closePath();
}
function circle(ctx, x, y, r) { ctx.beginPath(); ctx.arc(x, y, r, 0, TAU); }
function ell(ctx, x, y, rx, ry, rot = 0) { ctx.beginPath(); ctx.ellipse(x, y, Math.max(0.01, rx), Math.max(0.01, ry), rot, 0, TAU); }
function fillAll(ctx, c, a = 1) { ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.globalAlpha = a; ctx.fillStyle = c; ctx.fillRect(0, 0, W, H); ctx.restore(); }
function vgrad(ctx, y0, y1, stops) { const g = ctx.createLinearGradient(0, y0, 0, y1); stops.forEach((c, i) => g.addColorStop(i / (stops.length - 1), c)); return g; }
function glow(ctx, x, y, r, c, a = 1) {
  const g = ctx.createRadialGradient(x, y, 0, x, y, r); g.addColorStop(0, rgba(c, a)); g.addColorStop(1, rgba(c, 0));
  ctx.fillStyle = g; ctx.fillRect(x - r, y - r, 2 * r, 2 * r);
}

// offscreen layer: lets a character be tinted / silhouetted / glowed as one unit
const LAYER = document.createElement('canvas'); LAYER.width = W; LAYER.height = H;
const LX = LAYER.getContext('2d');
function layer(ctx, fn, o = {}) {
  LX.setTransform(1, 0, 0, 1, 0, 0); LX.globalAlpha = 1; LX.globalCompositeOperation = 'source-over';
  LX.clearRect(0, 0, W, H);
  LX.setTransform(ctx.getTransform());
  fn(LX);
  LX.setTransform(1, 0, 0, 1, 0, 0);
  for (const [c, a] of [[o.darkColor || '#08080e', o.dark || 0], [o.tint || '#000000', o.tintA || 0]]) {
    if (a <= 0) continue;
    LX.globalCompositeOperation = 'source-atop'; LX.globalAlpha = a; LX.fillStyle = c; LX.fillRect(0, 0, W, H);
  }
  LX.globalCompositeOperation = 'source-over'; LX.globalAlpha = 1;
  ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.globalAlpha = o.alpha ?? 1;
  if (o.glow) { ctx.shadowColor = o.glow; ctx.shadowBlur = o.glowBlur || 30; }
  ctx.drawImage(LAYER, 0, 0);
  ctx.restore();
}

// ---------------------------------------------------------------- camera / fx
function cam(ctx, cx, cy, z, ox = 0, oy = 0) { ctx.translate(W / 2 + ox, H / 2 + oy); ctx.scale(z, z); ctx.translate(-cx, -cy); }
function shake(ctx, t, amp) { if (amp <= 0) return; ctx.translate((noise1(t * 40) - 0.5) * 2 * amp, (noise1(t * 40 + 77) - 0.5) * 2 * amp); }
function vignette(ctx, a = 0.45) {
  ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0);
  const g = ctx.createRadialGradient(W / 2, H / 2, H * 0.3, W / 2, H / 2, H * 0.75);
  g.addColorStop(0, 'rgba(0,0,0,0)'); g.addColorStop(1, `rgba(0,0,0,${a})`);
  ctx.fillStyle = g; ctx.fillRect(0, 0, W, H); ctx.restore();
}
function flashAt(t, t0, k = 9) {
  if (t < t0) return 0; const d = t - t0;
  return Math.max(Math.exp(-d * k), d > 0.12 ? 0.75 * Math.exp(-(d - 0.12) * k * 0.8) : 0);
}
const RAIN = (() => { const r = rnd(11); return Array.from({ length: 320 }, () => ({ x: r() * (W + 400), y: r() * (H + 200), l: 26 + r() * 70, v: 1500 + r() * 900, a: 0.12 + r() * 0.35, w: 0.8 + r() * 1.6 })); })();
function rain(ctx, t, o = {}) {
  const ang = o.ang ?? 0.16, n = o.n ?? 240, sp = o.speed ?? 1;
  ctx.save(); ctx.lineCap = 'round'; ctx.strokeStyle = o.color || '#c4d6ff';
  for (let i = 0; i < n; i++) {
    const d = RAIN[i]; const yy = mod(d.y + t * d.v * sp, H + 200) - 100; const xx = mod(d.x - ang * (d.y + t * d.v * sp), W + 400) - 200;
    ctx.globalAlpha = d.a * (o.a ?? 1); ctx.lineWidth = d.w; ctx.beginPath(); ctx.moveTo(xx, yy); ctx.lineTo(xx + ang * d.l, yy - d.l); ctx.stroke();
  }
  ctx.restore();
}
function bolt(ctx, x0, y0, y1, seed, a) {
  const r = rnd(seed); ctx.save(); ctx.globalAlpha = a; ctx.strokeStyle = '#f2f6ff'; ctx.shadowColor = '#9fc0ff'; ctx.shadowBlur = 25;
  ctx.lineWidth = 4; ctx.beginPath(); let x = x0, y = y0; ctx.moveTo(x, y);
  while (y < y1) { x += (r() - 0.5) * 70; y += 30 + r() * 50; ctx.lineTo(x, y); }
  ctx.stroke(); ctx.lineWidth = 1.5; ctx.stroke(); ctx.restore();
}
function speedLines(ctx, cx, cy, t, o = {}) {
  const r = rnd(o.seed || 5), n = o.n || 70, rin = o.rin || 260;
  ctx.save(); ctx.fillStyle = o.color || '#000'; ctx.globalAlpha = o.a ?? 0.8;
  const jig = Math.floor(t * 12);
  for (let i = 0; i < n; i++) {
    const a = r() * TAU, w = 0.004 + r() * 0.012, k = rin * (0.75 + 0.6 * hash(i + jig * 31));
    ctx.beginPath(); ctx.moveTo(cx + Math.cos(a - w) * 1100, cy + Math.sin(a - w) * 1100);
    ctx.lineTo(cx + Math.cos(a) * k, cy + Math.sin(a) * k); ctx.lineTo(cx + Math.cos(a + w) * 1100, cy + Math.sin(a + w) * 1100); ctx.fill();
  }
  ctx.restore();
}
function vlines(ctx, t, o = {}) { // vertical motion streaks
  const r = rnd(o.seed || 9); ctx.save(); ctx.strokeStyle = o.color || '#fff'; ctx.globalAlpha = o.a ?? 0.5;
  for (let i = 0; i < (o.n || 40); i++) { const x = r() * W, l = 200 + r() * 500, y = mod(r() * H + t * (o.v ?? 3000), H + l) - l; ctx.lineWidth = 1 + r() * 3; ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x, y + l); ctx.stroke(); }
  ctx.restore();
}
function star4(ctx, x, y, r, a = 1, c = '#fff') {
  ctx.save(); ctx.globalAlpha = a; ctx.fillStyle = c; ctx.beginPath();
  ctx.moveTo(x, y - r); ctx.quadraticCurveTo(x, y, x + r, y); ctx.quadraticCurveTo(x, y, x, y + r); ctx.quadraticCurveTo(x, y, x - r, y); ctx.quadraticCurveTo(x, y, x, y - r); ctx.fill(); ctx.restore();
}
function sparkles(ctx, t, o = {}) {
  const r = rnd(o.seed || 21); const n = o.n || 18;
  for (let i = 0; i < n; i++) {
    const x = (o.x ?? 0) + r() * (o.w ?? W), y = (o.y ?? 0) + r() * (o.h ?? H), ph = r() * 10, sp = 1.5 + r() * 2.5, s = (o.size || 14) * (0.5 + r());
    const k = Math.pow(Math.max(0, Math.sin(t * sp + ph)), 3);
    if (k > 0.02) star4(ctx, x, y, s * k, k * (o.a ?? 1), o.color || '#fff');
  }
}
function bokeh(ctx, t, o = {}) {
  const r = rnd(o.seed || 33);
  ctx.save(); ctx.globalCompositeOperation = 'lighter';
  for (let i = 0; i < (o.n || 30); i++) {
    const x = (o.x ?? 0) + r() * (o.w ?? W), y = (o.y ?? 0) + r() * (o.h ?? H), rad = (o.r || 30) * (0.5 + r());
    const c = o.colors[Math.floor(r() * o.colors.length)], a = (o.a ?? 0.25) * (0.6 + 0.4 * Math.sin(t * (0.5 + r()) + i));
    glow(ctx, x + Math.sin(t * 0.3 + i) * 6, y, rad, c, a);
  }
  ctx.restore();
}
function panelFrame(ctx, r, k, from, fn, o = {}) {
  if (k <= 0) return;
  const e = eo(k); let dx = 0, dy = 0;
  if (from === 'left') dx = -(1 - e) * (W + 40); if (from === 'right') dx = (1 - e) * (W + 40);
  if (from === 'up') dy = -(1 - e) * 900; if (from === 'down') dy = (1 - e) * 900;
  ctx.save(); ctx.translate(dx, dy);
  if (from === 'fade') ctx.globalAlpha = e;
  ctx.save(); ctx.beginPath(); ctx.rect(r[0], r[1], r[2], r[3]); ctx.clip(); fn(); ctx.restore();
  ctx.lineWidth = o.border ?? 7; ctx.strokeStyle = o.borderColor || '#f6f2ea'; ctx.strokeRect(r[0], r[1], r[2], r[3]);
  ctx.restore();
}
function seal(ctx, x, y, text, a = 1) {
  ctx.save(); ctx.globalAlpha = a; ctx.translate(x, y); ctx.rotate(-0.12);
  ctx.fillStyle = '#c8202c'; rr(ctx, -62, -34, 124, 68, 10); ctx.fill();
  ctx.strokeStyle = '#fff3e0'; ctx.lineWidth = 3; rr(ctx, -54, -26, 108, 52, 6); ctx.stroke();
  ctx.fillStyle = '#fff3e0'; ctx.font = `44px ${F_BRUSH}`; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillText(text, 0, 3);
  ctx.restore();
}
function bigText(ctx, text, x, y, o = {}) {
  ctx.save(); ctx.translate(x, y); ctx.rotate(o.rot || 0); const s = o.scale ?? 1; ctx.scale(s, s);
  ctx.globalAlpha = o.a ?? 1; ctx.font = `${o.weight || ''} ${o.size || 90}px ${o.font || F_FUN}`; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  ctx.lineJoin = 'round';
  if (o.outer) { ctx.lineWidth = o.outerW || 22; ctx.strokeStyle = o.outer; ctx.strokeText(text, 0, 0); }
  if (o.stroke) { ctx.lineWidth = o.strokeW || 10; ctx.strokeStyle = o.stroke; ctx.strokeText(text, 0, 0); }
  if (o.glow) { ctx.shadowColor = o.glow; ctx.shadowBlur = o.glowBlur || 30; }
  ctx.fillStyle = o.fill || '#fff'; ctx.fillText(text, 0, 0);
  ctx.restore();
}

// ---------------------------------------------------------------- characters
const CHAR = {
  smx: { fem: true, skin: '#fde8dc', skinS: '#f0c2ad', line: '#7a4a40', hair: '#2a1e27', hairH: '#62485a', hairD: '#150e14', iris1: '#3d1f17', iris2: '#c98450', lip: '#c9606a', brow: '#3a2a2e' },
  zy: { fem: false, skin: '#f7e0d0', skinS: '#dfb19b', line: '#6b4537', hair: '#14161d', hairH: '#465170', hairD: '#07080b', iris1: '#0f141c', iris2: '#5a7aa0', lip: '#a7615c', brow: '#14161d' },
  ji: { fem: false, skin: '#fbe5d5', skinS: '#e6bba3', line: '#7a5040', hair: '#5d4232', hairH: '#9c7a5e', hairD: '#3a281d', iris1: '#3a2416', iris2: '#b07d4e', lip: '#c07a70', brow: '#4a3326' },
  dnz: { fem: false, skin: '#f6dac8', skinS: '#e0b09a', line: '#6b4537', hair: '#2b2521', hairH: '#5a4c44', hairD: '#141110', iris1: '#2a1d14', iris2: '#7a5636', lip: '#bb7369', brow: '#2b2521', glasses: true },
};
function blinkK(t, seed) {
  const p = 3.1 + hash(seed) * 1.7, x = mod(t + hash(seed + 3) * p, p);
  return x < 0.14 ? Math.abs(Math.cos(Math.PI * x / 0.14)) : 1;
}
function facePath(ctx, fem) {
  ctx.beginPath();
  if (fem) {
    ctx.moveTo(0, -128); ctx.bezierCurveTo(52, -128, 90, -96, 91, -38); ctx.bezierCurveTo(92, 8, 84, 44, 62, 76);
    ctx.bezierCurveTo(44, 100, 20, 114, 0, 117); ctx.bezierCurveTo(-20, 114, -44, 100, -62, 76);
    ctx.bezierCurveTo(-84, 44, -92, 8, -91, -38); ctx.bezierCurveTo(-90, -96, -52, -128, 0, -128);
  } else {
    ctx.moveTo(0, -132); ctx.bezierCurveTo(56, -132, 95, -98, 95, -36); ctx.bezierCurveTo(96, 10, 90, 42, 74, 72);
    ctx.bezierCurveTo(56, 100, 26, 120, 0, 123); ctx.bezierCurveTo(-26, 120, -56, 100, -74, 72);
    ctx.bezierCurveTo(-90, 42, -96, 10, -95, -36); ctx.bezierCurveTo(-95, -98, -56, -132, 0, -132);
  }
  ctx.closePath();
}
function bodyPath(ctx, k) {
  ctx.beginPath(); ctx.moveTo(-30 * k, 140);
  ctx.bezierCurveTo(-60 * k, 168, -150 * k, 172, -196 * k, 196); ctx.bezierCurveTo(-238 * k, 216, -252 * k, 262, -258 * k, 330);
  ctx.lineTo(-270 * k, 760); ctx.lineTo(270 * k, 760); ctx.lineTo(258 * k, 330);
  ctx.bezierCurveTo(252 * k, 262, 238 * k, 216, 196 * k, 196); ctx.bezierCurveTo(150 * k, 172, 60 * k, 168, 30 * k, 140); ctx.closePath();
}
function eyeShape(ctx, fem) {
  ctx.beginPath();
  if (fem) { ctx.moveTo(-21, 3); ctx.bezierCurveTo(-14, -14, 10, -19, 25, -7); ctx.bezierCurveTo(22, 8, 5, 16, -12, 13); ctx.quadraticCurveTo(-18, 10, -21, 3); }
  else { ctx.moveTo(-20, 2); ctx.bezierCurveTo(-12, -9, 10, -12, 24, -5); ctx.bezierCurveTo(20, 4, 4, 9, -12, 8); ctx.quadraticCurveTo(-17, 6, -20, 2); }
  ctx.closePath();
}
function drawEye(ctx, c, o, open, side) {
  const fem = c.fem, mode = o.eyes || 'normal', lash = '#22161a';
  ctx.lineCap = 'round'; ctx.lineJoin = 'round'; ctx.strokeStyle = lash;
  if (mode === 'happy') { ctx.lineWidth = 4.5; ctx.beginPath(); ctx.moveTo(-20, 7); ctx.quadraticCurveTo(2, -13, 24, 5); ctx.stroke(); return; }
  if (mode === 'dot') { ctx.fillStyle = lash; circle(ctx, 2, 2, 4.8); ctx.fill(); return; }
  if (mode === 'closed' || open < 0.16) {
    ctx.lineWidth = 4; ctx.beginPath(); ctx.moveTo(-21, 1); ctx.quadraticCurveTo(2, 10, 25, -2); ctx.stroke();
    if (fem) { ctx.beginPath(); ctx.moveTo(22, 0); ctx.lineTo(30, 3); ctx.stroke(); }
    return;
  }
  ctx.save(); ctx.translate(0, -2); ctx.scale(1, open); ctx.translate(0, 2);
  eyeShape(ctx, fem); ctx.fillStyle = '#fffdfb'; ctx.fill();
  ctx.save(); ctx.clip();
  const small = mode === 'wide' ? 0.62 : 1;
  const ir = fem ? [12.5 * small, 15.5 * small] : [10 * small, 11.5 * small];
  const ix = 2 + (o.lx || 0) * 7 * side, iy = (fem ? 2 : 1) + (o.ly || 0) * 4;
  const g = ctx.createLinearGradient(0, iy - ir[1], 0, iy + ir[1]);
  const i1 = o.dimEyes ? '#1a1416' : c.iris1, i2 = o.dimEyes ? mixc(c.iris2, '#30282c', 0.6) : c.iris2;
  g.addColorStop(0, i1); g.addColorStop(0.55, mixc(c.iris1, c.iris2, 0.5)); g.addColorStop(1, i2);
  ell(ctx, ix, iy, ir[0], ir[1]); ctx.fillStyle = g; ctx.fill();
  ctx.lineWidth = 1.2; ctx.strokeStyle = 'rgba(20,10,10,0.6)'; ctx.stroke();
  ell(ctx, ix, iy - 1, ir[0] * 0.45, ir[1] * 0.5); ctx.fillStyle = 'rgba(10,6,8,0.85)'; ctx.fill();
  ell(ctx, 2, -16, 34, 11); ctx.fillStyle = 'rgba(90,60,90,0.2)'; ctx.fill();
  if (!o.dimEyes) {
    ctx.fillStyle = '#fff';
    circle(ctx, ix - 4.5 * side, iy - 6, fem ? 4.3 : 3.3); ctx.fill();
    circle(ctx, ix + 4 * side, iy + 6, fem ? 2 : 1.5); ctx.fill();
    if (o.sparkle) { star4(ctx, ix + 3 * side, iy - 3, 6, 0.95); }
  }
  if (o.wet) {
    ctx.globalAlpha = 0.8 * o.wet; ctx.strokeStyle = '#fff'; ctx.lineWidth = 2;
    ctx.beginPath(); ctx.ellipse(ix, iy + 4, ir[0] * 0.8, ir[1] * 0.6, 0, 0.2, Math.PI - 0.2); ctx.stroke();
    circle(ctx, ix + 6 * side, iy - 9, 2.2); ctx.fillStyle = '#fff'; ctx.fill(); ctx.globalAlpha = 1;
  }
  ctx.restore();
  ctx.lineWidth = fem ? 4.8 : 4.3; ctx.strokeStyle = lash; ctx.beginPath();
  if (fem) { ctx.moveTo(-21, 3); ctx.bezierCurveTo(-14, -14, 10, -19, 25, -7); } else { ctx.moveTo(-20, 2); ctx.bezierCurveTo(-12, -9, 10, -12, 24, -5); }
  ctx.stroke();
  if (fem) { ctx.fillStyle = lash; ctx.beginPath(); ctx.moveTo(19, -11); ctx.lineTo(32, -14); ctx.lineTo(25, -2); ctx.fill(); }
  else { ctx.beginPath(); ctx.moveTo(20, -7); ctx.lineTo(27, -6); ctx.stroke(); }
  ctx.globalAlpha = 0.5; ctx.lineWidth = 1.4; ctx.beginPath();
  if (fem) { ctx.moveTo(6, 14); ctx.quadraticCurveTo(18, 11, 23, 3); } else { ctx.moveTo(4, 8); ctx.quadraticCurveTo(14, 7, 20, 2); }
  ctx.stroke();
  ctx.globalAlpha = 0.35; ctx.beginPath();
  if (fem) { ctx.moveTo(-13, -13); ctx.quadraticCurveTo(4, -23, 21, -15); } else { ctx.moveTo(-12, -10); ctx.quadraticCurveTo(4, -17, 20, -11); }
  ctx.stroke(); ctx.globalAlpha = 1;
  ctx.restore();
}
function features(ctx, c, o) {
  const fem = c.fem, fx = (o.turn || 0) * 12, ex = fem ? 44 : 44, ey = fem ? 14 : 12, es = fem ? 1.3 : 1.18;
  const open = (o.open ?? 1) * (o.noBlink ? 1 : blinkK(o.t || 0, o.seed || 1));
  // blush
  if (o.blush) {
    for (const s of [-1, 1]) {
      ell(ctx, fx + s * 52, 54, 22, 9); ctx.fillStyle = `rgba(255,105,120,${0.32 * o.blush})`; ctx.fill();
      ctx.strokeStyle = `rgba(230,80,100,${0.55 * o.blush})`; ctx.lineWidth = 1.6;
      for (let i = -1; i <= 1; i++) { ctx.beginPath(); ctx.moveTo(fx + s * 52 + i * 9 + 4, 49); ctx.lineTo(fx + s * 52 + i * 9 - 2, 59); ctx.stroke(); }
    }
  }
  if (o.redEyes) { for (const s of [-1, 1]) { ell(ctx, fx + s * ex, ey + 16, 32, 11); ctx.fillStyle = `rgba(235,110,120,${0.35 * o.redEyes})`; ctx.fill(); } }
  for (const side of [-1, 1]) {
    ctx.save(); ctx.translate(fx + side * ex, ey); ctx.scale(side * es, es); drawEye(ctx, c, o, open, side); ctx.restore();
    // brows
    const b = o.brow || 0;
    ctx.save(); ctx.translate(fx + side * ex, ey - (fem ? 6 : 3)); ctx.scale(side * es, es);
    ctx.strokeStyle = c.brow; ctx.lineCap = 'round'; ctx.lineWidth = fem ? 2.8 : 5;
    ctx.beginPath();
    if (fem) { ctx.moveTo(-17, -27 + 6 * b); ctx.quadraticCurveTo(4, -38 + 2 * b, 27, -29 - 2.5 * b); }
    else { ctx.moveTo(-19, -24 + 7 * b); ctx.quadraticCurveTo(2, -32 + 2 * b, 28, -28 - 3 * b); }
    ctx.stroke(); ctx.restore();
  }
  // nose
  ctx.strokeStyle = rgba('#a0604f', 0.55); ctx.lineWidth = 2.2; ctx.lineCap = 'round'; ctx.beginPath();
  const nx = fx * 1.35;
  if (fem) { ctx.moveTo(nx + 3, 47); ctx.quadraticCurveTo(nx - 1, 55, nx - 4, 57); } else { ctx.moveTo(nx + 4, 38); ctx.lineTo(nx - 1, 54); ctx.lineTo(nx + 5, 56); }
  ctx.stroke();
  mouth(ctx, c, o, fx);
  if (o.tear > 0 && o.tear < 1) {
    const k = o.tear, x = fx + ex + 8, y = lerp(ey + 20, 112, k);
    ctx.strokeStyle = 'rgba(200,230,255,0.7)'; ctx.lineWidth = 2.5; ctx.beginPath(); ctx.moveTo(fx + ex + 6, ey + 18); ctx.quadraticCurveTo(x - 2, (ey + y) / 2, x, y); ctx.stroke();
    ctx.fillStyle = 'rgba(205,235,255,0.95)'; ctx.beginPath(); ctx.moveTo(x, y - 9); ctx.quadraticCurveTo(x + 6, y + 2, x, y + 5); ctx.quadraticCurveTo(x - 6, y + 2, x, y - 9); ctx.fill();
    circle(ctx, x - 1.5, y, 1.4); ctx.fillStyle = '#fff'; ctx.fill();
  }
  if (o.glasses || c.glasses) {
    ctx.strokeStyle = '#2a2a30'; ctx.lineWidth = 3;
    for (const s of [-1, 1]) { rr(ctx, fx + s * ex - 32, ey - 21, 64, 42, 12); ctx.stroke(); }
    ctx.beginPath(); ctx.moveTo(fx - 13, ey - 6); ctx.quadraticCurveTo(fx, ey - 12, fx + 13, ey - 6); ctx.stroke();
    if (o.glint) { ctx.strokeStyle = `rgba(255,255,255,${o.glint})`; ctx.lineWidth = 5; for (const s of [-1, 1]) { ctx.beginPath(); ctx.moveTo(fx + s * ex - 14, ey + 12); ctx.lineTo(fx + s * ex + 8, ey - 14); ctx.stroke(); } }
  }
}
function mouth(ctx, c, o, fx) {
  const fem = c.fem; ctx.save(); ctx.translate(fx, fem ? 78 : 82);
  const m = o.mouth || 'neutral';
  let a = o.talk || 0; a = a > 0.12 ? 0.25 + 0.75 * a : 0;
  if (m === 'shout') a = 1.4; if (m === 'open') a = Math.max(a, 0.55); if (m === 'o') a = Math.max(a, 0.5);
  ctx.lineCap = 'round'; ctx.lineJoin = 'round';
  const dark = mixc(c.lip, '#3a1418', 0.5);
  if (a > 0) {
    const w = (fem ? 8 : 9) + 5 * a * (m === 'o' ? 0.3 : 1), h = 2 + 12 * a;
    ctx.beginPath(); ctx.moveTo(-w, 0); ctx.quadraticCurveTo(0, -h * 0.3, w, 0); ctx.quadraticCurveTo(w * 0.7, h * 1.15, 0, h * 1.15); ctx.quadraticCurveTo(-w * 0.7, h * 1.15, -w, 0);
    ctx.fillStyle = '#6e2228'; ctx.fill();
    ctx.save(); ctx.clip(); ell(ctx, 0, h * 1.05, w * 0.65, h * 0.45); ctx.fillStyle = '#d27078'; ctx.fill(); ctx.restore();
    ctx.strokeStyle = dark; ctx.lineWidth = 2; ctx.stroke();
  } else {
    ctx.strokeStyle = dark; ctx.lineWidth = 2.4; ctx.beginPath();
    if (m === 'smile') { ctx.moveTo(-14, -3); ctx.quadraticCurveTo(0, 8, 14, -3); }
    else if (m === 'bigsmile') {
      ctx.moveTo(-17, -4); ctx.quadraticCurveTo(0, 18, 17, -4); ctx.quadraticCurveTo(0, 2, -17, -4); ctx.fillStyle = '#7a2830'; ctx.fill();
      ctx.save(); ctx.clip(); ctx.fillStyle = '#fff'; ctx.fillRect(-17, -6, 34, 6); ctx.restore();
    }
    else if (m === 'smirk') { ctx.moveTo(-10, 1); ctx.quadraticCurveTo(4, 3, 15, -6); }
    else if (m === 'frown') { ctx.moveTo(-11, 4); ctx.quadraticCurveTo(0, -3, 11, 4); }
    else if (m === 'wavy') { ctx.moveTo(-12, 0); for (let i = 0; i < 4; i++) ctx.quadraticCurveTo(-9 + i * 6, i % 2 ? 4 : -4, -6 + i * 6, 0); }
    else if (m === 'tiny') { ctx.moveTo(-4, 0); ctx.lineTo(4, 0); }
    else { ctx.moveTo(-10, 0); ctx.quadraticCurveTo(0, 1.8, 10, 0); }
    ctx.stroke();
    if (fem && m !== 'bigsmile') { ctx.globalAlpha = 0.35; ell(ctx, 0, 6, 7, 2.5); ctx.fillStyle = c.lip; ctx.fill(); ctx.globalAlpha = 1; }
  }
  ctx.restore();
}
// --- hair
function hairShade(ctx, c, pathFn) {
  ctx.save(); pathFn(ctx); ctx.clip();
  ctx.strokeStyle = rgba(c.hairH.length === 7 ? c.hairH : '#ffffff', 0.55); ctx.lineWidth = 9; ctx.lineCap = 'round';
  ctx.globalAlpha = 0.6; ctx.lineWidth = 7; ctx.beginPath(); ctx.ellipse(0, -50, 82, 70, 0, -2.6, -0.55); ctx.stroke(); ctx.globalAlpha = 1;
  ctx.strokeStyle = rgba('#000000', 0.25); ctx.lineWidth = 2;
  for (let i = -4; i <= 4; i++) { ctx.beginPath(); ctx.moveTo(i * 12, -150); ctx.quadraticCurveTo(i * 22, -70, i * 20 - 6, 0); ctx.stroke(); }
  ctx.restore();
}
function bangsSMX(ctx) {
  ctx.beginPath(); ctx.moveTo(-100, 40);
  ctx.bezierCurveTo(-112, -70, -64, -148, 2, -148); ctx.bezierCurveTo(70, -148, 114, -72, 100, 40);
  ctx.quadraticCurveTo(95, 2, 86, -24); ctx.quadraticCurveTo(80, 0, 72, 16);
  ctx.quadraticCurveTo(68, -20, 54, -48); ctx.quadraticCurveTo(46, -14, 30, 0);
  ctx.quadraticCurveTo(24, -34, 12, -58); ctx.quadraticCurveTo(2, -24, -14, -6);
  ctx.quadraticCurveTo(-20, -38, -36, -56); ctx.quadraticCurveTo(-44, -20, -62, 6);
  ctx.quadraticCurveTo(-66, -24, -76, -40); ctx.quadraticCurveTo(-88, 0, -100, 40); ctx.closePath();
}
function bangsZY(ctx) {
  ctx.beginPath(); ctx.moveTo(-102, 24);
  ctx.bezierCurveTo(-116, -84, -60, -158, 4, -158); ctx.bezierCurveTo(76, -158, 118, -86, 102, 18);
  ctx.quadraticCurveTo(98, -14, 90, -32); ctx.quadraticCurveTo(88, -6, 80, 12);
  ctx.quadraticCurveTo(70, -34, 58, -62); ctx.quadraticCurveTo(50, -32, 36, -12);
  ctx.quadraticCurveTo(30, -48, 20, -68); ctx.quadraticCurveTo(8, -36, -12, 0);
  ctx.quadraticCurveTo(-18, -44, -26, -66); ctx.quadraticCurveTo(-38, -34, -58, -14);
  ctx.quadraticCurveTo(-60, -44, -66, -60); ctx.quadraticCurveTo(-80, -24, -96, 12);
  ctx.quadraticCurveTo(-100, 20, -102, 24); ctx.closePath();
}
function bangsJI(ctx) {
  ctx.beginPath(); ctx.moveTo(-102, 22);
  ctx.bezierCurveTo(-114, -86, -60, -156, 4, -154); ctx.bezierCurveTo(74, -156, 116, -84, 102, 22);
  ctx.quadraticCurveTo(98, -20, 88, -50); ctx.quadraticCurveTo(62, -74, 30, -76);
  ctx.quadraticCurveTo(18, -60, 4, -36); ctx.quadraticCurveTo(-6, -64, -22, -80);
  ctx.quadraticCurveTo(-52, -70, -72, -44); ctx.quadraticCurveTo(-84, -12, -92, 12);
  ctx.quadraticCurveTo(-98, 20, -102, 22); ctx.closePath();
}
function bangsDNZ(ctx) {
  ctx.beginPath(); ctx.moveTo(-100, 16);
  ctx.bezierCurveTo(-114, -86, -60, -152, 4, -152); ctx.bezierCurveTo(74, -152, 116, -84, 100, 14);
  ctx.lineTo(90, -36); ctx.lineTo(74, -18); ctx.lineTo(64, -56); ctx.lineTo(44, -26); ctx.lineTo(32, -62); ctx.lineTo(10, -30);
  ctx.lineTo(-2, -64); ctx.lineTo(-22, -28); ctx.lineTo(-34, -60); ctx.lineTo(-56, -26); ctx.lineTo(-66, -56); ctx.lineTo(-84, -14); ctx.lineTo(-92, -28);
  ctx.closePath();
}
const BANGS = { smx: bangsSMX, zy: bangsZY, ji: bangsJI, dnz: bangsDNZ };
function backHair(ctx, who, c, style) {
  ctx.fillStyle = c.hairD;
  if (who === 'smx' && style === 'long') {
    ctx.beginPath(); ctx.moveTo(0, -150);
    ctx.bezierCurveTo(-96, -150, -130, -80, -124, 0); ctx.bezierCurveTo(-120, 90, -146, 170, -172, 250);
    ctx.bezierCurveTo(-184, 300, -160, 370, -128, 400); ctx.lineTo(128, 400);
    ctx.bezierCurveTo(160, 370, 184, 300, 172, 250); ctx.bezierCurveTo(146, 170, 120, 90, 124, 0);
    ctx.bezierCurveTo(130, -80, 96, -150, 0, -150); ctx.fill();
  } else if (who === 'smx') {
    circle(ctx, 40, -150, 50); ctx.fill();
    ctx.beginPath(); ctx.ellipse(0, -40, 110, 115, 0, 0, TAU); ctx.fill();
  } else {
    ctx.beginPath(); ctx.moveTo(-104, 44); ctx.bezierCurveTo(-120, -80, -60, -160, 4, -158); ctx.bezierCurveTo(76, -160, 122, -80, 104, 44);
    ctx.lineTo(90, 70); ctx.lineTo(-90, 70); ctx.closePath(); ctx.fill();
  }
}
function frontHair(ctx, who, c, o) {
  const bang = BANGS[who];
  // fringe shadow on forehead
  ctx.save(); facePath(ctx, c.fem); ctx.clip(); ctx.translate(5, 12); bang(ctx); ctx.fillStyle = rgba(hexOf(c.skinS), 0.9); ctx.fill(); ctx.restore();
  bang(ctx); const g = ctx.createLinearGradient(0, -150, 0, 40); g.addColorStop(0, c.hair); g.addColorStop(1, mixc(c.hair, c.hairD, 0.6));
  ctx.fillStyle = g; ctx.fill(); ctx.strokeStyle = c.hairD; ctx.lineWidth = 2; ctx.stroke();
  hairShade(ctx, c, bang);
  if (who === 'smx' && o.hair === 'updo') {
    ctx.fillStyle = c.hair; circle(ctx, 40, -152, 44); ctx.fill(); ctx.strokeStyle = c.hairH; ctx.lineWidth = 3;
    ctx.beginPath(); ctx.arc(40, -152, 30, 3.6, 5.6); ctx.stroke();
    if (o.pin) { star4(ctx, 72, -128, 10, 1, '#fff6d0'); circle(ctx, 72, -128, 3); ctx.fillStyle = '#fff'; ctx.fill(); }
    ctx.strokeStyle = c.hair; ctx.lineWidth = 6; ctx.lineCap = 'round';
    for (const s of [-1, 1]) { ctx.beginPath(); ctx.moveTo(s * 90, -10); ctx.bezierCurveTo(s * 104, 40, s * 88, 80, s * 100, 128); ctx.stroke(); }
  }
  if (!c.fem) {
    ctx.fillStyle = c.hair;
    for (const s of [-1, 1]) { ctx.beginPath(); ctx.moveTo(s * 102, -20); ctx.lineTo(s * 97, 46); ctx.lineTo(s * 90, 30); ctx.lineTo(s * 92, -20); ctx.fill(); }
  }
}
function hexOf(c) { return c; }
function frontLocks(ctx, c) {
  ctx.fillStyle = c.hair; ctx.strokeStyle = c.hairD; ctx.lineWidth = 2;
  for (const s of [-1, 1]) {
    const L = s > 0 ? 1 : 0.85;
    ctx.beginPath(); ctx.moveTo(s * 80, -30);
    ctx.bezierCurveTo(s * 104, 40, s * 98, 120, s * 116, 200 * L);
    ctx.bezierCurveTo(s * 128, 250 * L, s * 112, 300 * L, s * 96, 340 * L);
    ctx.bezierCurveTo(s * 98, 290 * L, s * 84, 220 * L, s * 70, 150);
    ctx.bezierCurveTo(s * 62, 90, s * 70, 20, s * 64, -10); ctx.closePath(); ctx.fill(); ctx.stroke();
    ctx.strokeStyle = rgba(c.hairH, 0.5); ctx.lineWidth = 3; ctx.beginPath(); ctx.moveTo(s * 86, 20); ctx.bezierCurveTo(s * 96, 100, s * 100, 180, s * 108, 240 * L); ctx.stroke();
    ctx.strokeStyle = c.hairD; ctx.lineWidth = 2;
  }
}
function ears(ctx, c) {
  for (const s of [-1, 1]) {
    ell(ctx, s * 93, 18, 11, 22, s * 0.15); ctx.fillStyle = c.skin; ctx.fill(); ctx.strokeStyle = rgba('#a0604f', 0.4); ctx.lineWidth = 1.5; ctx.stroke();
    ctx.beginPath(); ctx.moveTo(s * 92, 6); ctx.quadraticCurveTo(s * 99, 18, s * 93, 30); ctx.stroke();
  }
}
// --- outfits
function vNeck(ctx, c, w, d) { ctx.beginPath(); ctx.moveTo(-w, 136); ctx.lineTo(0, d); ctx.lineTo(w, 136); ctx.closePath(); ctx.fillStyle = c.skin; ctx.fill();
  ctx.strokeStyle = rgba('#a0604f', 0.35); ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(-w * 0.8, 172); ctx.quadraticCurveTo(-w * 0.3, 166, -6, 176); ctx.moveTo(w * 0.8, 172); ctx.quadraticCurveTo(w * 0.3, 166, 6, 176); ctx.stroke(); }
function collar(ctx, fill, stroke) {
  for (const s of [-1, 1]) { ctx.beginPath(); ctx.moveTo(s * 22, 132); ctx.lineTo(s * 70, 158); ctx.lineTo(s * 52, 214); ctx.lineTo(s * 4, 244); ctx.lineTo(s * 18, 170); ctx.closePath(); ctx.fillStyle = fill; ctx.fill(); ctx.strokeStyle = stroke; ctx.lineWidth = 2; ctx.stroke(); }
}
function lapels(ctx, fill, stroke, k = 1) {
  for (const s of [-1, 1]) { ctx.beginPath(); ctx.moveTo(s * 34, 140); ctx.lineTo(s * 104 * k, 190); ctx.lineTo(s * 84 * k, 236); ctx.lineTo(s * 108 * k, 252); ctx.lineTo(s * 30, 420); ctx.lineTo(s * 12, 330); ctx.closePath(); ctx.fillStyle = fill; ctx.fill(); ctx.strokeStyle = stroke; ctx.lineWidth = 2; ctx.stroke(); }
}
function tie(ctx, c1, loose) {
  ctx.fillStyle = c1; ctx.beginPath();
  if (loose) { ctx.moveTo(-12, 230); ctx.lineTo(12, 230); ctx.lineTo(18, 270); ctx.lineTo(4, 520); ctx.lineTo(-14, 500); ctx.lineTo(-6, 270); }
  else { ctx.moveTo(-14, 158); ctx.lineTo(14, 158); ctx.lineTo(9, 186); ctx.lineTo(20, 420); ctx.lineTo(0, 450); ctx.lineTo(-20, 420); ctx.lineTo(-9, 186); }
  ctx.closePath(); ctx.fill(); ctx.strokeStyle = 'rgba(0,0,0,0.3)'; ctx.lineWidth = 1.5; ctx.stroke();
}
function rimLight(ctx, k, color, a) {
  ctx.save(); bodyPath(ctx, k); ctx.clip(); ctx.strokeStyle = rgba(color, a); ctx.lineWidth = 16; bodyPath(ctx, k); ctx.stroke(); ctx.restore();
}
function outfit(ctx, who, c, o) {
  const k = c.fem ? 0.8 : 1, of = o.outfit;
  const base = (col) => { bodyPath(ctx, k); ctx.fillStyle = col; ctx.fill(); ctx.strokeStyle = 'rgba(0,0,0,0.3)'; ctx.lineWidth = 2.5; ctx.stroke(); };
  if (of === 'shirt_black') {
    base('#1e2029'); vNeck(ctx, c, 28, 240); collar(ctx, '#2a2e3a', '#0b0c10');
    ctx.fillStyle = '#3a3f4e'; for (const y of [290, 380, 470]) { circle(ctx, 0, y, 5); ctx.fill(); }
  } else if (of === 'suit_black') {
    base('#15161c'); ctx.beginPath(); ctx.moveTo(-36, 138); ctx.lineTo(0, 360); ctx.lineTo(36, 138); ctx.fillStyle = '#2a2d38'; ctx.fill();
    tie(ctx, '#0a0a0e'); lapels(ctx, '#1d1f28', '#07070a');
  } else if (of === 'suit_silver') {
    base('#a3a9b4'); ctx.beginPath(); ctx.moveTo(-36, 138); ctx.lineTo(0, 360); ctx.lineTo(36, 138); ctx.fillStyle = '#ffffff'; ctx.fill();
    tie(ctx, '#7fb2da'); lapels(ctx, '#8f96a2', '#6c7380'); ctx.fillStyle = '#fff'; ctx.beginPath(); ctx.moveTo(140, 300); ctx.lineTo(196, 296); ctx.lineTo(186, 316); ctx.lineTo(150, 318); ctx.fill();
  } else if (of === 'suit_navy') {
    base('#2b3552'); ctx.beginPath(); ctx.moveTo(-36, 138); ctx.lineTo(0, 360); ctx.lineTo(36, 138); ctx.fillStyle = '#f4f4f6'; ctx.fill();
    tie(ctx, '#8c1f2f'); lapels(ctx, '#232b45', '#141a2c');
  } else if (of === 'shirt_white') {
    base('#f2f3f6'); ctx.strokeStyle = '#c8ccd6'; ctx.lineWidth = 2; bodyPath(ctx, k); ctx.stroke();
    vNeck(ctx, c, 22, 214); tie(ctx, '#24325a', true); collar(ctx, '#ffffff', '#b9bdc8');
    ctx.strokeStyle = '#d4d8e0'; ctx.beginPath(); ctx.moveTo(0, 250); ctx.lineTo(0, 760); ctx.stroke();
  } else if (of === 'hosp') {
    base('#d8e9f3'); ctx.save(); bodyPath(ctx, k); ctx.clip(); ctx.strokeStyle = '#b3d0e3'; ctx.lineWidth = 6;
    for (let x = -280; x < 280; x += 30) { ctx.beginPath(); ctx.moveTo(x, 120); ctx.lineTo(x, 760); ctx.stroke(); } ctx.restore();
    vNeck(ctx, c, 30, 220); ctx.strokeStyle = '#9fbfd3'; ctx.lineWidth = 6; ctx.beginPath(); ctx.moveTo(-30, 136); ctx.lineTo(0, 220); ctx.lineTo(30, 136); ctx.stroke();
    if (o.cast) {
      ctx.fillStyle = '#f7f7f7'; ctx.strokeStyle = '#c9c9c9'; ctx.lineWidth = 3;
      ctx.beginPath(); ctx.moveTo(-150, 190); ctx.lineTo(-110, 180); ctx.lineTo(200, 470); ctx.lineTo(170, 500); ctx.closePath(); ctx.fill(); ctx.stroke();
      rr(ctx, 20, 420, 230, 110, 40); ctx.fill(); ctx.stroke();
      ctx.beginPath(); for (let x = 60; x < 240; x += 30) { ctx.moveTo(x, 424); ctx.lineTo(x - 12, 528); } ctx.stroke();
    }
  } else if (of === 'sweater') {
    base('#ecdcc8'); vNeck(ctx, c, 30, 236);
    ctx.strokeStyle = '#d5bfa4'; ctx.lineWidth = 9; ctx.beginPath(); ctx.moveTo(-32, 134); ctx.lineTo(0, 240); ctx.lineTo(32, 134); ctx.stroke();
    ctx.save(); bodyPath(ctx, k); ctx.clip(); ctx.strokeStyle = 'rgba(160,130,100,0.18)'; ctx.lineWidth = 2;
    for (let x = -240; x < 240; x += 16) { ctx.beginPath(); for (let y = 250; y < 760; y += 12) ctx.lineTo(x + (y % 24 ? 3 : -3), y); ctx.stroke(); } ctx.restore();
  } else if (of === 'gown_black' || of === 'red') {
    const col = of === 'red' ? '#b0102a' : '#111116', hi = of === 'red' ? '#e2445c' : '#3a3a48';
    base(c.skin);
    ctx.strokeStyle = rgba('#a0604f', 0.3); ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(-90, 190); ctx.quadraticCurveTo(-40, 180, -8, 196); ctx.moveTo(90, 190); ctx.quadraticCurveTo(40, 180, 8, 196); ctx.stroke();
    ctx.strokeStyle = rgba('#b07060', 0.35); ctx.lineWidth = 3; for (const s of [-1, 1]) { ctx.beginPath(); ctx.moveTo(s * 160, 250); ctx.quadraticCurveTo(s * 150, 500, s * 158, 760); ctx.stroke(); }
    ctx.beginPath(); ctx.moveTo(-150, 304); ctx.quadraticCurveTo(-100, 290, -52, 302); ctx.quadraticCurveTo(-24, 336, 0, 318); ctx.quadraticCurveTo(24, 336, 52, 302);
    ctx.quadraticCurveTo(100, 290, 150, 304); ctx.quadraticCurveTo(142, 520, 156, 760); ctx.lineTo(-156, 760); ctx.quadraticCurveTo(-142, 520, -150, 304); ctx.closePath();
    const g = ctx.createLinearGradient(-150, 0, 150, 0); g.addColorStop(0, col); g.addColorStop(0.45, hi); g.addColorStop(0.6, col); g.addColorStop(1, mixc(col, '#000000', 0.4));
    ctx.fillStyle = g; ctx.fill();
    if (o.necklace !== false) {
      ctx.fillStyle = '#fffbea'; for (let i = 0; i <= 12; i++) { const a = i / 12; const x = lerp(-46, 46, a), y = 162 + Math.sin(a * Math.PI) * 52; circle(ctx, x, y, 3.2); ctx.fill(); }
      star4(ctx, 0, 222, 12, 0.9 + 0.1 * Math.sin((o.t || 0) * 6), '#fff');
    }
  } else if (of === 'pajama') {
    base('#f6c7d1'); vNeck(ctx, c, 26, 220); collar(ctx, '#f9d9e0', '#ffffff');
    ctx.fillStyle = '#fff'; for (const y of [290, 370, 450]) { circle(ctx, 0, y, 6); ctx.fill(); }
    ctx.save(); bodyPath(ctx, k); ctx.clip(); ctx.fillStyle = 'rgba(255,255,255,0.35)';
    for (let x = -260; x < 260; x += 46) for (let y = 260; y < 760; y += 46) { circle(ctx, x + (y % 92 ? 23 : 0), y, 5); ctx.fill(); } ctx.restore();
  }
  if (o.rim) rimLight(ctx, k, o.rim, o.rimA ?? 0.5);
}
function neck(ctx, c) {
  const nk = c.fem ? 0.8 : 1;
  ctx.beginPath(); ctx.moveTo(-27 * nk, 50); ctx.lineTo(-30 * nk, 170); ctx.lineTo(30 * nk, 170); ctx.lineTo(27 * nk, 50); ctx.closePath();
  ctx.fillStyle = c.skin; ctx.fill();
  ctx.save(); ctx.clip(); ell(ctx, 0, 112, 46, 36); ctx.fillStyle = c.skinS; ctx.fill(); ctx.restore();
}
function headXf(ctx, o) { ctx.translate(0, 110); ctx.rotate(o.tilt || 0); ctx.translate((o.turn || 0) * 6, -110 + (o.hy || 0)); }
function bust(ctx, who, o) {
  const c = CHAR[who], t = o.t || 0;
  const style = o.hair || (who === 'smx' ? 'long' : 'short');
  ctx.save();
  ctx.translate(o.x, o.y + Math.sin(t * 1.7 + (o.seed || 0)) * 2.2); ctx.scale((o.s || 1) * (o.flip ? -1 : 1), o.s || 1);
  ctx.save(); headXf(ctx, o); backHair(ctx, who, c, style); ctx.restore();
  neck(ctx, c);
  outfit(ctx, who, c, o);
  ctx.save(); headXf(ctx, o);
  if (!c.fem || style === 'updo') ears(ctx, c);
  if (o.earring) { for (const s of [-1, 1]) { ctx.fillStyle = '#f4d27a'; circle(ctx, s * 90, 50, 5); ctx.fill(); ell(ctx, s * 90, 66, 4, 9); ctx.fill(); } }
  facePath(ctx, c.fem); ctx.fillStyle = c.skin; ctx.fill();
  ctx.save(); facePath(ctx, c.fem); ctx.clip(); { const g = ctx.createRadialGradient(0, -10, 60, 0, 10, 130); g.addColorStop(0, rgba('#d89c86', 0)); g.addColorStop(1, rgba('#d89c86', 0.35)); ctx.fillStyle = g; ctx.fillRect(-110, -140, 220, 270); } ctx.restore();
  facePath(ctx, c.fem); ctx.strokeStyle = rgba(c.line.length === 7 ? c.line : '#6b4537', 0.55); ctx.lineWidth = 2; ctx.stroke();
  if (o.pale) { facePath(ctx, c.fem); ctx.fillStyle = `rgba(175,200,235,${0.35 * o.pale})`; ctx.fill(); }
  if (o.gloom) {
    ctx.save(); facePath(ctx, c.fem); ctx.clip(); ctx.strokeStyle = 'rgba(70,60,140,0.55)'; ctx.lineWidth = 3;
    for (let x = -80; x <= 80; x += 11) { ctx.beginPath(); ctx.moveTo(x, -130); ctx.lineTo(x, -130 + 90 + hash(x) * 50); ctx.stroke(); } ctx.restore();
  }
  if (o.bandage) { ctx.save(); ctx.rotate(-0.25); ctx.fillStyle = '#fff6ea'; rr(ctx, 10, -86, 46, 18, 5); ctx.fill(); ctx.strokeStyle = '#e8d6c0'; ctx.lineWidth = 1.5; ctx.stroke(); ctx.restore(); }
  features(ctx, c, o);
  frontHair(ctx, who, c, o);
  if (o.vein) {
    ctx.save(); ctx.translate(64, -96); ctx.scale(o.vein, o.vein); ctx.strokeStyle = '#e8283c'; ctx.lineWidth = 6; ctx.lineCap = 'round';
    for (let i = 0; i < 4; i++) { ctx.rotate(Math.PI / 2); ctx.beginPath(); ctx.moveTo(6, -16); ctx.quadraticCurveTo(6, -6, 16, -6); ctx.stroke(); } ctx.restore();
  }
  if (o.sweat) {
    const sy = -40 + (o.sweatY || 0);
    ctx.fillStyle = '#bfe3ff'; ctx.strokeStyle = '#4a8cc8'; ctx.lineWidth = 3;
    ctx.beginPath(); ctx.moveTo(112, sy - 30); ctx.quadraticCurveTo(130, sy + 4, 112, sy + 10); ctx.quadraticCurveTo(94, sy + 4, 112, sy - 30); ctx.fill(); ctx.stroke();
  }
  ctx.restore();
  if (style === 'long' && who === 'smx') { ctx.save(); headXf(ctx, o); frontLocks(ctx, c); ctx.restore(); }
  ctx.restore();
}

// --- full-body figures (mostly read as silhouettes in wide shots)
function figure(ctx, who, o) {
  const c = CHAR[who] || CHAR.zy, k = o.h / 760, t = o.t || 0;
  ctx.save(); ctx.translate(o.x, o.y); ctx.scale(k * (o.flip ? -1 : 1), k); ctx.rotate(o.rot || 0);
  const walk = o.walk ? Math.sin(t * o.walk * TAU) : 0, bob = o.walk ? Math.abs(Math.cos(t * o.walk * TAU)) * 8 : 0;
  ctx.translate(0, -bob);
  const skin = c.skin, hair = o.hairColor || c.hair, back = o.back;
  const kind = o.kind || (c.fem ? 'gown' : 'suit');
  if (kind === 'gown' || kind === 'skirt') {
    const col = o.color || '#111116';
    ctx.lineCap = 'round'; ctx.strokeStyle = o.armColor || skin; ctx.lineWidth = 20;
    for (const s of [-1, 1]) { ctx.beginPath(); ctx.moveTo(s * 64, -598); ctx.quadraticCurveTo(s * (86 + walk * 6 * s), -480, s * 76, -372); ctx.stroke(); }
    if (o.hairLong || back) { ctx.fillStyle = hair; ctx.beginPath(); ctx.moveTo(-56, -720); ctx.quadraticCurveTo(-74, -560, -60, -470); ctx.lineTo(60, -470); ctx.quadraticCurveTo(74, -560, 56, -720); ctx.fill(); }
    ctx.fillStyle = col; ctx.beginPath(); ctx.moveTo(-60, -590); ctx.lineTo(60, -590);
    ctx.bezierCurveTo(70, -480, 58, -410, 52, -360); ctx.bezierCurveTo(90 + walk * 10, -200, 130 + walk * 14, -60, 150 + walk * 16, 0);
    ctx.lineTo(-150 + walk * 16, 0); ctx.bezierCurveTo(-130 + walk * 14, -60, -90 + walk * 10, -200, -52, -360);
    ctx.bezierCurveTo(-58, -410, -70, -480, -60, -590); ctx.closePath(); ctx.fill();
    if (kind === 'gown') { ctx.fillStyle = skin; ctx.beginPath(); ctx.moveTo(-64, -600); ctx.quadraticCurveTo(0, -630, 64, -600); ctx.lineTo(60, -585); ctx.quadraticCurveTo(0, -600, -60, -585); ctx.fill(); }
    ctx.fillStyle = skin; ctx.fillRect(-13, -662, 26, 64);
  } else if (kind === 'girl') {
    ctx.strokeStyle = skin; ctx.lineWidth = 22; ctx.lineCap = 'round';
    for (const s of [-1, 1]) { ctx.beginPath(); ctx.moveTo(s * 28, -260); ctx.lineTo(s * 30, -10); ctx.stroke(); }
    ctx.fillStyle = o.color || '#f08aa8'; ctx.beginPath(); ctx.moveTo(-50, -560); ctx.lineTo(50, -560); ctx.lineTo(110, -230); ctx.lineTo(-110, -230); ctx.closePath(); ctx.fill();
    ctx.fillStyle = skin; ctx.fillRect(-12, -610, 24, 60);
  } else {
    const jc = o.color || '#15161c', pc = o.pants || mixc(jc, '#000000', 0.25);
    ctx.lineCap = 'round';
    for (const s of [-1, 1]) { const sw = walk * s * 0.22; ctx.save(); ctx.translate(s * 22, -300); ctx.rotate(sw); ctx.strokeStyle = pc; ctx.lineWidth = 40; ctx.beginPath(); ctx.moveTo(0, 0); ctx.lineTo(0, 280); ctx.stroke();
      ctx.fillStyle = '#0a0a0c'; ell(ctx, 6 * s, 296, 28, 12); ctx.fill(); ctx.restore(); }
    ctx.strokeStyle = jc; ctx.lineWidth = 34;
    for (const s of [-1, 1]) { const sw = -walk * s * 0.2; ctx.save(); ctx.translate(s * 74, -590); ctx.rotate(sw + (o.armUp && s > 0 ? -2.2 : 0)); ctx.beginPath(); ctx.moveTo(0, 0); ctx.lineTo(6 * s, 250); ctx.stroke();
      ctx.fillStyle = skin; circle(ctx, 6 * s, 270, 16); ctx.fill(); ctx.restore(); }
    ctx.fillStyle = jc; ctx.beginPath(); ctx.moveTo(-84, -600); ctx.quadraticCurveTo(0, -630, 84, -600); ctx.lineTo(58, -290); ctx.lineTo(-58, -290); ctx.closePath(); ctx.fill();
    if (!back) { ctx.fillStyle = o.shirt || '#e9ecf2'; ctx.beginPath(); ctx.moveTo(-22, -616); ctx.lineTo(0, -480); ctx.lineTo(22, -616); ctx.fill(); }
    ctx.fillStyle = skin; ctx.fillRect(-14, -662, 28, 52);
  }
  // head
  const hy = kind === 'girl' ? -650 : -712, hr = kind === 'girl' ? 46 : 46;
  if (back) {
    ell(ctx, 0, hy, hr, hr * 1.12); ctx.fillStyle = hair; ctx.fill();
  } else {
    ell(ctx, 0, hy, hr * 0.92, hr * 1.1); ctx.fillStyle = skin; ctx.fill();
    ctx.fillStyle = hair; ctx.beginPath(); ctx.ellipse(0, hy - 10, hr * 1.02, hr * 1.02, 0, Math.PI * 1.02, Math.PI * 1.98); ctx.lineTo(hr * 0.9, hy + 14); ctx.lineTo(hr * 0.5, hy - 18); ctx.lineTo(-hr * 0.6, hy - 14); ctx.lineTo(-hr * 0.95, hy + 16); ctx.closePath(); ctx.fill();
    if (o.updo) { circle(ctx, 0, hy - hr - 12, 24); ctx.fill(); }
    if (kind === 'girl') { circle(ctx, -hr - 8, hy + 6, 18); ctx.fill(); circle(ctx, hr + 8, hy + 6, 18); ctx.fill(); }
    if (o.white) { ctx.fillStyle = '#eceae4'; ctx.beginPath(); ctx.ellipse(0, hy - 14, hr * 1.02, hr * 0.9, 0, Math.PI, TAU); ctx.fill(); ell(ctx, 0, hy + 22, 18, 5); ctx.fill(); }
    ctx.fillStyle = '#1a1214'; for (const s of [-1, 1]) { ell(ctx, s * 16, hy + 4, 4, o.eyesClosed ? 1.2 : 5.5); ctx.fill(); }
    ctx.strokeStyle = '#8a4a46'; ctx.lineWidth = 2.5; ctx.beginPath(); ctx.moveTo(-6, hy + 28); ctx.quadraticCurveTo(0, hy + (o.smile ? 33 : 29), 6, hy + 28); ctx.stroke();
  }
  ctx.restore();
}
