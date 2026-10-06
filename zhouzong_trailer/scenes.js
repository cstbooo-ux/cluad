'use strict';
// =============================================================== props & backgrounds
function hand(ctx, x, y, rot, s, o = {}) {
  ctx.save(); ctx.translate(x, y); ctx.rotate(rot); ctx.scale(s, s);
  ctx.fillStyle = o.sleeve || '#1e2029'; ctx.fillRect(-48, 44, 96, 460);
  if (o.cuff) { ctx.fillStyle = o.cuff; ctx.fillRect(-50, 36, 100, 24); }
  const skin = o.skin || '#f7e0d0'; ctx.fillStyle = skin;
  rr(ctx, -42, -40, 84, 88, 28); ctx.fill();
  for (let i = 0; i < 4; i++) { rr(ctx, -40 + i * 21, -98 + Math.abs(i - 1.5) * 9, 18, 70, 9); ctx.fill(); }
  ctx.save(); ctx.translate(-38, 4); ctx.rotate(-0.75); rr(ctx, -11, -54, 22, 60, 10); ctx.fill(); ctx.restore();
  ctx.strokeStyle = 'rgba(150,90,70,0.35)'; ctx.lineWidth = 2;
  for (let i = 1; i < 4; i++) { ctx.beginPath(); ctx.moveTo(-40 + i * 21 - 1.5, -40); ctx.lineTo(-40 + i * 21 - 1.5, -70 + Math.abs(i - 1.5) * 9); ctx.stroke(); }
  ctx.restore();
}
function scribblePt(u, x0, y0, w, seed) {
  return [x0 + w * u + 14 * Math.sin(u * Math.PI * (8 + seed % 3)), y0 - 18 * Math.sin(u * Math.PI * (5 + seed % 2)) * (1 - 0.4 * u) + 7 * Math.cos(u * Math.PI * 13)];
}
function scribble(ctx, x0, y0, p, w, seed) {
  if (p <= 0) return;
  ctx.save(); ctx.strokeStyle = '#1b2f6b'; ctx.lineWidth = 3.2; ctx.lineCap = 'round'; ctx.lineJoin = 'round'; ctx.beginPath();
  const n = 90; for (let i = 0; i <= n * p; i++) { const [x, y] = scribblePt(i / n, x0, y0, w, seed); i ? ctx.lineTo(x, y) : ctx.moveTo(x, y); }
  ctx.stroke(); ctx.restore();
}
function paper(ctx, x, y, rot, sign = 0) {
  ctx.save(); ctx.translate(x, y); ctx.rotate(rot);
  ctx.shadowColor = 'rgba(0,0,0,0.55)'; ctx.shadowBlur = 34; ctx.shadowOffsetY = 12; ctx.fillStyle = '#f7f4ee'; ctx.fillRect(-240, -340, 480, 680);
  ctx.shadowBlur = 0; ctx.shadowOffsetY = 0;
  ctx.fillStyle = '#1c1c1c'; ctx.font = `900 50px ${F_SERIF}`; ctx.textAlign = 'center'; ctx.textBaseline = 'alphabetic'; ctx.fillText('离婚协议书', 0, -250);
  ctx.fillStyle = '#cfcac0'; for (let i = 0; i < 10; i++) ctx.fillRect(-190, -190 + i * 32, i % 3 === 2 ? 240 : 380, 10);
  ctx.fillStyle = '#333'; ctx.font = `600 26px ${F_SERIF}`; ctx.textAlign = 'left';
  ctx.fillText('男方：', -190, 200); ctx.fillText('女方：', -190, 270);
  ctx.fillRect(-112, 208, 170, 2); ctx.fillRect(-112, 278, 170, 2);
  scribble(ctx, -104, 262, 1, 150, 3);
  scribble(ctx, -104, 192, sign, 160, 8);
  ctx.restore();
}
function bgDesk(ctx, t) {
  ctx.fillStyle = vgrad(ctx, 0, H, ['#2b1b11', '#3a2618', '#22150d']); ctx.fillRect(0, 0, W, H);
  const r = rnd(17); ctx.strokeStyle = 'rgba(0,0,0,0.2)'; ctx.lineWidth = 2;
  for (let i = 0; i < 40; i++) { const y = r() * H; ctx.beginPath(); for (let x = 0; x <= W; x += 40) ctx.lineTo(x, y + Math.sin(x * 0.01 + i) * 8); ctx.stroke(); }
  glow(ctx, 620, 160, 640, '#ffb46a', 0.3);
  ctx.save(); ctx.globalAlpha = 0.25; rain(ctx, t * 0.25, { n: 70, color: '#000000', ang: 0.1 }); ctx.restore();
  ell(ctx, 600, 230, 72, 46); ctx.fillStyle = '#1a1a1e'; ctx.fill(); ell(ctx, 600, 226, 54, 32); ctx.fillStyle = '#0c0c0e'; ctx.fill();
  ctx.save(); ctx.translate(560, 222); ctx.rotate(-0.4); ctx.fillStyle = '#f2efe8'; ctx.fillRect(0, -5, 72, 10); ctx.fillStyle = '#d79a5a'; ctx.fillRect(52, -5, 20, 10); ctx.restore();
}
function bgStudy(ctx, t, o = {}) {
  const fl = o.flash || 0;
  ctx.fillStyle = vgrad(ctx, 0, H, ['#0e1526', '#080b14']); ctx.fillRect(0, 0, W, H);
  const wx = o.wx ?? 60, wy = o.wy ?? 230, ww = o.ww ?? 600, wh = o.wh ?? 800;
  ctx.save(); ctx.beginPath(); ctx.rect(wx, wy, ww, wh); ctx.clip();
  ctx.fillStyle = vgrad(ctx, wy, wy + wh, ['#18263f', '#0c1426', '#111b31']); ctx.fillRect(wx, wy, ww, wh);
  const r = rnd(8);
  for (let i = 0; i < 11; i++) {
    const bx = wx + r() * ww - 40, bw = 40 + r() * 80, bh = wh * (0.25 + r() * 0.5);
    ctx.fillStyle = '#0a1120'; ctx.fillRect(bx, wy + wh - bh, bw, bh); ctx.fillStyle = 'rgba(255,210,140,0.35)';
    for (let j = 0; j < 18; j++) if (r() < 0.45) ctx.fillRect(bx + 6 + (j % 3) * (bw - 12) / 3, wy + wh - bh + 14 + Math.floor(j / 3) * 30, 6, 10);
  }
  bokeh(ctx, t, { n: 26, x: wx, y: wy + wh * 0.3, w: ww, h: wh * 0.7, r: 26, colors: ['#ffb45a', '#ffd28a', '#7fb2ff', '#ff7a5a'], a: 0.25, seed: 4 });
  if (fl > 0) { ctx.fillStyle = `rgba(200,220,255,${0.75 * fl})`; ctx.fillRect(wx, wy, ww, wh); if (o.bolt) bolt(ctx, wx + ww * 0.62, wy, wy + wh * 0.7, o.bolt, fl); }
  rain(ctx, t, { n: 170, a: 0.8 });
  const d = rnd(13); ctx.fillStyle = 'rgba(200,220,255,0.28)';
  for (let i = 0; i < 60; i++) {
    const x = wx + d() * ww, y0 = wy + d() * wh, sp = d() < 0.3 ? 60 + d() * 140 : 0, y = sp ? wy + mod(y0 - wy + t * sp, wh) : y0;
    ell(ctx, x, y, 2 + d() * 3, 3 + d() * 4); ctx.fill(); if (sp) ctx.fillRect(x - 0.7, y - 40, 1.4, 40);
  }
  ctx.restore();
  ctx.fillStyle = '#05070c'; for (const k of [1 / 3, 2 / 3]) ctx.fillRect(wx + ww * k - 6, wy, 12, wh); ctx.fillRect(wx, wy + wh * 0.62, ww, 10);
  ctx.strokeStyle = '#05070c'; ctx.lineWidth = 18; ctx.strokeRect(wx, wy, ww, wh);
  ctx.fillStyle = vgrad(ctx, wy + wh, H, ['#0a0e18', '#05070c']); ctx.fillRect(0, wy + wh + 9, W, H);
  ctx.fillStyle = `rgba(120,150,210,${0.07 + 0.25 * fl})`; ctx.beginPath(); ctx.moveTo(wx, wy + wh + 9); ctx.lineTo(wx + ww, wy + wh + 9); ctx.lineTo(wx + ww + 120, H); ctx.lineTo(wx - 120, H); ctx.fill();
  if (fl > 0) fillAll(ctx, '#b8cfff', 0.16 * fl);
}
function chandelier(ctx, x, y, s, t) {
  glow(ctx, x, y + 70 * s, 240 * s, '#ffd79a', 0.45);
  ctx.save(); ctx.translate(x, y); ctx.scale(s, s);
  ctx.strokeStyle = 'rgba(255,232,190,0.8)'; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(0, -200); ctx.lineTo(0, 20); ctx.stroke();
  for (let k = 0; k < 3; k++) {
    const rx = 90 - k * 26, ry = 18 - k * 4, yy = 40 + k * 34; ell(ctx, 0, yy, rx, ry); ctx.stroke();
    for (let i = 0; i < 14 - k * 3; i++) { const a = i / (14 - k * 3) * TAU; const px = Math.cos(a) * rx, py = yy + Math.sin(a) * ry; ell(ctx, px, py + 10, 3, 7); ctx.fillStyle = 'rgba(255,245,220,0.85)'; ctx.fill(); }
  }
  ctx.restore();
  sparkles(ctx, t, { x: x - 100 * s, y: y + 10, w: 200 * s, h: 130 * s, n: 10, size: 12, seed: Math.round(x) });
}
function crowd(ctx, t, y, s, color, seed = 1) {
  const r = rnd(seed); ctx.fillStyle = color;
  for (let i = 0; i < 11; i++) {
    const x = -60 + i * 80 + r() * 30, sc = s * (0.85 + r() * 0.3), b = Math.sin(t * 2 + i) * 2;
    ell(ctx, x, y - 92 * sc + b, 30 * sc, 36 * sc); ctx.fill(); ell(ctx, x, y + b, 74 * sc, 60 * sc); ctx.fill();
    if (r() < 0.3) { ctx.strokeStyle = color; ctx.lineWidth = 8 * sc; ctx.beginPath(); ctx.moveTo(x + 50 * sc, y - 20 * sc); ctx.lineTo(x + 70 * sc, y - 110 * sc); ctx.stroke(); }
  }
}
function bgBanquet(ctx, t, o = {}) {
  ctx.fillStyle = vgrad(ctx, 0, H, ['#4a2c14', '#2a1709', '#1a0e06']); ctx.fillRect(0, 0, W, H);
  ctx.fillStyle = 'rgba(255,214,150,0.07)';
  for (const x of [120, 360, 600]) { ctx.beginPath(); ctx.moveTo(x - 80, 900); ctx.lineTo(x - 80, 340); ctx.arc(x, 340, 80, Math.PI, 0); ctx.lineTo(x + 80, 900); ctx.fill(); }
  ctx.strokeStyle = 'rgba(255,214,150,0.12)'; ctx.lineWidth = 3; for (const x of [0, 240, 480, 720]) { ctx.beginPath(); ctx.moveTo(x, 200); ctx.lineTo(x, 900); ctx.stroke(); }
  chandelier(ctx, 160, 80, 1, t); chandelier(ctx, 560, 60, 1.2, t);
  bokeh(ctx, t, { n: 40, colors: ['#ffd28a', '#ffb45a', '#fff0c8'], r: 22, a: 0.3, seed: 12, h: 760 });
  if (!o.noCrowd) { crowd(ctx, t, 860, 0.9, '#160c06', 3); crowd(ctx, t, 1010, 1.1, '#0c0703', 5); }
  if (o.dim) fillAll(ctx, '#020104', o.dim);
}
function bgGarage(ctx, t) {
  ctx.fillStyle = vgrad(ctx, 0, H, ['#3d4653', '#2c333d', '#1d2229']); ctx.fillRect(0, 0, W, H);
  const r = rnd(5); for (let i = 0; i < 40; i++) { ell(ctx, r() * W, r() * H, 20 + r() * 80, 10 + r() * 50); ctx.fillStyle = `rgba(0,0,0,${0.03 + r() * 0.05})`; ctx.fill(); }
  ctx.strokeStyle = 'rgba(0,0,0,0.3)'; ctx.lineWidth = 3;
  for (const y of [330, 760, 1180]) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke(); }
  for (const x of [250, 500]) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke(); }
  ctx.font = `900 200px ${F_SANS}`; ctx.fillStyle = 'rgba(230,190,60,0.16)'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillText('B2', 590, 1060);
  const fk = 0.85 + 0.15 * (noise1(t * 9) > 0.3 ? 1 : 0.3);
  glow(ctx, 360, 60, 420, '#dff2ff', 0.35 * fk); ctx.fillStyle = `rgba(240,250,255,${fk})`; rr(ctx, 150, 46, 420, 18, 9); ctx.fill();
}
function flames(ctx, t, k, o = {}) {
  if (k <= 0) return;
  const y0 = o.y ?? H, n = o.n || 16, x0 = o.x ?? -20, w = o.w ?? W + 40;
  ctx.save(); ctx.globalCompositeOperation = 'lighter';
  for (let i = 0; i < n; i++) {
    const x = x0 + (i + 0.5) / n * w + (noise1(i * 3.1 + t * 0.7) - 0.5) * 30;
    const h = (o.h || 260) * k * (0.45 + 0.8 * noise1(t * 2.4 + i * 1.7)), sw = Math.sin(t * 6 + i) * 18, bw = w / n * 0.9;
    const g = ctx.createLinearGradient(0, y0, 0, y0 - h);
    g.addColorStop(0, 'rgba(255,240,170,0.9)'); g.addColorStop(0.3, 'rgba(255,170,50,0.75)'); g.addColorStop(0.7, 'rgba(230,60,20,0.45)'); g.addColorStop(1, 'rgba(160,20,10,0)');
    ctx.fillStyle = g; ctx.beginPath(); ctx.moveTo(x - bw, y0); ctx.bezierCurveTo(x - bw, y0 - h * 0.5, x + sw - bw * 0.3, y0 - h * 0.7, x + sw, y0 - h);
    ctx.bezierCurveTo(x + sw + bw * 0.3, y0 - h * 0.7, x + bw, y0 - h * 0.5, x + bw, y0); ctx.fill();
  }
  const r = rnd(o.seed || 77); ctx.fillStyle = '#ffb050';
  for (let i = 0; i < 40; i++) { const sp = 120 + r() * 200, x = r() * W + Math.sin(t * 2 + i) * 20, y = y0 - mod(r() * 900 + t * sp, 900); circle(ctx, x, y, 1.5 + r() * 2.5); ctx.globalAlpha = k * (0.4 + r() * 0.6); ctx.fill(); }
  ctx.restore();
}
function bgHospital(ctx, t) {
  ctx.fillStyle = vgrad(ctx, 0, H, ['#e6f0f3', '#cfdee5']); ctx.fillRect(0, 0, W, H);
  ctx.fillStyle = '#f8fbfc'; ctx.fillRect(20, 100, 260, 560);
  ctx.fillStyle = '#dfe8ec'; for (let y = 110; y < 650; y += 26) ctx.fillRect(26, y, 248, 14);
  ctx.save(); ctx.globalCompositeOperation = 'lighter'; ctx.fillStyle = 'rgba(255,240,200,0.18)';
  for (let i = 0; i < 5; i++) { ctx.beginPath(); ctx.moveTo(30 + i * 50, 120); ctx.lineTo(70 + i * 50, 120); ctx.lineTo(460 + i * 60, 1280); ctx.lineTo(380 + i * 60, 1280); ctx.fill(); } ctx.restore();
  ctx.strokeStyle = '#9aa8b0'; ctx.lineWidth = 6; ctx.beginPath(); ctx.moveTo(640, 80); ctx.lineTo(640, 1280); ctx.stroke();
  ctx.fillStyle = 'rgba(220,240,255,0.85)'; rr(ctx, 600, 110, 80, 120, 20); ctx.fill(); ctx.strokeStyle = '#a5b8c4'; ctx.lineWidth = 2; ctx.stroke();
  ctx.fillStyle = '#1b2228'; rr(ctx, 470, 300, 150, 110, 10); ctx.fill();
  ctx.strokeStyle = '#4cf08a'; ctx.lineWidth = 2.5; ctx.beginPath();
  for (let x = 0; x <= 130; x += 2) { const u = mod(x / 130 - t * 0.6, 1); const y = u > 0.45 && u < 0.5 ? -26 : u > 0.5 && u < 0.53 ? 14 : 0; ctx.lineTo(480 + x, 360 + y); } ctx.stroke();
}
function pillow(ctx) { ctx.fillStyle = '#f9fbfc'; rr(ctx, 120, 300, 520, 620, 120); ctx.fill(); ctx.strokeStyle = '#d7e2e8'; ctx.lineWidth = 3; ctx.stroke(); }
function sheet(ctx, y) {
  ctx.fillStyle = '#f4f8fa'; ctx.beginPath(); ctx.moveTo(-20, y + 30); ctx.quadraticCurveTo(360, y - 30, 740, y + 20); ctx.lineTo(740, H); ctx.lineTo(-20, H); ctx.fill();
  ctx.strokeStyle = '#d3dee5'; ctx.lineWidth = 3; for (let i = 0; i < 5; i++) { ctx.beginPath(); ctx.moveTo(60 + i * 130, y + 60); ctx.quadraticCurveTo(100 + i * 130, y + 160, 80 + i * 130, H); ctx.stroke(); }
}
function bgCorridor(ctx, t) {
  const vx = 360, vy = 470;
  ctx.fillStyle = '#c9d6d2'; ctx.fillRect(0, 0, W, H);
  ctx.fillStyle = '#e4ecea'; ctx.beginPath(); ctx.moveTo(0, 0); ctx.lineTo(W, 0); ctx.lineTo(vx + 60, vy - 70); ctx.lineTo(vx - 60, vy - 70); ctx.fill();
  ctx.fillStyle = '#b7c6c1'; ctx.beginPath(); ctx.moveTo(0, 0); ctx.lineTo(vx - 60, vy - 70); ctx.lineTo(vx - 60, vy + 60); ctx.lineTo(0, H); ctx.fill();
  ctx.fillStyle = '#aebfba'; ctx.beginPath(); ctx.moveTo(W, 0); ctx.lineTo(vx + 60, vy - 70); ctx.lineTo(vx + 60, vy + 60); ctx.lineTo(W, H); ctx.fill();
  ctx.fillStyle = vgrad(ctx, vy, H, ['#c4ccc9', '#dfe5e3']); ctx.beginPath(); ctx.moveTo(vx - 60, vy + 60); ctx.lineTo(vx + 60, vy + 60); ctx.lineTo(W + 300, H); ctx.lineTo(-300, H); ctx.fill();
  ctx.fillStyle = '#e8eeec'; ctx.fillRect(vx - 60, vy - 70, 120, 130);
  ctx.fillStyle = 'rgba(255,255,250,0.9)';
  for (let i = 0; i < 5; i++) { const k = Math.pow(0.62, i), w = 260 * k, y = vy - 70 - 380 * k; ctx.fillRect(vx - w / 2, y, w, 30 * k); }
  ctx.strokeStyle = '#8fa29c'; ctx.lineWidth = 4; for (const s of [-1, 1]) { ctx.beginPath(); ctx.moveTo(vx + s * 60, vy + 10); ctx.lineTo(s > 0 ? W : 0, 820); ctx.stroke(); }
  ctx.fillStyle = '#8a7660'; ctx.beginPath(); ctx.moveTo(40, 300); ctx.lineTo(200, 380); ctx.lineTo(200, 640); ctx.lineTo(40, 760); ctx.fill();
  ctx.fillStyle = 'rgba(255,214,150,0.9)'; ctx.beginPath(); ctx.moveTo(90, 360); ctx.lineTo(160, 395); ctx.lineTo(160, 470); ctx.lineTo(90, 450); ctx.fill();
}
function bgParis(ctx, t) {
  ctx.fillStyle = vgrad(ctx, 0, H, ['#100a28', '#2a1650', '#6a2d5a', '#c0556a']); ctx.fillRect(0, 0, W, H);
  sparkles(ctx, t, { n: 60, h: 700, size: 5, seed: 3, a: 0.9 });
  glow(ctx, 560, 220, 120, '#fff4d8', 0.6); circle(ctx, 560, 220, 34); ctx.fillStyle = '#fff6e0'; ctx.fill();
  ctx.save(); ctx.translate(360, 1130); const s = 0.86; ctx.scale(s, s);
  ctx.fillStyle = '#0d0a1c'; ctx.beginPath(); ctx.moveTo(-260, 0); ctx.quadraticCurveTo(-120, -260, -70, -420); ctx.lineTo(-40, -700); ctx.lineTo(-12, -960); ctx.lineTo(0, -1010);
  ctx.lineTo(12, -960); ctx.lineTo(40, -700); ctx.lineTo(70, -420); ctx.quadraticCurveTo(120, -260, 260, 0); ctx.lineTo(170, 0); ctx.quadraticCurveTo(60, -220, 0, -230); ctx.quadraticCurveTo(-60, -220, -170, 0); ctx.closePath(); ctx.fill();
  ctx.fillRect(-110, -430, 220, 22); ctx.fillRect(-58, -710, 116, 16);
  ctx.strokeStyle = 'rgba(255,200,120,0.35)'; ctx.lineWidth = 2; ctx.beginPath();
  for (let y = -40; y > -900; y -= 46) { const w = y > -420 ? lerp(220, 70, -y / 420) : lerp(64, 12, (-y - 420) / 540); ctx.moveTo(-w, y); ctx.lineTo(w, y - 46); ctx.moveTo(w, y); ctx.lineTo(-w, y - 46); }
  ctx.stroke(); ctx.restore();
  sparkles(ctx, t * 2, { x: 250, y: 280, w: 220, h: 820, n: 40, size: 9, color: '#fff2c0', seed: 8 });
  const r = rnd(2); for (let i = 0; i < 18; i++) { const bx = i * 42 - 10, bh = 80 + r() * 140; ctx.fillStyle = '#0a0716'; ctx.fillRect(bx, H - bh, 44, bh); ctx.fillStyle = 'rgba(255,200,120,0.5)'; for (let j = 0; j < 6; j++) if (r() < 0.5) ctx.fillRect(bx + 8 + (j % 2) * 18, H - bh + 14 + Math.floor(j / 2) * 26, 7, 10); }
}
function bgStageGala(ctx, t) {
  ctx.fillStyle = vgrad(ctx, 0, H, ['#0b1030', '#060818']); ctx.fillRect(0, 0, W, H);
  glow(ctx, 360, 420, 520, '#ffcc66', 0.35);
  ctx.strokeStyle = 'rgba(255,214,130,0.5)'; ctx.lineWidth = 3; ctx.strokeRect(50, 120, 620, 560);
  ctx.fillStyle = 'rgba(255,224,160,0.85)'; ctx.font = `900 46px ${F_SERIF}`; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillText('国际珠宝设计金奖', 360, 190);
  ctx.save(); ctx.globalCompositeOperation = 'lighter';
  for (const [x0, ph] of [[60, 0], [660, 2]]) {
    const a = Math.sin(t * 0.8 + ph) * 0.25; const g = ctx.createLinearGradient(x0, 0, 360, 1100); g.addColorStop(0, 'rgba(255,240,200,0.35)'); g.addColorStop(1, 'rgba(255,240,200,0)');
    ctx.fillStyle = g; ctx.save(); ctx.translate(x0, -40); ctx.rotate(a + (x0 < 360 ? -0.35 : 0.35)); ctx.beginPath(); ctx.moveTo(-20, 0); ctx.lineTo(20, 0); ctx.lineTo(180, 1400); ctx.lineTo(-180, 1400); ctx.fill(); ctx.restore();
  }
  ctx.restore();
  bokeh(ctx, t, { n: 30, colors: ['#ffd28a', '#9ab8ff', '#fff0c8'], r: 24, a: 0.25, seed: 41 });
  const r = rnd(31);
  for (let i = 0; i < 60; i++) { const x = r() * W + Math.sin(t * 1.5 + i) * 30, y = mod(r() * H + t * (90 + r() * 120), H), a = t * 3 + i;
    ctx.save(); ctx.translate(x, y); ctx.rotate(a); ctx.fillStyle = i % 3 ? '#f4c95a' : '#fff1c4'; ctx.fillRect(-6, -3 * Math.abs(Math.cos(a)), 12, 6 * Math.abs(Math.cos(a)) + 0.5); ctx.restore(); }
}
function trophy(ctx, x, y, s) {
  ctx.save(); ctx.translate(x, y); ctx.scale(s, s);
  const g = ctx.createLinearGradient(-60, 0, 60, 0); g.addColorStop(0, '#9a6a1c'); g.addColorStop(0.45, '#ffe08a'); g.addColorStop(1, '#a8741e');
  ctx.fillStyle = g; ctx.beginPath(); ctx.moveTo(-70, -150); ctx.lineTo(70, -150); ctx.quadraticCurveTo(66, -40, 10, -10); ctx.lineTo(10, 40); ctx.lineTo(40, 60); ctx.lineTo(-40, 60); ctx.lineTo(-10, 40); ctx.lineTo(-10, -10); ctx.quadraticCurveTo(-66, -40, -70, -150); ctx.fill();
  ctx.fillStyle = '#2a1a10'; ctx.fillRect(-56, 60, 112, 40);
  ctx.strokeStyle = g; ctx.lineWidth = 9; for (const sd of [-1, 1]) { ctx.beginPath(); ctx.arc(sd * 72, -110, 26, sd > 0 ? -1.4 : 1.7, sd > 0 ? 1.4 : 4.6); ctx.stroke(); }
  star4(ctx, -30, -120, 18, 0.9); ctx.restore();
}
function bgHotel(ctx, t, o = {}) {
  const vx = 360, vy = 520;
  ctx.fillStyle = '#2e1e18'; ctx.fillRect(0, 0, W, H);
  ctx.fillStyle = '#4a322a'; ctx.beginPath(); ctx.moveTo(0, 0); ctx.lineTo(vx - 70, vy - 90); ctx.lineTo(vx - 70, vy + 60); ctx.lineTo(0, H); ctx.fill();
  ctx.fillStyle = '#44302a'; ctx.beginPath(); ctx.moveTo(W, 0); ctx.lineTo(vx + 70, vy - 90); ctx.lineTo(vx + 70, vy + 60); ctx.lineTo(W, H); ctx.fill();
  ctx.fillStyle = '#2a1a16'; ctx.beginPath(); ctx.moveTo(0, 0); ctx.lineTo(W, 0); ctx.lineTo(vx + 70, vy - 90); ctx.lineTo(vx - 70, vy - 90); ctx.fill();
  ctx.fillStyle = '#5e1820'; ctx.beginPath(); ctx.moveTo(vx - 70, vy + 60); ctx.lineTo(vx + 70, vy + 60); ctx.lineTo(W + 400, H); ctx.lineTo(-400, H); ctx.fill();
  ctx.strokeStyle = 'rgba(230,180,90,0.35)'; ctx.lineWidth = 2; for (let i = -6; i <= 6; i++) { ctx.beginPath(); ctx.moveTo(vx + i * 10, vy + 60); ctx.lineTo(vx + i * 140, H); ctx.stroke(); }
  for (let k = 0; k < 6; k++) { const y = vy + 60 + (H - vy - 60) * Math.pow(k / 6, 2); ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke(); }
  ctx.fillStyle = '#5a3e32'; ctx.fillRect(vx - 70, vy - 90, 140, 150);
  for (const s of [-1, 1]) for (let i = 0; i < 3; i++) {
    const k = [1, 0.55, 0.32][i], x = vx + s * (70 + 290 * k * 0.95), y = vy - 40 - 200 * k;
    glow(ctx, x, y, 140 * k, '#ffc37a', 0.55); ctx.fillStyle = '#ffe3b0'; rr(ctx, x - 10 * k, y - 18 * k, 20 * k, 36 * k, 6 * k); ctx.fill();
    ctx.fillStyle = '#2a170f'; const dx = vx + s * (70 + 180 * k), dw = 110 * k; ctx.beginPath(); ctx.moveTo(dx, vy - 60 - 330 * k * 0.6); ctx.lineTo(dx + s * dw, vy - 60 - 330 * k * 0.75); ctx.lineTo(dx + s * dw, vy + 60 + 520 * k * 0.75); ctx.lineTo(dx, vy + 60 + 520 * k * 0.6); ctx.fill();
  }
  if (o.dim) fillAll(ctx, '#0a0604', o.dim);
}
function bgDoor(ctx, t, o = {}) {
  ctx.fillStyle = vgrad(ctx, 0, H, ['#3e2c22', '#2a1d16']); ctx.fillRect(0, 0, W, H);
  glow(ctx, 70, 300, 240, '#ffc37a', 0.5); ctx.fillStyle = '#ffe3b0'; rr(ctx, 58, 270, 24, 44, 8); ctx.fill();
  const crack = o.crack || 0, x0 = 170, x1 = 550, y0 = 40, y1 = 900;
  ctx.fillStyle = '#1c120c'; ctx.fillRect(x0 - 18, y0 - 18, x1 - x0 + 36, y1 - y0 + 18);
  if (crack > 0) { ctx.fillStyle = '#fff3d6'; ctx.fillRect(x0, y0, 70 * crack, y1 - y0); glow(ctx, x0 + 30 * crack, (y0 + y1) / 2, 260 * crack, '#ffe6b0', 0.8 * crack); }
  ctx.save(); ctx.translate(x0 + 70 * crack, 0);
  const g = ctx.createLinearGradient(0, 0, x1 - x0, 0); g.addColorStop(0, '#5a3524'); g.addColorStop(1, '#41261a');
  ctx.fillStyle = g; ctx.fillRect(0, y0, x1 - x0 - 70 * crack, y1 - y0);
  ctx.strokeStyle = 'rgba(0,0,0,0.35)'; ctx.lineWidth = 4; ctx.strokeRect(40, y0 + 50, x1 - x0 - 80 - 70 * crack, 300); ctx.strokeRect(40, y0 + 420, x1 - x0 - 80 - 70 * crack, 380);
  ctx.fillStyle = '#d8b56a'; rr(ctx, (x1 - x0) / 2 - 60, y0 + 100, 120, 50, 8); ctx.fill();
  ctx.fillStyle = '#3a2410'; ctx.font = `700 34px ${F_SANS}`; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillText('1208', (x1 - x0) / 2, y0 + 126);
  ctx.restore();
  ctx.fillStyle = '#c9a65e'; rr(ctx, x1 - 70, 460, 22, 90, 10); ctx.fill();
  ctx.fillStyle = '#222'; rr(ctx, x1 + 40, 430, 50, 90, 8); ctx.fill(); ctx.fillStyle = o.green ? '#3cff7a' : '#ff3a3a'; circle(ctx, x1 + 65, 450, 5); ctx.fill();
  ctx.fillStyle = '#5e1820'; ctx.fillRect(0, y1, W, H - y1);
}
function phone(ctx, x, y, w, h, drawScreen) {
  ctx.save(); ctx.shadowColor = 'rgba(0,0,0,0.6)'; ctx.shadowBlur = 40;
  ctx.fillStyle = '#111'; rr(ctx, x, y, w, h, 56); ctx.fill(); ctx.shadowBlur = 0;
  ctx.strokeStyle = '#4a4a52'; ctx.lineWidth = 4; rr(ctx, x + 2, y + 2, w - 4, h - 4, 54); ctx.stroke();
  ctx.save(); rr(ctx, x + 16, y + 16, w - 32, h - 32, 42); ctx.clip(); drawScreen(x + 16, y + 16, w - 32, h - 32); ctx.restore();
  ctx.fillStyle = '#111'; rr(ctx, x + w / 2 - 70, y + 16, 140, 30, 15); ctx.fill();
  ctx.restore();
}
function avatar(ctx, x, y, s, col, ch) { ctx.fillStyle = col; rr(ctx, x, y, s, s, 10); ctx.fill(); ctx.fillStyle = '#fff'; ctx.font = `700 ${s * 0.5}px ${F_SANS}`; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillText(ch, x + s / 2, y + s / 2 + 1); }
function chatScreen(ctx, x, y, w, h, title, msgs, t) {
  ctx.fillStyle = '#ededed'; ctx.fillRect(x, y, w, h);
  ctx.fillStyle = '#f7f7f7'; ctx.fillRect(x, y, w, 120); ctx.fillStyle = '#d9d9d9'; ctx.fillRect(x, y + 120, w, 2);
  ctx.fillStyle = '#111'; ctx.font = `700 30px ${F_SANS}`; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillText(title, x + w / 2, y + 86);
  ctx.textAlign = 'left'; ctx.font = `500 22px ${F_SANS}`; ctx.fillText(title === '妲纽至' ? '09:12' : '01:07', x + 40, y + 36); ctx.font = `700 36px ${F_SANS}`; ctx.fillText('‹', x + 24, y + 86);
  let cy = y + 150;
  for (const m of msgs) {
    if (t < m.at) continue;
    const k = eback(seg(t, m.at, m.at + 0.22));
    if (m.div) { ctx.fillStyle = '#9a9a9a'; ctx.font = `500 22px ${F_SANS}`; ctx.textAlign = 'center'; ctx.fillText(m.div, x + w / 2, cy + 14); cy += 56; continue; }
    ctx.font = `500 27px ${F_SANS}`; const lines = wrapText(ctx, m.text, w - 190), lh = 38;
    const bw = Math.max(...lines.map(l => ctx.measureText(l).width)) + 36, bh = lines.length * lh + 26;
    ctx.save(); ctx.globalAlpha = m.dim ? 0.55 : 1;
    const L = m.side === 'L', ax = L ? x + 20 : x + w - 76, bx = L ? x + 90 : x + w - 90 - bw;
    ctx.translate(L ? bx : bx + bw, cy); ctx.scale(k, k); ctx.translate(-(L ? bx : bx + bw), -cy);
    avatar(ctx, ax, cy, 56, m.av[0], m.av[1]);
    ctx.fillStyle = L ? '#ffffff' : '#95ec69'; rr(ctx, bx, cy, bw, bh, 10); ctx.fill();
    ctx.beginPath(); if (L) { ctx.moveTo(bx, cy + 20); ctx.lineTo(bx - 10, cy + 28); ctx.lineTo(bx, cy + 36); } else { ctx.moveTo(bx + bw, cy + 20); ctx.lineTo(bx + bw + 10, cy + 28); ctx.lineTo(bx + bw, cy + 36); } ctx.fill();
    ctx.fillStyle = '#111'; ctx.textAlign = 'left'; ctx.textBaseline = 'middle'; lines.forEach((l, i) => ctx.fillText(l, bx + 18, cy + 13 + lh * (i + 0.5)));
    ctx.restore(); cy += bh + 26;
  }
}
function crow(ctx, x, y, s, t) {
  ctx.save(); ctx.translate(x, y); ctx.scale(s, s); ctx.fillStyle = '#111';
  ell(ctx, 0, 0, 26, 12); ctx.fill(); circle(ctx, -24, -6, 10); ctx.fill(); ctx.beginPath(); ctx.moveTo(-32, -6); ctx.lineTo(-46, -2); ctx.lineTo(-32, 0); ctx.fill();
  const f = Math.sin(t * 18) * 26; ctx.beginPath(); ctx.moveTo(-6, -4); ctx.quadraticCurveTo(10, -30 - f, 30, -20 - f * 1.4); ctx.quadraticCurveTo(14, -10, 6, -2); ctx.fill();
  ctx.beginPath(); ctx.moveTo(20, -2); ctx.lineTo(40, -8); ctx.lineTo(38, 4); ctx.fill(); ctx.restore();
}
function caption(ctx, text, x, y, a) {
  ctx.save(); ctx.globalAlpha = a; ctx.font = `600 28px ${F_SERIF}`; const w = ctx.measureText(text).width;
  ctx.fillStyle = 'rgba(10,10,18,0.75)'; ctx.fillRect(x, y, w + 40, 50); ctx.fillStyle = '#c9a45c'; ctx.fillRect(x, y, 5, 50);
  ctx.fillStyle = '#f3ede2'; ctx.textAlign = 'left'; ctx.textBaseline = 'middle'; ctx.fillText(text, x + 22, y + 26); ctx.restore();
}
const tint = (c, a) => ({ tint: c, tintA: a });

