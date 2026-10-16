# 《线性代数：AI 的母语》科普短片

- `linalg_ai.mp4`：成片（1920×1080，30fps，2 分钟，字幕 + 配乐，无配音），面向学过线性代数的大学生
- `linalg_ai.srt`：外挂字幕（成片里已经烧录了字幕，这份用于平台上传或翻译）

## 内容

| 时间 | 段落 | 线代概念 → AI 用途 |
|---|---|---|
| 0:00 | 片头 | 网格 + 基向量 |
| 0:08 | 01 数据，就是向量 | 8×8 图片拉平成 ℝ⁶⁴ 向量；词嵌入，king − man + woman ≈ queen |
| 0:28 | 02 矩阵 = 线性变换 = 神经网络的一层 | 网格变换、矩阵的列 = 基向量落点；h = σ(Wx + b)，ReLU 折叠空间；多层网络、梯度下降与反向传播 |
| 0:56 | 03 点积 → 注意力机制 | 点积与夹角、投影；Q/K/V、因果注意力分数表、softmax(QKᵀ/√d)V |
| 1:20 | 04 特征值 · SVD → PCA · LoRA | 协方差矩阵特征向量与 PCA 投影；SVD 截断成低秩近似；LoRA 参数量对比（d = 4096, r = 8） |
| 1:44 | 05 矩阵乘法 → GPU 算力 | 串行 vs 并行矩阵乘法；每个 token 约 2 × 参数量次浮点运算 |
| 1:53 | 回顾 | 概念对照表 |

## 文件

- `scenes.js`：分镜脚本，包括全部字幕（`SUBS`）、7 个场景的画面和时间轴。改字幕或节奏就改这里
- `formulas.js`：全部 LaTeX 公式；`tex.js` 用 MathJax 把它们排成 SVG（`build/tex.json`）
- `lib.js`：3B1B 风格的绘图元件（坐标网格及其变换、向量箭头、矩阵色块、字幕）
- `music.py`：用代码合成配乐（钢琴琶音 + 铺底 + 低音，D 大调，60 BPM，每小节 4 秒，换场正好落在小节线上）
- `anim.html`：画布页面；`render.js`：用 Chromium 逐帧渲染再交给 ffmpeg 编码

画面全部由 Canvas 代码绘制，没有用到任何外部图片素材。

## 重新生成

```
npm install                       # 思源黑体 / 思源宋体、MathJax
pip install numpy scipy
node tex.js                       # 公式 -> build/tex.json
python3 music.py                  # 配乐 -> build/music.wav
NODE_PATH=$(npm root -g) node render.js linalg_ai.mp4      # 需要全局安装 playwright
NODE_PATH=$(npm root -g) node render.js --srt linalg_ai.srt
```

预览单帧：`node render.js --stills 30,75 stills/`。实时预览：在本目录起一个 http 服务，打开 `anim.html?play`，点击画面开始播放。
