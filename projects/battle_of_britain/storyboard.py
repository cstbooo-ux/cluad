"""Key-frame storyboard of every shot -> design/storyboard.png (+ design/frames/*.png)."""
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from PIL import Image, ImageDraw, ImageFont
from silhouette_kit.core import new_canvas, post, W, H
import shots as S

D = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(D, "design")
os.makedirs(os.path.join(OUT, "frames"), exist_ok=True)
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

BOARD = [
    ("01 kent_run", "0.0-4.5s  boy runs, 1930 caption", lambda c: S.shot_kent_run(c, 0.55, 2.0)),
    ("02 kent_throw", "4.5-5.7s  throw from the hillock", lambda c: S.shot_kent_throw(c, 0.6, 5.0)),
    ("03 follow_gold", "5.7-8s  camera rides the plane", lambda c: S.shot_follow_plane(c, 0.2, 6.5, redness=0.1, drop=250)),
    ("04 follow_red", "8-13.4s  sky turns red, 1940 caption", lambda c: S.shot_follow_plane(c, 0.9, 12.0, redness=0.9, drop=900)),
    ("05 cut_spitfire", "13.50s  THE CUT: paper -> Spitfire", lambda c: S.shot_cut_spitfire(c, 0.1, 13.6)),
    ("06 formation", "13.5-17.5s  formation + bombers", lambda c: S.shot_formation(c, 0.5, 15.0)),
    ("07 cockpit", "cockpit profile, jaw set", lambda c: S.shot_cockpit(c, 0.5, 17.0)),
    ("08 stick", "hand tightens on the grip", lambda c: S.shot_stick(c, 0.5, 18.0)),
    ("09 wing_bank", "banking wing", lambda c: S.shot_wing_bank(c, 0.5, 18.7)),
    ("10 gunsight", "109 in the reflector sight", lambda c: S.shot_gunsight(c, 0.5, 19.3)),
    ("11 wing_guns", "wing guns open fire", lambda c: S.shot_wing_guns(c, 0.5, 20.0)),
    ("12 break_cloud", "bursting out of the cloud", lambda c: S.shot_break_cloud(c, 0.5, 21.0)),
    ("13 chase", "109 on the wingman's tail", lambda c: S.shot_chase(c, 0.5, 23.5)),
    ("14 attack", "side attack, 109 smoking", lambda c: S.shot_attack(c, 0.6, 25.0)),
    ("15 hit", "our Spitfire is hit", lambda c: S.shot_hit(c, 0.3, 27.0)),
    ("16 falling", "falling, fields rush up", lambda c: S.shot_dive(c, 0.4, 29.5)),
    ("17 tree", "skimming the great oak", lambda c: S.shot_tree(c, 0.4, 32.5)),
    ("18 cockpit_fall", "still hauling the stick", lambda c: S.shot_cockpit_fall(c, 0.7, 33.5)),
    ("19 ending", "34.85s  1930: plane in the grass", lambda c: S.shot_ending_grass(c, 0.3, 36.0, pick=0.2)),
    ("20 ending_pick", "he bends and picks it up", lambda c: S.shot_ending_grass(c, 0.6, 37.5, pick=0.5)),
    ("21 ending_look", "straightens it, looks at the sky", lambda c: S.shot_ending_grass(c, 0.9, 39.5, pick=0.97)),
]


def main(only=None):
    thumbs = []
    f = ImageFont.truetype(FONT, 26)
    for i, (name, cap, fn) in enumerate(BOARD):
        if only and name.split()[0] not in only:
            continue
        s, ctx = new_canvas()
        fn(ctx)
        im = Image.fromarray(post(s, seed=i, grain=6, vignette=0.3))
        im.save(os.path.join(OUT, "frames", name.replace(" ", "_") + ".png"))
        th = im.resize((W // 4, H // 4), Image.LANCZOS)
        d = ImageDraw.Draw(th)
        d.rectangle([0, H // 4 - 34, W // 4, H // 4], fill=(0, 0, 0))
        d.text((8, H // 4 - 31), f"{name.split()[0]}  {cap}", font=ImageFont.truetype(FONT, 17), fill=(240, 230, 210))
        thumbs.append(th)
    cols = 4
    rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (W // 4 + 8) + 8, rows * (H // 4 + 8) + 8), (12, 12, 12))
    for k, th in enumerate(thumbs):
        sheet.paste(th, (8 + (k % cols) * (W // 4 + 8), 8 + (k // cols) * (H // 4 + 8)))
    sheet.save(os.path.join(OUT, "storyboard.png"))


if __name__ == "__main__":
    main(sys.argv[1:] or None)
    print("ok")