// =============================================================== scenes
SCENES.cold_open = { vig: 0.6, draw(ctx, S) {
  const t = S.t, fl = flashAt(t, S.ev.thunder);
  ctx.fillStyle = vgrad(ctx, 0, H, ['#02040a', '#070b16']); ctx.fillRect(0, 0, W, H);
  if (fl > 0.01) { ctx.fillStyle = `rgba(150,175,230,${0.85 * fl})`; ctx.fillRect(0, 0, W, H); bolt(ctx, 500, 0, 760, 7, fl); }
  ctx.fillStyle = '#03050a'; ctx.beginPath(); ctx.moveTo(0, 1000); ctx.quadraticCurveTo(360, 900, 720, 980); ctx.lineTo(720, H); ctx.lineTo(0, H); ctx.fill();
  ctx.fillRect(170, 780, 380, 200); ctx.beginPath(); ctx.moveTo(150, 790); ctx.lineTo(360, 690); ctx.lineTo(570, 790); ctx.fill(); ctx.fillRect(470, 700, 40, 80);
  ctx.fillStyle = '#ffcf8a'; ctx.fillRect(400, 820, 60, 50); glow(ctx, 430, 845, 90, '#ffbf70', 0.5);
  ctx.fillStyle = 'rgba(255,207,138,0.25)'; ctx.fillRect(230, 900, 40, 40);
  rain(ctx, t, { n: 260, a: 0.7 });
  const txt = (s, y, a0) => { const n = Math.floor([...s].length * seg(t, a0, a0 + 0.7)); bigText(ctx, [...s].slice(0, n).join(''), 360, y, { font: F_SERIF, weight: 900, size: 58, fill: '#eef2ff', glow: '#6f8cd0', glowBlur: 20, a: 1 - seg(t, S.d - 0.4, S.d) }); };
  txt('凌晨一点。', 420, 0.3); txt('暴雨如注。', 520, 2.0);
}};

