"""'Paper Plane' compositor: timeline locked to the edited music, camera impact, captions, SFX, output.

python3 render.py video [out]      full render -> out/paper_plane.mp4 (silent), _sfx.mp4, _music.mp4 (+ preview)
python3 render.py frame <sec>      single frame png
python3 render.py sheet            contact sheet of the timeline
"""
import json, math, os, subprocess, sys
from multiprocessing import Pool
import numpy as np
from PIL import Image
import imageio_ffmpeg

D = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(D, "..", "..")))
sys.path.insert(0, D)
from silhouette_kit.core import W, H, new_canvas, post, rect
from silhouette_kit import aircraft as A
import shots as S
from captions import Caption

MUSIC = json.load(open(os.path.join(D, "music.json")))
FPS = 30
DUR = 41.2
NF = int(DUR * FPS)
BPM = MUSIC["climax_bpm"]
B0 = MUSIC["climax_beat0"]
PER = 60 / BPM
DROP = MUSIC["drop"]                 # 13.50: paper plane -> Spitfire
END = MUSIC["climax_end"]            # 34.85: back to 1930


def beat(k):
    return B0 + k * PER


def ease(u):
    u = max(0.0, min(1.0, u))
    return u * u * (3 - 2 * u)


def lin(t, t0, t1):
    return max(0.0, min(1.0, (t - t0) / (t1 - t0)))


# ------------------------------------------------------------------ shots
PLANE = dict(plane_xy=(1180, 450), size=260, pitch=0.38)


from silhouette_kit.child import run_travel
RUN_H = 250
RUN_PERIOD = 4.6 / (2000 / run_travel(1.0, RUN_H))          # stride time so he covers 2000 px in 4.6 s


def run_shot(ctx, t):
    ph = t / RUN_PERIOD
    xw = -120 + run_travel(ph, RUN_H)                          # feet planted: position follows the stance foot
    pan = 700 * ease((t - 0.8) / 3.8)
    S.shot_kent_run(ctx, t / 4.6, t, boy_x=xw, pan=pan, phase=ph)


def throw_pan(t):
    q = lin(t, 5.25, 5.71)
    return 700 + 260 * q * q                                   # accelerates into the follow shot


def throw_shot(ctx, t):
    k = 0.5 * lin(t, 4.6, 5.34) if t < 5.34 else 0.5 + 0.5 * lin(t, 5.34, 5.71)
    fly = lin(t, 5.34, 5.71)
    return S.shot_kent_throw(ctx, 0, t, pan=throw_pan(t), k=k, fly=fly)


V_PAN = 2 * 260 / 0.46                                         # pan speed at the end of the throw


def follow_pan(t):
    tau = max(0.0, t - 5.71)
    return 960 + 300 * tau + (V_PAN - 300) * 0.6 * (1 - math.exp(-tau / 0.6))


_THROW_END = None


def throw_end_pose():
    """Where the paper plane is on the last frame of the throw (so the follow shot can pick it up there)."""
    global _THROW_END
    if _THROW_END is None:
        s, ctx = new_canvas()
        _THROW_END = throw_shot(ctx, 5.71 - 1e-6)
    return _THROW_END


def follow_params(t):
    """One camera for the whole ride: pitch up (tilt) + climb, continuous pan, plane caught up to its mark."""
    x0, y0, s0, p0 = throw_end_pose()
    q = ease(lin(t, 5.71, 6.5))                                 # camera catches up with the plane
    return dict(redness=ease((t - 7.0) / 6.0),
                tilt=520 * ease((t - 5.71) / 4.5), climb=900 * ease((t - 5.71) / 6.5),
                plane_xy=(x0 + (PLANE["plane_xy"][0] - x0) * q, y0 + (PLANE["plane_xy"][1] - y0) * q),
                size=s0 + (PLANE["size"] - s0) * q, pitch=p0 + (PLANE["pitch"] - p0) * q, pan=follow_pan(t))


def follow_shot(ctx, t):
    S.shot_follow_plane(ctx, lin(t, 5.71, DROP), t, **follow_params(t))


def cut_shot(ctx, t):
    if t - DROP < 2.5 / FPS:                               # impact frames: white void, black silhouette
        rect(ctx, 0, 0, W, H, "#fff6ea")
        x, y = PLANE["plane_xy"]
        A.aircraft(ctx, "spitfire", x, y + 6 * math.sin(t * 2.3), PLANE["size"],
                   pitch=PLANE["pitch"] + 0.03 * math.sin(t * 1.7), livery=None, c="#000000", markings=False)
        return
    S.shot_cut_spitfire(ctx, lin(t, DROP, beat(4)), t, reveal=lin(t, beat(1) - 0.1, beat(3)), **follow_params(t))


