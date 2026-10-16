// Every formula in the video. tex.js turns these into SVG (build/tex.json); the page draws them onto the canvas.
//   s: font size in px (1em), c: default colour, t: TeX source
const TEX = (() => {
  const G = '#83C167', R = '#FC6255', Y = '#F4D345', B = '#58C4DD';
  const r = String.raw;
  return {
    x64:     { s: 44, t: r`\mathbf{x}=[\,0,\ 0,\ \dots,\ 0.19,\ 0.75,\ 0.94,\ \dots\,]^{\top}\in\mathbb{R}^{64}` },
    analogy: { s: 46, t: r`\vec{v}_{\text{king}}-\vec{v}_{\text{man}}+\vec{v}_{\text{woman}}\approx\vec{v}_{\text{queen}}` },

    ihat:  { s: 50, c: G, t: r`\hat{\imath}` },
    jhat:  { s: 50, c: R, t: r`\hat{\jmath}` },
    xv:    { s: 46, c: Y, t: r`\mathbf{x}` },
    Wxv:   { s: 46, c: Y, t: r`W\mathbf{x}` },
    Wmat:  { s: 50, t: r`W=\begin{bmatrix}\color{${G}}{2}&\color{${R}}{-1}\\\color{${G}}{1}&\color{${R}}{1}\end{bmatrix}` },
    Wcols: { s: 42, t: r`W\mathbf{x}=x_1\begin{bmatrix}\color{${G}}{2}\\\color{${G}}{1}\end{bmatrix}+x_2\begin{bmatrix}\color{${R}}{-1}\\\color{${R}}{1}\end{bmatrix}` },
    layer: { s: 66, t: r`\mathbf{h}=\sigma(W\mathbf{x}+\mathbf{b})` },
    relu:  { s: 30, t: r`\mathrm{ReLU}(z)=\max(0,z)` },
    net:   { s: 44, t: r`f(\mathbf{x})=W_3\,\sigma\big(W_2\,\sigma(W_1\mathbf{x}+\mathbf{b}_1)+\mathbf{b}_2\big)+\mathbf{b}_3` },
    W1:    { s: 34, t: r`W_1\in\mathbb{R}^{5\times 3}` },
    W2:    { s: 34, t: r`W_2\in\mathbb{R}^{5\times 5}` },
    W3:    { s: 34, t: r`W_3\in\mathbb{R}^{2\times 5}` },
    grad:  { s: 40, c: '#F0AC5F', t: r`W\leftarrow W-\eta\,\nabla_{W}\mathcal{L}` },

    dot1:  { s: 50, t: r`\color{${B}}{\mathbf{a}}\cdot\color{${Y}}{\mathbf{b}}=\|\color{${B}}{\mathbf{a}}\|\,\|\color{${Y}}{\mathbf{b}}\|\cos\theta` },
    dotlbl:{ s: 50, t: r`\color{${B}}{\mathbf{a}}\cdot\color{${Y}}{\mathbf{b}}=` },
    dot2:  { s: 46, t: r`=\color{${B}}{a_1}\color{${Y}}{b_1}+\color{${B}}{a_2}\color{${Y}}{b_2}` },
    av:    { s: 46, c: B, t: r`\mathbf{a}` },
    bv:    { s: 46, c: Y, t: r`\mathbf{b}` },
    theta: { s: 40, t: r`\theta` },
    X:     { s: 34, t: r`X` },
    Q:     { s: 30, t: r`Q=XW_Q` },
    K:     { s: 30, t: r`K=XW_K` },
    V:     { s: 30, t: r`V=XW_V` },
    scores:{ s: 34, t: r`QK^{\top}/\sqrt{d_k}` },
    soft:  { s: 34, t: r`\mathrm{softmax}\big(QK^{\top}/\sqrt{d_k}\big)` },
    attn:  { s: 50, t: r`\mathrm{Attention}(Q,K,V)=\mathrm{softmax}\!\left(\frac{QK^{\top}}{\sqrt{d_k}}\right)V` },

    cov:   { s: 44, t: r`C=\tfrac{1}{n}X^{\top}X,\qquad C\,\mathbf{v}=\lambda\,\mathbf{v}` },
    v1:    { s: 42, c: Y, t: r`\mathbf{v}_1` },
    v2:    { s: 42, c: G, t: r`\mathbf{v}_2` },
    svd:   { s: 76, t: r`W=U\,\Sigma\,V^{\top}` },
    svdr:  { s: 76, t: r`W\approx U_r\,\Sigma_r\,V_r^{\top}` },
    lora:  { s: 56, t: r`W=W_0+\Delta W,\qquad \Delta W=B\,A` },
    lora2: { s: 38, t: r`B\in\mathbb{R}^{d\times r},\quad A\in\mathbb{R}^{r\times d},\quad r\ll d` },
    Bm:    { s: 40, c: '#F0AC5F', t: r`B` },
    Am:    { s: 40, c: '#F0AC5F', t: r`A` },
    W0:    { s: 40, t: r`W_0` },

    mm:    { s: 50, t: r`C=AB,\qquad c_{ij}=\sum_{k} a_{ik}\,b_{kj}` },
  };
})();
if (typeof module !== 'undefined') module.exports = TEX;
