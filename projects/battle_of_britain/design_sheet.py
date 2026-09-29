"""Character / aircraft design sheets for review.  python3 design_sheet.py"""
import os, sys, math
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from PIL import Image, ImageDraw, ImageFont
from silhouette_kit.core import new_canvas, post, rect, vgrad, W, H
from silhouette_kit import aircraft as A

D = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(D, "design")
os.makedirs(OUT, exist_ok=True)
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def label(img, items):
    d = ImageDraw.Draw(img)
    f = ImageFont.truetype(FONT, 22)
    for x, y, t in items:
        d.text((x, y), t, font=f, fill=(60, 50, 50))
    return img


def aircraft_sheet():
    s, ctx = new_canvas()
    vgrad(ctx, 0, H, [(0, "#c9b6a0"), (1, "#a8917c")])
    A.aircraft(ctx, "spitfire", 330, 200, 520, markings="roundel")
    A.aircraft(ctx, "bf109", 960, 200, 500, markings="cross")
    A.aircraft(ctx, "he111", 1580, 210, 560, markings="cross")
    A.aircraft(ctx, "spitfire", 330, 540, 520, pitch=0.35, bank=0.22, markings="roundel")
    A.aircraft(ctx, "bf109", 960, 540, 500, pitch=-0.15, bank=-0.25, markings="cross")
    A.paper_plane(ctx, 1580, 540, 520, pitch=0.35)
    A.aircraft(ctx, "spitfire", 1580, 540, 520, pitch=0.35, bank=0.22, a=0.18)
    A.planform(ctx, "spitfire", 330, 880, 300, heading=-0.3)
    A.planform(ctx, "bf109", 800, 880, 290, heading=-0.3)
    A.planform(ctx, "he111", 1260, 880, 280, heading=-0.3)
    A.tail_on(ctx, "bf109", 1700, 860, 330, roll=0.2)
    img = Image.fromarray(post(s, grain=3, vignette=0.1))
    label(img, [(90, 40, "Spitfire Mk I  (side, RAF roundel hint)"), (740, 40, "Bf 109E  (side, cross hint)"),
                (1330, 40, "He 111  (side)"), (90, 360, "Spitfire climbing + banked"),
                (740, 360, "Bf 109 diving + banked"), (1330, 360, "paper plane over Spitfire ghost (cut match)"),
                (90, 700, "Spitfire planform"), (620, 700, "Bf 109 planform"), (1080, 700, "He 111 planform"),
                (1540, 700, "Bf 109 tail-on (gunsight)")])
    img.save(os.path.join(OUT, "aircraft.png"))


def character_sheet():
    from silhouette_kit.child import child
    from silhouette_kit.pilot import pilot_profile, spade_grip
    s, ctx = new_canvas()
    vgrad(ctx, 0, H, [(0, "#e9d9b8"), (1, "#caa98a")])
    for i in range(6):                                   # run cycle
        child(ctx, 110 + i * 150, 420, 300, i / 6, run=1.0)
    for i, k in enumerate((0.0, 0.3, 0.45, 0.55, 0.75, 1.0)):   # throw
        r = child(ctx, 110 + i * 160, 900, 300, 0.0, throw=k)
        if k < 0.5:
            A.paper_plane(ctx, r["hand"][0], r["hand"][1] - 8, 70, pitch=0.5)
    vgrad(ctx, 0, 560, [(0, "#3a1418"), (1, "#c8502e")], x0=1060, x1=W)
    pilot_profile(ctx, 1450, 270, 250, jaw=1.0, rim="#ff7a4a")
    vgrad(ctx, 560, H, [(0, "#2a1012"), (1, "#8a3024")], x0=1060, x1=W)
    spade_grip(ctx, 1400, 780, 140, squeeze=1.0, button="#c8a050")
    img = Image.fromarray(post(s, grain=3, vignette=0.1))
    label(img, [(90, 40, "boy · run cycle"), (90, 520, "boy · throw (wind-up -> release -> follow)"),
                (1080, 40, "pilot close-up (helmet, goggles, Irvin collar)"),
                (1080, 580, "gloved hand on the spade grip")])
    img.save(os.path.join(OUT, "characters.png"))


if __name__ == "__main__":
    aircraft_sheet()
    character_sheet()
    print("ok")