SCENES.study_wide = { fadeIn: 0.5, draw(ctx, S) {
  const t = S.t, fl = flashAt(t, S.ev.flash);
  ctx.save(); cam(ctx, 380, 720, lerp(1.0, 1.08, sm(t / S.d)));
  bgStudy(ctx, t, { flash: fl, bolt: 3, wx: 210, wy: 220, ww: 480, wh: 800 });
  ctx.fillStyle = '#ffd7a0'; ctx.fillRect(20, 500, 150, 540); glow(ctx, 95, 760, 300, '#ffb070', 0.5);
  ctx.strokeStyle = '#05070c'; ctx.lineWidth = 14; ctx.strokeRect(20, 500, 150, 540);
  ctx.save(); ctx.globalCompositeOperation = 'lighter'; ctx.fillStyle = 'rgba(255,170,90,0.16)'; ctx.beginPath(); ctx.moveTo(20, 1040); ctx.lineTo(170, 1040); ctx.lineTo(520, 1280); ctx.lineTo(0, 1280); ctx.fill(); ctx.restore();
  layer(ctx, c => figure(c, 'smx', { x: 95, y: 1036, h: 470, kind: 'skirt', color: '#d9c6ae', armColor: '#d9c6ae', hairLong: true, t }), { dark: 0.88, darkColor: '#0c0a10', glow: '#ffcf8a', glowBlur: 26 });
  ctx.fillStyle = '#ffffff'; ctx.save(); ctx.translate(124, 840); ctx.rotate(0.1); ctx.globalAlpha = 0.9; ctx.fillRect(0, 0, 30, 40); ctx.restore();
  const cx = 470;
  layer(ctx, c => {
    c.fillStyle = '#0b0e16';
    ell(c, cx, 838, 118, 52); c.fill();
    ell(c, cx, 742, 44, 52); c.fill(); c.fillRect(cx - 18, 770, 36, 50);
    c.beginPath(); c.moveTo(cx - 46, 730); c.lineTo(cx - 62, 768); c.lineTo(cx - 40, 752); c.lineTo(cx - 34, 780); c.lineTo(cx - 10, 760); c.lineTo(cx + 46, 724); c.lineTo(cx, 690); c.fill();
    c.beginPath(); c.moveTo(cx - 150, 1160); c.lineTo(cx - 150, 880); c.quadraticCurveTo(cx - 150, 820, cx - 100, 830); c.quadraticCurveTo(cx, 800, cx + 100, 830);
    c.quadraticCurveTo(cx + 150, 820, cx + 150, 880); c.lineTo(cx + 150, 1160); c.fill();
    rr(c, cx - 200, 940, 70, 220, 24); c.fill(); rr(c, cx + 130, 940, 70, 220, 24); c.fill();
    ell(c, cx + 168, 928, 26, 16); c.fill();
  }, { glow: rgba('#7fa6e0', 0.9), glowBlur: 18 });
  ctx.strokeStyle = '#eee'; ctx.lineWidth = 4; ctx.beginPath(); ctx.moveTo(cx + 180, 922); ctx.lineTo(cx + 214, 904); ctx.stroke();
  ctx.restore();
}};

