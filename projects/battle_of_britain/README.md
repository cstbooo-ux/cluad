# 纸飞机 · 不列颠空战（Paper Plane）

1930 年肯特郡，一个男孩把纸飞机掷向天空；纸飞机在音乐的重音上变成 1940 年 8 月 18 日的喷火式战斗机。
空战、中弹、坠落，最后在触地前切回 1930 年：纸飞机落进草地，男孩捡起它，抬头望天。

BGM：Kikuo《暗叫》剪辑版（41.2 秒，不入库；放到 `music/song.wav` 即可重新混音）。

## 成片（`video/`）
- `paper_plane_music_preview.mp4`：带音乐 + 音效的预览
- `paper_plane_sfx.mp4`：只有音效
- `paper_plane_1080p.mp4`：无声母版（高码率），剪辑用
- `audio/`：音效总混 + 环境 / 事件分轨

## 时间线（全部对齐 `music.json` 的节拍分析）
| 时间 | 画面 |
|---|---|
| 0 – 4.6s | 男孩跑过肯特郡乡间（1930 字幕从第一帧出现） |
| 4.6 – 5.7s | 跑上土坡，5.34s 拍点上松手 |
| 5.7 – 13.5s | 镜头随纸飞机飞，天空金→红；10.86s 字幕被烧掉，11.4s 出现 1940 字幕 |
| **13.50s** | 冲击帧（白底黑剪影）→ 纸飞机变喷火式，曳光弹横穿 |
| 13.5 – 34.85s | 按 90 BPM 强拍切：编队 → 座舱 → 握杆 → 机翼 → 瞄准镜 → 开火 → 冲出云层 → 救同伴 → 半拍停顿 → 中弹（红色冲击帧）→ 坠落 → 掠过大橡树 |
| **34.85s** | 闪白切回 1930 |
| 34.85 – 41.2s | 纸飞机落进草地，男孩捡起，抬头，渐黑 |

镜头冲击：切镜推近、强拍脉冲、震屏、闪白 / 红闪、色差分离、冲击帧、画面倾斜。

## 文件
- `analyze_music.py` → `music.json`：节拍、重音、切点
- `shots.py`：所有镜头（含空中交通、云层）
- `captions.py`：时地字幕 + 燃烧消失效果（`fonts/` 为思源宋体子集）
- `render.py`：时间线、镜头冲击、合成出片
- `soundtrack.py`：程序合成音效并与音乐混音
- `design_sheet.py` / `storyboard.py` / `traffic_preview.py`：设定图、分镜、动态小样（输出在 `design/`）

```
python3 projects/battle_of_britain/render.py video    # 输出到 out/
python3 projects/battle_of_britain/render.py frame 13.5
```
