# 从莱茵兰到长崎（1936—1945）

约 2 分钟的二战快节奏动画。暗色地图 + 墨迹式扩散的占领区 + 日期大字卡；
旁白做成"收音机换台"：每段是当地电台用当地语言播报，配中英/中俄等双语字幕。

- 成片：`ww2_1936_1945.mp4`（1920×1080，30fps，约 2:01，响度 -14 LUFS）
- 结构：莱茵兰（德语）→ 卢沟桥 / 南京（中文）→ 德奥合并、慕尼黑（英语）→ 波兰（波兰语）→ 英法宣战（英语）
  → 法国沦陷（法语）→ 不列颠空战（英语）→ 巴巴罗萨（俄语）→ 珍珠港（美式英语）→ 南进（日语）
  → 中途岛 → 斯大林格勒 → 诺曼底 → 攻克柏林 → 太平洋跳岛 → 广岛白闪、静默、白宫声明 → 长崎 → 片尾

## 文件

| 文件 | 作用 |
|---|---|
| `script.py` | 解说稿：每段的电台、语言、原文、中文字幕（用 `\|` 切成一一对应的字幕块） |
| `timeline.py` | 按配音真实时长排时间轴，段落起点对齐 120 BPM 的 16 分音符 → `build/timeline.json` |
| `geo.py` | 地图几何：海岸线、1938 年国界、各阶段占领区多边形 → `build/geo.pkl` |
| `render.py` | 逐帧渲染：镜头、占领区扩散/退去、箭头、航线、爆炸、地名、字幕、年份计数器、收音机面板、白闪 |
| `music.py` | 代码合成配乐（D 小调，1936–38 低音脉动 → 战鼓军鼓 → 斯大林格勒后转亮 → 广岛前只剩滴答声）与音效 |
| `mix.py` | 配音过老式调幅电台滤镜 + 配乐闪避 + 音效，响度标准化 |
| `tools/tts_offline.py` | 离线配音（当前成片所用） |
| `tools/tts_gen.py` | 微软 edge-tts 配音（网络放行后可替换） |
| `tools/contact.py` | 按时间点出缩略图总览，检查画面用 |
| `assets/tts/` | 已生成的配音片段 |

## 重新构建

```
pip install numpy scipy pillow opencv-python-headless shapely pyshp soundfile imageio-ffmpeg fonttools
bash tools/fetch_data.sh          # 地图数据与字体
bash build.sh
```
改画面只需改 `render.py` 里 `choreograph()` 的编排；改台词后先重新生成配音，再跑 `build.sh`。
预览单帧：`python3 render.py still 33.0` → `build/still_033.00.png`。

## 换成微软配音

当前环境的网络策略拦截了 `speech.platform.bing.com`，所以成片用的是离线配音。放行后：
```
pip install edge-tts && python3 tools/tts_gen.py   # 生成 assets/tts/*.mp3（优先于 .wav 使用）
bash build.sh
```
画面会按新的配音时长自动重新对齐。

`script.py` 里给慕尼黑（张伯伦）、珍珠港（罗斯福）、广岛（杜鲁门）预留了真实历史原声的位置。
把公有领域录音放进 `assets/archival/`，并在 `assets/archival_cuts.json` 里写上起止秒数
（`{"fdr_infamy.wav": {"start": 12.3, "end": 17.9}}`），就会替换现在的屏幕引语卡。

## 素材与许可

- 地图：Natural Earth（公有领域）；1938/1945 历史国界来自 [aourednik/historical-basemaps](https://github.com/aourednik/historical-basemaps)（GPL-3.0），占领区范围为手绘近似
- 字体：Noto Sans/Serif CJK、Oswald、Roboto Condensed、IBM Plex Mono、Special Elite（OFL / Apache-2.0）
- 配音模型（经 [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx) 运行）：
  Kokoro-82M（Apache-2.0，中文 zm_yunyang、英式 bm_george、美式 am_michael、日语 jm_kumo）；
  Piper：de_DE thorsten（CC0）、ru_RU denis（CC0）、pl_PL darkman（CC0）、fr_FR upmc / pierre（CC BY-SA 4.0）
- 配乐与音效：全部由 `music.py` 合成，无外部采样
- 画面不含纳粹标志，也不使用希特勒原声
