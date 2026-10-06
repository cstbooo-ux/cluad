# 《周总，夫人她真的不爱你了》2D 动态漫预告

- `zhouzong_trailer.mp4`：成片（720×1280 竖屏，24fps，约 2 分 40 秒，含配音 / 配乐 / 音效）
- `script.json`：分镜脚本，包括每个镜头的台词、气泡位置、事件时间、音效和配乐段落。改台词或节奏就改这里
- `timeline.py`：用离线中文 TTS（zhtts）合成全部台词，再按角色做变调（男声、老人声等），生成 `build/timeline.json`（镜头时间、口型包络）和 `build/dialogue.wav`
- `audio.py`：用代码合成配乐（钢琴、弦乐垫、钟琴、鼓等）和音效（雨、雷、关门、电话、火焰……），按对白自动压低音乐，混成 `build/mix.wav`
- `lib.js`：角色（半身像、全身剪影）、特效、镜头工具
- `scenes.js`：25 个镜头的画面
- `engine.js`：对白气泡、旁白框、时间轴
- `anim.html`：画布页面
- `render.js`：用 Chromium 逐帧渲染画面，再交给 ffmpeg 编码

画面全部由 Canvas 代码绘制，没有用到任何外部图片素材。

## 重新生成

```
npm install                                   # 字体：思源黑体/宋体、站酷快乐体、马善政毛笔体
# 中文 TTS 需要 Python 3.11 + TensorFlow 2.15
python3.11 -m venv venv && . venv/bin/activate
pip install "tensorflow-cpu==2.15.1" "numpy<2" scipy pypinyin zhtts
python timeline.py                            # 配音 + 时间轴
python audio.py                               # 配乐 + 音效 + 混音
NODE_PATH=$(npm root -g) node render.js zhouzong_trailer.mp4   # 需要全局安装 playwright
```

要预览单帧，可以运行 `node render.js --stills 12.5,60 stills/`。
要在浏览器里实时播放，先在本目录起一个 http 服务，然后打开 `anim.html?play`，点击画面即可开始。
