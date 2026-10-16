// Storyboard: 7 scenes, 120 s. Each scene function gets local time t (seconds since the scene started).

// ================================================================ subtitles (absolute times)
const SUBS = [
  [2.4, 7.6, '考完就忘的线性代数，其实是整个 AI 的底层语言。'],
  [8.4, 12.4, '在 AI 眼里，一切数据都是向量。'],
  [12.4, 17.6, '一张 8×8 的灰度图，拉平之后就是一个 64 维向量。'],
  [18.2, 23.2, '每个词也被表示成一个向量（词嵌入），意思相近的词挨得也近。'],
  [23.2, 27.6, '而且方向本身有含义：国王 − 男人 + 女人 ≈ 女王。'],
  [28.3, 33.4, '矩阵是什么？它描述的是对整个空间的一次线性变换。'],
  [33.4, 38.6, '它的第一列、第二列，恰好是基向量 î、ĵ 变换后的落点。'],
  [39.2, 44.0, '神经网络的一层：先做 Wx + b，再过一个非线性函数 σ。'],
  [44.0, 48.8, 'ReLU 把空间“折”起来；层层叠加，就能拟合复杂的函数。'],
  [49.4, 52.6, '训练，就是用梯度下降不断调整 W 里的每一个数；'],
  [52.6, 55.7, '而反向传播本身，也是一连串的矩阵乘法。'],
  [56.3, 62.6, '点积衡量两个向量有多“像”：方向越一致，点积越大。'],
  [64.3, 68.6, 'ChatGPT 背后的 Transformer，最核心的运算正是点积。'],
  [68.6, 74.4, '每个词的 Q 与各个词的 K 做点积，得到一张注意力分数表。'],
  [74.4, 79.7, '“它”最关注的是“小猫”；按分数对 V 加权求和，就是注意力。'],
  [80.3, 85.0, '协方差矩阵的特征向量，指出数据变化最剧烈的方向。'],
  [85.0, 90.2, '投影到主方向上，就是 PCA 降维：维度少了，信息大多还在。'],
  [90.8, 94.2, 'SVD：任何矩阵 = 旋转 · 拉伸 · 旋转。'],
  [94.2, 97.4, '只保留最大的几个奇异值，就得到低秩近似。'],
  [97.8, 103.7, '微调大模型常用的 LoRA：冻结原矩阵，只训练两个细长的低秩矩阵。'],
  [104.3, 108.4, '大模型里绝大部分的计算，都是矩阵乘法。'],
  [108.4, 112.6, 'GPU 能同时做成千上万次乘加，于是成了 AI 的发动机。'],
  [113.4, 119.4, '下次再翻开线代课本，你读到的，正是 AI 的母语。'],
].map(([t0, t1, text]) => ({ t0, t1, text }));

// ================================================================ 0 · title (0–8)
function s0(t) {
  const pl = new Plane(960, 760, 90);
  const k = prog(t, 2.8, 7.8);
  const M = [[1 + 0.2 * k, 0.45 * k], [0.18 * k, 1 + 0.08 * k]];
  const f = (x, y) => [M[0][0] * x + M[0][1] * y, M[1][0] * x + M[1][1] * y];
  grid(pl, { f, alpha: 0.6 * prog(t, 0, 1.6), xr: [-15, 15], yr: [-6, 12], ext: 4 });
  vec(pl, [0, 0], f(1, 0), { color: C.green, width: 7, grow: prog(t, 0.6, 1.4) });
  vec(pl, [0, 0], f(0, 1), { color: C.red, width: 7, grow: prog(t, 0.8, 1.6) });
  withAlpha(prog(t, 1.0, 2.6), () => {
    const g = ctx.createRadialGradient(960, 430, 60, 960, 430, 760);
    g.addColorStop(0, 'rgba(8,10,14,0.94)'); g.addColorStop(0.55, 'rgba(8,10,14,0.7)'); g.addColorStop(1, 'rgba(8,10,14,0)');
    ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
  });
  const a = prog(t, 1.4, 2.8);
  text('线性代数：AI 的母语', 960, 410 + 24 * (1 - a), { size: 108, weight: 700, font: SERIF, alpha: a });
  text('LINEAR ALGEBRA  ×  ARTIFICIAL INTELLIGENCE', 964, 520, { size: 26, color: C.grey, ls: 8, alpha: prog(t, 2.2, 3.4) });
}

