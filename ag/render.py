"""Frame renderer. Usage:
  python3 render.py still 3.2 41 ...      -> out/still_<t>.png
  python3 render.py seg <i0> <i1> <path>   -> frames [i0, i1) encoded to an intermediate mp4
(wrap with xvfb-run -a: the 3D scenes use Mesa's llvmpipe through GLX)"""
import sys, os, subprocess, time
import numpy as np, cv2
import imageio_ffmpeg
from engine import W, H, FPS
import scenes

FF = imageio_ffmpeg.get_ffmpeg_exe()
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
os.makedirs(OUT, exist_ok=True)

if sys.argv[1] == "still":
    for a in sys.argv[2:]:
        t = float(a)
        t0 = time.time()
        fr = scenes.render_frame(t)
        cv2.imwrite(os.path.join(OUT, f"still_{t:07.3f}.png"), fr[..., ::-1])
        print(f"t={t:.3f}  {time.time() - t0:.2f}s", flush=True)
elif sys.argv[1] == "seg":
    i0, i1, path = int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
    p = subprocess.Popen([FF, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "12",
                          "-pix_fmt", "yuv420p", path], stdin=subprocess.PIPE)
    t0 = time.time()
    for i in range(i0, i1):
        fr = scenes.render_frame((i + 0.5) / FPS)
        p.stdin.write(fr.tobytes())
        if (i - i0) % 30 == 0:
            print(f"{path}: frame {i} ({i - i0 + 1}/{i1 - i0})  {time.time() - t0:.0f}s", flush=True)
    p.stdin.close()
    p.wait()
    print("done", path, f"{time.time() - t0:.0f}s", flush=True)
