"""RAF fighter pilot close-ups: head-and-shoulders profile, and the gloved hand on the spade grip.

pilot_profile(ctx, x, y, s, ...)  s = head height (crown to chin) in px; (x, y) = head centre; faces right.
spade_grip(ctx, x, y, s, ...)     s = ring diameter in px; (x, y) = ring centre.
"""
import math
from .figure import Frame, smooth_path, HEAD

TAU = 2 * math.pi
C = True

# in head units, x forward, y DOWN (same frame as figure.HEAD)
HELMET = [(0.36, -0.22), (0.34, -0.36), (0.24, -0.5), (0.0, -0.6), (-0.26, -0.55), (-0.46, -0.36),
          (-0.53, -0.08), (-0.5, 0.2), (-0.4, 0.38, C), (-0.26, 0.4), (-0.12, 0.3), (0.0, 0.26), (0.05, 0.1),
          (0.12, -0.06), (0.3, -0.14, C)]
EAR_CUP = [(-0.08, -0.12), (0.08, -0.08), (0.14, 0.08), (0.08, 0.26), (-0.08, 0.3), (-0.2, 0.22), (-0.24, 0.05),
           (-0.2, -0.08)]
GOGGLE_STRAP = [(0.3, -0.12, C), (0.0, -0.16), (-0.53, -0.2, C), (-0.53, -0.1, C), (0.0, -0.06), (0.3, -0.02, C)]
GOGGLE = [(0.28, -0.14, C), (0.38, -0.155), (0.47, -0.13), (0.5, -0.06), (0.47, 0.02), (0.38, 0.04), (0.28, 0.02, C)]
GOGGLE_LENS = [(0.36, -0.12), (0.44, -0.11), (0.47, -0.06), (0.44, 0.0), (0.36, 0.01)]
CHIN_STRAP = [(0.02, 0.22, C), (0.2, 0.44, C), (0.3, 0.5, C), (0.28, 0.54, C), (0.16, 0.48, C), (-0.03, 0.27, C)]
# Irvin sheepskin collar + Mae West + shoulder (head units, y down)
COLLAR = [(-0.62, 0.3), (-0.4, 0.42), (-0.1, 0.52), (0.12, 0.58), (0.3, 0.66), (0.38, 0.8), (0.28, 0.95),
          (-0.1, 0.98), (-0.6, 0.9), (-0.85, 0.7), (-0.8, 0.45)]
BODY = [(-0.95, 0.6), (-0.4, 0.85), (0.1, 0.9), (0.36, 0.95), (0.48, 1.1), (0.52, 1.4), (0.54, 1.7, C),
        (-1.5, 1.7, C), (-1.45, 1.1), (-1.25, 0.75)]
MAE_WEST = [(0.25, 0.95), (0.48, 1.02), (0.6, 1.2), (0.6, 1.45), (0.5, 1.62), (0.3, 1.66)]


def _rgb(c):
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) / 255 for i in (0, 2, 4))


def pilot_profile(ctx, x, y, s, c="#000000", nod=0.0, jaw=0.0, rim=None, rim_w=0.0, lens="#8a3a30"):
    """Head-and-shoulders profile. jaw: 0..1 clench (pulls the mouth line in slightly).
    rim: optional rim-light colour traced along the face edge (e.g. red sky light)."""
    col = _rgb(c)
    F = Frame(x, y, nod, s)
    pts = lambda lst: F.pts([(p[0], -p[1]) + tuple(p[2:]) for p in lst])
    head = HEAD
    if jaw:
        head = [(p[0] - (0.02 * jaw if 0.2 < p[1] < 0.36 else 0.0), p[1]) + tuple(p[2:]) for p in HEAD]
    ctx.set_source_rgb(*col)
    for shape in (BODY, COLLAR, MAE_WEST, head, HELMET, EAR_CUP, GOGGLE_STRAP, GOGGLE, CHIN_STRAP):
        smooth_path(ctx, pts(shape)); ctx.fill()
    if lens:                                            # tinted lens reflecting the sky
        smooth_path(ctx, pts(GOGGLE_LENS)); ctx.set_source_rgba(*_rgb(lens), 0.85); ctx.fill()
        ctx.set_source_rgb(*col)
    # neck
    smooth_path(ctx, pts([(-0.36, 0.3), (-0.2, 0.45), (0.1, 0.55), (0.18, 0.5), (0.12, 0.42), (-0.1, 0.36)]))
    ctx.fill()
    if rim:
        rc = _rgb(rim)
        edge = [p for p in head if p[0] > 0.3 and -0.25 < p[1] < 0.52]
        ctx.new_path()
        smooth_path(ctx, pts(edge), closed=False)
        ctx.set_line_width(max(1.5, s * 0.012 * (1 + rim_w))); ctx.set_source_rgba(*rc, 0.8); ctx.stroke()
        gx, gy_ = F(0.43, 0.09)                          # goggle glint
        ctx.new_path(); ctx.arc(gx, gy_, s * 0.012, 0, TAU); ctx.set_source_rgba(*rc, 0.95); ctx.fill()


