# 《方程的形状》：代数几何，以及更远的地方

成片为 `algebraic_geometry.mp4`：1920×1080，30fps，约 2 分 10 秒，配乐为程序合成（D 小调，96 BPM），所有冲击音效都和画面的切换、闪光对齐。

画面中的数学都是真实计算出来的：曲面是对多项式方程做光线步进（ray-marching）直接渲染的；27 条直线和各曲面的奇点坐标用牛顿法数值求出（见 `mathdata.py`）；有限域上的点、ℤ[√2] 在各素数处的分裂方式也都是实际算出来的。

## 分镜

| 时间 | 段落 | 内容 |
|---|---|---|
| 0:00 | 方程即形状 | x² + y² = 1，满足方程的点汇聚成圆 |
| 0:07 | 圆锥曲线 | x² + y² = (1 + e·x)²，离心率 e 从 0 连续变到 1.8：圆 → 椭圆 → 抛物线 → 双曲线 |
| 0:12 | 椭圆曲线 | y² = x³ − x + c 的等高线族收束成 y² = x³ − x；弦切法作 P ⊕ Q，再不断累加，引出「群」 |
| 0:25 | 复数世界 | 周期格 ℤ + ℤi 的基本域卷成圆柱再弯成环面；两条金色的圆就是实曲线的两个分支 |
| 0:35 | 27 条直线 | 克莱布什对角三次曲面；27 条直线逐条亮起（Cayley–Salmon, 1849） |
| 0:50 | 奇点竞赛 | 凯莱三次（4）→ 库默尔四次（16）→ 巴特六次（65）→ 巴特十次（345）；7 次及以上的最大奇点数至今未知 |
| 1:10 | 费马大定理 | xⁿ + yⁿ = zⁿ：n = 2 时圆上布满有理点（勾股数），n ≥ 3 的费马曲线上只有平凡点；弗雷曲线与怀尔斯的证明 |
| 1:22 | 卡拉比–丘 | Hanson 构造的 z₁⁵ + z₂⁵ = 1 在四维空间中的投影，缓慢做 4D 旋转 |
| 1:32 | 有限域 | y² = x³ + 7 (mod p)，p = 13 → 1031，曲线碎成星尘；这正是比特币的 secp256k1 |
| 1:42 | 概形 | Mumford 式的 Spec ℤ[x]「藏宝图」：素数是纤维，金线是 x² = 2 在各素数处的分裂、惰性与分歧；「上升的海」 |
| 1:52 | 终章 | 快切回顾 → 代数几何 |

## 文件

- `algebraic_geometry.mp4`：成片
- `timeline.py`：分镜时间与所有冲击点（画面和配乐共用）
- `scenes.py`：11 个场景，每个都是 `scene(t) -> HDR 图像` 的纯函数
- `engine.py`：软件 OpenGL 光线步进 / 网格渲染器、辉光、排版、后期（bloom、ACES、色差、震屏）
- `mathdata.py`：计算 27 条直线与各曲面奇点，写入 `data.json`
- `music.py`：合成配乐 `out/score.wav`
- `render.py` / `build.py`：逐帧渲染、分段并行、拼接混流

## 重新生成

```
pip install numpy scipy sympy pillow opencv-python-headless imageio-ffmpeg moderngl matplotlib soundfile
# 字体放到 fonts/：NotoSerifSC-{Light,Regular,Bold,Black}.otf（思源宋体 SC）
#                 CormorantGaramond.ttf、CormorantGaramond-Italic.ttf（Google Fonts）
python3 mathdata.py            # 可选：data.json 已提交
python3 music.py               # -> out/score.wav
python3 build.py render 3      # 3 路并行渲染分段（需要 xvfb-run；3D 场景使用 Mesa llvmpipe）
python3 build.py final         # 拼接 + 混入配乐 -> algebraic_geometry.mp4
```

预览单帧：`AG_SS=0.75 AG_Q=0.6 xvfb-run -a python3 render.py still 47 67.5`（输出到 `out/`）。
