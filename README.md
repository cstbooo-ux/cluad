# 剪影卡点动画 · 资产库

纯代码生成的**扁平剪影插画**动画：一个纯黑剪影人物一直向右走，背景按音乐节拍切换场景，
配程序合成的环境音效。所有画面和声音都由 Python 生成，没有外部图片、视频或音频素材，也就没有版权顾虑。

![场景总览（平静版）](projects/ww2_silhouette/stills/scenes_A.png)

## 目录

```
.
├── silhouette_kit/                 可复用的画风引擎（核心资产）
│   ├── STYLE_GUIDE.md              画风规范：分层、配色、人物、道具、效果、节奏、做新动画的步骤
│   ├── core.py                     画布、颜色、基础形状、渐变、地形/天际线、胶片颗粒与暗角
│   ├── figure.py                   剪影人物（平民/士兵，走/跑/冲锋），脚步贴地不打滑
│   ├── child.py / pilot.py         小男孩（跑、扔、弯腰捡）/ 飞行员近景与握杆的手
│   ├── aircraft.py                 喷火式、Bf 109、He 111（侧视/俯视/尾视，1940 涂装）+ 纸飞机
│   ├── landscape.py                肯特乡间（烘干塔、橡树、树篱）与分层卡通云
│   ├── props.py                    地标、楼房、载具、飞机、植物、前景遮挡物
│   ├── fx.py                       天气（雪、雨、沙尘、雾、热浪）与战斗效果（火、烟、爆炸、曳光弹）
│   ├── sfx.py                      程序合成音效（环境声、脚步、爆炸、枪声、引擎、蓄力、重击）
│   ├── reference/                  人物特写、侧脸细节、走路循环小样
│   └── tools/figure_preview.py     重新生成人物参考图和走路小样
│
└── projects/
    └── ww2_silhouette/             作品一：二战剪影卡点视频（106 BPM，40.8 秒）
        ├── README.md               作品说明：结构、时间线、音效、怎么重新渲染
        ├── scenes.py               17 个场景，每个有 A 平静 / B 战火两个版本
        ├── render.py               时间线 + 渲染 + 出片
        ├── soundtrack.py           按时间线摆放音效
        ├── narration.md            旁白文案（俄/英/日三语）和字幕分段
        ├── cut_sheet.md            逐拍切点表
        ├── stills/                 场景总览图
        └── video/                  成片（1080p 母版、带音效版、节拍器版）和音效分轨
    └── battle_of_britain/          作品二：纸飞机 · 不列颠空战（Kikuo《暗叫》卡点，41.2 秒）
        ├── README.md               时间线、镜头冲击、文件说明
        ├── shots.py / render.py / soundtrack.py / captions.py
        ├── design/                 设定图、分镜、动态小样
        └── video/                  成片（带音乐预览、音效版、无声母版）
```

## 快速开始

```bash
pip install -r requirements.txt

# 出二战作品的全部场景总览图
python3 projects/ww2_silhouette/render.py sheets

# 渲染完整视频 + 音效（输出到 projects/ww2_silhouette/out/）
python3 projects/ww2_silhouette/render.py video
```

## 做新动画

复制 `projects/ww2_silhouette/` 为新文件夹，按 [`silhouette_kit/STYLE_GUIDE.md`](silhouette_kit/STYLE_GUIDE.md) 第 10 节改场景和时间线即可。
人物、道具、天气、音效直接从 `silhouette_kit` 引用。
