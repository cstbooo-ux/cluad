'use strict';
// ---------------------------------------------------------------- dialogue rendering
function wrapText(ctx, text, maxW) {
  const noStart = '，。！？、；：”’）》…—';
  const total = ctx.measureText(text).width;
  const n = Math.max(1, Math.ceil(total / maxW));
  const target = Math.min(maxW, total / n + ctx.measureText('字').width * 0.8);
  const out = []; let cur = '';
  for (const ch of text) {
    if (cur && ctx.measureText(cur + ch).width > target && !noStart.includes(ch)) { out.push(cur); cur = ch; }
    else cur += ch;
  }
  if (cur) out.push(cur);
  return out;
}
function bubblePath(ctx, st, x, y, w, h) {
  if (st === 'shout') {
    const n = 22, rx = w / 2 + 34, ry = h / 2 + 34; ctx.beginPath();
    for (let i = 0; i <= n * 2; i++) { const a = i / (n * 2) * TAU, r = i % 2 ? 0.8 : 1.1 + hash(i) * 0.12; const px = x + Math.cos(a) * rx * r, py = y + Math.sin(a) * ry * r; i ? ctx.lineTo(px, py) : ctx.moveTo(px, py); }
    ctx.closePath(); return;
  }
  if (st === 'think') {
    ctx.beginPath(); const n = 12, rx = w / 2 + 22, ry = h / 2 + 22;
    for (let i = 0; i < n; i++) { const a = i / n * TAU; const px = x + Math.cos(a) * rx, py = y + Math.sin(a) * ry; ctx.moveTo(px + 30, py); ctx.arc(px, py, 30, 0, TAU); }
    ctx.moveTo(x + rx, y); ctx.ellipse(x, y, rx, ry, 0, 0, TAU); return;
  }
  const r = st === 'cold' ? 6 : Math.min(30, h / 2);
  rr(ctx, x - w / 2 - 26, y - h / 2 - 18, w + 52, h + 36, r);
}
function tailPath(ctx, x, y, tx, ty, wid = 16) {
  const dx = tx - x, dy = ty - y, L = Math.hypot(dx, dy) || 1, nx = -dy / L, ny = dx / L;
  ctx.beginPath(); ctx.moveTo(x + nx * wid, y + ny * wid); ctx.quadraticCurveTo(x + dx * 0.6 + nx * wid * 0.3, y + dy * 0.6 + ny * wid * 0.3, tx, ty);
  ctx.quadraticCurveTo(x + dx * 0.55 - nx * wid * 0.2, y + dy * 0.55 - ny * wid * 0.2, x - nx * wid, y - ny * wid); ctx.closePath();
}
function drawBubble(ctx, ln, k, alpha, S) {
  const st = ln.st, [, y, tx, ty] = ln.b;
  if (st === 'nar' || st === 'card') return drawNarration(ctx, ln, k, alpha, S);
  if (st === 'roar') return;
  const big = st === 'shout';
  const size = big ? 46 : st === 'whisper' ? 28 : 34;
  ctx.save(); ctx.globalAlpha = alpha;
  ctx.font = `${st === 'whisper' ? 500 : 700} ${size}px ${st === 'shout' ? F_FUN : F_SANS}`;
  const lines = wrapText(ctx, ln.text, big ? 440 : 420);
  const lh = size * 1.32, w = Math.max(...lines.map(l => ctx.measureText(l).width)), h = lines.length * lh;
  const pad = (big ? 60 : 26) + 14; const x = clamp(ln.b[0], w / 2 + pad, W - w / 2 - pad);
  const pop = st === 'whisper' ? 1 : eback(k);
  ctx.translate(x, y); ctx.scale(pop, pop); ctx.translate(-x, -y);
  if (big) shake(ctx, S.t, 3);
  const fill = st === 'cold' ? '#eaf6ff' : st === 'whisper' ? 'rgba(255,255,255,0.86)' : '#fff';
  const stroke = st === 'cold' ? '#21507c' : '#111';
  const lw = 3.5;
  ctx.lineJoin = 'round';
  if (st === 'think') {
    ctx.fillStyle = fill; ctx.strokeStyle = stroke; ctx.lineWidth = lw * 2;
    bubblePath(ctx, st, x, y, w, h); ctx.stroke(); ctx.fill();
    if (tx !== undefined) for (let i = 1; i <= 3; i++) { const p = i / 4; circle(ctx, lerp(x, tx, p + 0.15), lerp(y + h / 2, ty, p + 0.15), 14 - i * 3); ctx.stroke(); ctx.fill(); }
  } else {
    if (st === 'whisper') ctx.setLineDash([10, 8]);
    ctx.strokeStyle = stroke; ctx.lineWidth = lw * 2;
    bubblePath(ctx, st, x, y, w, h); ctx.stroke();
    if (tx !== undefined) { tailPath(ctx, x, y, tx, ty, st === 'shout' ? 26 : 18); ctx.stroke(); }
    ctx.setLineDash([]); ctx.fillStyle = fill;
    bubblePath(ctx, st, x, y, w, h); ctx.fill();
    if (tx !== undefined) { tailPath(ctx, x, y, tx, ty, st === 'shout' ? 26 : 18); ctx.fill(); }
  }
  if (st === 'off' && TL.names[ln.who]) {
    const nm = TL.names[ln.who]; ctx.font = `700 22px ${F_SANS}`; const nw = ctx.measureText(nm).width + 22;
    const bx = x - w / 2 - 20, by = y - h / 2 - 34;
    ctx.fillStyle = ln.who === 'zy' ? '#1d2433' : ln.who === 'smx' ? '#a8243a' : '#4a4a58'; rr(ctx, bx, by, nw, 32, 8); ctx.fill();
    ctx.fillStyle = '#fff'; ctx.textAlign = 'left'; ctx.textBaseline = 'middle'; ctx.fillText(nm, bx + 11, by + 17);
  }
  ctx.font = `${st === 'whisper' ? 500 : 700} ${size}px ${st === 'shout' ? F_FUN : F_SANS}`;
  ctx.fillStyle = st === 'cold' ? '#0c2a48' : st === 'whisper' ? '#555' : st === 'shout' ? '#b0101e' : '#141414';
  ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  lines.forEach((l, i) => ctx.fillText(l, x, y - h / 2 + lh * (i + 0.5) + 1));
  ctx.restore();
}
function drawNarration(ctx, ln, k, alpha, S) {
  const [x, y] = ln.b, card = ln.st === 'card';
  ctx.save(); ctx.globalAlpha = alpha;
  const size = card ? 66 : 31;
  ctx.font = `${card ? 900 : 600} ${size}px ${F_SERIF}`;
  const lines = wrapText(ctx, ln.text, card ? 600 : 560);
  const lh = size * 1.45, w = Math.max(...lines.map(l => ctx.measureText(l).width)), h = lines.length * lh;
  const dur = Math.max(0.3, ln.end - ln.start), shown = Math.floor([...ln.text].length * clamp((S.t - ln.start) / (dur * 0.7)));
  if (card) {
    const s = lerp(1.25, 1, eo(k)); ctx.translate(x, y); ctx.scale(s, s); ctx.translate(-x, -y);
    ctx.shadowColor = 'rgba(0,0,0,0.8)'; ctx.shadowBlur = 20; ctx.fillStyle = '#f5efe6'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    lines.forEach((l, i) => ctx.fillText(l, x, y - h / 2 + lh * (i + 0.5)));
    ctx.restore(); return;
  }
  ctx.fillStyle = 'rgba(10,10,18,0.78)'; ctx.fillRect(x - w / 2 - 34, y - h / 2 - 22, w + 68, h + 44);
  ctx.strokeStyle = '#c9a45c'; ctx.lineWidth = 2;
  for (const yy of [y - h / 2 - 22, y + h / 2 + 22]) { ctx.beginPath(); ctx.moveTo(x - w / 2 - 34, yy); ctx.lineTo(x + w / 2 + 34, yy); ctx.stroke(); }
  ctx.fillStyle = '#f3ede2'; ctx.textAlign = 'left'; ctx.textBaseline = 'middle';
  let left = shown;
  lines.forEach((l, i) => {
    const ch = [...l]; const vis = ch.slice(0, Math.max(0, left)).join(''); left -= ch.length;
    ctx.fillText(vis, x - ctx.measureText(l).width / 2, y - h / 2 + lh * (i + 0.5));
  });
  ctx.restore();
}
function drawLines(ctx, S) {
  const L = S.L;
  for (let i = 0; i < L.length; i++) {
    const l = L[i]; if (!l.b || l.st === 'none' || l.st === 'roar') continue;
    let end = l.end + (l.st === 'card' ? 0.25 : 0.9);
    for (let j = i + 1; j < L.length; j++) {
      const m = L[j]; if (m.b && Math.hypot(m.b[0] - l.b[0], m.b[1] - l.b[1]) < 90) { end = Math.min(end, m.start - 0.02); break; }
    }
    end = Math.min(end, S.d - 0.04);
    if (S.t < l.start - 0.1 || S.t > end) continue;
    const k = seg(S.t, l.start - 0.1, l.start + 0.12), out = 1 - seg(S.t, end - 0.12, end);
    drawBubble(ctx, l, k, Math.min(seg(S.t, l.start - 0.1, l.start), out), S);
  }
}

