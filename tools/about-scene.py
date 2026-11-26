#!/usr/bin/env python3
"""Build the About-me background scene from the hand-off pictures.

The scene is one wide picture made of two traced pictures, side by side:

  * tools/about-scene.svg, the Dolomites sunset we were given (file2.svg,
    1709 flat-coloured shapes on a 2912 x 1440 canvas, drawn back to front):
    Tre Cime and Cinque Torri. It is the right part of the scene and keeps
    its own units, so nothing in it moves or changes size.
  * tools/about-scene-seceda.svg, the wide version made from it (Seceda on the
    left, a valley, then Tre Cime again). Only its left part is used: Seceda
    and the valley over to Tre Cime. It is scaled and placed (LEFT_M) so its
    Tre Cime lie exactly on the towers of the first picture, and it hands
    over to that picture along SEAM, a line that runs down the left edge of
    the towers' picture, bends round behind the foot of the first tower and,
    near the bottom, follows the edge of the dark foreground hill.

The scene ends with the pictures: nothing is added beyond Seceda on the left
or beyond Cinque Torri on the right.

  1. The shapes of the banded sky are dropped (SKY_PATHS, LEFT_SKY) together
     with the shapes nothing shows of. A smooth sky image takes the sky's
     place: the colours of the pictures' own sky, blurred, darkening upwards
     into a night or dusk colour, and running on far above the picture so
     the atmosphere fills the whole section up to its top edge.
  2. Small blob-like trees (TREES, none in the current picture) can be
     redrawn as narrow spruces: a wedge, wide at the foot and pointed at
     the top, with a few short branch tips along its sides.
  3. Every other shape keeps its outline. Its colour becomes a CSS custom
     property per colour theme: Devon keeps the picture's own colours, the
     other periods map them in OKLCH (keeping light and shadow), so every
     theme repaints the scene.

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

SRC = "tools/about-scene.svg"              # Tre Cime and Cinque Torri: the right part
SRC_LEFT = "tools/about-scene-seceda.svg"  # Seceda and the valley: the left part
HTML = "index.html"

W, H = 2912, 1440          # canvas of the right picture; the scene uses its units
TOP = -67                  # first row drawn (above the canvas: only sky there), so the
                           # towers start 14 % down the scene
X0 = -2553                 # the scene's left edge: the left edge of the Seceda picture
# The left picture's units to the scene's (found by matching its Tre Cime to
# the right picture's: scale 1.334, turned 0.54 degrees)
LEFT_M = ((1.33369471, -0.01248107, -2553.27521),
          (0.01248107, 1.33369471, -64.8051486))
# Where the left picture hands over to the right one, top to bottom (scene
# units), along edges both pictures share, so the hand-over does not show:
# the right picture's left edge through the sky, round the foot of the
# first tower (the left picture's mountain slopes down behind it), down the
# edge of the light stripe of scree below the towers, across the meadow in
# a slope that tapers the right picture's ochre band out, along the top of
# its dark foreground hill, which then slopes down to the bottom edge.
SEAM = [(2, TOP), (2, 718), (14, 724), (50, 736), (86, 748), (100, 754), (115, 775), (130, 792),
        (141, 800), (136, 820), (135, 840), (146, 860), (158, 880), (170, 900), (183, 920),
        (195, 940), (207, 960), (219, 980), (231, 1000), (243, 1020), (256, 1040), (275, 1060),
        (288, 1080), (292, 1100), (294, 1118), (200, 1142), (120, 1160), (38, 1184), (52, 1192),
        (65, 1200), (78, 1208), (90, 1216), (102, 1224), (110, 1232), (117, 1240), (122, 1248),
        (125, 1256), (128, 1264), (132, 1272), (140, 1282), (148, 1290), (155, 1297), (115, 1326),
        (78, 1358), (48, 1392), (26, 1420), (16, H)]
OVERLAP = 3                # the left picture reaches this far under the right one

# The towers' picture sits SHIFT units left of where its Tre Cime match the
# left picture's (so the left rock of Tre Cime stands at the middle of the
# scene and the empty valley before it narrows). SEAM above is in the towers'
# own units. In the sky above the seam the left picture reaches LEFT_REACH
# (scene units), so its mountains run on behind the first tower.
SHIFT = 80
LEFT_REACH = 60

# The towers' picture's dark foreground hill no longer rises to the left: its
# top edge (towers' units) slopes down from DARK_FROM and runs out into the
# bottom edge at DARK_TO; above it the brown band (DARK_BAND) carries on.
# The bush on the old hill top (TUFT box) is kept where it is.
DARK_FROM, DARK_TO = (700, 1378), (60, H)
DARK_SHAPE, DARK_BAND = 2, "#5A452A"
TUFT = (183, 266, 1250, 1340)

# Shapes of the towers' picture dropped (1-based): the hazy, layered far
# mountains between Tre Cime and Cinque Torri, and the hazy slope at the
# right edge. Copies of the left picture's brown mountains (RIDGE_SRC, a box
# in scene units) stand behind them instead (RIDGES: x scale, y scale, x, y).
HAZE = [5, 1004, 1059, 1302, (1303, 1304), 1306, (1312, 1313), (1343, 1347), (1474, 1482), 1513,
        (1603, 1606), 1638, (1641, 1642), 1648]
RIDGE_SRC = (-1250, -60, 430, 1020)
RIDGES = [(-0.6, 0.6, 1150, 422),      # between Tre Cime and Cinque Torri, mirrored
          (0.6, 0.6, 3130, 422)]       # behind Cinque Torri, out to the right edge
# The scene ends at the towers' picture's right edge (W - SHIFT): nothing is
# added beyond it.

# Left picture: shapes dropped (the spikes along the bottom edge), recoloured
# (the trodden path in the valley becomes grass), and its small blob-like
# trees, redrawn as copies of the towers' picture's spruces (TREE_SRC, the
# pair of spruces by the lake, towers' units), about as tall as the spruces
# at the same depth there: (shape, trees, height in units).
LEFT_DROP = [96, 97, 98]
LEFT_RECOLOUR = {383: "#868250"}
LEFT_TREES = [(599, 1, 96), (600, 1, 74), (604, 1, 88), (605, 1, 80), (795, 1, 66),
              (685, 3, 72), (686, 1, 56), (855, 2, 50), (698, 4, 52)]
TREE_SRC = (950, 1060, 1050, 1200)
TREE_SPLIT = 997          # the two spruces of TREE_SRC part at this x
EXT = 10000                # the sky runs on this far above the picture
SKY_PX = 24                # one pixel of the sky image covers 24 x 24 units

THEMES = ["hadean", "cambrian", "devonian", "cretaceous", "quaternary"]
DEFAULT = "cretaceous"

# The sky's shapes of the right picture (1-based, in source order), picked once: every shape
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

# The sky's shapes of the left picture (1-based), picked once: grown from
# the top edge through neighbouring shapes of nearly the same colour, then
# checked by eye (the sunlit faces of Seceda and a dark notch between its
# peaks are rock, not sky).
LEFT_SKY = [2, (4, 7), (9, 10), (12, 16), (18, 31), (33, 37), (41, 44), (47, 48), (50, 52), (55, 56),
            (63, 64), (66, 68), (70, 73), (76, 80), (101, 102), (110, 112), (115, 116), (119, 120),
            122, (126, 127), 132, (135, 136), 151, (169, 172), 178, (187, 192), (196, 199),
            (235, 236), (250, 251), (253, 254), (264, 266), 287, (319, 320), 335, 339, (352, 364),
            (366, 368), (480, 482), 484, (488, 491), 498, 500, 507, (519, 520), (533, 537),
            (539, 540), 555, (572, 575), 702, (706, 709), (713, 715), 739, 744, 749, (758, 760),
            762, (787, 790), 873, 876, 900, 902, (904, 906), 910, 912, (937, 938), 940, (943, 950),
            955, 1000, 1003, (1007, 1008), 1012, 1016]

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


def read_paths(src):
    svg = open(src, encoding="utf-8").read()
    found = re.findall(r'<path fill="(#[0-9A-Fa-f]{6})"[^>]*?d="([^"]*)"', svg)
    paths = []
    for fill, d in found:
        nums = [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?", d)]
        pts = np.array(nums).reshape(-1, 2)
        paths.append((fill.upper(), pts))      # M x y, then C in threes, closed
    return paths


def flatten(pts, steps=8):
    """Cubic Bézier chain (M + C...) to a polygon."""
    out = [pts[0]]
    t = np.linspace(0, 1, steps + 1)[1:, None]
    for i in range(1, len(pts) - 2, 3):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[i + 1], pts[i + 2]
        out.extend((1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1 + 3 * (1 - t) * t ** 2 * p2 + t ** 3 * p3)
    return np.array(out)


def id_map(paths):
    """Which shape shows at each pixel of the scene, from X0 to W and from 0
    to H (1-based, 0 = none)."""
    ids = np.zeros((H, W - X0), np.int32)
    for k, (_, pts) in enumerate(paths, 1):
        if pts is None:                                    # a dropped shape
            continue
        poly = np.round((flatten(pts) - [X0, 0]) * 4).astype(np.int32)   # 2 bits of sub-pixel precision
        cv2.fillPoly(ids, [poly], int(k), lineType=cv2.LINE_8, shift=2)
    return ids


def num(v):
    s = str(int(round(v)))
    return s


def path_d(pts):
    """Compact path data: integer units, relative curves."""
    q = np.round(pts).astype(int)
    out = [f"M{q[0][0]} {q[0][1]}c"]
    cur = q[0]
    parts = []
    for i in range(1, len(q) - 2, 3):
        seg = [q[i] - cur, q[i + 1] - cur, q[i + 2] - cur]
        parts.append(" ".join(f"{x} {y}" for x, y in seg))
        cur = q[i + 2]
    s = out[0] + " ".join(parts) + "z"
    return re.sub(r" -", "-", s)


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


def trees_of(k, pts):
    """Split one tree shape into its trees (peaks of its top edge)."""
    poly = flatten(pts)
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

def sky_lab(paths, ids, sky, where):
    """The sky colours (OKLab) a picture shows in the pixels `where`, and
    where it shows sky."""
    lab_of = np.array([[0, 0, 0]] + [srgb_to_oklab(hex_rgb(f)) for f, _ in paths])
    is_sky = np.zeros(len(paths) + 1, bool)
    is_sky[list(sky)] = True
    m = is_sky[ids] & where
    return lab_of[ids] * m[..., None], m


def sky_field(img, m):
    """The pictures' sky, blurred into a smooth field (OKLab, 1/8 scale)."""
    m = m.astype(float)
    f = 8
    small = lambda a: cv2.resize(a, ((W - X0) // f, H // f), interpolation=cv2.INTER_AREA)
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


def smoothstep(t):
    t = np.clip(t, 0, 1)
    return t * t * (3 - 2 * t)


def sky_images(field):
    x0, x1 = X0, W - SHIFT
    y0, y1 = TOP - EXT, H
    fw, fh = (x1 - x0) // SKY_PX, (y1 - y0) // SKY_PX
    xs = x0 + (np.arange(fw) + 0.5) * SKY_PX
    ys = y0 + (np.arange(fh) + 0.5) * SKY_PX
    fx = np.clip((xs - X0) / 8, 0, field.shape[1] - 1).astype(int)
    fy = np.clip(ys / 8, 0, field.shape[0] - 1).astype(int)
    base = field[fy[:, None], fx[None, :]]
    # the rows above the picture repeat its top row: soften that
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

def clip_line(side):
    """The seam as each side's clip sees it, top to bottom (scene units)."""
    right = [(x - SHIFT, y) for x, y in SEAM]
    if side == "right":
        return right
    join = 760
    return [(LEFT_REACH, TOP), (LEFT_REACH, join)] + [(x + OVERLAP, y) for x, y in right if y > join]


def line_x(line, ys):
    sx, sy = np.array(line, float).T
    return np.interp(ys, sy, sx)


def seam_clip(side):
    """Clip path data for one side of the seam, down to the bottom edge: the
    left picture stops at X0, its own edge, and reaches OVERLAP (in the sky
    LEFT_REACH) under the right one, so no hairline shows; the right one
    stops at its own right edge."""
    pts = clip_line(side)
    pts = pts + ([(X0, H), (X0, TOP)] if side == "left" else [(W - SHIFT, H), (W - SHIFT, TOP)])
    return poly_d(pts)


def poly_d(pts):
    return "M" + "L".join(f"{x:.1f} {y:.1f}".replace(".0 ", " ").replace(".0L", "L") for x, y in pts) + "z"


def mask_polys(mask, x0, y0, up=4, eps=0.35):
    """Outlines of a pixel mask (one pixel = one unit, its corner at x0, y0),
    smoothed: upsampled, softened and traced again."""
    big = cv2.resize(mask.astype(np.float32), None, fx=up, fy=up, interpolation=cv2.INTER_LINEAR)
    big = cv2.GaussianBlur(big, (0, 0), up * 0.5)
    cs, _ = cv2.findContours((big > 0.5).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    out = []
    for c in cs:
        if cv2.contourArea(c) < 4 * up * up:
            continue
        c = cv2.approxPolyDP(c, eps * up, True)[:, 0, :].astype(float)
        out.append(c / up + [x0, y0])
    return out


def tree_stamps(right_raw, ids_t):
    """The pair of spruces by the lake in the towers' picture, as outlines per
    colour (each tree on its own, and both), relative to the foot of the
    trunk: [(layers, height)], layers = [(fill, [polygon])]."""
    x0, x1, y0, y1 = TREE_SRC
    sub = ids_t[y0:y1, x0 - X0:x1 - X0]
    fills = np.array(["#000000"] + [f for f, _ in right_raw])
    dark, lit = "#4F3E20", "#604D25"
    m = np.isin(fills[sub], [dark, lit])
    n, lab, st, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8))
    m &= np.isin(lab, [i for i in range(1, n) if st[i][4] > 200])
    xs = np.arange(x0, x1)[None, :]
    stamps = []
    for part in (xs < TREE_SPLIT, xs >= TREE_SPLIT):
        tree = m & part
        rows, cols = np.nonzero(tree)
        foot_x, foot_y = x0 + cols.mean(), y0 + rows.max() + 1
        layers = []
        for fill, layer in ((dark, tree), (lit, tree & (fills[sub] == lit))):
            polys = [p - [foot_x, foot_y] for p in mask_polys(layer, x0, y0)]
            if polys:
                layers.append((fill, polys))
        stamps.append((layers, rows.max() + 1 - rows.min()))
    return stamps


def place_trees(left, stamps):
    """New spruces for LEFT_TREES: [(fill, path data)]."""
    out = []
    for i, (k, count, h) in enumerate(LEFT_TREES):
        pts = left[k - 1][1]
        (bx0, by0), (bx1, by1) = pts.min(0), pts.max(0)
        for j in range(count):
            t = (j + 0.5) / count
            cx = bx0 + (bx1 - bx0) * t
            hh = h * (1.0 if count == 1 else (0.8 + 0.4 * ((j * 7 + i) % 3) / 2))
            layers, sh = stamps[(i + j) % 2]
            sc = hh / sh
            flip = -1 if (i + j) % 3 == 1 else 1
            for fill, polys in layers:
                for poly in polys:
                    q = poly * [sc * flip, sc] + [cx, by1]
                    out.append((fill, poly_d(q)))
    return out


def dark_foreground(right_raw, ids_t):
    """Item for the towers' picture's bottom-left: the brown band carried down
    over the old dark hill top, the new sloping top edge of the dark ground
    below it, and the bush redrawn where it stood (towers' units)."""
    xs = np.arange(2, DARK_FROM[0] + 1, 2)
    def top(x):
        col = ids_t[1150:H, x - X0]
        hit = np.nonzero(col == DARK_SHAPE)[0]
        return 1150 + hit[0] if len(hit) else H
    tx0, tx1 = TUFT[0] - 1, TUFT[1] + 1
    t0, t1 = top(tx0), top(tx1)
    def old(x):
        if tx0 < x < tx1:
            return t0 + (t1 - t0) * (x - tx0) / (tx1 - tx0)
        return top(x)
    (fx, fy), (ex, ey) = (DARK_FROM[0], old(DARK_FROM[0])), DARK_TO
    def new(x):
        u = np.clip((fx - x) / (fx - ex), 0, 1)
        return fy + (ey - fy) * u ** 1.5
    upper = [(x, old(x) - 1.5) for x in xs]
    lower = [(x, new(x) if x >= ex else H) for x in xs[::-1]]
    filler = poly_d(upper + lower)
    # the bush: the dark shape inside TUFT, above the old ground line
    bx0, bx1, by0, by1 = TUFT
    sub = ids_t[by0:by1, bx0 - X0:bx1 - X0] == DARK_SHAPE
    yy = np.arange(by0, by1)[:, None]
    base = np.array([old(x) for x in range(bx0, bx1)])[None, :]
    bush = sub & (yy < base + 2)
    bush_d = [poly_d(p) for p in mask_polys(bush, bx0, by0, eps=0.25)]
    return filler, bush_d


def build():
    m = np.array(LEFT_M)
    left = [(f, pts @ m[:, :2].T + m[:, 2]) for f, pts in read_paths(SRC_LEFT)]
    right_raw = read_paths(SRC)
    haze = expand(HAZE)
    right = [(f, None if k in haze else pts - [SHIFT, 0]) for k, (f, pts) in enumerate(right_raw, 1)]
    ids_t = id_map(right_raw)                     # the towers' picture in its own units
    ids_r, ids_l = id_map(right), id_map(left)
    sky_r, sky_l = expand(SKY_PATHS), expand(LEFT_SKY)
    xs = X0 + np.arange(W - X0)[None, :] + 0.5
    ys = np.arange(H) + 0.5
    in_r = (xs >= line_x(clip_line("right"), ys)[:, None]) & (xs < W - SHIFT)
    in_l = xs < line_x(clip_line("left"), ys)[:, None]
    land_r = np.isin(ids_r, list(sky_r), invert=True) & (ids_r > 0) & in_r
    # shapes nothing (or only a speck of a few pixels) shows of are dropped
    def shown(ids, where):
        counts = np.bincount(ids[where].ravel(), minlength=ids.max() + 1)
        return set(np.nonzero(counts >= 8)[0].tolist()) - {0}
    shown_r = shown(ids_r, in_r)
    shown_l = shown(ids_l, in_l & ~land_r)
    rx0, rx1, ry0, ry1 = RIDGE_SRC
    in_src = (xs >= rx0) & (xs < rx1) & (ys[:, None] >= ry0) & (ys[:, None] < ry1)
    shown_src = shown(ids_l, in_src)
    img_r, m_r = sky_lab(right_raw, ids_r, sky_r, in_r)
    img_l, m_l = sky_lab(left, ids_l, sky_l, ~in_r & (xs < W - SHIFT))
    field = sky_field(img_r + img_l, m_r | m_l)
    skies, box = sky_images(field)

    classes = {}                                   # fill -> class
    cls = lambda fill: classes.setdefault(fill.upper(), f"c{len(classes)}")
    trees = {k for k, _, _ in LEFT_TREES}
    drop_l = set(LEFT_DROP) | trees | sky_l
    parts = {"left": [], "ridge": [], "right": []}
    # the old trees become patches of the ground around them (nothing else
    # may be drawn below them)
    fills_l = [f for f, _ in left]
    recolour = dict(LEFT_RECOLOUR)
    for k, _, _ in LEFT_TREES:
        own = (ids_l == k).astype(np.uint8)
        ring = cv2.dilate(own, np.ones((7, 7), np.uint8)).astype(bool) & ~own.astype(bool)
        around = [fills_l[i - 1] for i in ids_l[ring] if i > 0 and i not in trees]
        recolour.setdefault(k, max(set(around), key=around.count))
    for k, (fill, pts) in enumerate(left, 1):
        if k in drop_l and k not in trees:
            continue
        fill = recolour.get(k, fill)
        if k in shown_l:
            parts["left"].append((cls(fill), path_d(pts)))
        if k in shown_src:
            parts["ridge"].append((cls(fill), path_d(pts)))
    stamps = tree_stamps(right_raw, ids_t)
    parts["left"] += [(cls(f), d) for f, d in place_trees(left, stamps)]
    for k, (fill, pts) in enumerate(right, 1):
        if pts is None or k in sky_r:
            continue
        if k in shown_r:
            parts["right"].append((cls(fill), path_d(pts)))
    filler, bush = dark_foreground(right_raw, ids_t)
    parts["fore"] = [(cls(DARK_BAND), filler)] + [(cls(right_raw[DARK_SHAPE - 1][0]), d) for d in bush]
    colours = {c: {th: theme_colour(th, fill) for th in THEMES} for fill, c in classes.items()}
    return parts, colours, skies, box


def svg_markup(parts, skies, box):
    vb = f"{X0} {TOP} {W - SHIFT - X0} {H - TOP}"
    bx, by, bw, bh = box
    rx0, rx1, ry0, ry1 = RIDGE_SRC
    lines = [f'<svg class="about-scene" viewBox="{vb}" preserveAspectRatio="xMidYMax slice" '
             'aria-hidden="true" focusable="false">',
             "<defs>"]
    for side in ("left", "right"):
        lines.append(f'<clipPath id="about-{side}"><path d="{seam_clip(side)}"/></clipPath>')
    for i, (a, d, e, f) in enumerate(RIDGES):
        # the source box, and no further than the scene's edges
        lo, hi = sorted(((X0 - e) / a, (W - SHIFT - e) / a))
        x0, x1 = max(rx0, lo), min(rx1, hi)
        lines.append(f'<clipPath id="about-ridge-{i}"><rect x="{x0:.0f}" y="{ry0}" '
                     f'width="{x1 - x0:.0f}" height="{ry1 - ry0}"/></clipPath>')
    lines.append("</defs>")
    for th in THEMES:
        lines.append(f'<image class="sky sky-{th}" x="{bx}" y="{by}" width="{bw}" height="{bh}" '
                     f'preserveAspectRatio="none" href="data:image/png;base64,{skies[th]}"/>')
    lines.append('<g class="land">')
    path = lambda c, d: f'<path class="{c}" d="{d}"/>'
    # Seceda and the valley first, then the far ridges, then the towers'
    # picture over the seam
    lines.append('<g class="seceda" clip-path="url(#about-left)">')
    lines.extend(path(c, d) for c, d in parts["left"])
    lines.append("</g>")
    for i, (a, d, e, f) in enumerate(RIDGES):
        # copies, not <use>: CSS colours do not reach into <use> clones everywhere
        lines.append(f'<g class="ridge" transform="matrix({a} 0 0 {d} {e} {f})">'
                     f'<g clip-path="url(#about-ridge-{i})">')
        lines.extend(path(c, dd) for c, dd in parts["ridge"])
        lines.append("</g></g>")
    lines.append('<g class="tre-cime" clip-path="url(#about-right)">')
    lines.extend(path(c, d) for c, d in parts["right"])
    lines.append(f'<g transform="translate({-SHIFT} 0)">')
    lines.extend(path(c, d) for c, d in parts["fore"])
    lines.append("</g></g>")
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
    rules += [f".about-scene .{c} {{ fill: var(--s{c}); }}" for c in classes]
    return "\n".join(blocks + rules)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--debug", help="folder for a preview page per theme")
    ap.add_argument("--no-write", action="store_true")
    args = ap.parse_args()
    parts, colours, skies, box = build()
    svg = svg_markup(parts, skies, box)
    css = scene_css(colours)
    print(f"{' + '.join(str(len(v)) for v in parts.values())} shapes, {len(svg) / 1024:.0f} KB of SVG, {len(colours)} colours")
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
    open(HTML, "w", encoding="utf-8").write(html)


if __name__ == "__main__":
    main()
