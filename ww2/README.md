# 二战剪影卡点视频（BPM 105，72 拍 ≈ 41.1 秒，1920×1080）

当前阶段：画风确认静帧。

- `lib.py`：绘图基础（剪影人物走路循环、建筑、坦克、飞机、烟雾、后期颗粒/暗角）
- `scenes.py`：场景库（斯大林格勒雪原、柏林街头、日本战舰、战壕冲锋、空战、结尾日出）
- `stills.py`：输出静帧到 `stills/`（含 `00_contact_sheet.png` 总览）

```
pip install pycairo numpy pillow
python3 stills.py
```
