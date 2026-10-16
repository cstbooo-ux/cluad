// Frame-exact renderer: drives anim.html in headless Chromium and pipes frames into ffmpeg.
//   NODE_PATH=$(npm root -g) node render.js out.mp4             -> full video (muxes build/music.wav)
//   NODE_PATH=$(npm root -g) node render.js --stills 1,5.5 dir   -> PNG stills at those times
//   NODE_PATH=$(npm root -g) node render.js --srt out.srt         -> subtitle file
const http = require('http'), fs = require('fs'), path = require('path'), { spawn } = require('child_process');
const { chromium } = require('playwright');
const ROOT = __dirname, FPS = 30;
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
const stamp = s => { const ms = Math.round(s * 1000), h = Math.floor(ms / 3600000), m = Math.floor(ms / 60000) % 60, sec = Math.floor(ms / 1000) % 60;
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')},${String(ms % 1000).padStart(3, '0')}`; };

(async () => {
  const args = process.argv.slice(2);
  const srv = await serve();
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM || undefined });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  page.on('console', m => console.log('[page]', m.text()));
  page.on('pageerror', e => console.log('[pageerror]', e.message));
  await page.goto(`http://127.0.0.1:${srv.address().port}/anim.html`);
  const total = await page.evaluate(() => window.ready);
  if (args[0] === '--stills') {
    const dir = args[2] || 'stills'; fs.mkdirSync(dir, { recursive: true });
    for (const t of args[1].split(',').map(Number)) {
      const d = await page.evaluate(t => { renderFrame(t); return document.getElementById('c').toDataURL('image/png'); }, t);
      fs.writeFileSync(path.join(dir, `t${t.toFixed(2).padStart(6, '0')}.png`), Buffer.from(d.split(',')[1], 'base64'));
    }
  } else if (args[0] === '--srt') {
    const subs = await page.evaluate(() => SUBS);
    fs.writeFileSync(args[1], subs.map((s, i) => `${i + 1}\n${stamp(s.t0)} --> ${stamp(s.t1)}\n${s.text}\n`).join('\n'));
  } else {
    const out = args[0] || 'out.mp4', n = Math.round(total * FPS);
    const ff = spawn('ffmpeg', ['-v', 'error', '-y', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-',
      '-i', path.join(ROOT, 'build/music.wav'), '-c:v', 'libx264', '-preset', 'slow', '-tune', 'animation', '-crf', process.env.CRF || '20',
      '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '160k', '-shortest', '-movflags', '+faststart', out], { stdio: ['pipe', 'inherit', 'inherit'] });
    const t0 = Date.now();
    for (let i = 0; i < n; i++) {
      const d = await page.evaluate(t => { renderFrame(t); return document.getElementById('c').toDataURL('image/jpeg', 0.95); }, i / FPS);
      if (!ff.stdin.write(Buffer.from(d.split(',')[1], 'base64'))) await new Promise(r => ff.stdin.once('drain', r));
      if (i % 300 === 0) console.log(`frame ${i}/${n}  ${((Date.now() - t0) / 1000).toFixed(0)}s`);
    }
    ff.stdin.end(); await new Promise(r => ff.on('close', r));
    console.log('wrote', out);
  }
  await browser.close(); srv.close();
})();
