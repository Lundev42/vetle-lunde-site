#!/usr/bin/env python3
"""Build the About-me background scene from the hand-off picture.

Source: tools/about-scene.svg, the Dolomites sunset we were given
(file2.svg, 1709 flat-coloured shapes on a 2912 x 1440 canvas, drawn back to
front). It is not deployed; this script writes the scene into
index.html.

  1. The shapes of the banded sky are dropped (SKY_PATHS) together with the
     shapes nothing shows of. A smooth sky image takes the sky's place: the
     colours of the picture's own sky, blurred, darkening upwards into a
     night or dusk colour, and running on far above the picture so the
     atmosphere fills the whole section up to its top edge.
  2. Small blob-like trees (TREES, none in the current picture) can be
     redrawn as narrow spruces: a wedge, wide at the foot and pointed at
     the top, with a few short branch tips along its sides.
  3. Every other shape keeps its outline. Its colour becomes a CSS custom
     property per colour theme: Devon keeps the picture's own colours, the
     other periods map them in OKLCH (keeping light and shadow), so every
     theme repaints the scene.
  4. Two more mountains stand close on each side, from the user's Torres
     del Paine (left) and Stetind (right) pictures
     (tools/about-scene-torres.svg, tools/about-scene-stetind.svg):
     recoloured like the rest, with a little haze over them.
  5. The hazy far ridges from the middle of the main picture are copied
     into the gaps between the mountains.
  6. In front of the side mountains, layers of hills in the main picture's
     foreground colours rise from the bottom up to the mountains' feet,
     with a few spruces. Next to the main picture each layer runs into the
     band of its own colour there, so the joins do not show; the main
     picture's far ridge at its right edge is cut back into a slope.

Run from the repo root:  python3 tools/about-scene.py
Needs numpy, scipy, opencv and Pillow. It rewrites the <svg class="about-scene">
element and the generated CSS between the scene-tones markers in index.html.
Use --debug DIR to write a preview page per theme.
"""
import argparse
import base64
import re
import sys

import cv2
import numpy as np
from scipy.ndimage import gaussian_filter
from scipy.signal import find_peaks

SRC = "tools/about-scene.svg"
HTML = "index.html"

W, H = 2912, 1440          # canvas of the source SVG
TOP = -67                  # first row drawn (above the canvas: only sky there), so the
                           # towers start 14 % down the scene
# Two more mountains, one on each side of the main picture (the user's
# Torres del Paine and Stetind pictures). Their skies are dropped and their
# own foregrounds are covered by the scene's ground (below). Each is scaled
# by "scale" and moved so its pixel "anchor" (the foot on the side facing
# the main picture, at its ground line) lands at "at", close to the main
# picture's peaks, where the user marked them. "cut" trims the low outlying
# hills on the side facing the main picture along a slope (scene units, top
# to bottom), so they do not end in the picture's straight edge.
SIDE_PICS = [
    dict(name="torres", src="tools/about-scene-torres.svg", w=2752, h=1536, scale=0.62,
         anchor=(2700, 1190), at=(-130, 830), cut=None),
    dict(name="stetind", src="tools/about-scene-stetind.svg", w=2752, h=1536, scale=0.55,
         anchor=(200, 1130), at=(3020, 860),
         cut=[(3150, 620), (3095, 680), (3035, 735), (2975, 790), (2930, 850), (2910, 950), (2905, 1000)]),
]
# The hazy far ridges in the middle of the main picture (this box of it)
# are copied into the gaps between the mountains: (x shift, y shift, mirrored).
DISTANT_BOX = (1265, 640, 1800, 872)
DISTANT_COPIES = [(-1600, -12, False), (1300, 8, True)]
# The ground in front of the side mountains: layers of hills, low at the
# front and rising towards the mountains, in the main picture's foreground
# colours. Each is a ridge line (left to right, scene units), filled down
# to the bottom. Next to the main picture each one runs into the band of
# its own colour there (so the join does not show) and then drops away,
# hidden by the next layer in front.
GROUND = [
    [  # left
        ("#A48047", [(-1600, 872), (-1400, 850), (-1150, 878), (-900, 860), (-650, 846), (-420, 858),
                     (-220, 842), (-60, 832), (60, 860), (140, 960), (200, 1060), (240, 1114), (300, 1126),
                     (330, 1500)]),
        ("#85703F", [(-1600, 1000), (-1350, 1030), (-1050, 985), (-760, 1020), (-480, 975), (-250, 1010),
                     (-40, 1070), (150, 1138), (300, 1166), (400, 1180), (440, 1186), (470, 1500)]),
        ("#5A452A", [(-1600, 1190), (-1300, 1150), (-1000, 1185), (-700, 1145), (-400, 1175), (-120, 1220),
                     (150, 1265), (350, 1266), (550, 1252), (610, 1249), (650, 1500)]),
        ("#352816", [(-1600, 1330), (-1200, 1310), (-850, 1340), (-500, 1320), (-200, 1345), (100, 1360),
                     (300, 1346), (500, 1381), (700, 1384), (760, 1500)]),
    ],
    [  # right
        ("#A48047", [(2500, 1420), (2640, 1240), (2760, 1080), (2880, 958), (3000, 878), (3150, 862),
                     (3350, 872), (3550, 895), (3780, 935), (3980, 985), (4200, 1012), (4500, 1000)]),
        ("#85703F", [(2600, 1430), (2760, 1290), (2920, 1170), (3100, 1070), (3350, 1035), (3600, 1060),
                     (3880, 1105), (4200, 1122), (4500, 1110)]),
        ("#5A452A", [(2700, 1440), (2860, 1330), (3020, 1245), (3220, 1200), (3480, 1215), (3750, 1250),
                     (4050, 1268), (4500, 1245)]),
        ("#352816", [(2420, 1430), (2550, 1370), (2650, 1349), (2750, 1340), (2850, 1335), (3000, 1345),
                     (3200, 1362), (3500, 1376), (3800, 1394), (4100, 1384), (4500, 1392)]),
    ],
]
# Spruces on the ground layers: (side, layer, x, height).
GROUND_TREE_FILL = "#534021"
GROUND_TREES = [
    (0, 0, -1180, 46), (0, 0, -1150, 60), (0, 0, -1120, 40), (0, 0, -470, 44), (0, 0, -440, 58),
    (0, 0, -300, 38), (0, 1, -880, 62), (0, 1, -840, 82), (0, 1, -800, 56), (0, 1, -120, 70),
    (0, 1, -80, 52), (0, 2, -1350, 90), (0, 2, -1300, 70), (0, 2, -420, 84),
    (1, 0, 3180, 42), (1, 0, 3210, 56), (1, 0, 3240, 38), (1, 0, 3720, 46), (1, 0, 3750, 36),
    (1, 1, 2990, 70), (1, 1, 3030, 54), (1, 1, 3560, 66), (1, 1, 3600, 84), (1, 1, 3640, 58),
    (1, 2, 3280, 88), (1, 2, 3330, 70), (1, 2, 4050, 92),
]
# Near the main picture's right edge its far ridge is cut back along this
# line (scene units, top to bottom), so it slopes down instead of ending in
# a straight cut; the ground in front hides the rest of the edge.
LAND_CUT = [(2660, 772), (2730, 792), (2800, 838), (2865, 910), (2912, 1000)]
EXT = 10000                # the sky runs on this far above the picture
SKY_PX = 24                # one pixel of the sky image covers 24 x 24 units
HAZE = 0.9                 # the side mountains are further away: a little sky shows through
MASK_PX = 8                # one pixel of a side picture's fade mask covers 8 x 8 units


