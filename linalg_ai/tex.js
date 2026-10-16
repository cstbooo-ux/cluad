// Typeset formulas.js with MathJax (SVG output, glyphs as paths) -> build/tex.json
const fs = require('fs'), path = require('path');
const { mathjax } = require('mathjax-full/js/mathjax.js');
const { TeX } = require('mathjax-full/js/input/tex.js');
const { SVG } = require('mathjax-full/js/output/svg.js');
const { liteAdaptor } = require('mathjax-full/js/adaptors/liteAdaptor.js');
const { RegisterHTMLHandler } = require('mathjax-full/js/handlers/html.js');
const { AllPackages } = require('mathjax-full/js/input/tex/AllPackages.js');
const TEX = require('./formulas.js');

const adaptor = liteAdaptor();
RegisterHTMLHandler(adaptor);
const doc = mathjax.document('', { InputJax: new TeX({ packages: AllPackages }), OutputJax: new SVG({ fontCache: 'none' }) });

const out = {};
for (const [k, f] of Object.entries(TEX)) {
  let svg = adaptor.innerHTML(doc.convert(f.t, { display: true }));
  if (svg.includes('data-mml-node="merror"')) throw new Error(`TeX error in ${k}: ${f.t}`);
  const [, , vw, vh] = svg.match(/viewBox="([^"]+)"/)[1].split(' ').map(Number);
  // Pixel size = viewBox (1/1000 em) * font size, rendered at 2x so scaled-up draws stay crisp.
  const w = vw / 1000 * f.s, h = vh / 1000 * f.s;
  svg = svg.replace(/width="[^"]+"/, `width="${(w * 2).toFixed(1)}"`).replace(/height="[^"]+"/, `height="${(h * 2).toFixed(1)}"`)
           .replace(/style="[^"]*"/, '').replace(/currentColor/g, f.c || '#ECECEC');
  out[k] = { svg, w, h };
}
fs.mkdirSync(path.join(__dirname, 'build'), { recursive: true });
fs.writeFileSync(path.join(__dirname, 'build/tex.json'), JSON.stringify(out));
console.log('typeset', Object.keys(out).length, 'formulas');
