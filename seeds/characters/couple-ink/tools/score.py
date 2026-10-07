"""Score a rendered trace against the original: ink IoU plus a 3 px tolerant F1.

usage: score.py original.jpg mine.png x0 y0 x1 y1 overlay.png
Overlay: black = both, red = original only (I missed it), blue = mine only (I added it).
"""

import sys

import numpy as np
from PIL import Image
from scipy import ndimage as nd

orig, mine, x0, y0, x1, y1, overlay = (
    sys.argv[1],
    sys.argv[2],
    *map(int, sys.argv[3:7]),
    sys.argv[7],
)
a = np.array(Image.open(orig).convert("L"))[y0:y1, x0:x1] < 128
b = np.array(Image.open(mine).convert("L"))[y0:y1, x0:x1] < 128

iou = (a & b).sum() / (a | b).sum()
tol = 3
da = nd.distance_transform_edt(~a)  # distance to nearest original ink
db = nd.distance_transform_edt(~b)
precision = (da[b] <= tol).mean()  # my ink that lands near theirs
recall = (db[a] <= tol).mean()  # their ink I came near
f1 = 2 * precision * recall / (precision + recall)
print(
    f"IoU {iou:.3f} | F1@{tol}px {f1:.3f} (precision {precision:.3f}, recall {recall:.3f}) | ink orig {a.sum()} mine {b.sum()}"
)

rgb = np.full(a.shape + (3,), 255, np.uint8)
rgb[a & ~b] = (230, 40, 40)
rgb[b & ~a] = (40, 90, 230)
rgb[a & b] = (0, 0, 0)
Image.fromarray(rgb).resize(((x1 - x0) * 2, (y1 - y0) * 2), Image.NEAREST).save(overlay)