// ---------------------------------------------------------------- engine
let TL = null, CTX = null, CANVAS = null;
const SCENES = {};
function makeS(sh, t) {
  return {
    t, d: sh.dur, ev: sh.ev, L: sh.lines, sh, T: sh.start + t,
    talk(who) {
      for (const l of sh.lines) {
        if (l.who === who && t >= l.start && t < l.end) { const i = Math.floor((t - l.start) * TL.fps); return l.env[Math.min(i, l.env.length - 1)] || 0; }
      }
      return 0;
    },
    speaking(who) { return sh.lines.some(l => l.who === who && t >= l.start && t < l.end); },
    after(name, d = 0.3) { return seg(t, this.ev[name], this.ev[name] + d); },
  };
}
function renderFrame(T) {
  const ctx = CTX;
  let i = TL.shots.findIndex(s => T >= s.start && T < s.start + s.dur);
  if (i < 0) i = TL.shots.length - 1;
  const sh = TL.shots[i], S = makeS(sh, T - sh.start), sc = SCENES[sh.id];
  ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.globalAlpha = 1; ctx.globalCompositeOperation = 'source-over'; ctx.shadowBlur = 0; ctx.setLineDash([]);
  ctx.fillStyle = '#0b0b0f'; ctx.fillRect(0, 0, W, H);
  if (sc) { ctx.save(); sc.draw(ctx, S); ctx.restore(); }
  if (!sc || !sc.noBubbles) { ctx.save(); drawLines(ctx, S); ctx.restore(); }
  if (sc && sc.over) { ctx.save(); sc.over(ctx, S); ctx.restore(); }
  vignette(ctx, sc && sc.vig !== undefined ? sc.vig : 0.4);
  if (sc && sc.fadeIn && S.t < sc.fadeIn) fillAll(ctx, '#000', 1 - S.t / sc.fadeIn);
  if (sc && sc.fadeOut && S.t > S.d - sc.fadeOut) fillAll(ctx, '#000', (S.t - (S.d - sc.fadeOut)) / sc.fadeOut);
}
async function init() {
  CANVAS = document.getElementById('c'); CTX = CANVAS.getContext('2d');
  TL = await (await fetch('build/timeline.json')).json();
  const src = (await (await fetch('scenes.js')).text()) + (await (await fetch('lib.js')).text()) + (await (await fetch('engine.js')).text());
  let chars = TL.shots.flatMap(s => s.lines.map(l => l.text)).join('') + Object.values(TL.names).join('') + src;
  chars = [...new Set([...chars].filter(c => c.charCodeAt(0) > 127))].join('') + 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
  const specs = [`700 30px "Noto Sans SC"`, `500 30px "Noto Sans SC"`, `600 30px "Noto Serif SC"`, `900 30px "Noto Serif SC"`, `30px "ZCOOL KuaiLe"`, `30px "Ma Shan Zheng"`];
  await Promise.all(specs.map(s => document.fonts.load(s, chars)));
  await document.fonts.ready;
  window.TOTAL = TL.total;
  return TL.total;
}
window.renderFrame = renderFrame;
window.ready = init();