def _placed_x(pic, x):
    return pic["at"][0] + (x - pic["anchor"][0]) * pic["scale"]


# The drawing is centred on the main picture and reaches to the outer edge
# of Stetind's picture (its edge cuts through a ridge, so it must never
# show); Torres' picture runs on past the other end.
CX = W / 2
HALF = int(_placed_x(SIDE_PICS[1], SIDE_PICS[1]["w"]) - CX)
X0, X1 = int(CX - HALF), int(CX + HALF)

THEMES = ["hadean", "cambrian", "devonian", "cretaceous", "quaternary"]
DEFAULT = "cretaceous"

# The sky's shapes (1-based, in source order), picked once: every shape
# mostly above the skyline (found from the colour edges of the rendered
# picture), the glow seen between and beside the towers (checked by eye),
# and the specks of colour left floating in the sky. Check them again if
# the source picture changes.
SKY_PATHS = [1, 7, 9, (11, 24), (27, 58), (61, 66), (69, 80), (102, 103), (105, 129), (131, 132),
             (137, 153), (158, 159), (161, 166), 169, (171, 183), (185, 188), 190, 192, (194, 207),
             (211, 215), (217, 234), (239, 249), (276, 281), (283, 284), (287, 289), (291, 292), (294, 300),
             (302, 305), 309, 313, (316, 320), (322, 328), 330, (332, 353), (355, 356), (361, 368), 370,
             (375, 376), (382, 389), (391, 392), (395, 401), (403, 413), (415, 419), (421, 424), (430, 436),
             521, (523, 530), 532, (534, 535), (537, 545), (547, 548), (550, 558), (564, 568), 570, 573,
             575, (583, 590), 613, (627, 631), (633, 635), (640, 644), (646, 652), (654, 657), 661, 664,
             (671, 676), 679, (682, 683), (685, 687), 689, 691, 694, 697, (699, 700), (702, 703), 705,
             (707, 715), (717, 719), 722, 841, 846, 850, (852, 853), 855, 857, (859, 865), 867, 874, 876,
             (878, 882), (884, 887), (890, 896), 898, (900, 902), 910, 942, (944, 948), (952, 955),
             (957, 962), (1122, 1126), 1130, 1134, 1137, (1140, 1141), 1146, (1148, 1149), (1151, 1154),
             (1156, 1157), (1164, 1165), 1180, 1189, 1198, (1200, 1201), (1203, 1204), (1207, 1221),
             (1223, 1246), (1248, 1251), 1254, (1256, 1267), (1270, 1271), (1275, 1276), (1314, 1315),
             (1364, 1365), (1367, 1386), (1388, 1389), (1391, 1393), (1396, 1410), 1413, 1417, (1419, 1422),
             (1425, 1432), (1435, 1436), (1438, 1439), (1441, 1442), (1447, 1448), (1450, 1454),
             (1456, 1459), 1461, (1463, 1464), (1468, 1470), 1472, (1488, 1495), 1498, (1504, 1508),
             (1516, 1549), 1554, 1556, 1558, (1561, 1565), 1567, (1569, 1571), (1573, 1575), (1579, 1583),
             (1586, 1597), 1599, (1607, 1623), (1625, 1627), (1631, 1636), (1644, 1647), (1649, 1666),
             (1670, 1671), 1673, 1675, (1678, 1679), (1681, 1685), 1687, 1689, (1693, 1694), (1697, 1698),
             1700, (1702, 1703), (1705, 1709)]

