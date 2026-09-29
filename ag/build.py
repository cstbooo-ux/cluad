"""Render the whole film in parallel segments, then concatenate and mux the score.
  python3 build.py render [workers]   -> out/seg_###.mp4
  python3 build.py final              -> algebraic_geometry.mp4 (needs out/score.wav from music.py)"""
import sys, os, subprocess, concurrent.futures as cf
import imageio_ffmpeg
from timeline import DUR
from engine import FPS

D = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(D, "out")
FF = imageio_ffmpeg.get_ffmpeg_exe()
N = int(round(DUR * FPS))
SEG = 150


def job(k):
    i0, i1 = k * SEG, min((k + 1) * SEG, N)
    path = os.path.join(OUT, f"seg_{k:03d}.mp4")
    if os.path.exists(path):
        return path
    tmp = path + ".part.mp4"
    subprocess.run(["xvfb-run", "-a", "python3", os.path.join(D, "render.py"), "seg", str(i0), str(i1), tmp],
                   check=True, stdout=open(os.path.join(OUT, f"seg_{k:03d}.log"), "w"), stderr=subprocess.STDOUT)
    os.rename(tmp, path)
    return path


if sys.argv[1] == "render":
    os.makedirs(OUT, exist_ok=True)
    nseg = (N + SEG - 1) // SEG
    workers = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    with cf.ThreadPoolExecutor(workers) as ex:
        for p in ex.map(job, range(nseg)):
            print("ok", p, flush=True)
elif sys.argv[1] == "final":
    segs = sorted(f for f in os.listdir(OUT) if f.startswith("seg_") and f.endswith(".mp4") and "part" not in f)
    with open(os.path.join(OUT, "list.txt"), "w") as f:
        for s in segs:
            f.write(f"file '{os.path.join(OUT, s)}'\n")
    br = sys.argv[2] if len(sys.argv) > 2 else "5200k"
    common = ["-f", "concat", "-safe", "0", "-i", os.path.join(OUT, "list.txt")]
    venc = ["-c:v", "libx264", "-preset", "slow", "-b:v", br, "-maxrate", "9M", "-bufsize", "18M",
            "-pix_fmt", "yuv420p", "-profile:v", "high", "-tune", "film", "-passlogfile", os.path.join(OUT, "x264")]
    # two-pass so the file stays under GitHub's 100 MB limit without starving the busy scenes
    subprocess.run([FF, "-y", "-loglevel", "error", *common, *venc, "-pass", "1", "-an", "-f", "null", os.devnull],
                   check=True)
    subprocess.run([FF, "-y", "-loglevel", "error", *common, "-i", os.path.join(OUT, "score.wav"),
                    "-map", "0:v", "-map", "1:a", *venc, "-pass", "2",
                    "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", "-shortest",
                    os.path.join(D, "algebraic_geometry.mp4")], check=True)
    print("wrote", os.path.join(D, "algebraic_geometry.mp4"))
