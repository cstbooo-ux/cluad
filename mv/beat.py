import librosa, numpy as np, json
p="/root/.claude/uploads/93e1386f-6f2e-51d5-9d2c-32b3fb875e1b/b0460060-__.wav"
y,sr=librosa.load(p,sr=22050,duration=31)
hop=128
env=librosa.onset.onset_strength(y=y,sr=sr,hop_length=hop)
# low-band (kick) envelope
S=np.abs(librosa.stft(y,hop_length=hop,n_fft=1024))
f=librosa.fft_frequencies(sr=sr,n_fft=1024)
low=S[f<150].sum(0); lowd=np.maximum(0,np.diff(low,prepend=low[0]))
ft=librosa.frames_to_time(np.arange(len(env)),sr=sr,hop_length=hop)
def score(e,bpm,ph):
    per=60/bpm; ts=np.arange(ph,30,per); idx=np.searchsorted(ft,ts); idx=idx[idx<len(e)]; return e[idx].mean()
best=None
for bpm in np.arange(146.0,148.01,0.05):
  for ph in np.arange(0,60/bpm,0.005):
    s=score(env,bpm,ph)
    if best is None or s>best[0]: best=(s,bpm,ph)
print("best full",best, "base mean",env.mean())
per=60/147
sc=[(score(env,147,ph),ph) for ph in np.arange(0,per,0.005)]; print("147 phase",max(sc))
sc=[(score(lowd,147,ph),ph) for ph in np.arange(0,per,0.005)]; print("147 kick phase",max(sc))
# per-frame normalized envelopes for rendering (at 30fps)
fps=30; N=int(30*fps)
def samp(e):
    e=e/np.percentile(e,99); return np.clip(np.interp(np.arange(N)/fps,ft,e),0,1.5).tolist()
json.dump({"env":samp(env),"low":samp(lowd),"rms":samp(librosa.feature.rms(y=y,hop_length=hop)[0][:len(ft)])},open("feat.json","w"))
