"""混音：配音（老式调幅电台质感）+ 配乐（人声处自动压低）+ 音效 -> build/mix.wav

另外导出每帧的人声电平 build/voice_env.npy，给画面里收音机的电平表用。
"""
import json, os, subprocess

import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfilt

D = os.path.dirname(os.path.abspath(__file__))
B = os.path.join(D, "build")
SR = 44100
FPS = 30
tl = json.load(open(os.path.join(B, "timeline.json")))
N = int(tl["duration"] * SR)
rng = np.random.default_rng(7)


def sos(kind, fc, order=2):
    return butter(order, fc, kind, fs=SR, output="sos")


def radio(y):
    """30-40 年代调幅广播：带通、轻微饱和、一点点房间感"""
    rms = np.sqrt((y ** 2).mean()) + 1e-9
    y = y * (10 ** (-17 / 20) / rms)                       # 统一响度
    y = sosfilt(sos("band", [260, 4200], 3), y)
    y = np.tanh(y * 2.2) / 2.2 * 1.15                      # 轻度饱和
    y = y + 0.18 * sosfilt(sos("band", [1200, 2600], 2), y)  # 中频鼻音感
    k = int(0.011 * SR)                                     # 小房间早反射
    y2 = y.copy()
    y2[k:] += 0.16 * y[:-k]
    y2[2 * k:] += 0.08 * y[:-2 * k]
    return y2


voice = np.zeros(N)
for s in tl["segs"]:
    for c in s["chunks"]:
        if not c["file"]:
            continue
        y, sr = sf.read(c["file"])
        assert sr == SR
        y = radio(y)
        i = int(c["t"] * SR)
        j = min(N, i + len(y))
        voice[i:j] += y[:j - i]
    a = s.get("archival")
    if a and a.get("file"):
        y, sr = sf.read(a["file"])
        y = y[int(a["start"] * sr):int((a["start"] + a["dur"]) * sr)]
        if y.ndim > 1:
            y = y.mean(1)
        rms = np.sqrt((y ** 2).mean()) + 1e-9
        y = sosfilt(sos("band", [200, 5000], 2), y * (10 ** (-17 / 20) / rms))
        i = int(a["t"] * SR)
        j = min(N, i + len(y))
        voice[i:j] += y[:j - i]

# 人声下面垫一层很轻的电台底噪
env = np.abs(voice)
k = int(0.05 * SR)
env = np.convolve(env, np.ones(k) / k, mode="same")
active = np.clip(env / (env.max() * 0.08 + 1e-9), 0, 1)
active = np.convolve(active, np.ones(int(0.3 * SR)) / int(0.3 * SR), mode="same")
hiss = sosfilt(sos("band", [1500, 7000], 2), rng.normal(0, 1, N)) * 0.004
crackle = (rng.random(N) > 0.9993) * rng.normal(0, 0.05, N)
voice += (hiss + crackle) * np.clip(active * 1.5, 0, 1)

music, _ = sf.read(os.path.join(B, "music.wav"))
sfx, _ = sf.read(os.path.join(B, "sfx.wav"))
music, sfx = music[:N], sfx[:N]
if len(music) < N:
    music = np.pad(music, ((0, N - len(music)), (0, 0)))
    sfx = np.pad(sfx, ((0, N - len(sfx)), (0, 0)))

# 人声闪避：起 60ms、放 400ms
e = np.abs(voice)
att, rel = np.exp(-1 / (0.06 * SR)), np.exp(-1 / (0.4 * SR))
blk = 256
eb = e[: N // blk * blk].reshape(-1, blk).max(1)
duck = np.zeros_like(eb)
g = 0.0
for i, x in enumerate(eb):
    g = max(x, g * (rel ** blk)) if x > g else g * (rel ** blk)
    duck[i] = g
duck = np.clip(duck / (np.percentile(duck[duck > 0], 90) + 1e-9), 0, 1)
duck = np.interp(np.arange(N), np.arange(len(duck)) * blk, duck)
mgain = 1 - 0.62 * duck

mix = voice[:, None] * 1.0 + music * (0.55 * mgain)[:, None] + sfx * 0.55
mix = np.tanh(mix * 1.1) / 1.1
sf.write(os.path.join(B, "mix_raw.wav"), mix.astype(np.float32), SR)

# 响度标准化到 -14 LUFS（两遍 loudnorm）
p = subprocess.run(["ffmpeg", "-hide_banner", "-i", os.path.join(B, "mix_raw.wav"), "-af",
                    "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
                   capture_output=True, text=True)
js = p.stderr[p.stderr.rfind("{"):p.stderr.rfind("}") + 1]
m = json.loads(js)
af = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
      f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", os.path.join(B, "mix_raw.wav"), "-af", af, "-ar", str(SR),
                os.path.join(B, "mix.wav")], check=True)
print("loudness in", m["input_i"], "LUFS ->", "-14")

# 每帧人声电平（给收音机电平表）
nf = int(tl["duration"] * FPS)
hop = SR // FPS
lv = np.array([np.sqrt((voice[i * hop:(i + 1) * hop] ** 2).mean()) for i in range(nf)])
lv = np.clip(lv / (np.percentile(lv[lv > 1e-4], 95) + 1e-9), 0, 1.2)
np.save(os.path.join(B, "voice_env.npy"), lv.astype(np.float32))
print("mix done", N / SR, "s")
