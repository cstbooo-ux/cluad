"""把解说稿排成时间轴 -> build/timeline.json

有 assets/tts 里的真实配音就用真实时长（先解码、切掉首尾静音到 build/voice/），
否则按语速估算，方便在配音到位前先调画面。段落起点对齐到 120 BPM 的拍子上。
"""
import json, os, subprocess, sys

import numpy as np
import soundfile as sf

D = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, D)
import script  # noqa: E402

SR = 44100
BPM = 120.0
BEAT = 60 / BPM
TTS = os.path.join(D, "assets", "tts")
ARC = os.path.join(D, "assets", "archival")
VOICE = os.path.join(D, "build", "voice")

# 每段的前置时间（换台/日期卡）与收尾时间，单位秒
SPEC = dict(
    rhineland=dict(pre=0.6, post=0.5),
    marcopolo=dict(pre=1.3, post=0.8, card=("1937.07.07", "卢沟桥事变")),
    munich=dict(pre=0.5, post=0.95),
    poland=dict(pre=1.3, post=0.2, card=("1939.09.01", "德国入侵波兰")),
    declare=dict(pre=0.3, post=0.4),
    france=dict(pre=0.9, post=0.4),
    blitz=dict(pre=0.5, post=0.9),
    barbarossa=dict(pre=1.3, post=1.0, card=("1941.06.22", "巴巴罗萨行动")),
    pearl=dict(pre=1.7, post=0.3, card=("1941.12.07", "珍珠港")),
    southward=dict(pre=2.0, post=0.6),
    midway=dict(pre=0.4, post=0.5),
    stalingrad=dict(pre=0.9, post=0.65),
    dday=dict(pre=1.3, post=0.85, card=("1944.06.06", "诺曼底登陆")),
    berlin=dict(pre=0.9, post=1.1, card=("1945.05.08", "欧洲战事结束")),
    pacific=dict(pre=0.4, post=0.4),
    truman=dict(pre=0.5, post=0.6),
)
CHUNK_GAP = 0.14
ARCH_GAP = 0.3
INTRO = 1.6
# 结尾各段时长
HIRO_APPROACH = 3.3   # B-29 飞向广岛
HIRO_SILENCE = 1.5    # 白闪后的静默
NAGA = 2.7
SURRENDER = 2.2
TOLL = 2.9
TITLE = 3.1
TAIL = 0.5

# 估算语速（字符/秒），仅在没有真实配音时使用
CPS = dict(de=16.5, gb=16.5, us=16.5, fr=16.5, pl=15.0, ru=15.5, zh=5.8, ja=8.0)


def ffmpeg_decode(src, dst):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-ac", "1", "-ar", str(SR), dst], check=True)


def trim_silence(y, thr_db=-42, pad=0.03):
    env = np.abs(y)
    k = int(0.01 * SR)
    env = np.convolve(env, np.ones(k) / k, mode="same")
    thr = 10 ** (thr_db / 20) * max(env.max(), 1e-6)
    idx = np.where(env > thr)[0]
    if len(idx) == 0:
        return y, 0.0
    a = max(0, idx[0] - int(pad * SR))
    b = min(len(y), idx[-1] + int(pad * SR))
    return y[a:b], a / SR


def voice_chunk(seg, i, text):
    """返回 (wav路径或None, 时长, 词时间戳列表)"""
    base = os.path.join(TTS, f"{seg['id']}_{i}")
    src = next((base + e for e in (".mp3", ".wav") if os.path.exists(base + e)), None)  # 优先微软配音
    if src:
        os.makedirs(VOICE, exist_ok=True)
        raw = os.path.join(VOICE, f"{seg['id']}_{i}_raw.wav")
        out = os.path.join(VOICE, f"{seg['id']}_{i}.wav")
        ffmpeg_decode(src, raw)
        y, _ = sf.read(raw)
        y, off = trim_silence(y)
        sf.write(out, y, SR)
        words = []
        if os.path.exists(base + ".json"):
            words = [dict(t=w["t"] - off, d=w["d"], w=w["w"]) for w in json.load(open(base + ".json"))["words"]]
        return out, len(y) / SR, words
    n = len(text.replace(" ", ""))
    return None, max(0.8, n / CPS[seg["lang"]]), []