SCENES.agreement = { draw(ctx, S) {
  const t = S.t; bgDesk(ctx, t);
  const k = eo(seg(t, 0.05, 0.9)), py = lerp(1600, 680, k);
  paper(ctx, 360, py, -0.05);
  hand(ctx, 330, py + 400, 0.05, 1.05, { sleeve: '#e6d5bf', cuff: '#d5bfa4', skin: '#fde8dc' });
  hand(ctx, 690, 960, -0.9, 1.0, { sleeve: '#1e2029', skin: '#f7e0d0' });
}};

SCENES.split = { draw(ctx, S) {
  const t = S.t, tUp = S.L[2].end + 0.05, ku = sm(seg(t, tUp, tUp + 0.4));
  panelFrame(ctx, [24, 24, 672, 600], seg(t, 0, 0.3), 'left', () => {
    bgStudy(ctx, t, { wx: -10, wy: -10, ww: 740, wh: 760 }); fillAll(ctx, '#05070c', 0.3);
    const z = lerp(1, 1.14, ku); ctx.save(); ctx.translate(330, 330); ctx.scale(z, z); ctx.translate(-330, -330);
    layer(ctx, c => bust(c, 'zy', { x: 330, y: 380, s: 0.95, t, seed: 1, outfit: 'shirt_black', open: lerp(0.5, 0.92, ku), ly: lerp(0.95, -0.1, ku), lx: lerp(0.2, 0, ku), brow: lerp(0.15, 0.6, ku), talk: S.talk('zy'), rim: '#8fb2ee', rimA: 0.4 }), tint('#1a2440', 0.22));
    ctx.restore();
    ctx.fillStyle = '#f2efe8'; ctx.save(); ctx.translate(520, 600); ctx.rotate(-0.15); ctx.fillRect(-120, -40, 260, 200); ctx.restore();
  });
  panelFrame(ctx, [24, 648, 672, 608], seg(t, 0.25, 0.55), 'right', () => {
    ctx.fillStyle = '#21150f'; ctx.fillRect(0, 640, W, 640); glow(ctx, 640, 860, 520, '#ffb070', 0.55);
    ctx.fillStyle = 'rgba(255,215,160,0.5)'; ctx.fillRect(560, 660, 130, 600); ctx.fillStyle = '#120b08'; ctx.fillRect(540, 650, 22, 610);
    layer(ctx, c => bust(c, 'smx', { x: 420, y: 1010, s: 0.95, t, seed: 2, outfit: 'sweater', mouth: 'smile', brow: -0.5, wet: 0.8, lx: -0.25, talk: S.talk('smx'), rim: '#ffcf9a', rimA: 0.45 }), tint('#2a1810', 0.12));
  });
}};

SCENES.zy_close = { draw(ctx, S) {
  const t = S.t; ctx.save(); cam(ctx, 360, 640, lerp(1.0, 1.07, t / S.d));
  bgStudy(ctx, t, { wx: -20, wy: -20, ww: 760, wh: 1120 }); fillAll(ctx, '#050810', 0.4);
  layer(ctx, c => bust(c, 'zy', { x: 360, y: 560, s: 1.55, t, seed: 3, outfit: 'shirt_black', open: 0.74, brow: 0.75, mouth: 'neutral', talk: S.talk('zy'), rim: '#8fb2ee', rimA: 0.5 }), tint('#142038', 0.25));
  ctx.restore();
  if (t < 0.35) fillAll(ctx, '#d6e4ff', 0.45 * (1 - t / 0.35));
}};

SCENES.smx_close = { draw(ctx, S) {
  const t = S.t; ctx.save(); cam(ctx, 360, 600, lerp(1.0, 1.09, t / S.d));
  ctx.fillStyle = vgrad(ctx, 0, H, ['#24160f', '#120b08']); ctx.fillRect(0, 0, W, H);
  bokeh(ctx, t, { n: 30, colors: ['#ffb070', '#ffd29a', '#ff8a5a'], r: 50, a: 0.22, seed: 9 });
  const tear = seg(t, S.ev.tear, S.ev.tear + 1.6);
  layer(ctx, c => bust(c, 'smx', { x: 360, y: 540, s: 1.55, t, seed: 5, outfit: 'sweater', mouth: 'smile', brow: -0.6, wet: 1, redEyes: 0.4, tear, talk: S.talk('smx'), rim: '#ffcf9a', rimA: 0.35 }), tint('#2a1810', 0.1));
  ctx.restore();
}};

SCENES.sign = { draw(ctx, S) {
  const t = S.t, p = sm(seg(t, S.ev.sign, S.ev.sign + 0.75));
  ctx.save(); cam(ctx, 330, 820, 1.25);
  bgDesk(ctx, t); paper(ctx, 360, 640, -0.05, p);
  const [sx, sy] = scribblePt(p, -104, 192, 160, 8), a = -0.05;
  const px = 360 + Math.cos(a) * sx - Math.sin(a) * sy, py = 640 + Math.sin(a) * sx + Math.cos(a) * sy;
  ctx.save(); ctx.translate(px, py); ctx.rotate(0.55);
  ctx.fillStyle = '#111'; rr(ctx, -5, -230, 14, 230, 5); ctx.fill(); ctx.fillStyle = '#d4af37'; ctx.fillRect(-6, -200, 16, 8); ctx.fillRect(6, -190, 4, 70);
  ctx.fillStyle = '#c0c0c0'; ctx.beginPath(); ctx.moveTo(-5, 0); ctx.lineTo(9, 0); ctx.lineTo(2, 14); ctx.fill();
  ctx.restore();
  ctx.save(); ctx.translate(px, py); ctx.rotate(0.55);
  ctx.fillStyle = '#1e2029'; ctx.beginPath(); ctx.moveTo(-40, -150); ctx.lineTo(40, -150); ctx.lineTo(260, -620); ctx.lineTo(120, -660); ctx.fill();
  ctx.fillStyle = '#f7e0d0'; ell(ctx, 6, -105, 34, 52); ctx.fill(); ell(ctx, -18, -70, 13, 20); ctx.fill(); ell(ctx, 26, -78, 12, 22); ctx.fill();
  ctx.strokeStyle = 'rgba(150,90,70,0.4)'; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(-14, -120); ctx.quadraticCurveTo(4, -100, 26, -116); ctx.moveTo(-10, -96); ctx.quadraticCurveTo(8, -80, 28, -94); ctx.stroke();
  ctx.fillStyle = '#e9ebf0'; ctx.fillRect(-42, -160, 84, 18); ctx.restore();
  ctx.restore();
  const k = seg(t, S.ev.sign + 0.05, S.ev.sign + 0.25);
  if (k > 0) bigText(ctx, '唰——', 470, 520, { font: F_FUN, size: 110, fill: '#fff', stroke: '#111', strokeW: 12, rot: -0.2, scale: eback(k), a: 1 - seg(t, S.ev.sign + 1.2, S.ev.sign + 1.5) });
}};

