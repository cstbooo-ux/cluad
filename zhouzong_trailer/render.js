// Frame-exact renderer: drives anim.html in headless Chromium and pipes frames into ffmpeg.
//   NODE_PATH=$(npm root -g) node render.js out.mp4            -> full video (uses build/mix.wav)
//   NODE_PATH=$(npm root -g) node render.js --stills 1,5.5 dir  -> PNG stills at those times
const http = require('http'), fs = require('fs'), path = require('path'), { spawn } = require('child_process');
const { chromium } = require('playwright');
const ROOT = __dirname;
const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.json': 'application/json', '.css': 'text/css', '.woff2': 'font/woff2', '.woff': 'font/woff', '.wav': 'audio/wav' };

function serve() {
  const srv = http.createServer((req, res) => {
    const p = path.join(ROOT, decodeURIComponent(req.url.split('?')[0]));
    if (!p.startsWith(ROOT) || !fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); return res.end(); }
    res.writeHead(200, { 'Content-Type': TYPES[path.extname(p)] || 'application/octet-stream' });
    fs.createReadStream(p).pipe(res);
  });
  return new Promise(r => srv.listen(0, '127.0.0.1', () => r(srv)));
}

(async () => {
  const args = process.argv.slice(2);
  const srv = await serve();
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM || undefined });
  const page = await browser.newPage({ viewport: { width: 720, height: 1280 } });
  page.on('console', m => console.log('[page]', m.text()));
  page.on('pageerror', e => console.log('[pageerror]', e.message));
  const pageName = process.env.PAGE || 'anim.html';
  await page.goto(`http://127.0.0.1:${srv.address().port}/${pageName}`);
  const total = await page.evaluate(() => window.ready);
  if (args[0] === '--stills') {
    const dir = args[2] || 'stills'; fs.mkdirSync(dir, { recursive: true });
    for (const t of args[1].split(',').map(Number)) {
      const d = await page.evaluate(t => { renderFrame(t); return document.getElementById('c').toDataURL('image/png'); }, t);
      fs.writeFileSync(path.join(dir, `t${t.toFixed(2).padStart(7, '0')}.png`), Buffer.from(d.split(',')[1], 'base64'));
    }
  } else {
    const out = args[0] || 'out.mp4', fps = 24, n = Math.round(total * fps);
    const ff = spawn('ffmpeg', ['-v', 'error', '-y', '-f', 'image2pipe', '-framerate', String(fps), '-c:v', 'mjpeg', '-i', '-',
      '-i', path.join(ROOT, 'build/mix.wav'), '-c:v', 'libx264', '-preset', 'slow', '-crf', process.env.CRF || '27', '-pix_fmt', 'yuv420p',
      '-c:a', 'aac', '-b:a', '128k', '-shortest', '-movflags', '+faststart', out], { stdio: ['pipe', 'inherit', 'inherit'] });
    const t0 = Date.now();
    for (let i = 0; i < n; i++) {
      const d = await page.evaluate(t => { renderFrame(t); return document.getElementById('c').toDataURL('image/jpeg', 0.92); }, i / fps);
      if (!ff.stdin.write(Buffer.from(d.split(',')[1], 'base64'))) await new Promise(r => ff.stdin.once('drain', r));
      if (i % 240 === 0) console.log(`frame ${i}/${n}  ${((Date.now() - t0) / 1000).toFixed(0)}s`);
    }
    ff.stdin.end(); await new Promise(r => ff.on('close', r));
    console.log('wrote', out);
  }
  await browser.close(); srv.close();
})();