# Small trees to redraw as spruces (1-based; a shape may hold two trees side
# by side). The current picture draws its spruces well already: none.
TREES = []

# The sky darkens from the horizon (HORIZON_Y) upwards and reaches the
# theme's zenith colour at ZENITH_Y (units of the source canvas).
HORIZON_Y = 880
ZENITH_Y = -430
ZENITH = {
    "devonian": "#191d2b",      # dusk blue above the sunset
    "cretaceous": "#0f121a",
    "hadean": "#170b08",
    "cambrian": "#0b1713",
    "quaternary": "#c9d2de",    # light theme: a cool, slightly darker blue-grey
}


# ── colour ────────────────────────────────────────────────────────────────

def srgb_to_oklab(rgb):
    c = np.asarray(rgb, float) / 255.0
    c = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    m1 = np.array([[0.4122214708, 0.5363325363, 0.0514459929],
                   [0.2119034982, 0.6806995451, 0.1073969566],
                   [0.0883024619, 0.2817188376, 0.6299787005]])
    m2 = np.array([[0.2104542553, 0.7936177850, -0.0040720468],
                   [1.9779984951, -2.4285922050, 0.4505937099],
                   [0.0259040371, 0.7827717662, -0.8086757660]])
    return np.cbrt(c @ m1.T) @ m2.T


def oklab_to_srgb(lab):
    lab = np.asarray(lab, float)
    m2i = np.array([[1.0, 0.3963377774, 0.2158037573],
                    [1.0, -0.1055613458, -0.0638541728],
                    [1.0, -0.0894841775, -1.2914855480]])
    m1i = np.array([[4.0767416621, -3.3077115913, 0.2309699292],
                    [-1.2684380046, 2.6097574011, -0.3413193965],
                    [-0.0041960863, -0.7034186147, 1.7076147010]])
    lin = (lab @ m2i.T) ** 3 @ m1i.T
    c = np.where(lin <= 0.0031308, 12.92 * lin, 1.055 * np.abs(lin) ** (1 / 2.4) - 0.055)
    return c * 255


def in_gamut(lab):
    c = oklab_to_srgb(lab)
    return bool(np.all(c > -0.5) and np.all(c < 255.5))


def lch_hex(L, C, h):
    """OKLCH to a hex colour, lowering the chroma until it fits sRGB."""
    L = float(np.clip(L, 0, 1))
    for _ in range(40):
        lab = np.array([L, C * np.cos(np.radians(h)), C * np.sin(np.radians(h))])
        if in_gamut(lab):
            break
        C *= 0.92
    rgb = np.clip(np.round(oklab_to_srgb(lab)), 0, 255).astype(int)
    return "#%02x%02x%02x" % tuple(rgb)


def hex_rgb(h):
    h = h.lstrip("#")
    return [int(h[i:i + 2], 16) for i in (0, 2, 4)]


def hex_lab(h):
    return srgb_to_oklab(hex_rgb(h))


def theme_colour(theme, hexcol):
    """Map one colour of the picture into a period's palette.

    The picture is a sunset: rock is orange-brown (hue about 55), grass is
    olive (about 85). Each rule keeps the lightness order and the difference
    between rock and grass, and moves them to the period's hues."""
    if theme == "devonian":
        return hexcol.lower()
    L, a, b = hex_lab(hexcol)
    C = float(np.hypot(a, b))
    h = float(np.degrees(np.arctan2(b, a)) % 360)
    # 0 = sunlit rock, 30 = grass; greys (little chroma, unreliable hue) count as rock
    warm = float(np.clip((C - 0.02) / 0.03, 0, 1)) if 25 <= h <= 115 else 0.0
    hh = (float(np.clip(h, 45, 95)) - 55) * warm
    if theme == "cretaceous":                 # moonlit night, blue rock, teal grass
        return lch_hex(0.16 + 0.58 * L ** 1.35, min(0.014 + 0.42 * C, 0.06), 262 - 2.3 * hh)
    if theme == "hadean":                     # dark rock, the light parts glow like magma
        g = float(np.clip((L - 0.7) / 0.22, 0, 1))
        return lch_hex(0.13 + 0.5 * L ** 1.9 + 0.2 * g, 0.03 + 0.75 * C + 0.13 * g,
                       30 + 0.5 * hh + 30 * g)
    if theme == "cambrian":                   # green life
        return lch_hex(0.15 + 0.6 * L ** 1.25, min(0.016 + 0.72 * C, 0.075), 170 - 1.2 * hh)
    if theme == "quaternary":                 # ice age: blue-grey rock and snow, sage steppe
        return lch_hex(0.36 + 0.58 * L, 0.008 + 0.3 * C, 245 - 3.2 * hh)
    raise ValueError(theme)


