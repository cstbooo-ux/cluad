#!/usr/bin/env bash
# 一键构建：几何 -> 时间轴 -> 配乐 -> 混音 -> 逐帧渲染 -> 合成成片
set -euo pipefail
cd "$(dirname "$0")"
python3 geo.py
python3 timeline.py
python3 music.py
python3 mix.py
python3 render.py video build/video.mp4
ffmpeg -v error -y -i build/video.mp4 -i build/mix.wav -map 0:v -map 1:a \
  -c:v libx264 -preset slow -crf 19 -pix_fmt yuv420p -c:a aac -b:a 224k -movflags +faststart -shortest \
  ww2_1936_1945.mp4
echo "done: ww2_1936_1945.mp4"
