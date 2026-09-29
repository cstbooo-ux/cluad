"""Beat / accent analysis of the edited track -> music.json (drives every cut in the timeline).

python3 analyze_music.py [music/song.wav]
"""
import json, os, sys
import numpy as np
import librosa

D = os.path.dirname(os.path.abspath(__file__))
path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(D, "music", "song.wav")
y, sr = librosa.load(path, sr=22050, mono=True)
hop = 128
oenv = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop)
ft = librosa.frames_to_time(np.arange(len(oenv)), sr=sr, hop_length=hop)
S = np.abs(librosa.stft(y, n_fft=2048, hop_length=hop))
f = librosa.fft_frequencies(sr=sr, n_fft=2048)
low = S[f < 150].sum(0)
lowd = np.maximum(0, np.diff(low, prepend=low[0]))
lowd = lowd / lowd.max() * oenv.max()


def grid_score(env, per, ph, t0, t1):
    ts = np.arange(ph, t1, per)
    ts = ts[ts >= t0]
    return env[np.searchsorted(ft, ts)].mean()


# climax: steady grid
best = None
for bpm in np.arange(89.0, 92.01, 0.02):
    per = 60 / bpm
    for ph in np.arange(13.3, 13.3 + per, 0.004):
        s = grid_score(oenv, per, ph, 13.3, 34.5) + grid_score(lowd, per, ph, 13.3, 34.5)
        if best is None or s > best[0]:
            best = (s, bpm, ph)
_, bpm, ph = best
per = 60 / bpm

# intro: tracked beats (tempo is loose there)
_, intro_beats = librosa.beat.beat_track(onset_envelope=oenv[: np.searchsorted(ft, 13.3)], sr=sr,
                                         hop_length=hop, units="time")

score = lowd / lowd.max() + oenv / oenv.max()
peaks = librosa.util.peak_pick(score, pre_max=20, post_max=20, pre_avg=40, post_avg=40, delta=0.2, wait=40)
hits = sorted([(float(ft[i]), float(score[i])) for i in peaks], key=lambda h: -h[1])[:40]

out = {
    "duration": float(len(y) / sr),
    "intro_beats": [round(float(b), 3) for b in intro_beats],
    "drop": 13.50,                 # heaviest low hit: paper plane -> fighter
    "climax_bpm": round(float(bpm), 3),
    "climax_beat0": round(float(ph), 3),   # strong beats at beat0 + k * 60/bpm
    "climax_end": 34.85,           # last heavy accent, music drops out -> back to 1930
    "hits": sorted([[round(t, 3), round(s, 2)] for t, s in hits]),
}
json.dump(out, open(os.path.join(D, "music.json"), "w"), indent=1)
print(json.dumps({k: v for k, v in out.items() if k != "hits"}, indent=1))