def archival_clip(seg):
    a = seg.get("archival")
    if not a:
        return None
    path = os.path.join(ARC, a["file"])
    meta = os.path.join(D, "assets", "archival_cuts.json")
    cuts = json.load(open(meta)) if os.path.exists(meta) else {}
    if not os.path.exists(path) or a["file"] not in cuts:
        return dict(a, name=a["file"], file=None, dur=0 if a.get("replaces_tts") else 2.25)
    c = cuts[a["file"]]
    return dict(a, name=a["file"], file=path, start=c["start"], dur=c["end"] - c["start"])


def snap(t):
    q = BEAT / 2  # 对齐到 16 分音符
    return np.ceil(t / q - 1e-6) * q


def build():
    t = INTRO
    segs = []
    for seg in script.SEGMENTS:
        sp = SPEC[seg["id"]]
        if seg["id"] == "truman":
            break
        t0 = snap(t)
        tv = t0 + sp["pre"]
        chunks, tc = [], tv
        for i, (tx, zh) in enumerate(zip(seg["text"].split("|"), seg["zh"].split("|"))):
            f, dur, words = voice_chunk(seg, i, tx)
            chunks.append(dict(t=tc, dur=dur, file=f, text=tx.strip(), zh=zh.strip(), words=words))
            tc += dur + CHUNK_GAP
        tc -= CHUNK_GAP
        arc = archival_clip(seg)
        if arc and arc["dur"] > 0:
            arc["t"] = tc + ARCH_GAP
            tc = arc["t"] + arc["dur"]
        t1 = tc + sp["post"]
        segs.append(dict(id=seg["id"], st=seg["st"], lang=seg["lang"], y=seg["y"], m=seg["m"], t0=t0, tv=tv,
                         t1=t1, chunks=chunks, archival=arc, card=sp.get("card")))
        t = t1
    # ---- 结尾
    end = {}
    end["hiro_t0"] = snap(t)
    end["flash1"] = end["hiro_t0"] + HIRO_APPROACH
    seg = script.SEGMENTS[-1]
    sp = SPEC["truman"]
    t0 = end["flash1"] + HIRO_SILENCE
    tv = t0 + sp["pre"]
    arc = archival_clip(seg)
    chunks = []
    if arc and arc["file"]:
        arc["t"] = tv
        tc = tv + arc["dur"]
    else:
        tc = tv
        for i, (tx, zh) in enumerate(zip(seg["text"].split("|"), seg["zh"].split("|"))):
            f, dur, words = voice_chunk(seg, i, tx)
            chunks.append(dict(t=tc, dur=dur, file=f, text=tx.strip(), zh=zh.strip(), words=words))
            tc += dur + CHUNK_GAP
        tc -= CHUNK_GAP
        arc = None
    t1 = tc + sp["post"]
    segs.append(dict(id="truman", st=seg["st"], lang=seg["lang"], y=1945, m=8, t0=t0, tv=tv, t1=t1,
                     chunks=chunks, archival=arc, card=None, who=seg.get("who")))
    end["naga_t0"] = t1
    end["flash2"] = t1 + 1.6
    end["surrender"] = t1 + NAGA
    end["toll"] = end["surrender"] + SURRENDER
    end["title"] = end["toll"] + TOLL
    end["end"] = end["title"] + TITLE + TAIL
    tl = dict(bpm=BPM, sr=SR, intro=INTRO, segs=segs, end=end, duration=end["end"])
    os.makedirs(os.path.join(D, "build"), exist_ok=True)
    json.dump(tl, open(os.path.join(D, "build", "timeline.json"), "w"), ensure_ascii=False, indent=1)
    return tl


if __name__ == "__main__":
    tl = build()
    for s in tl["segs"]:
        src = "tts" if any(c["file"] for c in s["chunks"]) else "est"
        print(f"{s['id']:11s} {s['t0']:6.2f} -> {s['t1']:6.2f}  ({s['t1'] - s['t0']:4.1f}s, {src})")
    print({k: round(v, 2) for k, v in tl["end"].items()})
    print("total", round(tl["duration"], 1), "s")