def hit_shot(ctx, t):
    if t - beat(17) < 2.5 / FPS:                            # red impact frames
        rect(ctx, 0, 0, W, H, "#ff3a1a")
        A.aircraft(ctx, "spitfire", 960, 540, 520, pitch=0.05, livery=None, c="#000000", markings=False, damage=0.4)
        return
    S.shot_hit(ctx, lin(t, beat(17), beat(19)), t)


def ending_shot(ctx, t):
    if t < 35.6:
        pick = 0.05 * lin(t, END, 35.6)
    elif t < 37.2:
        pick = 0.05 + 0.25 * lin(t, 35.6, 37.2)
    elif t < 38.2:
        pick = 0.3 + 0.3 * lin(t, 37.2, 38.2)
    else:
        pick = 0.6 + 0.4 * lin(t, 38.2, 39.7)
    S.shot_ending_grass(ctx, 0, t, pick=pick)


# (start, end, draw(ctx, t), camera)
#   camera: zoom=(z0, z1) over the shot, center=(x, y), shake=base jitter px, roll=(r0, r1) radians, grade
TL = [
    (0.0, 4.6, run_shot, dict()),
    (4.6, 5.71, throw_shot, dict(zoom=(1.0, 1.06))),
    (5.71, DROP, follow_shot, dict(zoom=(1.0, 1.0), center=PLANE["plane_xy"], shake=1.0)),
    (DROP, beat(4), cut_shot, dict(center=PLANE["plane_xy"], push=(DROP, beat(1), beat(3)), shake=3.0)),
    (beat(4), beat(6), lambda c, t: S.shot_cockpit(c, lin(t, beat(4), beat(6)), t, jaw=0.4 + 0.6 * lin(t, beat(4), beat(5))),
     dict(zoom=(1.0, 1.08), shake=5.0)),
    (beat(6), beat(7), lambda c, t: S.shot_stick(c, 0, t, squeeze=ease(lin(t, beat(6), beat(6) + 0.3))),
     dict(zoom=(1.12, 1.0), shake=2.5)),
    (beat(7), beat(8), lambda c, t: S.shot_wing_bank(c, 0, t, bank=0.2 + 0.6 * lin(t, beat(7), beat(8))),
     dict(roll=(0.0, -0.08), shake=6.0)),
    (beat(8), beat(9), lambda c, t: S.shot_gunsight(c, lin(t, beat(8), beat(9)), t), dict(zoom=(1.0, 1.1), shake=5.0)),
    (beat(9), beat(10), lambda c, t: S.shot_wing_guns(c, lin(t, beat(9), beat(10)), t), dict(shake=11.0)),
    (beat(10), beat(12), lambda c, t: S.shot_break_cloud(c, lin(t, beat(10), beat(12)), t), dict(zoom=(1.1, 1.0), shake=6.0)),
    (beat(12), beat(14), lambda c, t: S.shot_chase(c, lin(t, beat(12), beat(14)), t), dict(zoom=(1.0, 1.08), shake=6.0)),
    (beat(14), beat(16.5), lambda c, t: S.shot_attack(c, lin(t, beat(14), beat(16.5)), t), dict(roll=(0.05, -0.03), shake=6.0)),
    (beat(16.5), beat(17), lambda c, t: S.shot_cockpit(c, 0.5, t, jaw=0.2, look=0.12), dict(zoom=(1.04, 1.06), shake=1.0)),
    (beat(17), beat(19), hit_shot, dict(shake=6.0)),
    (beat(19), beat(22), lambda c, t: S.shot_falling(c, 0.5 * lin(t, beat(19), beat(22)), t), dict(shake=5.0, roll=(0.0, 0.05))),
    (beat(22), beat(24), lambda c, t: S.shot_cockpit_fall(c, lin(t, beat(22), beat(24)), t), dict(shake=6.0, zoom=(1.0, 1.1))),
    (beat(24), beat(27), lambda c, t: S.shot_falling(c, 0.5 + 0.5 * lin(t, beat(24), beat(27)), t),
     dict(shake=7.0, roll=(0.05, 0.1), zoom=(1.7, 1.9), center=(930, 490), anchor=(960, 560))),
    (beat(27), beat(29), lambda c, t: S.shot_tree(c, lin(t, beat(27), beat(29)), t), dict(shake=8.0)),
    (beat(29), beat(30), lambda c, t: S.shot_cockpit_fall(c, 1.0, t), dict(shake=10.0, zoom=(1.08, 1.18))),
    (beat(30), END, lambda c, t: S.shot_falling(c, 1.0 + 0.3 * lin(t, beat(30), END), t),
     dict(shake=12.0, zoom=(1.0, 1.25), roll=(0.1, 0.16))),
    (END, DUR + 1, ending_shot, dict()),
]