// ================================================================ 1 · data are vectors (8–28)
const DIGIT = [ // a handwritten "7", grey levels 0..16
  [0, 0, 0, 0, 0, 0, 0, 0],
  [0, 3, 12, 15, 16, 16, 10, 0],
  [0, 2, 8, 6, 5, 13, 12, 0],
  [0, 0, 0, 0, 4, 15, 3, 0],
  [0, 0, 0, 1, 13, 8, 0, 0],
  [0, 0, 0, 8, 14, 1, 0, 0],
  [0, 0, 3, 16, 6, 0, 0, 0],
  [0, 0, 6, 13, 1, 0, 0, 0],
];
function s1(t) {
  section('01', '数据，就是向量', prog(t, 0.2, 1.0));

  // --- A: an image flattened into a vector
  const aA = 1 - prog(t, 9.4, 10.2);
  if (aA > 0) {
    const cs = 44, ix = 960 - 4 * cs, iy = 150, sx = 320, sy = 720, st = 20, ss = 17;
    const ap = prog(t, 0.3, 1.4), num = prog(t, 1.6, 2.4) * (1 - prog(t, 3.5, 4.1));
    for (let r = 0; r < 8; r++) for (let c = 0; c < 8; c++) {
      const v = DIGIT[r][c] / 16, k = r * 8 + c, m = prog(t, 4.1 + r * 0.38, 5.3 + r * 0.38);
      const x = lerp(ix + c * cs + cs / 2, sx + k * st + st / 2, m), y = lerp(iy + r * cs + cs / 2, sy, m), z = lerp(cs - 3, ss, m);
      withAlpha(ap * aA, () => {
        ctx.fillStyle = mix('#1a1f29', '#ffffff', v); ctx.fillRect(x - z / 2, y - z / 2, z, z);
        ctx.strokeStyle = 'rgba(255,255,255,0.16)'; ctx.lineWidth = 1; ctx.strokeRect(x - z / 2 + .5, y - z / 2 + .5, z - 1, z - 1);
      });
      if (num > 0) text(v.toFixed(1), x, y + 1, { size: 15, color: v >= 0.4 ? '#111' : '#c9ced6', alpha: num * aA });
    }
    text('8 × 8 = 64 个像素', ix + 8 * cs + 40, iy + 4 * cs, { align: 'left', size: 34, color: C.light, alpha: prog(t, 1.6, 2.4) * (1 - prog(t, 3.9, 4.5)) * aA });
    text('逐行拉平', 960, 600, { size: 30, color: C.grey, alpha: fadeIO(t, 4.2, 7.6, 0.4) * aA });
    const bA = prog(t, 7.4, 8.0) * aA;
    bracket(sx - 10, sy - 20, 40, 'l', C.white, bA); bracket(sx + 64 * st + 8, sy - 20, 40, 'r', C.white, bA);
    tex('x64', 960, 820, { wipe: lin(t, 7.7, 8.9), alpha: aA });
  }

  // --- B: word embeddings
  const aB = prog(t, 10.0, 11.0);
  if (aB > 0) {
    const pl = new Plane(960, 470, 95);
    grid(pl, { alpha: 0.5 * aB, xr: [-10.5, 10.5], yr: [-4.5, 4.9] });
    const FAINT = [['猫', [-6.3, -2.4]], ['狗', [-5.5, -2.9]], ['老虎', [-6.9, -3.3]], ['苹果', [6.1, -2.5]], ['香蕉', [6.9, -2.0]],
      ['葡萄', [6.4, -3.4]], ['北京', [-6.5, 2.8]], ['上海', [-5.6, 3.4]], ['东京', [-7.4, 3.6]]];
    FAINT.forEach(([n, p], i) => {
      const a = prog(t, 12.8 + i * 0.1, 13.3 + i * 0.1) * aB, [x, y] = pl.P(...p);
      dot(x, y, 6, C.grey, a); text(n, x + 14, y, { align: 'left', size: 26, color: C.grey, alpha: a });
    });
    const WORDS = [['男人', [-3.2, -0.6], C.blue, 11.0], ['女人', [-2.6, 1.6], C.pink, 11.4], ['国王', [2.2, -1.2], C.gold, 11.8], ['女王', [2.95, 1.15], C.purple, 12.2]];
    for (const [n, p, c, t0] of WORDS) {
      vec(pl, [0, 0], p, { color: c, width: 4, head: 18, grow: prog(t, t0, t0 + 0.7), alpha: aB });
      const L = Math.hypot(...p), [x, y] = pl.P(p[0] + p[0] / L * 0.55, p[1] + p[1] / L * 0.55);
      const sc = n === '女王' ? 1 + 0.25 * Math.sin(Math.PI * lin(t, 18.0, 18.8)) : 1;
      text(n, x, y, { size: 34 * sc, weight: 700, color: c, alpha: prog(t, t0 + 0.4, t0 + 0.9) * aB });
    }
    const m = [-3.2, -0.6], w = [-2.6, 1.6], k = [2.2, -1.2], d = [w[0] - m[0], w[1] - m[1]];
    vec(pl, m, w, { color: C.yellow, width: 5, head: 20, grow: prog(t, 15.4, 16.3), alpha: aB });
    { const [x, y] = pl.P(m[0] + d[0] / 2 + 0.25, m[1] + d[1] / 2); text('女人 − 男人', x, y, { align: 'left', size: 26, color: C.yellow, alpha: prog(t, 15.9, 16.4) * aB }); }
    if (t > 16.4) { const s = lerp2(m, k, prog(t, 16.6, 18.0)); vec(pl, s, [s[0] + d[0], s[1] + d[1]], { color: C.yellow, width: 5, head: 20, alpha: aB }); }
    { const [x, y] = pl.P(k[0] + d[0], k[1] + d[1]);
      withAlpha(prog(t, 17.9, 18.4) * aB, () => { ctx.strokeStyle = C.yellow; ctx.setLineDash([6, 6]); ctx.lineWidth = 2.5; ctx.beginPath(); ctx.arc(x + 7, y - 7, 34, 0, 7); ctx.stroke(); }); }
    tex('analogy', 960, 102, { wipe: lin(t, 16.0, 17.3), bg: true, alpha: aB });
    const note = '示意图：真实的词向量通常有几百到几千维';
    panel(1860 - textWidth(note, 22) - 16, 862, textWidth(note, 22) + 32, 40, prog(t, 12.5, 13.5) * aB, 8);
    text(note, 1860, 883, { align: 'right', size: 22, color: C.grey, alpha: prog(t, 12.5, 13.5) * aB });
  }
}

// ================================================================ 2 · matrix = linear map = a network layer (28–56)
const NET = (() => {
  const r = rng(7), L = [3, 5, 5, 2], W0 = [], W1 = [];
  for (let l = 0; l < 3; l++) {
    W0.push([]); W1.push([]);
    for (let i = 0; i < L[l]; i++) {
      W0[l].push([]); W1[l].push([]);
      for (let j = 0; j < L[l + 1]; j++) { W0[l][i].push(r() * 2 - 1); W1[l][i].push(r() * 2 - 1); }
    }
  }
  return { L, W0, W1 };
})();