SCENES.door = { draw(ctx, S) {
  const t = S.t, ev = S.ev, L2 = S.L[2];
  const cl = sm(seg(t, ev.door, ev.door + 0.35)), fl = flashAt(t, ev.door + 0.25);
  ctx.fillStyle = vgrad(ctx, 0, H, ['#0d1424', '#070a12']); ctx.fillRect(0, 0, W, H);
  ctx.fillStyle = '#0a0e18'; ctx.fillRect(0, 1060, W, 220);
  const dx0 = 230, dx1 = 490, dy0 = 300, dy1 = 1062;
  ctx.fillStyle = vgrad(ctx, dy0, dy1, ['#ffe4b8', '#ffc98a']); ctx.fillRect(dx0, dy0, dx1 - dx0, dy1 - dy0);
  ctx.save(); ctx.globalCompositeOperation = 'lighter'; glow(ctx, 360, 700, 520 * (1 - cl), '#ffb070', 0.5);
  ctx.fillStyle = `rgba(255,190,110,${0.22 * (1 - cl)})`; ctx.beginPath(); ctx.moveTo(dx0, dy1); ctx.lineTo(dx1, dy1); ctx.lineTo(640, H); ctx.lineTo(80, H); ctx.fill(); ctx.restore();
  const w1 = seg(t, 0, ev.stop), w2 = seg(t, L2.end + 0.05, ev.door);
  const h = lerp(lerp(800, 690, w1), 470, w2), y = lerp(lerp(1290, 1200, w1), 1062, w2);
  const walking = t < ev.stop || (t > L2.end + 0.05 && t < ev.door);
  if (t < ev.door + 0.1) layer(ctx, c => figure(c, 'smx', { x: 360, y, h, kind: 'skirt', color: '#d9c6ae', armColor: '#d9c6ae', back: true, hairLong: true, walk: walking ? 1.0 : 0, t }), { dark: lerp(0.8, 0.95, w2), darkColor: '#0c0a10', glow: '#ffcf8a', glowBlur: 30, alpha: 1 - seg(t, ev.door - 0.15, ev.door + 0.1) });
  ctx.fillStyle = '#2a1c14'; const pw = lerp(26, dx1 - dx0, cl); ctx.fillRect(dx1 - pw, dy0, pw, dy1 - dy0);
  ctx.strokeStyle = '#05070c'; ctx.lineWidth = 16; ctx.strokeRect(dx0, dy0, dx1 - dx0, dy1 - dy0);
  if (fl > 0) fillAll(ctx, '#9fb8f0', 0.35 * fl);
  if (t > ev.black) fillAll(ctx, '#000', sm(seg(t, ev.black, ev.black + 0.25)));
}};

SCENES.after = { draw(ctx, S) {
  const t = S.t, ev = S.ev;
  if (t < ev.phone + 0.35) {
    ctx.fillStyle = vgrad(ctx, 0, H, ['#151a24', '#0b0e14']); ctx.fillRect(0, 0, W, H);
    ctx.fillStyle = '#080a0f'; rr(ctx, 60, 860, 600, 260, 40); ctx.fill(); rr(ctx, 40, 800, 120, 300, 40); ctx.fill(); rr(ctx, 560, 800, 120, 300, 40); ctx.fill();
    ctx.fillStyle = '#0c0f16'; ctx.fillRect(560, 560, 10, 300); ell(ctx, 565, 545, 60, 30); ctx.fill();
    const cx = 360, cy = 760, R = 120;
    circle(ctx, cx, cy, R + 12); ctx.fillStyle = '#2a2f3a'; ctx.fill(); circle(ctx, cx, cy, R); ctx.fillStyle = '#e8e4da'; ctx.fill();
    ctx.strokeStyle = '#333'; ctx.lineWidth = 4; for (let i = 0; i < 12; i++) { const a = i / 12 * TAU; ctx.beginPath(); ctx.moveTo(cx + Math.cos(a) * R * 0.85, cy + Math.sin(a) * R * 0.85); ctx.lineTo(cx + Math.cos(a) * R * 0.95, cy + Math.sin(a) * R * 0.95); ctx.stroke(); }
    const a1 = t * 9, a2 = t * 0.75; ctx.lineCap = 'round';
    ctx.lineWidth = 8; ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(cx + Math.sin(a2) * R * 0.5, cy - Math.cos(a2) * R * 0.5); ctx.stroke();
    ctx.lineWidth = 5; ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(cx + Math.sin(a1) * R * 0.8, cy - Math.cos(a1) * R * 0.8); ctx.stroke();
    ctx.save(); ctx.globalAlpha = 0.25; ctx.strokeStyle = '#e8e4da'; ctx.lineWidth = 3; for (let i = 1; i < 6; i++) { ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(cx + Math.sin(a1 - i * 0.12) * R * 0.8, cy - Math.cos(a1 - i * 0.12) * R * 0.8); ctx.stroke(); } ctx.restore();
    if (t > ev.phone) fillAll(ctx, '#000', seg(t, ev.phone, ev.phone + 0.35));
    return;
  }
  ctx.fillStyle = vgrad(ctx, 0, H, ['#0f1420', '#06080d']); ctx.fillRect(0, 0, W, H);
  bokeh(ctx, t, { n: 18, colors: ['#7fb2ff', '#ffb45a'], r: 60, a: 0.15, seed: 6 });
  const k = eo(seg(t, ev.phone, ev.phone + 0.4));
  phone(ctx, 120, lerp(1300, 170, k), 480, 940, (x, y, w, h) => {
    if (t < ev.msg - 0.1) {
      ctx.fillStyle = vgrad(ctx, y, y + h, ['#2b3445', '#141924']); ctx.fillRect(x, y, w, h);
      circle(ctx, x + w / 2, y + 260, 90); ctx.fillStyle = '#c9707e'; ctx.fill(); ctx.fillStyle = '#fff'; ctx.font = `700 80px ${F_SANS}`; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillText('轩', x + w / 2, y + 262);
      ctx.font = `700 44px ${F_SANS}`; ctx.fillText('史明轩', x + w / 2, y + 420);
      let st = '正在呼叫…', col = '#c9d3e6', n = 1;
      if (t > ev.call1 + 0.55) st = '无人接听'; if (t > ev.call2) { st = '正在呼叫…'; n = 2; } if (t > ev.call2 + 0.55) st = '无人接听';
      if (t > ev.hang) { st = '对方已挂断'; col = '#ff6b6b'; n = 3; }
      ctx.font = `500 30px ${F_SANS}`; ctx.fillStyle = col; ctx.fillText(st, x + w / 2, y + 490);
      ctx.font = `500 24px ${F_SANS}`; ctx.fillStyle = '#8f9bb3'; ctx.fillText(`第 ${n} 次呼叫`, x + w / 2, y + 540);
      circle(ctx, x + w / 2, y + h - 150, 54); ctx.fillStyle = '#e5484d'; ctx.fill();
      ctx.save(); ctx.translate(x + w / 2, y + h - 150); ctx.rotate(2.35); ctx.fillStyle = '#fff'; rr(ctx, -30, -10, 60, 20, 10); ctx.fill(); ctx.restore();
    } else {
      const zy = ['#2b3552', '禹'], sm_ = ['#c9707e', '轩'];
      chatScreen(ctx, x, y, w, h, '史明轩', [
        { side: 'L', text: '今天降温，记得多穿一点。', at: 0, dim: true, av: sm_ },
        { side: 'L', text: '胃药放在你办公室右边第二个抽屉。', at: 0, dim: true, av: sm_ },
        { side: 'L', text: '晚上回来吃饭吗？我等你。', at: 0, dim: true, av: sm_ },
        { div: '— 半个月后 —', at: 0 },
        { side: 'L', text: '有事说事。', at: ev.msg, av: sm_ },
      ], t);
    }
  });
}};

const WHISPERS = [['周总终于离了？', 160, 540, 'w1'], ['早该离了。', 580, 620, 'w2'], ['如雪才是白月光吧？', 200, 690, 'w3']];
SCENES.gossip = { draw(ctx, S) {
  const t = S.t, ev = S.ev, hush = seg(t, ev.hush, ev.hush + 0.25);
  bgBanquet(ctx, t, { noCrowd: true });
  crowd(ctx, t, 860, 0.9, '#1a0e07', 3);
  if (hush > 0) fillAll(ctx, '#9cc6ff', 0.25 * hush * (1 - seg(t, ev.hush + 0.3, ev.hush + 1.2)));
  for (const [txt, x, y, e] of WHISPERS) {
    if (t < ev[e]) continue;
    const a = seg(t, ev[e], ev[e] + 0.2) * (1 - hush), s = 1 + 0.2 * hush;
    if (a <= 0) continue;
    ctx.save(); ctx.translate(x, y); ctx.scale(s, s); ctx.translate(-x, -y);
    drawBubble(ctx, { st: 'whisper', b: [x, y], text: txt, who: 'crowd' }, 1, a * 0.9, S); ctx.restore();
  }
  layer(ctx, c => bust(c, 'zy', { x: 480, y: 950, s: 1.0, t, seed: 4, outfit: 'suit_black', open: hush > 0 ? 0.72 : 0.9, brow: hush > 0 ? 0.85 : 0.2, lx: hush > 0 ? -0.55 : -0.1, talk: S.talk('zy'), rim: '#ffcf8a', rimA: 0.35 }), tint('#2a1608', 0.12));
  if (hush > 0) { sparkles(ctx, t, { n: 30, color: '#dff0ff', size: 8, seed: 55, a: hush }); }
}};

SCENES.entrance = { draw(ctx, S) {
  const t = S.t, ev = S.ev, op = eo(seg(t, ev.open, ev.open + 0.7)), p = seg(t, ev.open + 0.35, S.d + 0.6);
  bgBanquet(ctx, t, { noCrowd: true });
  const dx0 = 150, dx1 = 570, dy0 = 260, dy1 = 900;
  ctx.fillStyle = '#c9a052'; ctx.fillRect(dx0 - 22, dy0 - 22, dx1 - dx0 + 44, dy1 - dy0 + 22);
  ctx.fillStyle = '#fffaf0'; ctx.fillRect(dx0, dy0, dx1 - dx0, dy1 - dy0);
  ctx.save(); ctx.globalCompositeOperation = 'lighter';
  glow(ctx, 360, 600, 700 * op + 1, '#fff2cc', 0.8 * op);
  ctx.fillStyle = `rgba(255,240,200,${0.18 * op})`;
  for (let i = 0; i < 14; i++) { const a = i / 14 * TAU + t * 0.15; ctx.beginPath(); ctx.moveTo(360, 600); ctx.lineTo(360 + Math.cos(a - 0.05) * 1200, 600 + Math.sin(a - 0.05) * 1200); ctx.lineTo(360 + Math.cos(a + 0.05) * 1200, 600 + Math.sin(a + 0.05) * 1200); ctx.fill(); }
  ctx.restore();
  const half = (dx1 - dx0) / 2 * (1 - op);
  ctx.fillStyle = '#6a3e1c'; ctx.fillRect(dx0, dy0, half, dy1 - dy0); ctx.fillRect(dx1 - half, dy0, half, dy1 - dy0);
  ctx.strokeStyle = '#d8b062'; ctx.lineWidth = 4; if (half > 4) { ctx.strokeRect(dx0 + 20, dy0 + 30, half - 40, dy1 - dy0 - 60); ctx.strokeRect(dx1 - half + 20, dy0 + 30, half - 40, dy1 - dy0 - 60); }
  if (t > ev.open + 0.2) {
    const h = lerp(420, 900, eo(p)), y = lerp(880, 1380, eo(p)), dk = lerp(0.85, 0.35, p);
    layer(ctx, c => {
      figure(c, 'ji', { x: lerp(430, 560, p), y, h: h * 1.05, kind: 'suit', color: '#a3a9b4', walk: 0.8, t: t + 0.3, smile: true });
      figure(c, 'smx', { x: lerp(300, 250, p), y, h, kind: 'gown', color: '#111116', updo: true, walk: 0.8, t });
    }, { dark: dk, darkColor: '#140c08', glow: '#fff1c8', glowBlur: 40 });
    sparkles(ctx, t, { x: 100, y: 500, w: 400, h: 600, n: 24, size: 16, seed: 71 });
  }
  for (const ft of [1.1, 1.5, 2.1]) { const f = flashAt(t, ft, 14); if (f > 0.02) { const x = 80 + hash(ft) * 560, y = 700 + hash(ft + 1) * 400; glow(ctx, x, y, 200, '#ffffff', f); star4(ctx, x, y, 60 * f, f); } }
  crowd(ctx, t, 1250, 1.3, '#0a0503', 9);
  const ki = seg(t, ev.inset, ev.inset + 0.25);
  panelFrame(ctx, [24, 1000, 672, 210], ki, 'right', () => {
    ctx.fillStyle = '#1a0f08'; ctx.fillRect(0, 980, W, 260);
    layer(ctx, c => bust(c, 'zy', { x: 360, y: 1066, s: 2.6, t, seed: 4, outfit: 'suit_black', open: 0.7, brow: 0.9, lx: -0.35, noBlink: true }), tint('#2a1608', 0.15));
  });
}};