def sky_map(theme, lab):
    """Map the picture's sky (OKLab, shape [..., 3]) into a theme's sky: the
    sunset glow (light, orange) becomes the theme's horizon glow, the
    blue-grey upper sky its darker upper sky."""
    lab = np.asarray(lab, float)
    if theme == "devonian":
        return lab
    L = lab[..., 0]
    C = np.hypot(lab[..., 1], lab[..., 2])
    t = np.clip((L - 0.6) / 0.2, 0, 1)
    if theme == "cretaceous":
        L2, C2, h2 = 0.3 + 0.3 * t, 0.025 + 0.3 * C, 265 - 20 * t
    elif theme == "hadean":
        L2, C2, h2 = 0.26 + 0.34 * t, 0.07 + 0.55 * C, 28 + 22 * t
    elif theme == "cambrian":
        L2, C2, h2 = 0.28 + 0.32 * t, 0.03 + 0.4 * C, 165 - 15 * t
    elif theme == "quaternary":
        # winter dusk: blue-grey above, a pale warm glow on the horizon
        L2, C2, h2 = 0.8 + 0.15 * t, 0.018 + 0.12 * C, 245 - 170 * t ** 2
    else:
        raise ValueError(theme)
    hr = np.radians(h2)
    return np.stack([L2, C2 * np.cos(hr), C2 * np.sin(hr)], -1)


# ── paths ─────────────────────────────────────────────────────────────────

def expand(spec):
    out = set()
    for s in spec:
        if isinstance(s, tuple):
            out.update(range(s[0], s[1] + 1))
        else:
            out.add(s)
    return out