function s2(t) {
  section('02', '矩阵 = 线性变换 = 神经网络的一层', prog(t, 0.2, 1.0));

  const aP = 1 - prog(t, 20.6, 21.4);
  if (aP > 0) {
    const pl = new Plane(1000, 600, 80);
    const M = [[2, -1], [1, 1]], b = [1, -0.5];
    const kM = prog(t, 2.6, 5.4), kB = prog(t, 12.8, 14.0), kR = prog(t, 16.0, 18.8);
    const lm = (x, y) => [lerp(x, M[0][0] * x + M[0][1] * y, kM), lerp(y, M[1][0] * x + M[1][1] * y, kM)];
    const F = (x, y) => {
      let [X, Y] = lm(x, y); X += b[0] * kB; Y += b[1] * kB;
      return [lerp(X, Math.max(X, 0), kR), lerp(Y, Math.max(Y, 0), kR)];
    };
    const aG = prog(t, 0, 1.0) * aP;
    grid(pl, { alpha: 0.2 * aG, color: '#7a7f88', sub: false, axes: false, xr: [-13, 12], yr: [-7, 8] });
    grid(pl, { f: F, alpha: aG, xr: [-14, 14], yr: [-14, 14], n: kR > 0 ? 160 : 2 });

    // basis vectors and a sample vector x = (1, 2)
    const aV = prog(t, 0.6, 1.4) * (1 - prog(t, 11.0, 11.8)) * aP;
    const I = pl.P(...lm(1, 0)), J = pl.P(...lm(0, 1)), Xv = pl.P(...lm(1, 2)), O = pl.P(0, 0);
    arrow(O[0], O[1], Xv[0], Xv[1], { color: C.yellow, width: 6, grow: prog(t, 1.8, 2.5), alpha: aV });
    arrow(O[0], O[1], I[0], I[1], { color: C.green, width: 7, grow: prog(t, 0.6, 1.3), alpha: aV });
    arrow(O[0], O[1], J[0], J[1], { color: C.red, width: 7, grow: prog(t, 0.8, 1.5), alpha: aV });
    tex('ihat', I[0] + 22, I[1] + 32, { alpha: prog(t, 1.1, 1.6) * aV });
    tex('jhat', J[0] - 30, J[1] - 22, { alpha: prog(t, 1.3, 1.8) * aV });
    const xl = prog(t, 3.6, 4.6);
    tex('xv', Xv[0] + 22, Xv[1], { align: 'left', alpha: prog(t, 2.2, 2.7) * (1 - xl) * aV });
    tex('Wxv', Xv[0] + 22, Xv[1], { align: 'left', alpha: xl * aV });
    const cl = prog(t, 5.6, 6.3) * aV;
    panel(I[0] + 14, I[1] - 52, textWidth('(2, 1)', 30, 700) + 20, 44, cl, 8);
    text('(2, 1)', I[0] + 24, I[1] - 30, { align: 'left', size: 30, weight: 700, color: C.green, alpha: cl });
    panel(J[0] - 34 - textWidth('(−1, 1)', 30, 700), J[1] + 14, textWidth('(−1, 1)', 30, 700) + 20, 44, cl, 8);
    text('(−1, 1)', J[0] - 24, J[1] + 36, { align: 'right', size: 30, weight: 700, color: C.red, alpha: cl });

    const aT = (1 - prog(t, 10.4, 11.2)) * aP;
    tex('Wmat', 80, 200, { align: 'left', bg: true, wipe: lin(t, 1.2, 2.3), alpha: aT });
    tex('Wcols', 80, 370, { align: 'left', bg: true, wipe: lin(t, 6.6, 8.0), alpha: aT });

    // --- B: one layer of a network, and ReLU folding space
    tex('layer', 80, 190, { align: 'left', bg: true, wipe: lin(t, 11.3, 12.5), alpha: aP });
    panel(62, 272, 560, 176, prog(t, 12.3, 12.8) * aP);
    [['Wx：线性变换（拉伸、旋转、剪切）', 12.5], ['+ b：平移', 12.9], ['σ：非线性函数，例如 ReLU', 14.2]]
      .forEach(([s, t0], i) => text(s, 92, 312 + i * 50, { align: 'left', size: 30, color: C.light, alpha: prog(t, t0, t0 + 0.5) * aP }));
    const aR = prog(t, 14.2, 15.0) * aP;
    if (aR > 0) {
      const bx = 1560, by = 110, bw = 300, bh = 230, ox = bx + bw / 2, oy = by + bh * 0.72, s = 50;
      panel(bx, by, bw, bh + 60, aR);
      line(bx + 20, oy, bx + bw - 20, oy, C.white, 2, aR * 0.8); line(ox, by + 20, ox, by + bh - 10, C.white, 2, aR * 0.8);
      withAlpha(aR, () => {
        ctx.strokeStyle = C.yellow; ctx.lineWidth = 5; ctx.lineJoin = 'round';
        ctx.beginPath(); ctx.moveTo(bx + 25, oy); ctx.lineTo(ox, oy); ctx.lineTo(ox + 2.5 * s, oy - 2.5 * s); ctx.stroke();
      });
      tex('relu', ox, by + bh + 26, { alpha: aR });
    }
  }

  // --- C: a whole network, trained by gradient descent
  const aN = prog(t, 21.0, 21.9);
  if (aN > 0) drawNet(t, aN);
}

