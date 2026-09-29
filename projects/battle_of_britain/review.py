"""Self-review: dense contact strips of a time window.  python3 review.py t0 t1 step [name]"""
import sys, os
import render
from PIL import Image, ImageDraw
t0, t1, st = map(float, sys.argv[1:4])
name = sys.argv[4] if len(sys.argv) > 4 else f"rev_{t0}_{t1}"
ts = []
t = t0
while t <= t1 + 1e-6:
    ts.append(t); t += st
th = []
for t in ts:
    im = Image.fromarray(render.render_frame(int(round(t * 30)))).resize((384, 216))
    ImageDraw.Draw(im).text((6, 4), f"{t:.2f}", fill=(255, 255, 0))
    th.append(im)
cols = 6
rows = (len(th) + cols - 1) // cols
sheet = Image.new("RGB", (cols * 388, rows * 220))
for k, im in enumerate(th):
    sheet.paste(im, ((k % cols) * 388, (k // cols) * 220))
out = f"/tmp/claude-0/-home-user-cluad/7b25c843-1897-532f-b28a-df66ee3cf495/scratchpad/{name}.png"
sheet.save(out); print(out)
