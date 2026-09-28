"""用微软 edge-tts 生成全部播报，逐句一个文件，并记录词级时间戳。

用法: pip install edge-tts && python3 ww2/tools/tts_gen.py
输出: ww2/assets/tts/<段id>_<句序号>[_<备选声音>].mp3 与同名 .json（WordBoundary 时间，单位秒）
"""
import asyncio, json, os, sys

import edge_tts

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import script  # noqa: E402

OUT = os.path.join(ROOT, "assets", "tts")
# 同一种语言多备一个声音，挑效果更好的
ALTS = {"zh": ["zh-CN-YunjianNeural", "zh-CN-YunxiNeural"], "us": ["en-US-ChristopherNeural"],
        "gb": ["en-GB-ThomasNeural"], "de": ["de-DE-KillianNeural"]}


async def synth(text, voice, path):
    comm = edge_tts.Communicate(text, voice, rate=script.RATE, boundary="WordBoundary")
    words = []
    with open(path + ".mp3", "wb") as f:
        async for ch in comm.stream():
            if ch["type"] == "audio":
                f.write(ch["data"])
            elif ch["type"] in ("WordBoundary", "SentenceBoundary"):
                words.append(dict(t=ch["offset"] / 1e7, d=ch["duration"] / 1e7, w=ch["text"]))
    json.dump(dict(voice=voice, text=text, words=words), open(path + ".json", "w"), ensure_ascii=False, indent=0)


async def main():
    os.makedirs(OUT, exist_ok=True)
    jobs = []
    for seg in script.SEGMENTS:
        chunks = [c.strip() for c in seg["text"].split("|")]
        voices = [(script.VOICES[seg["lang"]], "")] + [(v, "_" + v.split("-")[2].replace("Neural", "").lower())
                                                        for v in ALTS.get(seg["lang"], [])]
        for voice, suf in voices:
            for i, c in enumerate(chunks):
                jobs.append((c, voice, os.path.join(OUT, f"{seg['id']}_{i}{suf}")))
    for c, v, p in jobs:
        for attempt in range(4):
            try:
                await synth(c, v, p)
                print("ok", os.path.basename(p), v)
                break
            except Exception as e:  # 网络抖动时重试
                print("retry", os.path.basename(p), e)
                await asyncio.sleep(2 ** attempt)
        else:
            sys.exit(f"failed: {p}")


if __name__ == "__main__":
    asyncio.run(main())