function drawNet(t, a) {
  const xs = [520, 820, 1120, 1420], cy = 500, dy = 100, R = 24, L = NET.L;
  const ys = (l, i) => cy + (i - (L[l] - 1) / 2) * dy;
  const tr = prog(t, 23.0, 27.8);
  tex('net', 960, 150, { wipe: lin(t, 21.6, 22.8), alpha: a });
  for (let l = 0; l < 3; l++) for (let i = 0; i < L[l]; i++) for (let j = 0; j < L[l + 1]; j++) {
    const w = lerp(NET.W0[l][i][j], NET.W1[l][i][j], tr);
    line(xs[l] + R, ys(l, i), xs[l + 1] - R, ys(l + 1, j), w > 0 ? C.blue : C.red, 0.8 + 3.4 * Math.abs(w), a * (0.22 + 0.6 * Math.abs(w)));
  }
  // forward pulses (white) then backprop pulses (gold)
  if (t > 22.0 && t < 27.9) {
    const P = 1.45, u = ((t - 22.0) % P) / P, fwd = u < 0.5, p = fwd ? u / 0.5 : (u - 0.5) / 0.5;
    const g = Math.min(2, Math.floor(p * 3)), fr = p * 3 - g, l = fwd ? g : 2 - g, k = fwd ? fr : 1 - fr;
    const pa = a * Math.sin(Math.PI * fr) ** 0.5;
    for (let i = 0; i < L[l]; i++) for (let j = 0; j < L[l + 1]; j++) {
      const x = lerp(xs[l] + R, xs[l + 1] - R, k), y = lerp(ys(l, i), ys(l + 1, j), k);
      dot(x, y, 5, fwd ? C.white : C.gold, pa * 0.9);
    }
  }
  for (let l = 0; l < 4; l++) for (let i = 0; i < L[l]; i++) withAlpha(a, () => {
    ctx.fillStyle = '#151a22'; ctx.strokeStyle = C.white; ctx.lineWidth = 2.5;
    ctx.beginPath(); ctx.arc(xs[l], ys(l, i), R, 0, 7); ctx.fill(); ctx.stroke();
  });
  ['输入 x', '隐藏层 1', '隐藏层 2', '输出'].forEach((s, l) => text(s, xs[l], 236, { size: 28, color: C.grey, alpha: a }));
  ['W1', 'W2', 'W3'].forEach((k, l) => tex(k, (xs[l] + xs[l + 1]) / 2, 785, { alpha: prog(t, 22.2 + l * 0.2, 22.8 + l * 0.2) * a }));
  // loss curve
  const la = prog(t, 22.6, 23.2) * a;
  if (la > 0) {
    const bx = 1560, by = 330, bw = 300, bh = 200;
    panel(bx, by, bw, bh, la);
    line(bx + 24, by + bh - 24, bx + bw - 16, by + bh - 24, C.white, 2, la * 0.7); line(bx + 24, by + 16, bx + 24, by + bh - 24, C.white, 2, la * 0.7);
    text('损失 loss', bx + 36, by + 30, { align: 'left', size: 22, color: C.grey, alpha: la });
    withAlpha(la, () => {
      ctx.strokeStyle = C.gold; ctx.lineWidth = 3; ctx.beginPath();
      for (let i = 0; i <= 100; i++) {
        const s = tr * i / 100, Lv = 0.08 + 0.85 * Math.exp(-4.5 * s) + 0.04 * Math.sin(37 * s) * Math.exp(-2 * s);
        const x = bx + 26 + s * (bw - 50), y = by + bh - 26 - Lv * (bh - 60);
        i ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
      }
      ctx.stroke();
    });
    tex('grad', bx + bw / 2, by + bh + 50, { alpha: prog(t, 23.2, 23.8) * a });
  }
}

// ================================================================ 3 · dot product -> attention (56–80)
const ATT = (() => {
  const tok = ['小猫', '吃', '了', '鱼', '因为', '它', '饿'];
  const A = [[1], [.7, .3], [.2, .6, .2], [.15, .55, .1, .2], [.3, .2, .1, .15, .25], [.62, .04, .04, .12, .05, .13], [.45, .08, .04, .05, .1, .25, .03]];
  const r = rng(11), R = (n, m) => Array.from({ length: n }, () => Array.from({ length: m }, () => r() * 2 - 1));
  const X = R(7, 6), Q = R(7, 4), K = R(7, 4), V = R(7, 4);
  const S = A.map(row => { const c = r() * 1.5 - 0.5; return row.map(a => Math.log(a) + c); });
  const O = A.map(row => [0, 1, 2, 3].map(k => row.reduce((s, a, j) => s + a * V[j][k], 0)));
  return { tok, A, X, Q, K, V, S, O };
})();

function s3(t) {
  section('03', '点积 → 注意力机制', prog(t, 0.2, 1.0));
  const aA = 1 - prog(t, 7.4, 8.2);
  if (aA > 0) dotScene(t, aA);
  const aB = prog(t, 7.9, 8.7);
  if (aB > 0) attnScene(t, aB);
}

function dotScene(t, a) {
  const pl = new Plane(520, 600, 105);
  ctx.save(); ctx.beginPath(); ctx.rect(60, 130, 1060, 790); ctx.clip();
  grid(pl, { alpha: 0.5 * a, xr: [-5, 6], yr: [-4, 5] });
  ctx.restore();
  const A = [3, 1], la = Math.hypot(...A), angA = Math.atan2(A[1], A[0]);
  const phi = keys(t, [[0.9, 25], [2.6, 90], [4.3, 155], [6.0, 35]]) * Math.PI / 180;
  const lb = 2.7, angB = angA + phi, B = [lb * Math.cos(angB), lb * Math.sin(angB)];
  const val = A[0] * B[0] + A[1] * B[1], cos = Math.cos(phi);
  const kp = val / (la * la), Pj = [A[0] * kp, A[1] * kp];
  const aPr = prog(t, 1.4, 2.0) * a;
  line(...pl.P(-A[0] * 1.4, -A[1] * 1.4), ...pl.P(A[0] * 1.75, A[1] * 1.75), C.blue, 1.5, aPr * 0.4, [8, 8]);
  line(...pl.P(0, 0), ...pl.P(...Pj), C.yellow, 12, aPr * 0.45);
  line(...pl.P(...B), ...pl.P(...Pj), C.white, 2, aPr * 0.6, [6, 6]);
  withAlpha(prog(t, 1.0, 1.6) * a, () => {
    ctx.strokeStyle = C.white; ctx.lineWidth = 2.5; ctx.beginPath(); ctx.arc(pl.ox, pl.oy, 0.62 * pl.s, -angB, -angA); ctx.stroke();
  });
  const am = (angA + angB) / 2;
  tex('theta', ...pl.P(0.95 * Math.cos(am), 0.95 * Math.sin(am)), { alpha: prog(t, 1.2, 1.7) * a });
  vec(pl, [0, 0], A, { color: C.blue, width: 7, grow: prog(t, 0.2, 0.8), alpha: a });
  vec(pl, [0, 0], B, { color: C.yellow, width: 7, grow: prog(t, 0.5, 1.1), alpha: a });
  tex('av', ...pl.P(A[0] + 0.3, A[1] - 0.3), { alpha: prog(t, 0.6, 1.0) * a });
  tex('bv', ...pl.P(B[0] * 1.14, B[1] * 1.14), { alpha: prog(t, 0.9, 1.3) * a });

  const rx = 1500, ar = prog(t, 2.4, 3.0) * a;
  tex('dot1', rx, 250, { wipe: lin(t, 1.2, 2.3), alpha: a });
  tex('dot2', rx, 340, { wipe: lin(t, 2.0, 2.8), alpha: a });
  const col = cos > 0.15 ? C.green : cos < -0.15 ? C.red : C.white;
  tex('dotlbl', rx - 6, 470, { align: 'right', alpha: ar });
  text((val < 0 ? '−' : '') + Math.abs(val).toFixed(2), rx + 10, 474, { align: 'left', size: 56, weight: 700, color: col, alpha: ar });
  const bw = 300, by = 565;
  withAlpha(ar, () => {
    ctx.fillStyle = 'rgba(255,255,255,0.08)'; rr(rx - bw, by - 9, 2 * bw, 18, 9); ctx.fill();
    ctx.fillStyle = col; const v = cos * bw; ctx.fillRect(Math.min(rx, rx + v), by - 9, Math.abs(v), 18);
  });
  line(rx, by - 22, rx, by + 22, C.white, 2, ar);
  const d1 = clamp((cos - 0.35) / 0.25), d0 = clamp(1 - Math.abs(cos) / 0.3), d2 = clamp((-cos - 0.35) / 0.25);
  text('方向接近 → 点积大', rx, 645, { size: 34, color: C.green, alpha: ar * d1 });
  text('互相垂直 → 点积 ≈ 0', rx, 645, { size: 34, alpha: ar * d0 });
  text('方向相反 → 点积为负', rx, 645, { size: 34, color: C.red, alpha: ar * d2 });
}

