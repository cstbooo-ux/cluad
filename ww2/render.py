"""Timeline + renderer for the 106 BPM silhouette video.

python3 render.py sheets            -> stills/scenes_A.png, stills/scenes_B.png (all scenes, for review)
python3 render.py video [out_dir]   -> ww2_106bpm.mp4 (silent), ww2_106bpm_click.mp4 (with metronome),
                                       click_106bpm.wav, cut_sheet.md
python3 render.py frame <sec>       -> single frame png, for spot checks
"""
import math, os, sys, subprocess, wave
from dataclasses import dataclass, field
from multiprocessing import Pool
import numpy as np
from PIL import Image
import imageio_ffmpeg

from lib import W, H, FIG_H, new_canvas, post, rect
from figure import travel
from scenes import SCENES
import fx

D = os.path.dirname(os.path.abspath(__file__))
BPM = 106
BEAT = 60 / BPM
FPS = 30
NB = 72
DUR = NB * BEAT
NF = int(round(DUR * FPS))

CIV = {"kind": "civ"}
SOL = {"kind": "sol"}
RUN = {"kind": "sol", "run": 1.0, "charge": True}

# ------------------------------------------------------------------ timeline
# (start_beat, n_beats, scene, B, fig)
SHOTS = [(0, 4, "prologue", 0, CIV), (4, 4, "paris", 0, CIV), (8, 4, "station", 0, CIV)]
A2 = ["london", "berlin", "stalingrad", "warship", "desert", "moscow", "jungle", "carrier", "mountains",
      "normandy", "airfield", "trench"]
for i, sc in enumerate(A2):
    SHOTS.append((12 + 2 * i, 2, sc, 0, CIV))
B1 = ["trench", "berlin", "airbattle", "normandy", "stalingrad", "warship", "desert", "london", "jungle", "carrier",
      "moscow", "paris", "station", "mountains", "airfield", "trench", "stalingrad", "berlin", "normandy", "warship",
      "airbattle", "desert", "london", "moscow"]
for i, sc in enumerate(B1):
    SHOTS.append((36 + i, 1, sc, 1, SOL))
B2 = ["trench", "normandy", "stalingrad", "berlin", "jungle", "airbattle", "desert", "trench"]
for i, sc in enumerate(B2):
    SHOTS.append((60 + i, 1, sc, 1, RUN))
SHOTS.append((68, 4, "dawn", 0, CIV))
assert sum(s[1] for s in SHOTS) == NB

# variant numbers so repeated scenes differ
_seen = {}
VARS = []
for s in SHOTS:
    VARS.append(_seen.get(s[2], 0)); _seen[s[2]] = _seen.get(s[2], 0) + 1


def beat_frame(k):
    return int(round(k * BEAT * FPS))


@dataclass
class Shot:
    t: float
    phase: float
    fig: dict
    B: int
    scroll: float
    var: int
    scene: str = ""
    post: dict = field(default_factory=dict)


def fig_phase(tg, fig):
    return tg / BEAT if fig.get("run") else tg / (2 * BEAT)


def shot_at(fi):
    for i, s in enumerate(SHOTS):
        if beat_frame(s[0]) <= fi < beat_frame(s[0] + s[1]):
            return i
    return len(SHOTS) - 1


