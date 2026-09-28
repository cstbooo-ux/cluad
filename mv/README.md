# 晚风粒子 MV（前 30 秒）

- `wanfeng_mv.mp4`：成片（1920×1080，30fps，147 BPM 节拍同步）
- `render.py`：逐帧渲染器（粒子、歌词、冲击效果；歌词时间在 `FR` 列表里改）
- `beat.py`：节拍对齐与音频特征提取，生成 `feat.json`

重新渲染：
```
pip install numpy scipy librosa soundfile opencv-python-headless pillow imageio-ffmpeg
# 字体放到 fonts/：NotoSerifSC-Bold.otf、NotoSerifSC-Black.otf（思源宋体 SC）
python3 render.py video out.mp4
```