function attnScene(t, a) {
  const D = ATT, y0 = 290, rs = 64, ch = 56, rowY = i => y0 + i * rs;
  const opt = { cw: 26, ch, gx: 4, gy: rs - ch, alpha: a };
  D.tok.forEach((s, i) => text(s, 128, rowY(i) + ch / 2, { align: 'right', size: 28, alpha: prog(t, 8.0 + i * 0.08, 8.5 + i * 0.08) * a }));
  cells(145, y0, D.X, { ...opt, cellAlpha: i => prog(t, 8.1 + i * 0.08, 8.6 + i * 0.08) });
  tex('X', 232, 250, { alpha: prog(t, 8.2, 8.8) * a });
  for (const [k, M, x, t0] of [['Q', D.Q, 400, 9.0], ['K', D.K, 560, 9.4], ['V', D.V, 720, 9.8]]) {
    cells(x, y0, M, { ...opt, cellAlpha: (i, j) => prog(t, t0 + j * 0.1, t0 + 0.4 + j * 0.1) });
    tex(k, x + 57, 250, { alpha: prog(t, t0, t0 + 0.5) * a });
  }

  // attention score table, filled row by row (causal: a word only looks at earlier words)
  const hx = 960, cs = 58, t0 = 12.4, dr = 0.42, kS = prog(t, 15.4, 16.4);
  const la = prog(t, 11.6, 12.2) * a;
  D.tok.forEach((s, j) => text(s, hx + j * rs + cs / 2, y0 - 26, { size: 24, color: C.light, alpha: la }));
  D.tok.forEach((s, i) => text(s, hx - 14, rowY(i) + cs / 2, { align: 'right', size: 24, color: C.light, alpha: la }));
  tex('scores', hx + 3.5 * rs - 3, 212, { alpha: la * (1 - kS) });
  tex('soft', hx + 3.5 * rs - 3, 212, { alpha: kS * a });
  for (let i = 0; i < 7; i++) for (let j = 0; j < 7; j++) {
    const ap = prog(t, t0 + i * dr + j * 0.04, t0 + i * dr + j * 0.04 + 0.25) * a; if (ap <= 0) continue;
    const x = hx + j * rs, y = rowY(i);
    withAlpha(ap, () => {
      if (j > i) { ctx.fillStyle = 'rgba(255,255,255,0.045)'; ctx.fillRect(x, y, cs, cs); return; }
      ctx.fillStyle = mix('#161b24', C.blue, clamp((D.S[i][j] + 3.5) / 4.5)); ctx.fillRect(x, y, cs, cs);
      ctx.globalAlpha *= kS; ctx.fillStyle = mix('#161b24', C.yellow, Math.pow(D.A[i][j], 0.6)); ctx.fillRect(x, y, cs, cs);
    });
  }
  if (t > t0 && t < t0 + 7 * dr) {
    const i = Math.floor((t - t0) / dr);
    outline(397, rowY(i) - 3, 120, ch + 6, C.yellow, a);
    outline(557, y0 - 3, 120, 6 * rs + ch + 6, C.white, a * 0.6, 2);
    outline(hx - 4, rowY(i) - 4, 7 * rs + 2, cs + 8, C.yellow, a * 0.8, 2);
  }
  // the row for "它"
  const h5 = prog(t, 17.4, 18.0) * a;
  if (h5 > 0) {
    outline(hx - 5, rowY(5) - 5, 6 * rs + 4, cs + 10, C.yellow, h5, 3.5);
    for (let j = 0; j <= 5; j++) text(D.A[5][j].toFixed(2), hx + j * rs + cs / 2, rowY(5) + cs / 2 + 1, { size: 19, weight: 700, color: D.A[5][j] > 0.3 ? '#1a1a1a' : C.white, alpha: h5 });
    const vg = prog(t, 18.2, 18.8) * a;
    for (let j = 0; j <= 5; j++) outline(717, rowY(j) - 3, 120, ch + 6, C.yellow, vg * clamp(D.A[5][j] * 1.6 + 0.08), 3);
    arrow(hx + 7 * rs - 2, rowY(5) + cs / 2, 1482, rowY(5) + cs / 2, { color: C.yellow, width: 4, head: 16, grow: prog(t, 18.6, 19.2), alpha: a });
  }
  cells(1490, y0, D.O, { ...opt, colorFn: v => cellColor(v * 1.6), cellAlpha: i => i === 5 ? prog(t, 18.9, 19.5) : prog(t, 19.8 + i * 0.1, 20.3 + i * 0.1) });
  text('输出', 1547, 250, { size: 28, alpha: prog(t, 18.8, 19.3) * a });
  tex('attn', 960, 832, { bg: true, wipe: lin(t, 20.2, 21.4), alpha: a });
}

