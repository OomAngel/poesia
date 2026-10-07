"""Her and the dog walking in autumn — SVG in the style of the reference ink drawing."""

import math
import random

random.seed(7)
W, H = 940, 690
INK = "#111"
out = []


def add(s):
    out.append(s)


def scallop(cx, cy, rx, ry, n, bulge, jitter=0.0, a0=0.0):
    """Fluffy outline: an ellipse made of n outward-bulging arcs (fur)."""
    pts = []
    for i in range(n):
        a = a0 + 2 * math.pi * i / n
        j = 1 + random.uniform(-jitter, jitter)
        pts.append((cx + rx * j * math.cos(a), cy + ry * j * math.sin(a), a))
    d = f"M {pts[0][0]:.1f} {pts[0][1]:.1f} "
    for i in range(n):
        x1, y1, a1 = pts[i]
        x2, y2, a2 = pts[(i + 1) % n]
        am = a1 + math.pi / n
        b = bulge * (1 + random.uniform(-0.3, 0.3))
        qx = cx + (rx + b) * math.cos(am)
        qy = cy + (ry + b) * math.sin(am)
        d += f"Q {qx:.1f} {qy:.1f} {x2:.1f} {y2:.1f} "
    return d + "Z"


def leaf(x, y, size, angle, filled=False):
    """Almond leaf with a midrib and stem, like the reference's sprig leaves."""
    s = size
    body = f"M 0 {-s} C {s * 0.6} {-s * 0.5}, {s * 0.55} {s * 0.5}, 0 {s} C {-s * 0.55} {s * 0.5}, {-s * 0.6} {-s * 0.5}, 0 {-s} Z"
    fill = INK if filled else "white"
    g = f'<g transform="translate({x},{y}) rotate({angle})">'
    g += f'<path d="{body}" fill="{fill}" stroke="{INK}" stroke-width="5" stroke-linejoin="round"/>'
    if not filled:
        g += f'<path d="M 0 {-s * 0.7} L 0 {s * 0.75}" stroke="{INK}" stroke-width="3.5" stroke-linecap="round"/>'
    g += (
        f'<path d="M 0 {s} L 0 {s * 1.35}" stroke="{INK}" stroke-width="4" stroke-linecap="round"/>'
    )
    return g + "</g>"


def stroke(d, w=8, fill="none"):
    return (
        f'<path d="{d}" fill="{fill}" stroke="{INK}" stroke-width="{w}" '
        f'stroke-linecap="round" stroke-linejoin="round"/>'
    )


add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">')
# Hand-inked wobble: displace every stroke slightly, like brush pen on paper.
add(
    '<defs><filter id="ink" x="-5%" y="-5%" width="110%" height="110%">'
    '<feTurbulence type="fractalNoise" baseFrequency="0.035" numOctaves="2" seed="3"/>'
    '<feDisplacementMap in="SourceGraphic" scale="4"/></filter></defs>'
)
add(f'<rect width="{W}" height="{H}" fill="white"/>')
add('<g filter="url(#ink)">')

# ---------- left: autumn branch shedding leaves (stands in for the left flower)
add(stroke("M 120 640 C 125 560, 110 480, 135 400 C 145 365, 150 340, 148 310", 7))
for x, y, a in [(150, 300, -10), (118, 360, -55), (162, 395, 45), (112, 450, -60), (152, 500, 40)]:
    add(leaf(x, y, 22, a))
# ---------- right: tall sprig (echoes the reference's right-hand sprig)
add(stroke("M 860 650 C 865 580, 850 520, 868 450", 6))
for x, y, a, f in [
    (842, 470, -40, False),
    (888, 500, 45, False),
    (845, 540, -45, True),
    (884, 580, 40, False),
]:
    add(leaf(x, y, 18, a, f))

# ---------- falling leaves + the reference's scattered dots
for x, y, s, a, f in [
    (560, 150, 20, 30, False),
    (640, 250, 16, -50, True),
    (500, 70, 15, 70, False),
    (760, 190, 18, -20, False),
    (215, 130, 17, 60, False),
    (90, 230, 14, -30, True),
]:
    add(leaf(x, y, s, a, f))