SCENES.reveal = { draw(ctx, S) {
  const t = S.t, ev = S.ev;
  if (t < ev.cut) {
    ctx.save(); cam(ctx, 360, 700, lerp(1.0, 1.1, t / ev.cut));
    ctx.fillStyle = vgrad(ctx, 0, H, ['#120812', '#07040a']); ctx.fillRect(0, 0, W, H);
    for (const s of [-1, 1]) { const x0 = s < 0 ? 0 : W - 130; ctx.fillStyle = vgrad(ctx, 0, H, ['#7a0f1c', '#3a0610']); ctx.fillRect(x0, 0, 130, 1100);
      ctx.strokeStyle = 'rgba(0,0,0,0.35)'; ctx.lineWidth = 6; for (let i = 0; i < 5; i++) { ctx.beginPath(); ctx.moveTo(x0 + 13 + i * 26, 0); ctx.lineTo(x0 + 13 + i * 26, 1100); ctx.stroke(); } }
    ctx.fillStyle = '#8a1220'; ctx.beginPath(); ctx.moveTo(0, 0); ctx.lineTo(W, 0); ctx.lineTo(W, 90); for (let i = 6; i >= 0; i--) ctx.quadraticCurveTo(i * 120 + 60, 150, i * 120, 90); ctx.fill();
    ctx.save(); ctx.globalCompositeOperation = 'lighter'; const g = ctx.createLinearGradient(0, 0, 0, 1050); g.addColorStop(0, 'rgba(255,240,200,0.4)'); g.addColorStop(1, 'rgba(255,240,200,0.05)');
    ctx.fillStyle = g; ctx.beginPath(); ctx.moveTo(320, 0); ctx.lineTo(400, 0); ctx.lineTo(680, 1050); ctx.lineTo(60, 1050); ctx.fill(); ctx.restore();
    ctx.fillStyle = '#2a1a14'; ctx.fillRect(0, 1040, W, 40); ctx.fillStyle = '#100a08'; ctx.fillRect(0, 1080, W, 200);
    figure(ctx, 'ji', { x: 230, y: 1040, h: 520, kind: 'suit', color: '#3a2a22', white: true, hairColor: '#eceae4', smile: true, t });
    ctx.fillStyle = '#5a3a24'; ctx.beginPath(); ctx.moveTo(150, 800); ctx.lineTo(320, 800); ctx.lineTo(300, 1040); ctx.lineTo(170, 1040); ctx.fill(); ctx.fillStyle = '#d8b062'; ctx.fillRect(150, 800, 170, 12);
    ctx.strokeStyle = '#222'; ctx.lineWidth = 4; ctx.beginPath(); ctx.moveTo(250, 800); ctx.lineTo(225, 720); ctx.stroke(); ell(ctx, 222, 712, 7, 12); ctx.fillStyle = '#333'; ctx.fill();
    figure(ctx, 'smx', { x: 480, y: 1040, h: 600, kind: 'gown', color: '#111116', updo: true, t });
    crowd(ctx, t, 1260, 1.2, '#050305', 4);
    ctx.restore(); return;
  }
  const hit = seg(t, ev.hit, ev.hit + 0.3), sh = 14 * flashAt(t, ev.hit, 5);
  ctx.save(); shake(ctx, t, sh); cam(ctx, 360, 640, lerp(1.06, 1.0, eo(seg(t, ev.cut, ev.cut + 0.6))));
  ctx.fillStyle = vgrad(ctx, 0, H, ['#160c16', '#07040a']); ctx.fillRect(0, 0, W, H);
  ctx.save(); ctx.globalCompositeOperation = 'lighter'; ctx.fillStyle = 'rgba(255,214,130,0.12)';
  for (let i = 0; i < 16; i++) { const a = i / 16 * TAU + t * 0.3; ctx.beginPath(); ctx.moveTo(360, 560); ctx.lineTo(360 + Math.cos(a - 0.06) * 1400, 560 + Math.sin(a - 0.06) * 1400); ctx.lineTo(360 + Math.cos(a + 0.06) * 1400, 560 + Math.sin(a + 0.06) * 1400); ctx.fill(); }
  glow(ctx, 360, 520, 480, '#ffd79a', 0.5); ctx.restore();
  if (hit > 0) speedLines(ctx, 360, 560, t, { color: '#fff3d0', a: 0.5 * hit, rin: 330, n: 60 });
  layer(ctx, c => bust(c, 'smx', { x: 360, y: 640, s: 1.25, t, seed: 6, outfit: 'gown_black', hair: 'updo', pin: true, mouth: 'smirk', open: 0.82, brow: 0.1, lx: 0.1 }), tint('#2a1608', 0.06));
  sparkles(ctx, t, { n: 26, size: 18, seed: 14, color: '#fff3c8' });
  if (hit > 0) {
    bigText(ctx, '季家唯一的外孙女', 360, 1080, { font: F_SERIF, weight: 900, size: 68, fill: '#ffd76a', stroke: '#2a1404', strokeW: 10, outer: '#fff6dc', outerW: 18, glow: '#ffb030', glowBlur: 30, scale: lerp(1.8, 1, eback(hit)), a: hit });
    bigText(ctx, '轰——', 560, 230, { font: F_FUN, size: 100, fill: '#fff', stroke: '#1a0d04', strokeW: 12, rot: 0.18, scale: eback(seg(t, ev.hit + 0.1, ev.hit + 0.35)) });
  }
  ctx.restore();
  if (t < ev.hit + 0.1 && t > ev.hit) fillAll(ctx, '#fff', 0.6);
}};

SCENES.wall = { draw(ctx, S) {
  const t = S.t, ev = S.ev, sl = flashAt(t, ev.slam, 12), L1 = S.L[1];
  ctx.save(); shake(ctx, t, 12 * sl);
  bgGarage(ctx, t); fillAll(ctx, '#10141a', 0.15);
  layer(ctx, c => {
    c.save(); c.strokeStyle = '#15161c'; c.lineWidth = 92; c.lineCap = 'round'; c.beginPath(); c.moveTo(330, 820); c.quadraticCurveTo(200, 620, 128, 548); c.stroke(); c.restore();
    hand(c, 108, 520, -0.85, 0.85, { sleeve: '#15161c', skin: '#f7e0d0' });
  }, tint('#10141a', 0.1));
  if (sl > 0.05) { ctx.save(); ctx.strokeStyle = `rgba(255,255,255,${sl})`; ctx.lineWidth = 5; for (let i = 0; i < 8; i++) { const a = i / 8 * TAU; ctx.beginPath(); ctx.moveTo(90 + Math.cos(a) * 80, 470 + Math.sin(a) * 80); ctx.lineTo(90 + Math.cos(a) * 130, 470 + Math.sin(a) * 130); ctx.stroke(); } ctx.restore(); }
  const smug = t > L1.start - 0.2;
  layer(ctx, c => bust(c, 'smx', { x: 250, y: 720, s: 1.0, t, seed: 7, outfit: 'gown_black', hair: 'updo', eyes: !smug && t < 1.2 ? 'wide' : 'normal', open: smug ? 0.7 : 1, mouth: smug ? 'smirk' : 'neutral', brow: smug ? 0.15 : -0.3, lx: 0.6, ly: -0.35, talk: S.talk('smx') }), tint('#10141a', 0.12));
  layer(ctx, c => bust(c, 'zy', { x: 530, y: 560, s: 1.1, t, seed: 8, outfit: 'suit_black', brow: 0.95, open: smug ? 0.85 : 0.78, lx: -0.7, ly: 0.35, mouth: 'frown', talk: S.talk('zy'), blush: smug ? 0.35 : 0 }), tint('#10141a', 0.12));
  ctx.restore();
}};

SCENES.uncle = { draw(ctx, S) {
  const t = S.t, ev = S.ev, kb = seg(t, ev.blank, ev.blank + 0.3);
  panelFrame(ctx, [24, 24, 672, 600], seg(t, 0, 0.3), 'down', () => {
    bgGarage(ctx, t); fillAll(ctx, '#fff6e0', 0.12);
    sparkles(ctx, t, { x: 24, y: 24, w: 672, h: 600, n: 16, color: '#fff6c8', size: 18, seed: 19 });
    bust(ctx, 'ji', { x: 330, y: 400, s: 0.95, t, seed: 9, outfit: 'suit_silver', eyes: 'happy', mouth: 'smile', talk: S.talk('ji') });
  });
  panelFrame(ctx, [24, 648, 672, 608], seg(t, 0.15, 0.45), 'up', () => {
    if (kb <= 0) {
      bgGarage(ctx, t); fillAll(ctx, '#0a0d12', 0.35);
      layer(ctx, c => bust(c, 'zy', { x: 360, y: 990, s: 0.95, t, seed: 10, outfit: 'suit_black', brow: 0.9, open: 0.8, lx: -0.25, ly: -0.6, mouth: 'frown' }), tint('#10141a', 0.1));
    } else {
      ctx.fillStyle = '#58617a'; ctx.fillRect(0, 640, W, 640);
      ctx.strokeStyle = 'rgba(30,30,70,0.5)'; ctx.lineWidth = 4; for (let x = 30; x < W; x += 34) { ctx.beginPath(); ctx.moveTo(x, 648); ctx.lineTo(x, 648 + 120 + hash(x) * 200); ctx.stroke(); }
      const s = lerp(1.2, 1, eback(kb)); ctx.save(); ctx.translate(360, 990); ctx.scale(s, s); ctx.translate(-360, -990);
      layer(ctx, c => bust(c, 'zy', { x: 360, y: 990, s: 0.95, t, outfit: 'suit_black', eyes: 'dot', mouth: 'tiny', sweat: 1, sweatY: Math.min(40, (t - ev.blank) * 20), gloom: 1, pale: 0.7, noBlink: true }), tint('#3a3a70', 0.15));
      ctx.restore();
      const ct = t - ev.blank - 0.3;
      if (ct > 0) { for (let i = 0; i < 3; i++) crow(ctx, 760 - ct * 260 - i * 90, 760 + i * 40 + Math.sin(ct * 3 + i) * 10, 1.1, ct + i);
        bigText(ctx, '嘎——', 560 - ct * 120, 700, { font: F_FUN, size: 54, fill: '#222', stroke: '#fff', strokeW: 8, a: seg(ct, 0, 0.2) }); }
    }
  });
}};

SCENES.fire = { draw(ctx, S) {
  const t = S.t, ev = S.ev;
  const dark = seg(t, ev.dark, ev.dark + 0.12) * (t < ev.dark + 0.5 ? (noise1(t * 30) > 0.35 ? 1 : 0.6) : 1), fk = seg(t, ev.fire, ev.fire + 1.4);
  const hitF = flashAt(t, ev.hit, 5);
  ctx.save(); shake(ctx, t, 3 * fk + 16 * hitF);
  bgBanquet(ctx, t, { dim: 0.88 * dark });
  ctx.save(); ctx.globalCompositeOperation = 'lighter'; glow(ctx, 360, 1300, 1000, '#ff4a1a', 0.55 * fk); glow(ctx, 60, 500, 400, '#ff7a2a', 0.4 * fk); ctx.restore();
  flames(ctx, t, fk, { x: -40, w: 260, y: 1000, h: 520, n: 6, seed: 3 });
  const r = rnd(66); ctx.fillStyle = 'rgba(30,24,26,0.35)'; for (let i = 0; i < 14; i++) { const sp = 30 + r() * 40; circle(ctx, r() * W + Math.sin(t + i) * 30, mod(r() * 900 - t * sp, 900) + 100, 60 + r() * 90); if (fk > 0) ctx.fill(); }
  const fall = seg(t, ev.fall, ev.hit), leap = seg(t, ev.fall + 0.25, ev.hit);
  layer(ctx, c => {
    figure(c, 'smx', { x: 360, y: 1180, h: 560, kind: 'gown', color: '#111116', updo: true, t, eyesClosed: t > ev.fall });
    figure(c, 'smx', { x: 300, y: 1185, h: 300, kind: 'girl', color: '#f08aa8', t });
  }, { dark: 0.55 * fk, darkColor: '#1a0604', glow: rgba('#ff7a2a', 0.9 * fk), glowBlur: 26 });
  if (t > ev.fall - 0.4) {
    const by = lerp(-260, 650, ei(fall)), rot = lerp(-0.3, 0.6, fall);
    ctx.save(); ctx.translate(360 + fall * 40, by); ctx.rotate(rot); ctx.fillStyle = '#3a2216'; ctx.fillRect(-180, -36, 360, 72);
    ctx.strokeStyle = '#d8a050'; ctx.lineWidth = 6; ctx.strokeRect(-170, -28, 340, 56); ctx.restore();
    flames(ctx, t, 1, { x: 200 + fall * 40, w: 320, y: by + 10, h: 180, n: 5, seed: 9 });
  }
  if (leap > 0.55 && t < ev.hit + 0.1) {
    const q = eo(seg(leap, 0.55, 1)), x = lerp(900, 330, q);
    const g = ctx.createLinearGradient(x, 0, x + 520, 0); g.addColorStop(0, 'rgba(8,6,10,0.95)'); g.addColorStop(1, 'rgba(8,6,10,0)');
    ctx.fillStyle = g; ctx.beginPath(); ctx.moveTo(x, 780); ctx.quadraticCurveTo(x - 40, 900, x + 20, 1060); ctx.lineTo(x + 560, 1000); ctx.lineTo(x + 520, 820); ctx.fill();
    ell(ctx, x + 10, 800, 40, 46); ctx.fillStyle = '#08060a'; ctx.fill();
  }
  flames(ctx, t, fk, { y: H + 20, h: 300, n: 14 });
  ctx.restore();
  const ki = seg(t, ev.fall - 0.05, ev.fall + 0.1) * (1 - seg(t, ev.hit - 0.35, ev.hit - 0.2));
  panelFrame(ctx, [36, 110, 648, 400], ki, 'right', () => {
    ctx.fillStyle = '#5a0e08'; ctx.fillRect(0, 100, W, 420); speedLines(ctx, 360, 330, t, { color: '#ffb070', a: 0.6, rin: 160, n: 50 });
    bust(ctx, 'zy', { x: 360, y: 380, s: 1.1, t, outfit: 'suit_black', eyes: 'wide', brow: 0.9, mouth: 'shout', noBlink: true, rim: '#ff9a4a', rimA: 0.6 });
  });
  if (t > ev.white) {
    const k = t - ev.white;
    fillAll(ctx, '#fff', Math.max(0, 1 - k / 0.25)); fillAll(ctx, '#000', sm(seg(k, 0.15, 0.6)));
    bigText(ctx, '砰——', 360, 640, { font: F_FUN, size: 150, fill: '#fff', stroke: '#c0161e', strokeW: 14, scale: eback(seg(k, 0.05, 0.3)), a: 1 - seg(k, 0.9, 1.2) });
  }
}};

