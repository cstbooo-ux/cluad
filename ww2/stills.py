"""Render style-check stills: python3 stills.py [out_dir]"""
import os, sys
from PIL import Image
from lib import new_canvas, post, W, H
from scenes import SCENES

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "stills")
SHOTS = [
    ("01_stalingrad", "stalingrad", 0.10, {"kind": "civ"}),
    ("02_berlin", "berlin", 0.35, {"kind": "civ"}),
    ("03_warship", "warship", 0.0, {"kind": "sol"}),
    ("04_trench_charge", "trench", 0.02, {"kind": "sol", "run": 1.0, "charge": True}),
    ("05_air_battle", "airbattle", 0.5, {"kind": "sol"}),
    ("06_dawn_ending", "dawn", 0.15, {"kind": "civ"}),
]

os.makedirs(OUT, exist_ok=True)
thumbs = []
for i, (name, scene, phase, fig) in enumerate(SHOTS):
    s, ctx = new_canvas()
    SCENES[scene](ctx, t=0.4, phase=phase, fig=fig)
    img = Image.fromarray(post(s, seed=i))
    img.save(os.path.join(OUT, name + ".png"))
    thumbs.append(img.resize((W // 3, H // 3), Image.LANCZOS))

sheet = Image.new("RGB", (W // 3 * 3 + 40, H // 3 * 2 + 30), (16, 16, 16))
for i, th in enumerate(thumbs):
    sheet.paste(th, (10 + (i % 3) * (W // 3 + 10), 10 + (i // 3) * (H // 3 + 10)))
sheet.save(os.path.join(OUT, "00_contact_sheet.png"))
print("wrote", OUT)
