"""6 s motion test of the air-battle traffic, clouds and fly-bys -> design/traffic_preview.mp4 (720p)."""
import os, sys, subprocess
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import numpy as np
from PIL import Image
from multiprocessing import Pool
import imageio_ffmpeg
from silhouette_kit.core import new_canvas, post, W, H
import shots as S

D = os.path.dirname(os.path.abspath(__file__))
FPS = 30


def frame(i):
    t = i / FPS
    s, ctx = new_canvas()
    if t < 3:
        S.shot_chase(ctx, t / 3, 22.0 + t)
    else:
        S.battle_sky(ctx, 30.0 + t, scroll=t * 60, bombers=(900, 260, 150, 6), traffic=1.2, zmax=0.8)
    img = Image.fromarray(post(s, seed=i, grain=6, vignette=0.3)).resize((1280, 720), Image.LANCZOS)
    return np.asarray(img).tobytes()


if __name__ == "__main__":
    out = os.path.join(D, "design", "traffic_preview.mp4")
    p = subprocess.Popen([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt",
                          "rgb24", "-s", "1280x720", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "23",
                          "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    with Pool(os.cpu_count()) as pool:
        for b in pool.imap(frame, range(6 * FPS), chunksize=4):
            p.stdin.write(b)
    p.stdin.close(); p.wait()
    print(out)