def render_frame(fi):
    tg = fi / FPS
    i = shot_at(fi)
    b0, nb, scene, B, fig = SHOTS[i]
    t0 = beat_frame(b0) / FPS
    ts = tg - t0
    ph = fig_phase(tg, fig)
    ga = (FIG_H, fig.get("run", 0.0), fig.get("charge", False), fig.get("kind", "civ"))
    S = Shot(t=ts, phase=ph, fig=fig, B=B, scroll=travel(ph, *ga) - travel(fig_phase(t0, fig), *ga), var=VARS[i],
             scene=scene)

    beat_idx = int(tg / BEAT + 1e-6)
    tb = tg - beat_idx * BEAT                 # time since the last beat
    s, ctx = new_canvas()
    # camera: punch-in on every cut, softer pulse on every beat, shake in part B
    z = 1.0 + (0.045 if B else 0.03) * math.exp(-ts / 0.12) + 0.008 * math.exp(-tb / 0.1)
    sx = sy = 0.0
    if B:
        amp = 9 * math.exp(-tb / 0.16) + 2
        sx = amp * math.sin(tg * 97.0)
        sy = amp * math.cos(tg * 71.0)
        z += 0.012
    ctx.save()
    ctx.translate(W / 2 + sx, H / 2 + sy); ctx.scale(z, z); ctx.translate(-W / 2, -H / 2)
    SCENES[scene](ctx, S)
    ctx.restore()

    # flashes
    fl = 0.0
    if beat_idx == 36:
        fl = 0.85 * math.exp(-tb / 0.16)
    elif B and beat_idx % 4 == 0:
        fl = 0.3 * math.exp(-tb / 0.08)
    if 60 <= beat_idx < 68:
        th = tb % (BEAT / 2)
        fl = max(fl, 0.22 * math.exp(-th / 0.06))
    if beat_idx >= 68:
        fl = max(fl, 0.75 * math.exp(-(tg - 68 * BEAT) / 0.35))
    if fl > 0.004:
        rect(ctx, 0, 0, W, H, "#fff6e8", fl)
    fade = 0.0
    if tg < 0.45:
        fade = 1 - tg / 0.45
    if tg > DUR - BEAT:
        fade = min(1.0, (tg - (DUR - BEAT)) / (BEAT * 0.9))
    if fade > 0:
        rect(ctx, 0, 0, W, H, "#000000", fade)

    img = post(s, seed=fi, grain=7.0 + 3 * B, vignette=0.32 + 0.08 * B)
    if "heat" in S.post:
        img = fx.heat_shimmer(img, tg, *S.post["heat"])
    return img


def _render_bytes(fi):
    return render_frame(fi).tobytes()