# impacts: (time, strength, flash colour or None)
IMPACTS = [(DROP, 1.8, "#ffffff"), (beat(17), 2.0, "#ff5a30"), (END, 1.2, "#fff4e0"), (5.34, 0.25, None),
           (10.86, 0.35, None), (11.36, 0.25, None)]
for t_, st_ in ((8.4, 0.18), (9.9, 0.18), (11.2, 0.3), (11.86, 0.25), (12.2, 0.3), (12.37, 0.3), (12.85, 0.4),
                (13.22, 0.5)):                              # turbulence jolts as clouds whip past before the drop
    IMPACTS.append((t_, st_, None))
for s_ in TL[3:-1]:                                          # every climax cut
    if s_[0] not in (beat(17), DROP):
        IMPACTS.append((s_[0], 0.55, None))
for h_t, h_s in MUSIC["hits"]:                              # strong accents inside the climax
    if DROP + 0.3 < h_t < END - 0.1 and h_s > 1.0:
        IMPACTS.append((h_t, 0.3, None))

CAPS = [Caption("1930年 · 英格兰肯特郡乡间", "KENT, ENGLAND · 1930", 0.0, 10.86, burn_dur=0.9, seed=3),
        Caption("1940年8月18日 · 英格兰南部", "SOUTHERN ENGLAND · 18 AUGUST 1940", 11.4, beat(4), burn_dur=0.9, seed=7)]


def shot_at(t):
    for i, s_ in enumerate(TL):
        if s_[0] <= t < s_[1]:
            return i
    return len(TL) - 1


def camera(t, i):
    t0, t1, _, cam = TL[i]
    u = lin(t, t0, t1)
    z0, z1 = cam.get("zoom", (1.0, 1.0))
    ku = ease(u) if cam.get("zoom_ease") else (1 - (1 - u) ** 3 if cam.get("zoom_out") else u)
    z = z0 + (z1 - z0) * ku
    r0, r1 = cam.get("roll", (0.0, 0.0))
    roll = r0 + (r1 - r0) * u
    cx, cy = cam.get("center", (W / 2, H / 2))
    ax, ay = cx, cy                                          # screen point the world `center` is pinned to
    if "anchor" in cam:
        ax, ay = cx + (cam["anchor"][0] - cx) * ku, cy + (cam["anchor"][1] - cy) * ku
    if "push" in cam:                                        # push in on the plane, then pull back out (one shot)
        p0, p1, p2 = cam["push"]
        if t < p1:
            k = 1 - (1 - lin(t, p0, p1)) ** 3
        else:
            k = 1 - ease(lin(t, p1, p2))
        z = 1.0 + 0.9 * k
        ax, ay = cx + (1010 - cx) * k, cy + (560 - cy) * k
    if "anchor0" in cam:
        ax, ay = cam["anchor0"][0] + (cx - cam["anchor0"][0]) * ku, cam["anchor0"][1] + (cy - cam["anchor0"][1]) * ku
    amp = cam.get("shake", 0.0)
    if 11.0 < t < DROP:                                      # buffeting builds toward the transformation
        amp += 9.0 * ((t - 11.0) / (DROP - 11.0)) ** 1.5
    flash, fcol, chroma = 0.0, None, 0.0
    for ti, st, col in IMPACTS:
        dt = t - ti
        if 0 <= dt < 1.2:
            amp += st * 22 * math.exp(-dt / 0.16)
            z += st * 0.07 * math.exp(-dt / 0.1)
            roll += st * 0.02 * math.exp(-dt / 0.2) * math.sin(dt * 40)
            chroma += st * 9 * math.exp(-dt / 0.14)
            if col:
                f = 0.85 * math.exp(-dt / 0.22)
                if f > flash:
                    flash, fcol = f, col
    if DROP <= t < END:                                     # pulse on every beat of the climax
        k = (t - B0) / PER
        dt = (k - math.floor(k)) * PER
        z += 0.012 * math.exp(-dt / 0.08)
    sx = amp * (math.sin(t * 91.3) * 0.6 + math.sin(t * 57.1 + 1.3) * 0.4)
    sy = amp * (math.cos(t * 83.7) * 0.6 + math.sin(t * 41.9 + 0.7) * 0.4)
    if DROP + 0.4 <= t < END:                               # handheld buffeting in the fight: slow sway + roll
        sx += 11 * (math.sin(t * 3.1) * 0.6 + math.sin(t * 7.3 + 0.4) * 0.4)
        sy += 9 * (math.sin(t * 2.6 + 1.1) * 0.6 + math.sin(t * 6.1 + 2.0) * 0.4)
        roll += 0.009 * math.sin(t * 2.2 + 0.5) + 0.004 * math.sin(t * 5.7)
    return z, roll, (cx, cy), (ax, ay), (sx, sy), flash, fcol, chroma


