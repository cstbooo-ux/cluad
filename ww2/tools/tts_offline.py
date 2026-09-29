"""离线配音（后备方案，微软 edge-tts 连不上时使用）

模型来自 k2-fsa/sherpa-onnx 的 tts-models 发布页，解压到 build/models/：
  kokoro-multi-lang-v1_0            中文 / 英式英语 / 美式英语 / 日语
  vits-piper-de_DE-thorsten-high    德语
  vits-piper-ru_RU-denis-medium     俄语
  vits-piper-pl_PL-darkman-medium   波兰语
  vits-piper-fr_FR-upmc-medium      法语（说话人 pierre）
日语走 misaki 的 G2P 生成音素，再直接喂给 Kokoro 的 ONNX 模型。

输出与 tts_gen.py 相同的位置：assets/tts/<段id>_<句序号>.wav
"""
import os, sys

import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import script  # noqa: E402

M = os.path.join(ROOT, "build", "models")
OUT = os.path.join(ROOT, "assets", "tts")
SPEED = 1.0 + int(script.RATE.strip("%+")) / 100
KOKORO = os.path.join(M, "kokoro-multi-lang-v1_0")
# Kokoro v1.0 的说话人编号（按声音名字母序）
KSPK = {"am_michael": 16, "am_onyx": 17, "am_eric": 13, "bm_george": 26, "bm_lewis": 27, "bm_daniel": 24,
        "jm_kumo": 41, "zm_yunyang": 52, "zm_yunjian": 49}
VOICE = {
    "zh": ("kokoro", "zm_yunyang", "lexicon-zh.txt"),
    "gb": ("kokoro", "bm_george", "lexicon-gb-en.txt"),
    "us": ("kokoro", "am_michael", "lexicon-us-en.txt"),
    "de": ("piper", "vits-piper-de_DE-thorsten-high", None),
    "ru": ("piper", "vits-piper-ru_RU-denis-medium", None),
    "pl": ("piper", "vits-piper-pl_PL-darkman-medium", None),
    "fr": ("piper", "vits-piper-fr_FR-upmc-medium", None),
    "ja": ("kokoro-ja", "jm_kumo", None),
}
PIPER_SID = {"vits-piper-fr_FR-upmc-medium": 1}  # pierre（男声）
_cache = {}


def engine(lang):
    import sherpa_onnx
    kind, name, lex = VOICE[lang]
    key = (kind, name, lex)
    if key in _cache:
        return _cache[key]
    if kind == "piper":
        d = os.path.join(M, name)
        onnx = [f for f in os.listdir(d) if f.endswith(".onnx")][0]
        mc = sherpa_onnx.OfflineTtsModelConfig(
            vits=sherpa_onnx.OfflineTtsVitsModelConfig(model=os.path.join(d, onnx), tokens=os.path.join(d, "tokens.txt"),
                                                       data_dir=os.path.join(d, "espeak-ng-data")),
            num_threads=4)
    else:
        d = KOKORO
        mc = sherpa_onnx.OfflineTtsModelConfig(
            kokoro=sherpa_onnx.OfflineTtsKokoroModelConfig(
                model=os.path.join(d, "model.onnx"), voices=os.path.join(d, "voices.bin"),
                tokens=os.path.join(d, "tokens.txt"), data_dir=os.path.join(d, "espeak-ng-data"),
                dict_dir=os.path.join(d, "dict"), lexicon=os.path.join(d, lex)),
            num_threads=4)
    fst = []
    if lang == "zh":
        fst = [os.path.join(KOKORO, f) for f in ("date-zh.fst", "number-zh.fst", "phone-zh.fst")]
    cfg = sherpa_onnx.OfflineTtsConfig(model=mc, rule_fsts=",".join(fst), max_num_sentences=1)
    _cache[key] = sherpa_onnx.OfflineTts(cfg)
    return _cache[key]


def kokoro_ja(text, voice, speed):
    """misaki 日语 G2P -> Kokoro 音素 token -> onnxruntime 推理"""
    import onnxruntime as ort
    from misaki import ja
    import re
    g2p = ja.JAG2P(version="pyopenjtalk")
    ps, _ = g2p(text)
    ps = ps[: len(ps) - len(re.search(r"[_\-^j]*$", ps).group(0))]  # 去掉末尾附带的音高标记
    vocab = {}
    for line in open(os.path.join(KOKORO, "tokens.txt"), encoding="utf-8"):
        sym, _, idx = line.rstrip("\n").rpartition(" ")
        vocab[sym] = int(idx)
    ids = [vocab[c] for c in ps if c in vocab]
    voices = np.fromfile(os.path.join(KOKORO, "voices.bin"), np.float32).reshape(-1, 510, 256)
    style = voices[KSPK[voice], min(len(ids), 509)][None]
    sess = _cache.setdefault("ja_sess", ort.InferenceSession(os.path.join(KOKORO, "model.onnx")))
    names = [i.name for i in sess.get_inputs()]
    feed = {names[0]: np.array([[0] + ids + [0]], np.int64), names[1]: style.astype(np.float32),
            names[2]: np.array([speed], np.float32)}
    return sess.run(None, feed)[0].reshape(-1), 24000, ps


def main():
    os.makedirs(OUT, exist_ok=True)
    only = set(sys.argv[1:])
    for seg in script.SEGMENTS:
        if only and seg["id"] not in only:
            continue
        lang = seg["lang"]
        kind, name, _ = VOICE[lang]
        for i, c in enumerate(x.strip() for x in seg["text"].split("|")):
            if kind == "kokoro-ja":
                y, sr, ps = kokoro_ja(c, name, SPEED)
                print("   phonemes:", ps)
            else:
                sid = KSPK[name] if kind == "kokoro" else PIPER_SID.get(name, 0)
                a = engine(lang).generate(c, sid=sid, speed=SPEED)
                y, sr = np.asarray(a.samples, np.float32), a.sample_rate
            path = os.path.join(OUT, f"{seg['id']}_{i}.wav")
            sf.write(path, y, sr)
            print(f"ok {seg['id']}_{i} {lang} {name} {len(y) / sr:.2f}s")


if __name__ == "__main__":
    main()