SCENES.hospital = { fadeIn: 0.7, draw(ctx, S) {
  const t = S.t, L1 = S.L[1];
  ctx.save(); cam(ctx, 380, 640, lerp(1.0, 1.05, t / S.d));
  bgHospital(ctx, t); pillow(ctx);
  bust(ctx, 'smx', { x: 380, y: 600, s: 1.1, t, seed: 11, outfit: 'hosp', bandage: true, pale: 0.35, open: 0.85, brow: -0.2, lx: t < L1.start ? -0.35 : 0, ly: t < L1.start ? 0.35 : 0, talk: S.talk('smx') });
  sheet(ctx, 1000);
  ctx.restore();
}};

SCENES.corridor = { draw(ctx, S) {
  const t = S.t, L1 = S.L[1], up = sm(seg(t, L1.start - 0.3, L1.start + 0.2));
  ctx.save(); cam(ctx, 380, 600, lerp(1.0, 1.07, t / S.d));
  bgCorridor(ctx, t); fillAll(ctx, '#3a5a6a', 0.12);
  layer(ctx, c => bust(c, 'zy', { x: 390, y: 620, s: 1.1, t, seed: 12, outfit: 'hosp', cast: true, redEyes: 1, wet: 1, brow: -0.75, ly: lerp(0.6, -0.05, up), open: lerp(0.75, 0.9, up), mouth: t > L1.end ? 'smile' : 'neutral', talk: S.talk('zy') }), tint('#3a5a6a', 0.1));
  ctx.restore();
}};

SCENES.paris = { draw(ctx, S) {
  const t = S.t, ev = S.ev, L2 = S.L[2];
  if (t < 1.9) {
    bgParis(ctx, t);
    const a = seg(t, 0.2, 0.6) * (1 - seg(t, 1.5, 1.85));
    bigText(ctx, '一年后', 360, 470, { font: F_SERIF, weight: 900, size: 76, fill: '#fff6e8', glow: '#ff9ac0', glowBlur: 24, a });
    bigText(ctx, '· 巴黎 ·', 360, 570, { font: F_SERIF, weight: 600, size: 40, fill: '#ffd9e6', a });
    if (t > 1.6) fillAll(ctx, '#000', seg(t, 1.6, 1.9));
    return;
  }
  ctx.save(); cam(ctx, 380, 640, lerp(1.0, 1.06, seg(t, 1.9, S.d)));
  bgStageGala(ctx, t);
  const look = t > L2.start - 0.2;
  bust(ctx, 'smx', { x: 380, y: 640, s: 1.05, t, seed: 13, outfit: 'red', earring: true, mouth: 'smile', blush: look ? 0.8 : 0.35, lx: look ? 0 : -0.45, ly: look ? 0 : -0.1, talk: S.talk('smx'), rim: '#ffe0a0', rimA: 0.35 });
  trophy(ctx, 560, 1000, 1.25);
  for (const ft of [2.4, 2.9, 3.6, L2.end + 0.2]) { const f = flashAt(t, ft, 14); if (f > 0.02) { const x = 60 + hash(ft) * 600, y = 900 + hash(ft + 2) * 300; glow(ctx, x, y, 160, '#ffffff', f); star4(ctx, x, y, 50 * f, f); } }
  ctx.restore();
  if (t < 2.15) fillAll(ctx, '#000', 1 - seg(t, 1.9, 2.15));
  const ki = seg(t, ev.inset, ev.inset + 0.25) * (1 - seg(t, ev.inset_out - 0.2, ev.inset_out));
  panelFrame(ctx, [40, 840, 640, 380], ki, 'down', () => {
    ctx.fillStyle = '#0e1630'; ctx.fillRect(0, 820, W, 420); glow(ctx, 360, 1000, 400, '#5a8aff', 0.35);
    layer(ctx, c => bust(c, 'zy', { x: 360, y: 1110, s: 0.95, t, outfit: 'shirt_black', eyes: 'wide', pale: 1, sweat: 1, mouth: 'o', noBlink: true }), tint('#3a5aa0', 0.25));
    ctx.fillStyle = 'rgba(0,0,0,0.18)'; for (let y = 842; y < 1220; y += 6) ctx.fillRect(40, y, 640, 2);
  });
}};

SCENES.jet = { draw(ctx, S) {
  const t = S.t, ev = S.ev;
  if (t < ev.jet) {
    const st = eback(seg(t, ev.stand, ev.stand + 0.35));
    panelFrame(ctx, [24, 24, 672, 700], 1, 'fade', () => {
      ctx.fillStyle = vgrad(ctx, 0, 720, ['#141a2c', '#0a0d16']); ctx.fillRect(0, 0, W, 740);
      glow(ctx, 80, 380, 380, '#5a8aff', 0.35);
      if (seg(t, ev.stand, ev.stand + 0.4) < 1) vlines(ctx, t, { a: 0.35, v: -3000 });
      layer(ctx, c => bust(c, 'zy', { x: 400, y: lerp(980, 440, st), s: 1.0, t, seed: 14, outfit: 'shirt_black', brow: 0.6, open: 1, lx: -0.2, talk: S.talk('zy'), rim: '#8fb2ee', rimA: 0.45 }), tint('#141e38', 0.15));
    });
    panelFrame(ctx, [24, 748, 672, 508], seg(t, S.L[1].start - 0.35, S.L[1].start - 0.05), 'left', () => {
      ctx.fillStyle = vgrad(ctx, 740, H, ['#2a3040', '#1a1e28']); ctx.fillRect(0, 740, W, 540);
      bust(ctx, 'dnz', { x: 230, y: 1050, s: 0.8, t, seed: 15, outfit: 'suit_navy', sweat: 1, brow: -0.6, glint: 0.6, talk: S.talk('dnz') });
    });
    return;
  }
  const p = seg(t, ev.jet, ev.jet + 2.4);
  ctx.fillStyle = vgrad(ctx, 0, H, ['#060a1e', '#14204a', '#2a3a78']); ctx.fillRect(0, 0, W, H);
  sparkles(ctx, t, { n: 70, size: 5, seed: 5 });
  glow(ctx, 160, 260, 160, '#fff4d8', 0.55); circle(ctx, 160, 260, 40); ctx.fillStyle = '#fff6e0'; ctx.fill();
  ctx.fillStyle = 'rgba(200,210,255,0.08)'; for (let i = 0; i < 5; i++) { ell(ctx, mod(i * 200 - t * 40, 1000) - 100, 900 + i * 60, 240, 30); ctx.fill(); }
  const pe = eo(p), px = lerp(-120, 600, pe), py = lerp(1150, 300, pe), sc = lerp(1.5, 0.5, pe);
  const g = ctx.createLinearGradient(-120, 1150, px, py); g.addColorStop(0, 'rgba(255,255,255,0)'); g.addColorStop(1, 'rgba(255,255,255,0.8)');
  ctx.strokeStyle = g; ctx.lineWidth = 6 * sc; ctx.beginPath(); ctx.moveTo(-120, 1150); ctx.lineTo(px, py); ctx.stroke();
  ctx.save(); ctx.translate(px, py); ctx.rotate(-0.82); ctx.scale(sc, sc); ctx.fillStyle = '#f2f4fa';
  ell(ctx, 0, 0, 90, 16); ctx.fill(); ctx.beginPath(); ctx.moveTo(-10, 0); ctx.lineTo(-40, -80); ctx.lineTo(-20, -80); ctx.lineTo(30, 0); ctx.lineTo(-20, 80); ctx.lineTo(-40, 80); ctx.fill();
  ctx.beginPath(); ctx.moveTo(-70, 0); ctx.lineTo(-92, -34); ctx.lineTo(-80, -34); ctx.lineTo(-56, 0); ctx.fill();
  circle(ctx, -20, -80, 5); ctx.fillStyle = Math.sin(t * 10) > 0 ? '#ff4040' : '#601010'; ctx.fill(); ctx.restore();
}};

SCENES.hotel = { draw(ctx, S) {
  const t = S.t, ev = S.ev, L = S.L;
  bgHotel(ctx, t, { dim: 0.15 });
  const away = eo(seg(t, ev.turn, ev.turn + 0.6)) * (1 - eo(seg(t, ev.back, ev.back + 0.3)));
  const dimmed = t > ev.dim && t < ev.back, lit = t > L[4].start;
  layer(ctx, c => bust(c, 'zy', { x: 470 + 260 * away, y: 600, s: 1.0, t, seed: 16, outfit: 'shirt_black', hair: 'short',
    eyes: t > ev.back && t < ev.back + 0.6 ? 'wide' : 'normal', dimEyes: dimmed, sparkle: lit, open: dimmed ? 0.7 : 1, brow: dimmed ? -0.8 : -0.3,
    lx: -0.5, ly: dimmed ? 0.6 : 0.1, blush: t < L[1].start ? 0.4 : lit ? 0.6 : 0, mouth: lit ? 'smile' : 'neutral', talk: S.talk('zy'), rim: '#ffc37a', rimA: 0.3 }), { tint: '#1a0e08', tintA: 0.12, alpha: 1 - 0.5 * away });
  bust(ctx, 'smx', { x: 220, y: 830, s: 1.05, t, seed: 17, outfit: 'red', earring: true, open: t < L[3].start ? 0.72 : 0.95,
    mouth: t > L[4].start ? 'smile' : 'neutral', blush: t > L[4].start ? 0.5 : 0, brow: t > L[3].start && t < L[4].start ? 0.4 : 0, lx: 0.55, ly: -0.25, talk: S.talk('smx'), rim: '#ffc37a', rimA: 0.35 });
  caption(ctx, '凌晨三点', 30, 40, seg(t, 0.2, 0.5) * (1 - seg(t, 2.2, 2.6)));
}};