// ================================================================ 4 · eigenvectors, SVD -> PCA, LoRA (80–104)
const PCA = (() => {
  const r = rng(5), th = Math.PI / 6, raw = [];
  for (let i = 0; i < 160; i++) {
    const u = gauss(r) * 2.0, v = gauss(r) * 0.55;
    raw.push([u * Math.cos(th) - v * Math.sin(th), u * Math.sin(th) + v * Math.cos(th)]);
  }
  const mx = raw.reduce((s, p) => s + p[0], 0) / raw.length, my = raw.reduce((s, p) => s + p[1], 0) / raw.length;
  const pts = raw.map(p => [p[0] - mx, p[1] - my]), n = pts.length;
  const sxx = pts.reduce((s, p) => s + p[0] * p[0], 0) / n, syy = pts.reduce((s, p) => s + p[1] * p[1], 0) / n, sxy = pts.reduce((s, p) => s + p[0] * p[1], 0) / n;
  const tr = sxx + syy, det = sxx * syy - sxy * sxy, q = Math.sqrt(tr * tr / 4 - det), l1 = tr / 2 + q, l2 = tr / 2 - q;
  let v1 = [sxy, l1 - sxx]; const L = Math.hypot(...v1); v1 = [v1[0] / L, v1[1] / L];
  return { pts, l1, l2, v1, v2: [-v1[1], v1[0]], keep: l1 / (l1 + l2) };
})();

const SVD = (() => {
  const r = rng(21), n = 10;
  const orth = () => {
    const Q = [];
    while (Q.length < n) {
      let v = Array.from({ length: n }, () => gauss(r));
      for (const q of Q) { const d = v.reduce((s, x, i) => s + x * q[i], 0); v = v.map((x, i) => x - d * q[i]); }
      const L = Math.hypot(...v); Q.push(v.map(x => x / L));
    }
    return Q;
  };
  return { n, U: orth(), V: orth(), sig: [9.1, 6.2, 3.8, 1.2, 0.6, 0.35, 0.2, 0.12, 0.06, 0.03] };
})();

const LORA = (() => {
  const r = rng(33), R = (n, m) => Array.from({ length: n }, () => Array.from({ length: m }, () => r() * 2 - 1));
  return { W0: R(12, 12), B: R(12, 2), A: R(2, 12), ph: R(12, 12) };
})();

function s4(t) {
  section('04', '特征值 · SVD → PCA · LoRA', prog(t, 0.2, 1.0));
  const aA = prog(t, 0, 0.8) * (1 - prog(t, 9.8, 10.5));
  if (aA > 0) pcaScene(t, aA);
  const aS = prog(t, 10.4, 11.0) * (1 - prog(t, 16.9, 17.5));
  if (aS > 0) svdScene(t, aS);
  const aL = prog(t, 17.3, 18.0);
  if (aL > 0) loraScene(t, aL);
}

function pcaScene(t, a) {
  const pl = new Plane(960, 520, 70), D = PCA, v1 = D.v1, v2 = D.v2, s1 = 2 * Math.sqrt(D.l1), s2 = 2 * Math.sqrt(D.l2);
  grid(pl, { alpha: 0.35 * a, xr: [-14, 14], yr: [-7, 8] });
  line(...pl.P(-v1[0] * 9, -v1[1] * 9), ...pl.P(v1[0] * 9, v1[1] * 9), C.yellow, 2, prog(t, 4.4, 5.0) * a * 0.6);
  const ea = prog(t, 2.0, 3.0) * (1 - prog(t, 5.2, 6.0)) * a;
  withAlpha(ea, () => {
    ctx.strokeStyle = C.white; ctx.lineWidth = 2; ctx.setLineDash([10, 8]);
    ctx.beginPath(); ctx.ellipse(pl.ox, pl.oy, s1 * pl.s, s2 * pl.s, -Math.atan2(v1[1], v1[0]), 0, Math.PI * 2 * prog(t, 2.0, 3.0)); ctx.stroke();
  });
  D.pts.forEach((p, i) => {
    const ap = prog(t, 0.3 + (i % 40) * 0.03, 0.7 + (i % 40) * 0.03);
    const s = p[0] * v1[0] + p[1] * v1[1], q = [s * v1[0], s * v1[1]];
    const d = (i * 0.618) % 1 * 1.4, kp = prog(t, 5.2 + d, 6.2 + d);
    if (kp > 0 && kp < 1) line(...pl.P(...p), ...pl.P(...q), C.white, 1, a * 0.4 * Math.sin(Math.PI * kp), [3, 4]);
    const [x, y] = pl.P(...lerp2(p, q, kp));
    dot(x, y, 5, mix(C.blue, C.yellow, kp), ap * a * 0.9);
  });
  vec(pl, [0, 0], [v1[0] * s1, v1[1] * s1], { color: C.yellow, width: 7, grow: prog(t, 2.4, 3.2), alpha: a });
  const a2 = (1 - prog(t, 7.8, 8.4)) * a;
  vec(pl, [0, 0], [v2[0] * s2, v2[1] * s2], { color: C.green, width: 7, grow: prog(t, 2.7, 3.4), alpha: a2 });
  tex('v1', ...pl.P(v1[0] * s1 + v2[0] * 0.55, v1[1] * s1 + v2[1] * 0.55), { alpha: prog(t, 3.0, 3.5) * a });
  tex('v2', ...pl.P(v2[0] * (s2 + 0.5), v2[1] * (s2 + 0.5)), { alpha: prog(t, 3.2, 3.7) * a2 });
  tex('cov', 80, 190, { align: 'left', bg: true, wipe: lin(t, 1.6, 2.6), alpha: a });
  const na = prog(t, 2.4, 3.0) * a, note = '（X 已减去均值）';
  panel(62, 240, textWidth(note, 24) + 36, 44, na, 8);
  text(note, 80, 263, { align: 'left', size: 24, color: C.grey, alpha: na });
  const ka = prog(t, 8.2, 8.8) * a;
  panel(1390, 220, 380, 140, ka);
  text('2 维 → 1 维', 1580, 265, { size: 44, weight: 700, color: C.yellow, alpha: ka });
  text(`仍保留 ${Math.round(D.keep * 100)}% 的方差`, 1580, 322, { size: 28, color: C.light, alpha: ka });
}

