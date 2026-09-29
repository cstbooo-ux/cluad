"""按时间点渲染缩略图拼成一张总览图: python3 tools/contact.py out.png t1 t2 ..."""
import os, sys
from multiprocessing import Pool

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import render as R  # noqa: E402

COLS, TW, TH = 3, 640, 360


def job(t):
    return cv2.resize(R.to8(R.render(t, int(t * R.FPS))), (TW, TH), interpolation=cv2.INTER_AREA)


if __name__ == "__main__":
    out, ts = sys.argv[1], [float(x) for x in sys.argv[2:]]
    rows = (len(ts) + COLS - 1) // COLS
    sheet = np.zeros((rows * (TH + 4), COLS * (TW + 4), 3), np.uint8)
    with Pool(4) as p:
        ims = p.map(job, ts)
    for k, (t, im) in enumerate(zip(ts, ims)):
        r, c = divmod(k, COLS)
        im = cv2.cvtColor(im, cv2.COLOR_RGB2BGR)
        cv2.putText(im, f"{t:.1f}", (8, TH - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        sheet[r * (TH + 4):r * (TH + 4) + TH, c * (TW + 4):c * (TW + 4) + TW] = im
    cv2.imwrite(out, sheet)
    print("wrote", out)