SCENES.ring = { draw(ctx, S) {
  const t = S.t, ev = S.ev, L2 = S.L[2];
  bgHotel(ctx, t, { dim: 0.35 }); fillAll(ctx, '#2a1810', 0.2);
  const happy = t > L2.start;
  layer(ctx, c => bust(c, 'zy', { x: 360, y: 1010, s: 1.05, t, seed: 18, outfit: 'shirt_black', redEyes: 0.8, wet: 1, sparkle: happy, ly: -0.7, brow: happy ? -0.2 : -0.5,
    mouth: happy ? 'smile' : 'neutral', blush: 0.4, talk: S.talk('zy'), rim: '#ffc37a', rimA: 0.35 }), tint('#1a0e08', 0.1));
  if (t > ev.catch) hand(ctx, 330, 540, 0.5, 0.75, { sleeve: '#1e2029', skin: '#f7e0d0' });
  const fly = seg(t, 0.05, ev.catch), bx = t < ev.catch ? lerp(-80, 360, fly) : 360, by = t < ev.catch ? lerp(80, 420, fly) - Math.sin(fly * Math.PI) * 180 : 420 + Math.sin(t * 2) * 4;
  const rot = t < ev.catch ? fly * 8 : 0, op = eo(seg(t, ev.open, ev.open + 0.35));
  ctx.save(); ctx.translate(bx, by); ctx.rotate(rot);
  if (op > 0) { ctx.fillStyle = '#4a0814'; rr(ctx, -110, -20 - 120 * op, 220, 120 * op, 14); ctx.fill(); ctx.fillStyle = '#f2e6e0'; rr(ctx, -96, -14 - 112 * op, 192, 104 * op, 10); ctx.fill(); }
  ctx.fillStyle = '#7a0f22'; rr(ctx, -110, -20, 220, 100, 16); ctx.fill(); ctx.fillStyle = '#2a0610'; rr(ctx, -92, -14, 184, 30, 8); ctx.fill();
  if (op > 0) {
    ctx.strokeStyle = '#dfe3ec'; ctx.lineWidth = 9; ell(ctx, 0, -26 - 16 * op, 30, 26); ctx.stroke(); ctx.strokeStyle = '#ffffff'; ctx.lineWidth = 2; ctx.stroke();
    star4(ctx, 0, -70 - 16 * op, 28 * op * (0.8 + 0.2 * Math.sin(t * 8)), op);
  } else { ctx.fillStyle = '#8a1428'; rr(ctx, -110, -62, 220, 46, 16); ctx.fill(); }
  ctx.restore();
  const km = seg(t, ev.open + 0.5, ev.open + 0.8);
  if (km > 0) {
    ctx.save(); ctx.globalAlpha = km; circle(ctx, 570, 230, 110 * eback(km)); ctx.fillStyle = 'rgba(20,10,20,0.85)'; ctx.fill(); ctx.strokeStyle = '#d8c69a'; ctx.lineWidth = 5; ctx.stroke();
    ctx.strokeStyle = '#cfd4de'; ctx.lineWidth = 46; ctx.beginPath(); ctx.arc(570, 340, 150, -2.3, -0.84); ctx.stroke();
    ctx.fillStyle = '#5a5a66'; ctx.font = `700 30px ${F_SERIF}`; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillText('S M X', 570, 192);
    ctx.fillStyle = '#d8c69a'; ctx.font = `500 22px ${F_SANS}`; ctx.fillText('戒指内侧', 570, 280); ctx.restore();
  }
}};

SCENES.callback = { draw(ctx, S) {
  const t = S.t, ev = S.ev, L = S.L;
  const shut = flashAt(t, ev.shut, 10), crack = sm(seg(t, ev.crack, ev.crack + 0.3));
  ctx.save(); shake(ctx, t, 8 * shut);
  bgDoor(ctx, t, { crack, green: t > ev.crack });
  const happy = t > ev.card + 0.3, soft = t > ev.memory;
  layer(ctx, c => bust(c, 'zy', { x: 400, y: 1010, s: 1.05, t, seed: 19, outfit: 'shirt_black', eyes: happy ? 'happy' : t < 0.6 ? 'closed' : 'normal',
    open: soft ? 0.85 : 0.95, brow: soft ? -0.25 : 0.1, ly: soft && !happy ? 0.3 : -0.2, mouth: happy ? 'bigsmile' : t > L[2].start - 0.3 ? 'smile' : 'neutral',
    blush: happy ? 0.7 : 0, talk: S.talk('zy'), rim: '#ffc37a', rimA: 0.3 }), tint('#1a0e08', 0.1));
  if (t > ev.card) {
    const p = seg(t, ev.card, ev.card + 0.45), x = lerp(220, 470, eo(p)), y = lerp(520, 830, eo(p)) - Math.sin(p * Math.PI) * 120, r = p < 1 ? p * 9 : 0.25;
    ctx.save(); ctx.translate(x, y); ctx.rotate(r); ctx.fillStyle = '#f4f1ea'; rr(ctx, -70, -44, 140, 88, 10); ctx.fill(); ctx.fillStyle = '#c9a45c'; ctx.fillRect(-70, -16, 140, 16);
    ctx.fillStyle = '#5a4a3a'; ctx.font = `700 22px ${F_SANS}`; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillText('1209', 0, 22); ctx.restore();
  }
  ctx.restore();
  const m = seg(t, ev.memory, ev.memory + 0.3) * (1 - seg(t, ev.memory_out - 0.3, ev.memory_out));
  if (m > 0) {
    fillAll(ctx, '#0c1830', 0.62 * m);
    ctx.save(); ctx.globalAlpha = 0.5 * m; ctx.fillStyle = '#ffd7a0'; ctx.fillRect(250, 300, 220, 700);
    layer(ctx, c => figure(c, 'smx', { x: 360, y: 1000, h: 640, kind: 'skirt', color: '#d9c6ae', armColor: '#d9c6ae', back: true, hairLong: true, t: 0 }), { dark: 0.9, darkColor: '#0a0c18', alpha: 0.55 * m });
    ctx.restore();
    ctx.save(); ctx.globalAlpha = m; rain(ctx, t, { n: 200, a: 0.8 }); ctx.restore();
    caption(ctx, '三年前 · 那个雨夜', 30, 40, m);
  }
}};

SCENES.title = { fadeOut: 0.5, draw(ctx, S) {
  const t = S.t;
  ctx.fillStyle = vgrad(ctx, 0, H, ['#070a1e', '#1c1640', '#4a2456', '#a04a68']); ctx.fillRect(0, 0, W, H);
  sparkles(ctx, t, { n: 80, size: 6, seed: 2, h: 900 });
  rain(ctx, t, { n: 120, a: 1 - seg(t, 0, 1.4) });
  const r = rnd(9); ctx.save(); ctx.globalCompositeOperation = 'lighter';
  for (let i = 0; i < 40; i++) { const x = r() * W + Math.sin(t + i) * 20, y = H - mod(r() * H + t * (40 + r() * 60), H + 100); glow(ctx, x, y, 10 + r() * 14, i % 2 ? '#ffd0e0' : '#fff0c0', 0.5); }
  ctx.restore();
  glow(ctx, 360, 620, 420, '#ffb0c8', 0.25);
  const line = (txt, y, a0, size) => {
    const k = sm(seg(t, a0, a0 + 0.8)); if (k <= 0) return;
    ctx.save(); ctx.beginPath(); ctx.rect(0, y - 100, W * k, 200); ctx.clip();
    bigText(ctx, txt, 360, y, { font: F_BRUSH, size, fill: '#fff8ee', stroke: '#2a1030', strokeW: 8, glow: '#ff9ac0', glowBlur: 30 }); ctx.restore();
  };
  line('周总，夫人她', 560, 0.35, 100); line('真的不爱你了', 690, 1.05, 100);
  const a = seg(t, 2.0, 2.5);
  bigText(ctx, '原创动态漫 · 预告', 360, 810, { font: F_SERIF, weight: 600, size: 32, fill: '#ffe6ef', a });
  ctx.fillStyle = `rgba(255,214,150,${0.8 * a})`; ctx.fillRect(220, 760, 280, 2);
}};

SCENES.cream = { draw(ctx, S) {
  const t = S.t, ev = S.ev, L = S.L, roar = seg(t, ev.roar, ev.roar + 0.15);
  ctx.save(); shake(ctx, t, roar > 0 ? 18 : 0);
  panelFrame(ctx, [24, 24, 672, 600], seg(t, 0, 0.3), 'right', () => {
    ctx.fillStyle = '#e4f1f6'; ctx.fillRect(0, 0, W, 640); ctx.strokeStyle = '#c6dbe4'; ctx.lineWidth = 3;
    for (let x = 0; x < W; x += 80) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, 640); ctx.stroke(); } for (let y = 0; y < 640; y += 80) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke(); }
    glow(ctx, 600, 100, 300, '#ffffff', 0.6);
    bust(ctx, 'smx', { x: 330, y: 400, s: 0.95, t, seed: 20, outfit: 'pajama', brow: 0.9, vein: 1 + 0.15 * Math.sin(t * 12), mouth: roar > 0 ? 'shout' : 'neutral', eyes: roar > 0 ? 'closed' : 'normal', talk: S.talk('smx') });
  });
  panelFrame(ctx, [24, 648, 672, 608], seg(t, L[1].start - 0.4, L[1].start - 0.1), 'left', () => {
    ctx.fillStyle = '#f6ead8'; ctx.fillRect(0, 640, W, 640); glow(ctx, 120, 760, 360, '#fff3d0', 0.8);
    ctx.fillStyle = '#e9d6bc'; ctx.fillRect(560, 650, 120, 600);
    bust(ctx, 'zy', { x: 380, y: 990, s: 0.95, t, seed: 21, outfit: 'shirt_white', eyes: roar > 0 ? 'dot' : 'normal', sweat: roar > 0 ? 1 : 0, pale: roar > 0 ? 0.5 : 0, mouth: roar > 0 ? 'tiny' : 'neutral', lx: -0.2, talk: S.talk('zy') });
  });
  ctx.restore();
  if (roar > 0) {
    speedLines(ctx, 360, 640, t, { color: '#c0161e', a: 0.55, rin: 300, n: 80 });
    bigText(ctx, '周禹——！', 360, 640, { font: F_FUN, size: 130, fill: '#e8202e', stroke: '#fff', strokeW: 14, outer: '#111', outerW: 26, scale: eback(roar) * (1 + 0.04 * Math.sin(t * 40)), rot: -0.06 });
  }
}, over(ctx, S) { seal(ctx, 96, 70, '彩蛋'); }};

SCENES.chat = { fadeOut: 0.8, draw(ctx, S) {
  const t = S.t, ev = S.ev;
  ctx.fillStyle = vgrad(ctx, 0, H, ['#dfe6ee', '#b9c6d4']); ctx.fillRect(0, 0, W, H);
  bokeh(ctx, t, { n: 16, colors: ['#ffffff'], r: 70, a: 0.25, seed: 22 });
  const zy = ['#2b3552', '禹'], dz = ['#4a7bd0', '妲'];
  phone(ctx, 120, lerp(1300, 140, eo(seg(t, 0, 0.4))), 480, 940, (x, y, w, h) => chatScreen(ctx, x, y, w, h, '妲纽至', [
    { side: 'R', text: '帮我买十瓶史明轩那个面霜。', at: ev.m1, av: zy },
    { side: 'L', text: '什么牌子？', at: ev.m2, av: dz },
    { side: 'R', text: '不知道。', at: ev.m3, av: zy },
    { side: 'R', text: '白色瓶子。', at: ev.m4, av: zy },
  ], t));
  const kf = seg(t, ev.face, ev.face + 0.3);
  if (kf > 0) {
    ctx.save(); ctx.translate(0, (1 - eo(kf)) * 500);
    bust(ctx, 'dnz', { x: 190, y: 1090, s: 0.8, t, seed: 23, outfit: 'suit_navy', eyes: 'dot', mouth: 'tiny', sweat: 1, glint: 0.8, noBlink: true });
    ctx.restore();
    drawBubble(ctx, { st: 'think', b: [420, 920, 260, 1000], text: '……', who: 'dnz' }, 1, kf, S);
  }
  const ke = seg(t, ev.end, ev.end + 0.6);
  if (ke > 0) {
    fillAll(ctx, '#0a0812', 0.88 * ke);
    bigText(ctx, '周总，夫人她', 360, 520, { font: F_BRUSH, size: 84, fill: '#fff8ee', glow: '#ff9ac0', glowBlur: 24, a: ke });
    bigText(ctx, '真的不爱你了', 360, 630, { font: F_BRUSH, size: 84, fill: '#fff8ee', glow: '#ff9ac0', glowBlur: 24, a: ke });
    bigText(ctx, '敬 请 期 待', 360, 780, { font: F_SERIF, weight: 900, size: 44, fill: '#ffd78a', a: seg(t, ev.end + 0.4, ev.end + 0.9) });
  }
}};