def read_paths(src=SRC):
    """The shapes of a traced picture: (fill, [subpath points]). Each subpath
    is M x y, then C in threes, closed; a second subpath is a hole."""
    svg = open(src, encoding="utf-8").read()
    found = re.findall(r'<path fill="(#[0-9A-Fa-f]{6})"[^>]*?d="([^"]*)"', svg)
    paths = []
    for fill, d in found:
        subs = []
        for part in d.split("M")[1:]:
            nums = [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?", part)]
            subs.append(np.array(nums).reshape(-1, 2))
        paths.append((fill.upper(), subs))
    return paths


def flatten(pts, steps=8):
    """Cubic Bézier chain (M + C...) to a polygon."""
    out = [pts[0]]
    t = np.linspace(0, 1, steps + 1)[1:, None]
    for i in range(1, len(pts) - 2, 3):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[i + 1], pts[i + 2]
        out.extend((1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1 + 3 * (1 - t) * t ** 2 * p2 + t ** 3 * p3)
    return np.array(out)


def id_map(paths, w=W, h=H):
    """Which shape shows at each pixel of the canvas (1-based, 0 = none)."""
    ids = np.zeros((h, w), np.int32)
    for k, (_, subs) in enumerate(paths, 1):
        polys = [np.round(flatten(pts) * 4).astype(np.int32) for pts in subs]   # 2 bits of sub-pixel precision
        cv2.fillPoly(ids, polys, int(k), lineType=cv2.LINE_8, shift=2)
    return ids


def num(v):
    s = str(int(round(v)))
    return s


def path_d(subs):
    """Compact path data: integer units, relative curves."""
    out = []
    for pts in subs:
        q = np.round(pts).astype(int)
        cur = q[0]
        parts = []
        for i in range(1, len(q) - 2, 3):
            seg = [q[i] - cur, q[i + 1] - cur, q[i + 2] - cur]
            parts.append(" ".join(f"{x} {y}" for x, y in seg))
            cur = q[i + 2]
        out.append(f"M{q[0][0]} {q[0][1]}c" + " ".join(parts) + "z")
    return re.sub(r" -", "-", "".join(out))


# ── trees ─────────────────────────────────────────────────────────────────

def spruce(cx, top, w, h):
    """A narrow spruce: a wedge, wide at the foot and pointed at the top,
    with a few short branch tips along each side and a stub of trunk."""
    tiers = int(np.clip(round(h / 13), 3, 6))
    foot = top + h * 0.93
    half = w / 2
    right = [(cx, top)]
    for i in range(1, tiers + 1):
        y_tip = top + (foot - top) * i / tiers
        hw = half * (0.32 + 0.68 * i / tiers)            # wedge: thin at the top
        right.append((cx + hw, y_tip))                    # branch tip
        if i < tiers:
            right.append((cx + hw * 0.76, y_tip - h * 0.01))    # a little back in towards the stem
    trunk = max(w * 0.07, 1.5)
    right += [(cx + trunk, foot), (cx + trunk, top + h)]
    left = [(2 * cx - x, y) for x, y in reversed(right[1:])]
    pts = right + left
    return "M" + " ".join(f"{x:.1f} {y:.1f}" for x, y in pts) + "z"


def trees_of(k, subs):
    """Split one tree shape into its trees (peaks of its top edge)."""
    poly = flatten(subs[0])
    x0, y0 = poly.min(0)
    x1, y1 = poly.max(0)
    mask = np.zeros((int(y1 - y0) + 3, int(x1 - x0) + 3), np.uint8)
    cv2.fillPoly(mask, [np.round(poly - [x0 - 1, y0 - 1]).astype(np.int32)], 1)
    cols = np.where(mask.any(0), mask.argmax(0), mask.shape[0])
    peaks, _ = find_peaks(-np.concatenate([[mask.shape[0]], cols, [mask.shape[0]]]), prominence=8)
    peaks = peaks - 1
    out = []
    bounds = [0] + [int((a + b) / 2) for a, b in zip(peaks[:-1], peaks[1:])] + [mask.shape[1]]
    for p, a, b in zip(peaks, bounds[:-1], bounds[1:]):
        sub = mask[:, a:b]
        rows = np.nonzero(sub.any(1))[0]
        tp, bt = rows.min(), rows.max()
        width = sub.sum(1)[int(tp + 0.8 * (bt - tp))]
        cx = x0 - 1 + p
        out.append((cx, y0 - 1 + tp, max(width * 1.05, 8.0), bt - tp))
    return out


# ── sky ───────────────────────────────────────────────────────────────────

def sky_field(paths, ids, sky):
    """The picture's sky, blurred into a smooth field (OKLab, 1/8 scale)."""
    lab_of = np.array([[0, 0, 0]] + [srgb_to_oklab(hex_rgb(f)) for f, _ in paths])
    is_sky = np.zeros(len(paths) + 1, bool)
    is_sky[list(sky)] = True
    m = is_sky[ids].astype(float)
    img = lab_of[ids] * m[..., None]
    f = 8
    small = lambda a: cv2.resize(a, (W // f, H // f), interpolation=cv2.INTER_AREA)
    m8, img8 = small(m), small(img)
    field = np.zeros_like(img8)
    weight = np.zeros(m8.shape)
    # normalized convolution at growing scales: fine where there is sky,
    # wide where the land hides it
    for sigma in (10, 20, 40, 80):
        mw = gaussian_filter(m8, sigma)
        fw = np.stack([gaussian_filter(img8[..., c], sigma) for c in range(3)], -1)
        est = fw / np.maximum(mw, 1e-6)[..., None]
        take = (weight < 0.5) & (mw > 0.02)
        field[take] = est[take]
        weight[take] = 1
    return field


def side_sky(paths, ids, thr=0.05, frac=0.35):
    """The sky shapes of a side picture, found from its colours: starting at
    the top row, spread to neighbouring shapes of nearly the same colour
    that reach the picture's side edges (the sky's bands); then take in
    shapes of the sky's colours with much of their outline on the sky (the
    bands seen between peaks) and specks surrounded by sky."""
    n = len(paths)
    h, w = ids.shape
    lab = np.array([[0, 0, 0]] + [srgb_to_oklab(hex_rgb(f)) for f, _ in paths])
    xs = [(min(p[:, 0].min() for p in subs), max(p[:, 0].max() for p in subs)) for _, subs in paths]
    edge = [False] + [a <= 4 or b >= w - 4 for a, b in xs]
    keys = []
    for a, b in ((ids[:, :-1], ids[:, 1:]), (ids[:-1, :], ids[1:, :])):
        m = a != b
        keys += [a[m].astype(np.int64) * (n + 1) + b[m], b[m].astype(np.int64) * (n + 1) + a[m]]
    keys, counts = np.unique(np.concatenate(keys), return_counts=True)
    border = {i: {} for i in range(n + 1)}
    for k, c in zip(keys.tolist(), counts.tolist()):
        border[k // (n + 1)][k % (n + 1)] = c
    sky = set()
    todo = list(set(np.unique(ids[6]).tolist()) - {0})
    while todo:
        k = todo.pop()
        if k in sky:
            continue
        sky.add(k)
        todo += [j for j in border[k] if j and j not in sky and edge[j]
                 and np.linalg.norm(lab[j] - lab[k]) < thr]
    changed = True
    while changed:
        changed = False
        for j in range(1, n + 1):
            if j in sky or not border[j]:
                continue
            total = sum(border[j].values())
            on_sky = sum(c for i, c in border[j].items() if i in sky)
            close = min((np.linalg.norm(lab[j] - lab[i]) for i in border[j] if i in sky), default=9)
            if close < thr and on_sky / total >= frac:
                sky.add(j)
                changed = True
    for j in range(1, n + 1):
        if j not in sky and border[j]:
            total = sum(border[j].values())
            if total < 600 and sum(c for i, c in border[j].items() if i in sky) / total > 0.9:
                sky.add(j)
    return sky


def smoothstep(t):
    t = np.clip(t, 0, 1)
    return t * t * (3 - 2 * t)


def sky_images(field):
    x0, x1 = X0, X1
    y0, y1 = TOP - EXT, H
    fw, fh = (x1 - x0) // SKY_PX, (y1 - y0) // SKY_PX
    xs = x0 + (np.arange(fw) + 0.5) * SKY_PX
    ys = y0 + (np.arange(fh) + 0.5) * SKY_PX
    # beyond the picture the sky is mirrored: the sunset glow at the left
    # edge is the sun between the main picture and the left mountain
    xr = np.abs(xs)
    xr = np.where(xr > W, 2 * W - xr, xr)
    fx = np.clip(xr / 8, 0, field.shape[1] - 1).astype(int)
    fy = np.clip(ys / 8, 0, field.shape[0] - 1).astype(int)
    base = field[fy[:, None], fx[None, :]]
    base = np.stack([cv2.GaussianBlur(base[..., c], (0, 0), 2.0) for c in range(3)], -1)
    s = smoothstep((HORIZON_Y - ys) / (HORIZON_Y - ZENITH_Y))[:, None, None]
    out = {}
    for th in THEMES:
        sky = sky_map(th, base)
        img = sky * (1 - s) + hex_lab(ZENITH[th]) * s
        rgb = np.clip(np.round(oklab_to_srgb(img.reshape(-1, 3))), 0, 255).reshape(fh, fw, 3).astype(np.uint8)
        _, png = cv2.imencode(".png", cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_PNG_COMPRESSION, 9])
        out[th] = base64.b64encode(png.tobytes()).decode()
    return out, (x0, y0, x1 - x0, y1 - y0)


# ── output ────────────────────────────────────────────────────────────────

def smooth_line(pts):
    """A smooth line through the points (Catmull-Rom), as a list of points."""
    P = np.array(pts, float)
    P = np.vstack([P[0], P, P[-1]])
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for t in np.linspace(0, 1, 12, endpoint=False):
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(P[-2])
    return [tuple(p) for p in out]


def ridge_path(pts):
    """A smooth hill through its ridge points (Catmull-Rom), filled down to
    below the bottom of the scene."""
    P = np.array(pts, float)
    P = np.vstack([P[0], P, P[-1]])
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for t in np.linspace(0, 1, 12, endpoint=False):
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(P[-2])
    q = np.round(np.array(out)).astype(int)
    d = "M" + " ".join(f"{x} {y}" for x, y in q)
    return d + f" {q[-1][0]} {H + 60} {q[0][0]} {H + 60}z"


def land_clip():
    """Outline of the main picture's land: all of it, but for the far ridge
    at its right edge, cut back along LAND_CUT."""
    pts = [(-40, TOP - 40), (LAND_CUT[0][0], TOP - 40)] + smooth_line(LAND_CUT)
    pts += [(W + 40, LAND_CUT[-1][1]), (W + 40, H + 80), (-40, H + 80)]
    return "M" + " ".join(f"{x:.0f} {y:.0f}" for x, y in pts) + "z"


def placed(subs, pic):
    s = pic["scale"]
    (ax, ay), (X, Y) = pic["anchor"], pic["at"]
    return [np.column_stack([X + (p[:, 0] - ax) * s, Y + (p[:, 1] - ay) * s]) for p in subs]


def side_mask(pic):
    """Fade mask of a side picture (a grey PNG and its box): a little haze
    over the mountain, solid ground, and the ground fading into the main
    picture's plain on the side facing it."""
    x0, x1 = sorted(_placed_x(pic, v) for v in (0, pic["w"]))
    x0, x1 = int(x0) - 16, int(x1) + 16
    y0, y1 = TOP, H + 40
    xs = x0 + (np.arange((x1 - x0) // MASK_PX) + 0.5) * MASK_PX
    ys = y0 + (np.arange((y1 - y0) // MASK_PX) + 0.5) * MASK_PX
    gy = pic["at"][1]
    a = HAZE + (1 - HAZE) * smoothstep((ys - (gy - 60)) / 100)[:, None] * np.ones_like(xs)[None, :]
    img = np.clip(np.round(a * 255), 0, 255).astype(np.uint8)
    _, png = cv2.imencode(".png", img, [cv2.IMWRITE_PNG_COMPRESSION, 9])
    return base64.b64encode(png.tobytes()).decode(), (x0, y0, len(xs) * MASK_PX, len(ys) * MASK_PX)


def build():
    paths = read_paths()
    ids = id_map(paths)
    sky = expand(SKY_PATHS)
    # shapes nothing (or only a speck of a few pixels) shows of are dropped
    counts = np.bincount(ids.ravel(), minlength=len(paths) + 1)
    shown = set(np.nonzero(counts >= 8)[0].tolist()) - {0}
    field = sky_field(paths, ids, sky)
    skies, box = sky_images(field)

    classes = {}                                   # fill -> class
    cls_of = lambda fill: classes.setdefault(fill.upper(), f"c{len(classes)}")
    shapes = []                                    # (class, d)
    distant = []                                   # main shapes in DISTANT_BOX
    bx0, by0, bx1, by1 = DISTANT_BOX
    trees = set(TREES)
    for k, (fill, subs) in enumerate(paths, 1):
        if k in sky or k not in shown:
            continue
        cls = cls_of(fill)
        if k in trees:
            for cx, top, w, h in trees_of(k, subs):
                shapes.append((cls, spruce(cx, top, w, h)))
            continue
        shapes.append((cls, path_d(subs)))
        p = subs[0]
        if p[:, 0].max() > bx0 and p[:, 0].min() < bx1 and p[:, 1].max() > by0 and p[:, 1].min() < by1:
            distant.append((cls, subs))

    far = []                                       # per side picture: [(class, d)]
    for pic in SIDE_PICS:
        sp = read_paths(pic["src"])
        sids = id_map(sp, pic["w"], pic["h"])
        ssky = side_sky(sp, sids)
        cnt = np.bincount(sids.ravel(), minlength=len(sp) + 1)
        out = []
        for k, (fill, subs) in enumerate(sp, 1):
            # the sky, specks, and the foreground the ground covers go
            pts = placed(subs, pic)
            if k in ssky or cnt[k] < 8 or min(p[:, 1].min() for p in pts) > 1000:
                continue
            out.append((cls_of(fill), path_d(pts)))
        print(f"{pic['name']}: {len(out)} shapes ({len(ssky)} sky shapes dropped)")
        far.append(out)

    ridges = []                                    # per copy: [(class, d)]
    for dx, dy, mirror in DISTANT_COPIES:
        cx = (bx0 + bx1) / 2
        out = []
        for cls, subs in distant:
            moved = [np.column_stack([(2 * cx - p[:, 0] if mirror else p[:, 0]) + dx, p[:, 1] + dy]) for p in subs]
            out.append((cls, path_d(moved)))
        ridges.append(out)

    ground = []                                    # per side: [(class, d)]
    tree_cls = cls_of(GROUND_TREE_FILL)
    for side, layers in enumerate(GROUND):
        out = []
        for li, (fill, ridge) in enumerate(layers):
            out.append((cls_of(fill), ridge_path(ridge)))
            line = np.array(smooth_line(ridge))
            for s_, l_, x, h in GROUND_TREES:
                if s_ == side and l_ == li:
                    y = float(np.interp(x, line[:, 0], line[:, 1])) + h * 0.12
                    out.append((tree_cls, spruce(x, y - h, h * 0.4, h)))
        ground.append(out)
    colours = {cls: {th: theme_colour(th, fill) for th in THEMES} for fill, cls in classes.items()}
    return dict(shapes=shapes, far=far, ridges=ridges, ground=ground), colours, skies, box


def svg_markup(parts, skies, box):
    vb = f"{X0} {TOP} {X1 - X0} {H - TOP}"
    bx, by, bw, bh = box
    lines = [f'<svg class="about-scene" viewBox="{vb}" preserveAspectRatio="xMidYMax slice" '
             'aria-hidden="true" focusable="false">',
             "<defs>"]
    # the side pictures: a little haze over their mountains
    for i, pic in enumerate(SIDE_PICS):
        png, (mx, my, mw, mh) = side_mask(pic)
        lines.append(f'<mask id="about-far-{i}" maskUnits="userSpaceOnUse" x="{mx}" y="{my}" width="{mw}" height="{mh}">'
                     f'<image x="{mx}" y="{my}" width="{mw}" height="{mh}" preserveAspectRatio="none" '
                     f'href="data:image/png;base64,{png}"/></mask>')
    lines.append(f'<clipPath id="about-land"><path d="{land_clip()}"/></clipPath>')
    for i, pic in enumerate(SIDE_PICS):
        if pic["cut"]:
            c = pic["cut"]
            pts = [(c[-1][0], H + 80), (X1 + 400, H + 80), (X1 + 400, TOP - 40), (c[0][0], TOP - 40)] + smooth_line(c)
            lines.append(f'<clipPath id="about-cut-{i}"><path d="M' + " ".join(f"{x:.0f} {y:.0f}" for x, y in pts) + 'z"/></clipPath>')
    bx0, by0, bx1, by1 = DISTANT_BOX
    for i, (dx, dy, _) in enumerate(DISTANT_COPIES):
        # the copied ridges are cut to the box (its bottom edge is hidden by the ground)
        lines.append(f'<clipPath id="about-ridge-{i}"><rect x="{bx0 + dx}" y="{by0 + dy - 400}" '
                     f'width="{bx1 - bx0}" height="{by1 - by0 + 400}"/></clipPath>')
    lines.append("</defs>")
    for th in THEMES:
        lines.append(f'<image class="sky sky-{th}" x="{bx}" y="{by}" width="{bw}" height="{bh}" '
                     f'preserveAspectRatio="none" href="data:image/png;base64,{skies[th]}"/>')
    for i, ((dx, dy, _), out) in enumerate(zip(DISTANT_COPIES, parts["ridges"])):
        lines.append(f'<g class="distant" clip-path="url(#about-ridge-{i})">')
        lines.extend(f'<path class="{c}" d="{d}"/>' for c, d in out)
        lines.append("</g>")
    for i, (pic, out) in enumerate(zip(SIDE_PICS, parts["far"])):
        clip = f' clip-path="url(#about-cut-{i})"' if pic["cut"] else ""
        lines.append(f'<g class="far far-{pic["name"]}" mask="url(#about-far-{i})"{clip}>')
        lines.extend(f'<path class="{c}" d="{d}"/>' for c, d in out)
        lines.append("</g>")
    lines.append('<g class="land" clip-path="url(#about-land)">')
    lines.extend(f'<path class="{c}" d="{d}"/>' for c, d in parts["shapes"])
    lines.append("</g>")
    for side, out in zip(("left", "right"), parts["ground"]):
        lines.append(f'<g class="ground ground-{side}">')
        lines.extend(f'<path class="{c}" d="{d}"/>' for c, d in out)
        lines.append("</g>")
    lines.append("</svg>")
    return "\n".join(lines)


def scene_css(colours):
    classes = sorted(colours, key=lambda c: int(c[1:]))
    blocks = []
    for th in [DEFAULT] + [t for t in THEMES if t != DEFAULT]:
        sel = "#om-meg" if th == DEFAULT else f'[data-theme="{th}"] #om-meg'
        props = [f"--s{c}: {colours[c][th]};" for c in classes]
        lines, line = [], ""
        for p in props:
            if len(line) + len(p) > 100:
                lines.append(line.rstrip())
                line = ""
            line += p + " "
        lines.append(line.rstrip())
        blocks.append(sel + " {\n  " + "\n  ".join(lines) + "\n}")
    rules = [".about-scene .sky { display: none; }",
             ":root:not([data-theme]) .about-scene .sky-" + DEFAULT + ",\n"
             + ",\n".join(f'[data-theme="{th}"] .about-scene .sky-{th}' for th in THEMES)
             + " { display: inline; }"]
    rules += [f".about-scene .{c} {{ fill: var(--s{c}); stroke: var(--s{c}); }}" for c in classes]
    # the side pictures and the copied ridges are scaled or moved: a thin
    # outline in each shape's own colour closes the hairline seams between
    # their shapes (elsewhere no outline)
    rules += [".about-scene path { stroke-width: 0; }",
              ".about-scene .far path, .about-scene .distant path { stroke-width: 1.5px; stroke-linejoin: round; }"]
    return "\n".join(blocks + rules)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--debug", help="folder for a preview page per theme")
    ap.add_argument("--no-write", action="store_true")
    args = ap.parse_args()
    parts, colours, skies, box = build()
    svg = svg_markup(parts, skies, box)
    css = scene_css(colours)
    print(f"{len(parts['shapes'])} shapes, {len(svg) / 1024:.0f} KB of SVG, {len(colours)} colours")
    if args.debug:
        for th in THEMES:
            with open(f"{args.debug}/preview-{th}.html", "w") as f:
                f.write(f'<!doctype html><html data-theme="{th}"><style>body{{margin:0;background:#888}}'
                        f'#om-meg{{overflow:hidden;padding-top:300px}}svg{{display:block;width:100%;height:auto;overflow:visible}}'
                        f'{css}</style><section id="om-meg">{svg}</section></html>')
    if args.no_write:
        return
    html = open(HTML, encoding="utf-8").read()
    html, n = re.subn(r'<svg class="about-scene".*?</svg>', lambda m: svg, html, count=1, flags=re.S)
    if n != 1:
        sys.exit("could not find the About background <svg> in index.html")
    block = "\n".join(("    " + r) if r else r for r in css.split("\n"))
    html, n = re.subn(r"/\* scene-tones:start \*/.*?/\* scene-tones:end \*/",
                      lambda m: "/* scene-tones:start */\n" + block + "\n    /* scene-tones:end */",
                      html, count=1, flags=re.S)
    if n != 1:
        sys.exit("no scene-tones markers in index.html")
    # the drawing's proportions, used by the layout
    vw, vh = X1 - X0, H - TOP
    html, n1 = re.subn(r"aspect-ratio: \d+ / \d+;", f"aspect-ratio: {vw} / {vh};", html, count=1)
    html, n2 = re.subn(r"calc\(100vw / [\d.]+\)", f"calc(100vw / {vw / vh:.4f})", html, count=1)
    if n1 != 1 or n2 != 1:
        sys.exit("could not find the scene's proportions in index.html")
    open(HTML, "w", encoding="utf-8").write(html)


if __name__ == "__main__":
    main()
