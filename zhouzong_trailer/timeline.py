"""Synthesize every dialogue line (zhtts, offline) and lay out the shot timeline.

Writes build/voice/*.wav (44.1 kHz mono, per-character pitch/formant shift)
and build/timeline.json (shot/line/event times + lip-sync envelopes), which
both audio.py and anim.js read.
"""
import hashlib, json, os, re, subprocess, sys
import numpy as np
from scipy.io import wavfile

D = os.path.dirname(os.path.abspath(__file__))
B = os.path.join(D, "build")
VD = os.path.join(B, "voice")
os.makedirs(VD, exist_ok=True)
SR = 44100

S = json.load(open(os.path.join(D, "script.json"), encoding="utf-8"))
FPS = S["fps"]

_tts = None
def tts():
    global _tts
    if _tts is None:
        from zhtts.tts import TTS
        _tts = TTS()
    return _tts

def tts_text(t):
    t = t.replace("……", "，").replace("——", "。").replace("…", "，")
    t = re.sub(r"[^一-鿿，。！？、]", "", t)
    t = re.sub(r"^[，。]+", "", t)
    return t or "嗯。"

def voice_filter(v):
    rb_pitch = v["pitch"] / v["formant"]
    f = [f"rubberband=tempo={v['speed']:.3f}:pitch={rb_pitch:.3f}:formant=preserved"]
    if abs(v["formant"] - 1) > 1e-3:
        f.append(f"asetrate={24000 * v['formant']:.0f},aresample=24000,atempo={1 / v['formant']:.4f}")
    if v.get("whisper"):
        f.append("highpass=f=350,lowpass=f=4500")
    if v.get("reverb"):
        f.append("aecho=0.85:0.5:45|90:0.22|0.12")
    f.append(f"aresample={SR}")
    return ",".join(f)

def synth_line(who, text):
    v = S["voices"][who]
    key = hashlib.md5(json.dumps([who, text, v], ensure_ascii=False).encode()).hexdigest()[:12]
    out = os.path.join(VD, f"{who}_{key}.wav")
    if not os.path.exists(out):
        raw = os.path.join(VD, f"raw_{key}.wav")
        a = tts().synthesis(tts_text(text), sil_time=0.12).astype(np.float32)
        wavfile.write(raw, 24000, a)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-af", voice_filter(v),
                        "-ac", "1", "-c:a", "pcm_f32le", out], check=True)
        os.remove(raw)
    sr, x = wavfile.read(out)
    x = np.nan_to_num(x.astype(np.float32))
    x = x / (np.abs(x).max() + 1e-9) * 0.55 * v["gain"]
    # trim leading/trailing silence so bubbles and lips line up with the voice
    thr = 0.02 * np.abs(x).max()
    nz = np.where(np.abs(x) > thr)[0]
    x = x[max(0, nz[0] - int(0.02 * sr)): nz[-1] + int(0.08 * sr)]
    return out, x

def envelope(x):
    hop = SR // FPS
    n = int(np.ceil(len(x) / hop))
    e = np.array([np.sqrt(np.mean(x[i * hop:(i + 1) * hop] ** 2) + 1e-12) for i in range(n)])
    e = e / (np.percentile(e, 90) + 1e-9)
    e = np.clip(e, 0, 1)
    e = np.convolve(e, [0.25, 0.5, 0.25], mode="same")
    return [round(float(v), 2) for v in e]

def ev_eval(expr, ns):
    if isinstance(expr, (int, float)):
        return float(expr)
    return float(eval(expr, {"__builtins__": {}}, ns))

def resolve_events(evs, ns):
    changed = True
    while changed:
        changed = False
        for k, e in evs.items():
            if k in ns:
                continue
            try:
                ns[k] = ev_eval(e, ns)
                changed = True
            except NameError:
                pass

def main():
    shots, sfx, voices = [], [], []
    T = 0.0
    for sh in S["shots"]:
        ns = {}
        evs = sh.get("ev", {})
        cur = sh.get("pre", 0.4)
        lines = []
        for i, ln in enumerate(sh["lines"]):
            path, x = synth_line(ln["who"], ln["text"])
            dur = len(x) / SR
            resolve_events(evs, ns)
            if "at" in ln:
                st = ev_eval(ln["at"], ns)
            else:
                st = cur + (ln.get("gap", 0.25) if i else 0.0)
            ns[f"L{i}_start"], ns[f"L{i}_end"] = st, st + dur
            cur = st + dur
            lines.append({"who": ln["who"], "text": ln["text"], "start": round(st, 3), "end": round(st + dur, 3),
                          "b": ln.get("b"), "st": ln.get("st", "nar" if ln["who"] == "nar" else "speech"),
                          "env": envelope(x)})
            voices.append((T + st, x))
        resolve_events(evs, ns)
        missing = [k for k in evs if k not in ns]
        if missing:
            sys.exit(f"{sh['id']}: unresolved events {missing}")
        ev = {k: round(ns[k], 3) for k in evs}
        dur = max(sh.get("min", 0), cur + sh.get("post", 0.6), max(ev.values(), default=0) + 0.3)
        if "min_after" in sh:
            dur = max(dur, ev[sh["min_after"]["ev"]] + sh["min_after"]["dur"])
        for e in sh.get("sfx", []):
            row = [e[0], round(T + ev_eval(e[1], ns), 3)]
            if len(e) > 2:
                row.append(round(T + ev_eval(e[2], ns), 3))
            sfx.append(row)
        mg = [[round(ev_eval(a, ns), 3), g] for a, g in sh.get("mus_gain", [])]
        shots.append({"id": sh["id"], "start": round(T, 3), "dur": round(dur, 3), "lines": lines, "ev": ev,
                      "mus": sh.get("mus", "none"), "rain": sh.get("rain", False), "mus_gain": mg})
        T += dur
    out = {"W": S["W"], "H": S["H"], "fps": FPS, "total": round(T, 3), "shots": shots, "sfx": sfx,
           "names": {k: v["name"] for k, v in S["voices"].items()}}
    json.dump(out, open(os.path.join(B, "timeline.json"), "w", encoding="utf-8"), ensure_ascii=False)
    # dialogue stem
    n = int((T + 1) * SR)
    stem = np.zeros(n, np.float32)
    for t0, x in voices:
        i = int(t0 * SR)
        stem[i:i + len(x)] += x[: n - i]
    wavfile.write(os.path.join(B, "dialogue.wav"), SR, stem)
    for s in shots:
        print(f"{s['start']:7.2f} {s['dur']:5.2f} {s['id']}")
    print(f"total {T:.2f}s, {len(voices)} lines")

if __name__ == "__main__":
    main()
