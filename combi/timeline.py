# Shared timeline: music.py and render.py both read this, so every visual
# event lands exactly on a musical one. 120 BPM -> beat = 0.5 s, bar = 2 s.
BPM = 120
BEAT = 60 / BPM
TOTAL = 134.0
CUT = 126.0        # hard cut to silence
FINAL = 127.0      # last boom: "数得清吗？"

SECTIONS = [
    ("intro", 0, 10), ("mult", 10, 26), ("perm", 26, 42), ("comb", 42, 60),
    ("incl", 60, 76), ("catalan", 76, 94), ("genf", 94, 108),
    ("ramsey", 108, CUT), ("outro", CUT, TOTAL),
]

# (time, strength) of big impacts: boom in the music, shake/flash on screen
HITS = [(6, .8), (10, .6), (26, .7), (38, 1.0), (42, .75), (54, .9), (60, .85),
        (72, .95), (76, .95), (90, 1.0), (94, 1.0), (102, 1.05), (108, 1.25),
        (115, 1.15), (119, 1.3), (FINAL, 1.6)]

# intro: the single point splits at these times (2^8 particles by 6.0 s)
SPLITS = [2.0, 3.0, 3.75, 4.25, 4.625, 4.875, 5.125, 5.375]

GRID_T0, GRID_DT = 13.0, 0.25          # 3x4 outfit grid, 12 cells
TREE_T0, TREE_DT, TREE_N = 18.0, 0.5, 13  # radial binary tree levels
PERM_T0, PERM_DT = 29.0, 0.25          # 24 permutations of ABCD
FACT_T0, FACT_DT = 35.0, 0.25          # factorial cascade (12 lines)
PAIR_T0, PAIR_DT = 45.0, 0.25          # C(5,2): 10 edges
PASCAL_T0, PASCAL_DT, PASCAL_N = 48.0, 0.5, 12
VENN_T0, VENN_DT = 63.0, 0.5           # 7 inclusion-exclusion terms
DER_T0, DER_DT, DER_N = 67.0, 0.5, 10  # derangement ratios D_n/n!
DYCK_T0, DYCK_DT = 79.0, 0.375         # 14 Dyck paths
TRI_T0, TRI_DT = 85.0, 0.25            # 14 hexagon triangulations
K6_T0, K6_DT = 111.0, 0.5              # 8 random 2-colourings of K6


def section_at(t):
    for name, a, b in SECTIONS:
        if a <= t < b:
            return name, a, b
    return SECTIONS[-1]


def kick_times():
    """Kick drum pattern, shared with the renderer for the pulse."""
    ks = []
    for i in range(int(TOTAL / BEAT)):
        t = i * BEAT
        if t >= CUT:
            break
        if 18 <= t < 26 and i % 4 == 0:
            ks.append(t)
        elif 26 <= t < 42 and i % 2 == 0:
            ks.append(t)
        elif 42 <= t < 94:
            ks.append(t)
        elif 94 <= t < 108:          # heartbeat: 1 and the "and" of 1
            if i % 4 == 0:
                ks += [t, t + 0.25]
            elif i % 4 == 2:
                ks.append(t)
        elif 108 <= t < CUT:
            ks.append(t)
            if t >= 115 and i % 2 == 1:
                ks.append(t + 0.25)
    return ks