def spade_grip(ctx, x, y, s, c="#000000", squeeze=0.0, glove=None, button=None):
    """Spitfire spade grip (ring) with a gloved right hand gripping its side, thumb on the gun button.
    squeeze 0..1 tightens the fist; button = colour for the brass firing button (None = silhouette)."""
    col = _rgb(c)
    gc = _rgb(glove) if glove else col
    r = s / 2
    ctx.set_source_rgb(*col)
    # stick shaft + ring
    ctx.rectangle(x - r * 0.12, y + r * 0.8, r * 0.24, r * 3.2); ctx.fill()
    ctx.new_path(); ctx.arc(x, y, r * 0.86, 0, TAU); ctx.set_line_width(r * 0.26); ctx.stroke()
    ctx.rectangle(x - r * 0.18, y + r * 0.62, r * 0.36, r * 0.4); ctx.fill()
    # firing button on the top of the ring
    bx, by = x - r * 0.25, y - r * 0.95
    ctx.new_path(); ctx.arc(bx, by, r * 0.16, 0, TAU)
    ctx.set_source_rgb(*(_rgb(button) if button else col)); ctx.fill()
    # gloved fist: back of the hand behind the ring, four fingers curled over its right rim
    k = 1 - 0.06 * squeeze
    ctx.set_source_rgb(*gc)
    palm = [(x + r * 0.9, y - r * 1.0), (x + r * 1.55, y - r * 0.85), (x + r * 1.8 * k, y - r * 0.2),
            (x + r * 1.75 * k, y + r * 0.6), (x + r * 1.4, y + r * 1.05), (x + r * 0.95, y + r * 0.95)]
    smooth_path(ctx, palm); ctx.fill()
    ctx.set_line_cap(1)                                    # round caps -> fingertip bumps on the left edge
    for i in range(4):
        fy = y - r * 0.62 + i * r * 0.42
        tip = x + r * (0.48 + 0.06 * abs(i - 1.5) - 0.05 * squeeze)
        ctx.new_path(); ctx.move_to(x + r * 1.3, fy); ctx.line_to(tip, fy + r * 0.04)
        ctx.set_line_width(r * 0.36); ctx.stroke()
    # thumb over the top of the ring onto the button
    ctx.new_path(); ctx.move_to(x + r * 1.1, y - r * 0.85)
    ctx.curve_to(x + r * 0.7, y - r * 1.3, x + r * 0.1, y - r * 1.3, x - r * (0.12 - 0.05 * squeeze), y - r * 1.08)
    ctx.set_line_width(r * 0.34); ctx.stroke()
    ctx.set_line_cap(0)
    # gauntlet + sleeve going out of frame to the lower right
    cuff = [(x + r * 1.5, y - r * 0.7), (x + r * 2.4, y - r * 0.3), (x + r * 3.8, y + r * 1.4), (x + r * 3.4, y + r * 2.7),
            (x + r * 2.0, y + r * 1.9), (x + r * 1.4, y + r * 0.9)]
    ctx.set_source_rgb(*col)
    smooth_path(ctx, cuff); ctx.fill()
