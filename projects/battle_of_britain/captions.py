"""Time/place captions rendered into the frame, with a fade-in and a 'burn away' exit:
a noisy burn front sweeps left -> right, the edge glows orange, a charred band darkens the letters
just ahead of it, and sparks drift up off the edge.
"""
import glob, math, os, random
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont

D = os.path.dirname(os.path.abspath(__file__))
CJK = [ImageFont.truetype(f, 46) for f in sorted(glob.glob(os.path.join(D, "fonts", "noto-serif-sc-*-700-normal.ttf")))]
LATIN = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf", 25)
W, H = 1920, 1080


_FILES = sorted(glob.glob(os.path.join(D, "fonts", "noto-serif-sc-*-700-normal.ttf")))
_CMAPS = [set(TTFont(f).getBestCmap()) for f in _FILES]


def _font_for(ch):
    for f, cm in zip(CJK, _CMAPS):
        if ord(ch) in cm:
            return f
    return LATIN


def _draw_cjk(d, x, y, text, fill):
    for ch in text:
        f = _font_for(ch) if ch != " " else CJK[0]
        if ch == " ":
            x += 16
            continue
        d.text((x, y), ch, font=f, fill=fill)
        x += f.getlength(ch) + 2
    return x


def _draw_spaced(d, x, y, text, font, fill, spacing=4):
    for ch in text:
        d.text((x, y), ch, font=font, fill=fill)
        x += font.getlength(ch) + spacing
    return x


class Caption:
    """zh / en lines, placed bottom-left. t_in: fade-in start, t_burn: burn start, burn_dur: seconds to burn."""

    def __init__(self, zh, en, t_in, t_burn, burn_dur=0.9, x=110, y=110, seed=1):
        self.t_in, self.t_burn, self.burn_dur = t_in, t_burn, burn_dur
        mask = Image.new("L", (W, H), 0)
        d = ImageDraw.Draw(mask)
        x1 = _draw_cjk(d, x, y, zh, 255)
        x2 = _draw_spaced(d, x + 2, y + 66, en, LATIN, 230, spacing=5)
        # thin rule between the lines
        d.rectangle([x, y + 62, x + 60, y + 63], fill=200)
        a = np.asarray(mask).astype(np.float32) / 255.0
        ys, xs = np.nonzero(a > 0.02)
        self.box = (max(0, xs.min() - 30), max(0, ys.min() - 60), min(W, xs.max() + 40), min(H, ys.max() + 30))
        x0, y0, x1b, y1b = self.box
        self.a = a[y0:y1b, x0:x1b]
        h, w = self.a.shape
        rng = np.random.default_rng(seed)
        # smooth noise for the burn front
        small = rng.random((h // 12 + 2, w // 12 + 2)).astype(np.float32)
        noise = np.asarray(Image.fromarray((small * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)) / 255.0
        xx = np.linspace(0, 1, w, dtype=np.float32)[None, :]
        yy = np.linspace(0, 1, h, dtype=np.float32)[:, None]
        self.field = xx * 0.78 + noise * 0.22 + yy * 0.04
        # soft glow version of the text for a faint halo
        self.halo = np.asarray(Image.fromarray((self.a * 255).astype(np.uint8)).resize(
            (max(1, w // 6), max(1, h // 6)), Image.BILINEAR).resize((w, h), Image.BILINEAR)).astype(np.float32) / 255.0
        self.seed = seed

    def draw(self, img, t, text_col=(244, 234, 214)):
        """img: HxWx3 uint8 (modified copy returned)."""
        if t < self.t_in or t > self.t_burn + self.burn_dur + 0.8:
            return img
        fade = min(1.0, (t - self.t_in) / 0.45)
        p = (t - self.t_burn) / self.burn_dur if t >= self.t_burn else -1.0
        p = -0.2 + 1.45 * p if p >= 0 else -1.0          # front position in field units
        x0, y0, x1, y1 = self.box
        out = img.copy()
        reg = out[y0:y1, x0:x1].astype(np.float32)
        a = self.a * fade
        if p > -1:
            alive = np.clip((self.field - p) / 0.02, 0, 1)
            char = np.clip(1 - (self.field - p) / 0.09, 0, 1) * (self.field > p)      # charring just ahead
            edge = np.exp(-((self.field - p) / 0.018) ** 2)
        else:
            alive, char, edge = 1.0, 0.0, 0.0
        # dark halo behind the letters for legibility
        sh = self.halo * fade * 0.45 * (alive if p > -1 else 1.0)
        reg *= (1 - sh[..., None] * 0.6)
        col = np.array(text_col, np.float32)
        charred = np.array((60, 30, 18), np.float32)
        tc = col[None, None, :] * (1 - char[..., None] * 0.85) + charred * (char[..., None] * 0.85) if p > -1 else col
        ta = (a * alive)[..., None]
        reg = reg * (1 - ta) + tc * ta
        if p > -1:
            glow = (edge * np.clip(self.halo * 3, 0, 1) * fade)[..., None]
            reg = reg + glow * np.array((255, 140, 40), np.float32) * 1.4
            hot = (edge * self.a)[..., None]
            reg = reg * (1 - hot) + np.array((255, 214, 120), np.float32) * hot
        out[y0:y1, x0:x1] = np.clip(reg, 0, 255).astype(np.uint8)
        if p > -1:
            self._sparks(out, t, p)
        return out

    def _sparks(self, out, t, p):
        """Embers rising from the burn front."""
        x0, y0, x1, y1 = self.box
        h, w = self.a.shape
        rng = random.Random(self.seed * 1000 + int(t * 30))
        cols = int(np.clip(p, 0, 1) * (w - 1))
        for k in range(40):
            born = t - rng.uniform(0, 0.8)
            pb = -0.2 + 1.45 * (born - self.t_burn) / self.burn_dur
            if pb < 0 or pb > 1.05:
                continue
            cx = x0 + int(np.clip((pb - 0.02) / 0.78, 0, 1) * w)
            age = t - born
            yy_ = rng.uniform(y0 + 40, y1 - 20)
            sx = int(cx + 60 * age + 15 * math.sin(age * 9 + k))
            sy = int(yy_ - 140 * age - 60 * age * age)
            r = max(1, int(3 * (1 - age / 0.8)))
            if 0 <= sx < W - r and 0 <= sy < H - r and r > 0:
                c = np.array((255, 180 - int(100 * age), 60), np.float32)
                a_ = 1 - age / 0.8
                patch = out[sy - r:sy + r + 1, sx - r:sx + r + 1].astype(np.float32)
                out[sy - r:sy + r + 1, sx - r:sx + r + 1] = np.clip(patch * (1 - a_) + c * a_, 0, 255).astype(np.uint8)