function svdScene(t, a) {
  const D = SVD, n = D.n, cw = 23, g = 3, st = cw + g, y = 380;
  const kT = prog(t, 14.4, 15.8), m = k => k < 3 ? 1 : 1 - kT;
  const Wm = Array.from({ length: n }, (_, i) => Array.from({ length: n }, (_, j) => {
    let s = 0; for (let k = 0; k < n; k++) s += D.sig[k] * m(k) * D.U[k][i] * D.V[k][j]; return s / 3;
  }));
  const Um = Array.from({ length: n }, (_, i) => Array.from({ length: n }, (_, k) => D.U[k][i] * 2.5));
  const Vt = Array.from({ length: n }, (_, k) => Array.from({ length: n }, (_, j) => D.V[k][j] * 2.5));
  const Sg = Array.from({ length: n }, (_, i) => Array.from({ length: n }, (_, j) => i === j ? D.sig[i] : 0));
  const kf = k => k < 3 ? 1 : lerp(1, 0.12, kT);
  const ap = x0 => (i, j) => prog(t, x0 + (i + j) * 0.02, x0 + 0.3 + (i + j) * 0.02);
  const pos = [340, 720, 1020, 1320];
  cells(pos[0], y, Wm, { cw, ch: cw, gx: g, alpha: a, cellAlpha: ap(10.9) });
  text('=', 660, y + 5 * st, { size: 64, color: C.light, alpha: prog(t, 11.2, 11.6) * a });
  cells(pos[1], y, Um, { cw, ch: cw, gx: g, alpha: a, cellAlpha: (i, k) => ap(11.1)(i, k) * kf(k) });
  cells(pos[2], y, Sg, { cw, ch: cw, gx: g, alpha: a, colorFn: (v, i, j) => i === j ? mix('#161b24', C.yellow, Math.sqrt(v / 9.1)) : '#161b24',
    cellAlpha: (i, j) => ap(11.3)(i, j) * (i === j ? kf(i) : 0.6) });
  cells(pos[3], y, Vt, { cw, ch: cw, gx: g, alpha: a, cellAlpha: (k, j) => ap(11.5)(k, j) * kf(k) });
  ['旋转', '拉伸', '旋转'].forEach((s, i) => text(s, pos[i + 1] + 5 * st, y + n * st + 40, { size: 34, color: C.light, alpha: prog(t, 12.2 + i * 0.3, 12.7 + i * 0.3) * a }));
  tex('svd', 960, 220, { wipe: lin(t, 10.8, 11.8), alpha: a * (1 - prog(t, 14.6, 15.4)) });
  tex('svdr', 960, 220, { alpha: a * prog(t, 14.6, 15.4) });
  const ka = prog(t, 15.4, 16.0) * a;
  outline(pos[1] - 5, y - 5, 3 * st + 7, n * st + 7, C.yellow, ka);
  outline(pos[2] - 5, y - 5, 3 * st + 7, 3 * st + 7, C.yellow, ka);
  outline(pos[3] - 5, y - 5, n * st + 7, 3 * st + 7, C.yellow, ka);
  text('只保留最大的 r 个奇异值', 1150, y + n * st + 96, { size: 28, color: C.yellow, alpha: ka });
}

function loraScene(t, a) {
  const D = LORA, cw = 22, g = 2, st = cw + g, y = 360;
  tex('lora', 960, 190, { wipe: lin(t, 17.6, 18.6), alpha: a });
  tex('lora2', 960, 270, { wipe: lin(t, 18.4, 19.2), alpha: a });
  cells(200, y, D.W0, { cw, ch: cw, gx: g, alpha: a, colorFn: v => mix('#1b2029', '#5b6b80', (v + 1) / 2) });
  tex('W0', 200 + 6 * st, y + 12 * st + 38, { alpha: a });
  text('（冻结）', 200 + 6 * st, y + 12 * st + 84, { size: 26, color: C.grey, alpha: a });
  text('+', 545, y + 6 * st, { size: 64, color: C.light, alpha: a });
  const live = (v, i, j) => v + 0.45 * Math.sin(2.4 * t + 6 * D.ph[i][j]) * prog(t, 18.8, 19.6);
  const goldCol = v => v >= 0 ? mix('#161b24', C.gold, Math.min(1, v)) : mix('#161b24', C.teal, Math.min(1, -v));
  cells(600, y, D.B.map((r, i) => r.map((v, j) => live(v, i, j))), { cw, ch: cw, gx: g, alpha: a, colorFn: goldCol });
  cells(690, y, D.A.map((r, i) => r.map((v, j) => live(v, j, i))), { cw, ch: cw, gx: g, alpha: a, colorFn: goldCol });
  tex('Bm', 600 + st, y + 12 * st + 38, { alpha: a });
  tex('Am', 690 + 6 * st, y + 2 * st + 36, { alpha: a });
  text('只训练这两个小矩阵', 834, y + 2 * st + 100, { size: 28, color: C.gold, alpha: prog(t, 19.0, 19.6) * a });

  const rx = 1130, bwid = 700;
  text('以 d = 4096、r = 8 为例', rx, 400, { align: 'left', size: 28, color: C.grey, alpha: prog(t, 19.2, 19.7) * a });
  text('全量微调 ΔW：4096 × 4096 ≈ 1678 万个参数', rx, 470, { align: 'left', size: 30, alpha: prog(t, 19.4, 19.9) * a });
  withAlpha(a, () => { ctx.fillStyle = rgba(C.red, 0.85); ctx.fillRect(rx, 500, bwid * prog(t, 19.6, 20.6), 22); });
  text('LoRA：2 × 4096 × 8 ≈ 6.6 万个参数', rx, 580, { align: 'left', size: 30, alpha: prog(t, 20.2, 20.7) * a });
  withAlpha(prog(t, 20.4, 20.9) * a, () => { ctx.fillStyle = C.green; ctx.fillRect(rx, 610, Math.max(3, bwid * 65536 / 16777216), 22); });
  text('只有 0.39%', rx, 690, { align: 'left', size: 48, weight: 700, color: C.gold, alpha: prog(t, 20.8, 21.4) * a });
}