# ------------------------------------------------------------------ audio / sheets
def click_track(path, dur=None, sr=48000):
    dur = DUR if dur is None else dur
    n = int(dur * sr)
    a = np.zeros(n, np.float32)
    for k in range(NB):
        i0 = int(round(k * BEAT * sr))
        acc = k % 4 == 0
        f = 1760 if acc else 1320
        L = int(0.03 * sr)
        tt = np.arange(L) / sr
        burst = np.sin(2 * np.pi * f * tt) * np.exp(-tt / 0.008) * (0.9 if acc else 0.6)
        a[i0:i0 + L] += burst[: max(0, min(L, n - i0))]
    pcm = (np.clip(a, -1, 1) * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(pcm.tobytes())


NAMES = {"prologue": "序幕·乡间小路", "paris": "巴黎", "london": "伦敦大轰炸", "berlin": "柏林",
         "stalingrad": "斯大林格勒", "moscow": "莫斯科红场", "warship": "日本战舰", "carrier": "航空母舰",
         "desert": "北非沙漠", "jungle": "太平洋丛林", "normandy": "诺曼底海滩", "station": "火车站·难民",
         "mountains": "意大利山地·卡西诺", "airfield": "机场", "trench": "战壕", "airbattle": "空战", "dawn": "尾声·日出"}


def cut_sheet(path):
    rows = ["| # | 拍 | 开始时间 (s) | 时长 (拍) | 场景 | 版本 | 人物 |", "|---|---|---|---|---|---|---|"]
    for i, (b0, nb, sc, B, fig) in enumerate(SHOTS):
        who = "平民" if fig["kind"] == "civ" else ("士兵冲锋" if fig.get("run") else "士兵")
        rows.append(f"| {i + 1} | {b0 + 1}–{b0 + nb} | {b0 * BEAT:.3f} | {nb} | {NAMES[sc]} | {'B 战火' if B else 'A 平静'} | {who} |")
    with open(path, "w") as f:
        f.write(f"# 切点表（BPM {BPM}，一拍 {BEAT:.4f}s，共 {NB} 拍 = {DUR:.3f}s，{FPS}fps / {NF} 帧）\n\n")
        f.write("时间从视频第 0 帧起算；音乐的第一拍对齐 0.000s。\n\n")
        f.write("\n".join(rows) + "\n")


def sheets(out):
    order = ["prologue", "paris", "london", "berlin", "stalingrad", "moscow", "warship", "carrier", "desert",
             "jungle", "normandy", "station", "mountains", "airfield", "trench", "dawn"]
    borders = []
    for B, name, lst in ((0, "scenes_A.png", order), (1, "scenes_B.png", [o for o in order if o not in ("prologue", "dawn")] + ["airbattle"])):
        thumbs = []
        for k, sc in enumerate(lst):
            fig = CIV if not B else SOL
            S = Shot(t=0.35, phase=0.02 + 0.5 * (k % 2), fig=fig, B=B, scroll=0.0, var=0, scene=sc)
            s, ctx = new_canvas()
            SCENES[sc](ctx, S)
            img = post(s, seed=k)
            if "heat" in S.post:
                img = fx.heat_shimmer(img, 0.35, *S.post["heat"])
            im = Image.fromarray(img)
            im.save(os.path.join(out, f"scene_{sc}_{'B' if B else 'A'}.png"))
            thumbs.append(im.resize((W // 4, H // 4), Image.LANCZOS))
        cols = 4
        rows = (len(thumbs) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * (W // 4 + 8) + 8, rows * (H // 4 + 8) + 8), (14, 14, 14))
        for k, th in enumerate(thumbs):
            sheet.paste(th, (8 + (k % cols) * (W // 4 + 8), 8 + (k // cols) * (H // 4 + 8)))
        sheet.save(os.path.join(out, name))
        print("wrote", name)


def audio(out):
    import soundtrack as st
    os.makedirs(out, exist_ok=True)
    stems = st.build(SHOTS, VARS, BEAT, NB, DUR, beat_frame, FPS)
    mix, scaled = st.master(stems)
    st.write_wav(os.path.join(out, "sfx_mix.wav"), mix)
    for k, v in scaled.items():
        st.write_wav(os.path.join(out, f"sfx_{k}.wav"), v)
    click_track(os.path.join(out, f"click_{BPM}bpm.wav"))
    # SFX + metronome, for checking the sync
    import wave
    with wave.open(os.path.join(out, f"click_{BPM}bpm.wav")) as w:
        c = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32767
    both = mix * 0.7
    both[: len(c)] += np.stack([c, c], 1)[: len(both)] * 0.8
    st.write_wav(os.path.join(out, "sfx_with_click.wav"), both / max(1.0, np.max(np.abs(both)) / 0.95))
    return mix


def video(out):
    os.makedirs(out, exist_ok=True)
    silent = os.path.join(out, f"ww2_{BPM}bpm.mp4")
    exe = imageio_ffmpeg.get_ffmpeg_exe()
    p = subprocess.Popen([exe, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "21",
                          "-pix_fmt", "yuv420p", silent], stdin=subprocess.PIPE)
    with Pool(max(1, os.cpu_count())) as pool:
        for k, b in enumerate(pool.imap(_render_bytes, range(NF), chunksize=4)):
            p.stdin.write(b)
            if k % 100 == 0:
                print("frame", k, "/", NF, flush=True)
    p.stdin.close(); p.wait()
    audio(out)
    for wav, name in (("sfx_mix.wav", f"ww2_{BPM}bpm_sfx.mp4"), ("sfx_with_click.wav", f"ww2_{BPM}bpm_sfx_click.mp4")):
        subprocess.run([exe, "-y", "-loglevel", "error", "-i", silent, "-i", os.path.join(out, wav), "-c:v", "copy",
                        "-c:a", "aac", "-b:a", "192k", "-shortest", os.path.join(out, name)], check=True)
    cut_sheet(os.path.join(out, "cut_sheet.md"))
    print("done", NF, "frames")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "video"
    if cmd == "sheets":
        out = os.path.join(D, "stills"); os.makedirs(out, exist_ok=True); sheets(out)
    elif cmd == "audio":
        audio(sys.argv[2] if len(sys.argv) > 2 else os.path.join(D, "out"))
    elif cmd == "frame":
        sec = float(sys.argv[2])
        Image.fromarray(render_frame(int(sec * FPS))).save(sys.argv[3] if len(sys.argv) > 3 else "frame.png")
    else:
        video(sys.argv[2] if len(sys.argv) > 2 else os.path.join(D, "out"))
