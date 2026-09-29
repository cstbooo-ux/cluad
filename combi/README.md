# 组合数学 · COMBINATORICS（2 分 14 秒）

- `combinatorics.mp4`：成片（1920×1080，30fps，H.264 + AAC）
- `timeline.py`：共享时间轴（120 BPM）。画面事件和音乐事件都从这里取时间，所以每个动作都卡在拍子上
- `music.py`：配乐合成器，不用任何采样。D 小调，一段比一段密、一段比一段低沉，最后在 2:06 硬切成静音
- `render.py`：逐帧渲染器（numpy + OpenCV + Pillow + matplotlib mathtext）

章节（由浅入深）：

| 时间 | 章节 | 内容 |
|---|---|---|
| 0:00 | 序 | 一个点不断分裂 → 标题 |
| 0:10 | 壹 乘法原理 | 3×4 穿搭格子 → 放射状二叉树 → 2⁶⁴ |
| 0:26 | 贰 排列 | ABCD 的 24 种排列 → 阶乘爆炸 → 52! |
| 0:42 | 叁 组合 | C(5,2) → 帕斯卡三角 → 谢尔宾斯基三角形 |
| 1:00 | 肆 容斥原理 | 三圆韦恩图 → 错排概率收敛到 1/e |
| 1:16 | 伍 卡特兰数 | 14 条山路 / 14 种六边形三角剖分 → 通项公式 |
| 1:34 | 陆 生成函数 | 斐波那契 = 1/(1−x−x²)，卡特兰数的生成函数 |
| 1:48 | 柒 拉姆齐数 | R(3,3)=6 → K₄₃ → 43 ≤ R(5,5) ≤ 46 → 埃尔德什名言 → 数得清吗？ |

重新渲染：

```
pip install numpy scipy opencv-python-headless pillow matplotlib imageio-ffmpeg
# 字体放进 fonts/：SerifBlack.ttf、SerifBold.ttf（Noto Serif SC 900/700），
#                  SansLight.ttf、SansBold.ttf（Noto Sans SC 300/700）
python3 music.py music.wav
python3 render.py still 38.5 frame_#.jpg          # 单帧预览
python3 render.py video combinatorics.mp4 music.wav
```