// ================================================================ 5 · matrix multiplication -> GPUs (104–113)
const MM = (() => {
  const r = rng(42), R = () => Array.from({ length: 8 }, () => Array.from({ length: 8 }, () => r() * 2 - 1));
  const A = R(), B = R();
  return { A, B, C: A.map(row => B[0].map((_, j) => row.reduce((s, a, k) => s + a * B[k][j], 0) / 2.5)) };
})();

function s5(t) {
  section('05', '矩阵乘法 → GPU 算力', prog(t, 0.2, 1.0));
  tex('mm', 960, 200, { wipe: lin(t, 0.4, 1.4) });
  const cw = 32, g = 6, st = cw + g, y = 300, ax = 392, bx = 808, cx = 1224;
  const o = { cw, ch: cw, gx: g, cellAlpha: (i, j) => prog(t, 0.2 + (i + j) * 0.02, 0.6 + (i + j) * 0.02) };
  cells(ax, y, MM.A, o); cells(bx, y, MM.B, o);
  text('×', 750, y + 4 * st - 3, { size: 56, color: C.light });
  text('=', 1166, y + 4 * st - 3, { size: 56, color: C.light });
  const seq = 0.8, dt = 0.12, nSeq = 22, p2 = 4.0;
  cells(cx, y, MM.C, { cw, ch: cw, gx: g, cellAlpha: (i, j) => {
    const k = i * 8 + j;
    const a1 = (k < nSeq ? prog(t, seq + k * dt, seq + k * dt + 0.08) : 0) * (1 - prog(t, 3.5, 3.9));
    return Math.max(a1, prog(t, p2 + (i + j) * 0.05, p2 + (i + j) * 0.05 + 0.25));
  } });
  if (t > seq && t < seq + nSeq * dt) {
    const k = Math.floor((t - seq) / dt), i = Math.floor(k / 8), j = k % 8;
    outline(ax - 4, y + i * st - 4, 8 * st, cw + 8, C.yellow);
    outline(bx + j * st - 4, y - 4, cw + 8, 8 * st, C.yellow);
    outline(cx + j * st - 4, y + i * st - 4, cw + 8, cw + 8, C.yellow);
  }
  const fl = Math.sin(Math.PI * lin(t, p2, p2 + 1.1));
  if (fl > 0) for (const x of [ax, bx, cx]) outline(x - 8, y - 8, 8 * st + 10, 8 * st + 10, C.yellow, fl, 3, 8);
  text('串行：一次只算一个', 960, 680, { size: 34, color: C.light, alpha: fadeIO(t, 0.8, 3.8) });
  text('并行：成千上万次乘加同时完成', 960, 680, { size: 34, color: C.yellow, alpha: prog(t, 4.0, 4.5) });
  const sa = prog(t, 5.4, 6.0), s1 = '一个 700 亿参数的模型，每生成 1 个词 ≈ 1400 亿次浮点运算';
  panel(960 - textWidth(s1, 34) / 2 - 30, 745, textWidth(s1, 34) + 60, 120, sa);
  text(s1, 960, 785, { size: 34, alpha: sa });
  text('（约等于 2 × 参数量，绝大部分来自矩阵乘法）', 960, 835, { size: 26, color: C.grey, alpha: prog(t, 5.8, 6.4) });
}

// ================================================================ 6 · recap (113–120)
function s6(t) {
  const rows = [['向量', '数据、词嵌入'], ['矩阵 · 线性变换', '神经网络的每一层'], ['点积', '注意力机制'], ['特征值 · SVD', 'PCA 降维、LoRA 微调'], ['矩阵乘法', 'GPU 算力']];
  rows.forEach(([l, r], i) => {
    const y = 200 + i * 86, a = prog(t, 0.3 + i * 0.35, 0.8 + i * 0.35);
    text(l, 900, y, { align: 'right', size: 42, weight: 700, color: C.yellow, alpha: a });
    arrow(928, y + 2, 1002, y + 2, { color: C.grey, width: 3, head: 14, grow: a });
    text(r, 1030, y, { align: 'left', size: 42, color: C.blue, alpha: a });
  });
  text('线性代数，AI 的母语。', 960, 720, { size: 80, weight: 700, font: SERIF, alpha: prog(t, 2.6, 3.6) });
}

// ================================================================ timeline
const SCENES = [[0, 8, s0], [8, 28, s1], [28, 56, s2], [56, 80, s3], [80, 104, s4], [104, 113, s5], [113, 120, s6]];
const TOTAL = 120;
function renderFrame(T) {
  background();
  for (const [a, b, fn] of SCENES) if (T >= a && T <= b) { GA = fadeIO(T, a, b, 0.45); fn(T - a); }
  GA = 1;
  drawSubs(T);
}
async function init() {
  await loadTex();
  COLLECT = new Set();
  for (let t = 0; t <= TOTAL; t += 0.25) renderFrame(t);
  const chars = [...COLLECT].join(''); COLLECT = null;
  await Promise.all(['500 40px "Noto Sans SC"', '700 40px "Noto Sans SC"', '700 40px "Noto Serif SC"'].map(s => document.fonts.load(s, chars)));
  await document.fonts.ready;
  return TOTAL;
}
window.ready = init();
