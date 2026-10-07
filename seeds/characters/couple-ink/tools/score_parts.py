"""Per-feature IoU so the big hair mass can't hide misses in the small identity features.

usage: score_parts.py original.jpg mine.png
"""

import sys

import numpy as np
from PIL import Image

PARTS = {  # x0, y0, x1, y1 in original-image pixels
    "bun": (325, 30, 435, 104),
    "dome": (225, 104, 525, 262),
    "fringe": (282, 154, 462, 260),
    "brows": (298, 230, 440, 252),
    "eyes": (276, 280, 472, 322),
    "nose+mouth": (358, 288, 394, 330),
    "ears": (205, 260, 535, 336),
    # jaw stops at y 376: below that the robe collar enters the box and I don't draw it
    "jaw": (262, 334, 478, 376),
    "lock L": (244, 334, 272, 410),
    "lock R": (468, 334, 496, 402),
}
a = np.array(Image.open(sys.argv[1]).convert("L")) < 128
b = np.array(Image.open(sys.argv[2]).convert("L")) < 128
for name, (x0, y0, x1, y1) in PARTS.items():
    pa, pb = a[y0:y1, x0:x1], b[y0:y1, x0:x1]
    print(
        f"{name:11s} IoU {(pa & pb).sum() / (pa | pb).sum():.3f}  ink orig {pa.sum():5d} mine {pb.sum():5d}"
    )