for x, y, r in [
    (600, 95, 5),
    (618, 80, 4),
    (588, 112, 3.5),
    (720, 120, 7),
    (70, 300, 4),
    (95, 285, 3),
    (185, 90, 4),
    (800, 300, 5),
]:
    add(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{INK}"/>')
# leaves on the ground
for x, y, a, f in [
    (230, 640, 80, False),
    (470, 648, -75, True),
    (560, 655, 95, False),
    (330, 660, -85, False),
]:
    add(leaf(x, y, 15, a, f))

# ---------- the girl (chibi proportions from the reference: head ≈ 45% of height)
# legs mid-stride, black boots
add(stroke("M 295 525 L 285 600", 9))
add(stroke("M 365 525 L 392 595", 9))
add(f'<ellipse cx="276" cy="608" rx="24" ry="13" fill="{INK}"/>')
add(f'<ellipse cx="404" cy="602" rx="24" ry="13" fill="{INK}" transform="rotate(-12 404 602)"/>')
# coat
add(
    stroke(
        "M 272 370 C 240 420, 232 480, 245 535 L 415 535 C 428 480, 420 420, 388 370", 9, "white"
    )
)
# wrap closure, as in the reference robe
add(stroke("M 298 395 C 320 430, 340 460, 352 500", 7))
add(stroke("M 300 535 L 300 505", 6))
add(stroke("M 360 535 L 360 512", 6))
# left arm swinging back, right arm holding the leash
add(stroke("M 262 400 C 232 445, 228 478, 238 500", 9))
add(f'<circle cx="242" cy="508" r="13" fill="white" stroke="{INK}" stroke-width="7"/>')
add(stroke("M 398 400 C 432 425, 458 445, 478 452", 9))
add(f'<circle cx="488" cy="456" r="13" fill="white" stroke="{INK}" stroke-width="7"/>')
# scarf with a hanging tail
add(
    stroke(
        "M 262 368 C 300 392, 362 392, 400 368 L 404 388 C 362 412, 300 412, 258 388 Z", 8, "white"
    )
)
add(stroke("M 372 398 L 385 452 L 405 446 L 392 394", 7, "white"))
# ears, then face over them
add(stroke("M 216 252 C 186 252, 186 306, 218 306", 8, "white"))
add(stroke("M 444 252 C 474 252, 474 306, 442 306", 8, "white"))
add(f'<ellipse cx="330" cy="262" rx="118" ry="110" fill="white" stroke="{INK}" stroke-width="9"/>')
# bun
add(f'<circle cx="330" cy="112" r="42" fill="{INK}"/>')
# hair cap with a fringe of rounded strands
fringe = "M 212 285 C 200 170, 278 138, 330 138 C 382 138, 460 170, 448 285 "
xs = [440, 425, 408, 390, 372, 352, 332, 312, 292, 272, 254, 236, 220]
ys = [250, 238, 252, 232, 250, 236, 254, 234, 250, 236, 252, 240, 262]
for x, y in zip(xs, ys, strict=True):
    fringe += f"L {x} {y} "
add(f'<path d="{fringe}Z" fill="{INK}" stroke="{INK}" stroke-width="6" stroke-linejoin="round"/>')
# white strand partings inside the hair, the reference's signature detail
for x1, y1, x2, y2 in [
    (300, 165, 282, 236),
    (322, 160, 318, 240),
    (345, 160, 362, 238),
    (368, 168, 398, 228),
    (278, 175, 252, 238),
    (392, 182, 425, 236),
]:
    add(
        f'<path d="M {x1} {y1} Q {(x1 + x2) / 2 + 4} {(y1 + y2) / 2} {x2} {y2}" stroke="white" '
        f'stroke-width="5" stroke-linecap="round" fill="none"/>'
    )
# loose strands beside the cheeks
add(stroke("M 228 270 C 232 310, 228 345, 236 372", 6))
add(stroke("M 432 270 C 428 310, 432 345, 424 372", 6))
# closed eyes with lashes, dot nose, small smile
for cx in (288, 372):
    add(stroke(f"M {cx - 24} 298 Q {cx} 314 {cx + 24} 298", 6))
    for k, dx in enumerate((-16, -6, 4, 14)):
        add(stroke(f"M {cx + dx} {306 + (2 if k in (1, 2) else 0)} l {dx * 0.12:.1f} 9", 3.5))
add(f'<circle cx="330" cy="322" r="3.5" fill="{INK}"/>')
add(stroke("M 318 338 Q 330 350 342 338", 5))

# ---------- the dog, trotting beside her
# leash
add(stroke("M 496 462 C 545 525, 600 515, 638 478", 5))
# tail tuft, body, legs
add(
    f'<path d="{scallop(800, 528, 22, 16, 7, 9, 0.15)}" fill="white" stroke="{INK}" stroke-width="6"/>'
)
add(
    f'<path d="{scallop(708, 568, 88, 52, 20, 11, 0.06)}" fill="white" stroke="{INK}" stroke-width="7"/>'
)
for x, dx in [(650, -6), (690, 4), (735, -4), (770, 6)]:
    add(stroke(f"M {x} 605 l {dx} 28", 7))
    add(stroke(f"M {x + dx - 10} 636 q 10 -8 20 0", 6))
# floppy ears behind the head, then the head
add(
    f'<path d="{scallop(618, 478, 26, 42, 9, 9, 0.12)}" fill="white" stroke="{INK}" stroke-width="6"/>'
)
add(
    f'<path d="{scallop(744, 478, 26, 42, 9, 9, 0.12)}" fill="white" stroke="{INK}" stroke-width="6"/>'
)
add(
    f'<path d="{scallop(681, 462, 66, 60, 18, 10, 0.07)}" fill="white" stroke="{INK}" stroke-width="7"/>'
)
# collar
add(stroke("M 632 512 Q 681 532 730 512", 6))
# face: two bead eyes, nose, tiny mouth (the reference's dog face)
add(f'<circle cx="660" cy="462" r="9.5" fill="{INK}"/>')
add(f'<circle cx="704" cy="462" r="9.5" fill="{INK}"/>')
add(f'<ellipse cx="682" cy="482" rx="7" ry="5.5" fill="{INK}"/>')
add(stroke("M 674 494 Q 682 502 690 494", 4))

add("</g></svg>")

with open("autumn_walk.svg", "w") as f:
    f.write("\n".join(out))
print("wrote autumn_walk.svg")
