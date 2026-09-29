"""Close-up sheet + short walk-cycle clip of the silhouettes at 106 BPM.
python3 silhouette_kit/tools/figure_preview.py  ->  silhouette_kit/reference/figure_closeup.png, walk_cycle.mp4
"""
import os, sys, subprocess
import numpy as np
from PIL import Image
import imageio_ffmpeg
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from silhouette_kit.core import new_canvas, post, rect, line, figure, W, H

D = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(D, "..", "reference")
BEAT = 60 / 106          # one step per beat, one stride (phase 0..1) per two beats
FPS = 30


def frame(t, big=False):
    s, ctx = new_canvas()
    rect(ctx, 0, 0, W, H, "#d9d3c5")
    gy = 1000
    line(ctx, [(0, gy + 2), (W, gy + 2)], "#b8b0a0", 3)
    ph = (t / (2 * BEAT)) % 1.0
    hgt = 860
    figure(ctx, 400, gy, hgt, ph, "civ")
    figure(ctx, 1010, gy, hgt, ph, "sol")
    figure(ctx, 1500, gy, hgt, (t / (1.2 * BEAT)) % 1.0, "sol", run=1.0, charge=True)
    return post(s, seed=int(t * FPS), grain=4, vignette=0.15)


Image.fromarray(frame(0.02)).save(os.path.join(OUT, "figure_closeup.png"))
n = int(round(8 * BEAT * FPS))
exe = imageio_ffmpeg.get_ffmpeg_exe()
p = subprocess.Popen([exe, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                      "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
                      os.path.join(OUT, "walk_cycle.mp4")], stdin=subprocess.PIPE)
for i in range(n):
    p.stdin.write(frame(i / FPS).tobytes())
p.stdin.close(); p.wait()
print("frames", n)