def render_frame(fi):
    t = fi / FPS
    i = shot_at(t)
    z, roll, (cx, cy), (ax, ay), (sx, sy), flash, fcol, chroma = camera(t, i)
    s, ctx = new_canvas()
    ctx.save()
    ctx.translate(ax + sx, ay + sy); ctx.rotate(roll); ctx.scale(z, z); ctx.translate(-cx, -cy)
    TL[i][2](ctx, t)
    ctx.restore()
    impact_frame = 0 <= t - DROP < 2.5 / FPS or 0 <= t - beat(17) < 2.5 / FPS
    if flash > 0.01 and not impact_frame:
        rect(ctx, 0, 0, W, H, fcol, flash)
    battle = DROP <= t < END
    fade = 0.0
    if t < 0.35:
        fade = 1 - t / 0.35
    if t > 39.7:
        fade = min(1.0, (t - 39.7) / 1.2)
    if fade > 0:
        rect(ctx, 0, 0, W, H, "#000000", fade)
    img = post(s, seed=fi, grain=7.0 + 3 * battle, vignette=0.3 + 0.12 * battle)
    if chroma > 0.6:
        k = int(round(chroma))
        img = img.copy()
        img[:, :, 0] = np.roll(img[:, :, 0], k, axis=1)
        img[:, :, 2] = np.roll(img[:, :, 2], -k, axis=1)
    for c in CAPS:
        img = c.draw(img, t)
    return img


def _bytes(fi):
    return render_frame(fi).tobytes()


def ffmpeg():
    return imageio_ffmpeg.get_ffmpeg_exe()


def video(out):
    os.makedirs(out, exist_ok=True)
    silent = os.path.join(out, "paper_plane.mp4")
    p = subprocess.Popen([ffmpeg(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "20",
                          "-pix_fmt", "yuv420p", silent], stdin=subprocess.PIPE)
    with Pool(os.cpu_count()) as pool:
        for k, b in enumerate(pool.imap(_bytes, range(NF), chunksize=3)):
            p.stdin.write(b)
            if k % 100 == 0:
                print("frame", k, "/", NF, flush=True)
    p.stdin.close(); p.wait()
    audio(out)
    music = os.path.join(D, "music", "song.wav")
    subprocess.run([ffmpeg(), "-y", "-loglevel", "error", "-i", silent, "-i", os.path.join(out, "sfx_mix.wav"),
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", os.path.join(out, "paper_plane_sfx.mp4")],
                   check=True)
    if os.path.exists(music):
        subprocess.run([ffmpeg(), "-y", "-loglevel", "error", "-i", silent, "-i", os.path.join(out, "music_sfx_mix.wav"),
                        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest",
                        os.path.join(out, "paper_plane_music.mp4")], check=True)
    print("done")


def audio(out):
    import soundtrack
    soundtrack.build(out, TL, IMPACTS, beat, DROP, END, DUR)


def sheet(out):
    ts = np.linspace(0.3, 40.5, 24)
    th = [Image.fromarray(render_frame(int(t * FPS))).resize((W // 5, H // 5)) for t in ts]
    im = Image.new("RGB", (6 * (W // 5 + 6), 4 * (H // 5 + 6)), (10, 10, 10))
    for k, t_ in enumerate(th):
        im.paste(t_, ((k % 6) * (W // 5 + 6), (k // 6) * (H // 5 + 6)))
    im.save(os.path.join(out, "timeline_sheet.png"))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "video"
    out = os.path.join(D, "out")
    if cmd == "frame":
        Image.fromarray(render_frame(int(float(sys.argv[2]) * FPS))).save(sys.argv[3] if len(sys.argv) > 3 else "frame.png")
    elif cmd == "sheet":
        os.makedirs(out, exist_ok=True); sheet(out)
    elif cmd == "audio":
        audio(sys.argv[2] if len(sys.argv) > 2 else out)
    else:
        video(sys.argv[2] if len(sys.argv) > 2 else out)
