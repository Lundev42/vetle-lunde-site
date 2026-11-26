#!/usr/bin/env python3
"""Build the About-me background scene from the hand-off picture.

Source: tools/about-scene.svg, the Dolomites sunset we were given
(DOLOMITES_TRUE.svg, 852 flat-coloured shapes on a 2752 x 1536 canvas, drawn
back to front). It is not deployed; this script writes the scene into
index.html.

  1. The shapes of the banded sky are dropped (SKY_PATHS) together with the
     shapes nothing shows of. A smooth sky image takes the sky's place: the
     colours of the picture's own sky, blurred, darkening upwards into a
     night or dusk colour, and running on far above the picture so the
     atmosphere fills the whole section up to its top edge.
  2. The small trees on the slopes (TREES) are redrawn as narrow spruces:
     a wedge, wide at the foot and pointed at the top, with a few short
     branch tips along its sides.
  3. Every other shape keeps its outline. Its colour becomes a CSS custom
     property per colour theme: Devon keeps the picture's own colours, the
     other periods map them in OKLCH (keeping light and shadow), so every
     theme repaints the scene.
  4. Wide screens: a thin strip at each side of the picture is mirrored and
     stretched, so the hills roll on to the edges of the screen.

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
from scipy.interpolate import PchipInterpolator
from scipy.signal import find_peaks

SRC = "tools/about-scene.svg"
HTML = "index.html"

W, H = 2752, 1536          # canvas of the source SVG
TOP = 100                  # first row drawn: the towers start 14 % down the scene
SIDE = 1800                # units added on each side for wide screens
STRIPS = ((6, 156, -12), (2546, 2746, -9))   # (from, to, x stretch): mirrored just inside the picture's edges (x 2 and 2750), so the copies overlap it
EXT = 10000                # the sky runs on this far above the picture
SKY_PX = 24                # one pixel of the sky image covers 24 x 24 units

THEMES = ["hadean", "cambrian", "devonian", "cretaceous", "quaternary"]
DEFAULT = "cretaceous"

# The sky's shapes (1-based, in source order), picked once by comparing every
# shape with the land/sky split of the first version of the scene, plus the
# specks of colour left floating in the sky and the sky seen between the
# left towers (401). Check them again if the source picture changes.
SKY_PATHS = [(3, 5), (7, 9), (11, 15), (17, 25), (27, 32), 34, (36, 43), 45, (49, 50), (79, 80),
             (83, 95), (99, 107), (109, 112), (114, 121), 130, 135, (137, 140), 144, (146, 164),
             (167, 168), (171, 176), (178, 179), (181, 183), (198, 203), 207, (210, 213),
             (216, 223), 237, (239, 242), 244, (250, 253), (264, 265), (286, 287), (296, 307),
             (310, 313), (320, 321), (323, 329), 333, (336, 341), (343, 347), (349, 357),
             (388, 394), 401, (403, 405), (410, 412), 414, 416, 418, (423, 424), (426, 427),
             (431, 432), (543, 544), 547, (550, 558), 560, 563, (566, 570), (577, 580), 599,
             (602, 603), 605, 609, 611, (722, 724), (732, 733), (735, 739), (741, 747),
             (750, 754), 772, 774, 803, 806, 813, (832, 833), (837, 841), 848]

# The small trees (1-based). A shape may hold two trees side by side.
TREES = [714, 715, 716, 787, 793, 800, 818, 819, 823, 825, 842]

# The sky above the picture's own sunset: the picture's sky shows up to
# GLOW_TOP and fades out by GLOW_END; above it the colours run through an
# afterglow (A0, A), a dusk band (B) and end in the zenith colour (Z) at
# these heights (units of the source canvas; the text sits around y -450..60
# on laptops, so A and B are dark enough for it in the dark themes).
GLOW_TOP, GLOW_END = 820, 120
DUSK_Y = (800, 150, -450, -1500)
DUSK = {                     # A0, A, B, Z
    "devonian":   ("#c9725c", "#58334a", "#2e2443", "#191d2b"),   # coral, mauve, violet, dusk blue
    "cretaceous": ("#4f6f9a", "#2d3a5c", "#1b2238", "#0f121a"),
    "hadean":     ("#a8452a", "#5c2118", "#2e110c", "#170b08"),
    "cambrian":   ("#3f8a6c", "#21493b", "#132b22", "#0b1713"),
    "quaternary": ("#f0dccb", "#ddd3e2", "#d0d6e3", "#c9d2de"),   # light: peach, lilac, ice
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


def read_paths():
    svg = open(SRC, encoding="utf-8").read()
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
    """Which shape shows at each pixel of the canvas (1-based, 0 = none)."""
    ids = np.zeros((H, W), np.int32)
    for k, (_, pts) in enumerate(paths, 1):
        poly = np.round(flatten(pts) * 4).astype(np.int32)       # 2 bits of sub-pixel precision
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


# ── side mountains ────────────────────────────────────────────────────────
#
# Beyond the picture the land would only be the stretched strips, which are
# flat. Mountains of our own rise behind them: same flat-colour style and
# light (sun low on the right: right-hand faces lit, left-hand faces in
# shadow), but different shapes from the towers: a hazy far range on each
# side, a table mountain with sandstone layers on the left, a pyramid peak
# with snow and a row of rock teeth on the right. Colours are in the
# picture's own palette; every theme maps them like the rest of the land.

PULL = (600, -400)          # shift of the near mountains, left and right


def catmull(points, closed=True):
    """Points to a smooth Bézier chain (M + C...), as in the source paths."""
    p = np.asarray(points, float)
    n = len(p)
    out = [p[0]]
    for i in range(n if closed else n - 1):
        p0, p1 = p[(i - 1) % n], p[i]
        p2, p3 = p[(i + 1) % n], p[(i + 2) % n]
        if not closed:
            p0 = p[max(i - 1, 0)]
            p3 = p[min(i + 2, n - 1)]
        out += [p1 + (p2 - p0) / 6, p2 - (p3 - p1) / 6, p2]
    return np.array(out)


def ridge(rng, keys, step=22, rough=7.0):
    """A ridge line through key points, with small rocky irregularities."""
    pts = []
    for (x0, y0), (x1, y1) in zip(keys[:-1], keys[1:]):
        n = max(int(np.hypot(x1 - x0, y1 - y0) / step), 1)
        for t in np.arange(n) / n:
            jitter = rng.normal(0, rough) if 0 < t else 0.0
            pts.append((x0 + (x1 - x0) * t + rng.normal(0, rough * 0.4), y0 + (y1 - y0) * t + jitter))
    pts.append(keys[-1])
    return pts


def blob(rng, cx, cy, rx, ry, n=9, wobble=0.28):
    a = np.sort(rng.uniform(0, 2 * np.pi, n))
    r = 1 + rng.uniform(-wobble, wobble, n)
    return [(cx + rx * ri * np.cos(ai), cy + ry * ri * np.sin(ai)) for ai, ri in zip(a, r)]


def body(top):
    """Close a ridge line down below the bottom of the scene."""
    return top + [(top[-1][0], H + 40), (top[0][0], H + 40)]


def side_mountains():
    """Returns [(name, body points, fill, [(points, fill), ...] drawn inside it)]."""
    rng = np.random.default_rng(1376)
    m = []

    # far ranges, hazy in the sunset light
    far_l = ridge(rng, [(-1900, 930), (-1640, 760), (-1500, 700), (-1330, 745), (-1120, 790), (-900, 720),
                        (-760, 735), (-560, 800), (-330, 770), (-120, 840), (120, 905), (340, 960)], rough=5)
    m.append(("far-l", body(far_l), "#9C8C8A", [
        (body(ridge(rng, [(-1500, 700), (-1560, 860), (-1640, 1000), (-1900, 1000), (-1900, 700)], rough=9)), "#8A7F82"),
        (body(ridge(rng, [(-900, 720), (-990, 860), (-1080, 1000), (-1250, 1000), (-1120, 790)], rough=9)), "#8A7F82"),
    ]))
    far_r = ridge(rng, [(2420, 960), (2700, 860), (2960, 735), (3120, 770), (3300, 820), (3520, 760),
                        (3800, 690), (3960, 730), (4200, 800), (4400, 745), (4660, 820)], rough=5)
    m.append(("far-r", body(far_r), "#9C8C8A", [
        (body(ridge(rng, [(2960, 735), (2900, 860), (2860, 1000), (2600, 1000), (2700, 860)], rough=9)), "#8A7F82"),
        (body(ridge(rng, [(3800, 690), (3740, 830), (3700, 1000), (3420, 1000), (3520, 760)], rough=9)), "#8A7F82"),
    ]))

    # left: a table mountain, cliffs of tilted sandstone layers on a scree base
    mesa = ridge(rng, [(-1720, 1000), (-1560, 905), (-1430, 830), (-1340, 770), (-1305, 700), (-1270, 645),
                       (-1215, 615), (-1150, 622), (-1080, 600), (-1010, 612), (-950, 640), (-905, 690),
                       (-870, 770), (-780, 830), (-640, 890), (-470, 965), (-300, 1010)], rough=7)
    strata = []
    for y, hgt, col in ((690, 15, "#D9A47E"), (735, 10, "#C08B66"), (780, 16, "#D9A47E")):
        band = ridge(rng, [(-1450, y + 40), (-1100, y + 5), (-750, y - 45)], step=30, rough=4) + \
            ridge(rng, [(-750, y - 45 + hgt), (-1100, y + 5 + hgt * 1.3), (-1450, y + 40 + hgt)], step=30, rough=4)
        strata.append((band, col))
    gullies = [(ridge(rng, [(x, 640), (x + 12, 700), (x + 30, 860), (x - 6, 860), (x - 6, 700)], rough=3),
                "#B98F70") for x in (-960, -900)]
    m.append(("mesa", body(mesa), "#A48A7A", [
        # shadowed left half of the cliffs and the scree below them
        (ridge(rng, [(-1800, 560), (-1170, 560), (-1185, 690), (-1235, 800), (-1310, 1100), (-1800, 1100)], rough=10),
         "#6E6062"),
        *strata,
        # sunlit right-hand cliff and scree
        (ridge(rng, [(-1010, 560), (-860, 560), (-820, 1100), (-700, 1100), (-760, 880), (-860, 780),
                     (-950, 660)], rough=6), "#E7B48C"),
        *gullies,
    ]))
    # a rounded grassy hill in front of it
    hill = ridge(rng, [(-1260, 1010), (-1100, 930), (-930, 890), (-760, 880), (-600, 905), (-420, 960),
                       (-220, 1010)], rough=3)
    m.append(("hill", body(hill), "#8A7135", [
        (ridge(rng, [(-760, 860), (-560, 880), (-200, 1000), (-200, 1100), (-700, 1100), (-700, 960)], rough=6),
         "#A9893F"),
    ]))

    # right: a row of rock teeth
    teeth = ridge(rng, [(2620, 900), (2700, 800), (2735, 735), (2770, 790), (2830, 720), (2880, 700),
                        (2920, 760), (2990, 690), (3040, 745), (3110, 715), (3170, 780), (3290, 850),
                        (3380, 900)], rough=6)
    m.append(("teeth", body(teeth), "#6D5F5D", [
        (ridge(rng, [(2880, 700), (2905, 800), (2950, 1100), (3080, 1100), (3010, 820), (2990, 690)], rough=5),
         "#9C8174"),
        (ridge(rng, [(3110, 715), (3150, 800), (3250, 1100), (3400, 1100), (3290, 850), (3170, 780)], rough=5),
         "#B98F70"),
    ]))
    # and a pyramid peak with snow, its right face in the sun
    peak = ridge(rng, [(3080, 900), (3260, 760), (3380, 640), (3470, 520), (3540, 440), (3575, 430),
                       (3610, 455), (3700, 540), (3800, 640), (3930, 730), (4080, 810), (4250, 880),
                       (4420, 930)], rough=7)
    spine = ridge(rng, [(3575, 430), (3590, 560), (3640, 700), (3660, 820), (3720, 1100)], rough=8)
    m.append(("peak", body(peak), "#9B8578", [
        (ridge(rng, [(3000, 300), (3575, 300)], rough=1) + spine + [(3000, 1100)], "#5D5354"),
        (spine + ridge(rng, [(4500, 1100), (4500, 300), (3575, 300)], rough=1), "#D79A76"),
        (ridge(rng, [(3575, 420), (3640, 470), (3740, 560), (3700, 590), (3640, 560), (3600, 600),
                     (3590, 520)], rough=4), "#F1C29C"),
        (blob(rng, 3520, 520, 45, 22), "#C9BDBE"),
        (blob(rng, 3470, 600, 30, 14), "#C9BDBE"),
        (blob(rng, 3640, 520, 40, 18), "#F3E6D8"),
        (blob(rng, 3700, 610, 34, 14), "#F3E6D8"),
    ]))
    # most screens only show a little beyond the picture (about 600 units
    # on each side at 1840 px wide), so the near mountains are moved in
    # towards it (keeping their shapes); the far ranges run on to the edges
    # for very wide screens
    def pull(pts):
        return [((x + PULL[0] if x < W / 2 else x + PULL[1]), y) for x, y in pts]
    return [(n, b, f, parts) if n.startswith("far") else
            (n, pull(b), f, [(pull(p), c) for p, c in parts]) for n, b, f, parts in m]


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


def smoothstep(t):
    t = np.clip(t, 0, 1)
    return t * t * (3 - 2 * t)


def sky_images(field):
    x0, x1 = -SIDE, W + SIDE
    y0, y1 = TOP - EXT, H
    fw, fh = (x1 - x0) // SKY_PX, (y1 - y0) // SKY_PX
    xs = x0 + (np.arange(fw) + 0.5) * SKY_PX
    ys = y0 + (np.arange(fh) + 0.5) * SKY_PX
    fx = np.clip(xs / 8, 0, field.shape[1] - 1).astype(int)
    fy = np.clip(ys / 8, 0, field.shape[0] - 1).astype(int)
    base = field[fy[:, None], fx[None, :]]
    # the strips beyond the picture repeat its edge columns: soften that
    base = np.stack([cv2.GaussianBlur(base[..., c], (0, 0), 2.0) for c in range(3)], -1)
    m = smoothstep((ys - GLOW_END) / (GLOW_TOP - GLOW_END))[:, None, None]
    out = {}
    for th in THEMES:
        sky = sky_map(th, base)
        stops = np.array([hex_lab(c) for c in DUSK[th]])
        # monotone cubic through the stops, flat above the last one
        yk = np.array(DUSK_Y[::-1], float)
        dusk = PchipInterpolator(yk, stops[::-1], axis=0, extrapolate=False)(np.clip(ys, yk[0], yk[-1]))
        img = sky * m + dusk[:, None, :] * (1 - m)
        rgb = np.clip(np.round(oklab_to_srgb(img.reshape(-1, 3))), 0, 255).reshape(fh, fw, 3).astype(np.uint8)
        _, png = cv2.imencode(".png", cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_PNG_COMPRESSION, 9])
        out[th] = base64.b64encode(png.tobytes()).decode()
    return out, (x0, y0, x1 - x0, y1 - y0)


# ── output ────────────────────────────────────────────────────────────────

def build():
    paths = read_paths()
    ids = id_map(paths)
    sky = expand(SKY_PATHS)
    shown = set(np.unique(ids).tolist()) - {0}
    field = sky_field(paths, ids, sky)
    skies, box = sky_images(field)

    classes = {}                                   # fill -> class
    shapes = []                                    # (class, d)
    trees = set(TREES)
    for k, (fill, pts) in enumerate(paths, 1):
        if k in sky or k not in shown:
            continue
        cls = classes.setdefault(fill, f"c{len(classes)}")
        if k in trees:
            for cx, top, w, h in trees_of(k, pts):
                shapes.append((cls, spruce(cx, top, w, h), (cx - w, cx + w)))
        else:
            shapes.append((cls, path_d(pts), (pts[:, 0].min(), pts[:, 0].max())))
    peaks = []                                     # (id, class, d, [(class, d)])
    for name, outline, fill, parts in side_mountains():
        cls = classes.setdefault(fill, f"c{len(classes)}")
        inner = [(classes.setdefault(f, f"c{len(classes)}"), path_d(catmull(p))) for p, f in parts]
        peaks.append((name, cls, path_d(catmull(outline)), inner))
    colours = {cls: {th: theme_colour(th, fill) for th in THEMES} for fill, cls in classes.items()}
    return shapes, colours, skies, box, peaks


def svg_markup(shapes, skies, box, peaks):
    vb = f"{-SIDE} {TOP} {W + 2 * SIDE} {H - TOP}"
    bx, by, bw, bh = box
    lines = [f'<svg class="about-scene" viewBox="{vb}" preserveAspectRatio="xMidYMax slice" '
             'aria-hidden="true" focusable="false">',
             "<defs>"]
    for i, (a, b, _) in enumerate(STRIPS):
        lines.append(f'<clipPath id="about-strip-{i}"><rect x="{a}" y="0" width="{b - a}" height="{H}"/></clipPath>')
    for name, _, d, _ in peaks:
        lines.append(f'<clipPath id="about-{name}"><path d="{d}"/></clipPath>')
    lines.append("</defs>")
    for th in THEMES:
        lines.append(f'<image class="sky sky-{th}" x="{bx}" y="{by}" width="{bw}" height="{bh}" '
                     f'preserveAspectRatio="none" href="data:image/png;base64,{skies[th]}"/>')
    def own(group):
        lines.append(f'<g class="{group}">')
        for name, cls, d, inner in peaks:
            lines.append(f'<path class="{cls}" d="{d}"/>')
            lines.append(f'<g clip-path="url(#about-{name})">')
            lines.extend(f'<path class="{c}" d="{dd}"/>' for c, dd in inner)
            lines.append("</g>")
        lines.append("</g>")
    # our own mountains beside the picture, behind it
    own("peaks")
    lines.append('<g class="land">')
    lines.extend(f'<path class="{c}" d="{d}"/>' for c, d, _ in shapes)
    lines.append("</g>")
    for i, (a, b, k) in enumerate(STRIPS):
        edge = a if i == 0 else b
        # the shapes in the strip, mirrored at the picture's edge and
        # stretched outwards (copies, not <use>: CSS colours do not reach
        # into <use> clones in every browser)
        lines.append(f'<g class="strip" clip-path="url(#about-strip-{i})" '
                     f'transform="matrix({k} 0 0 1 {edge * (1 - k)} 0)">')
        lines.extend(f'<path class="{c}" d="{d}"/>' for c, d, (x0, x1) in shapes if x1 >= a and x0 <= b)
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
    shapes, colours, skies, box, peaks = build()
    svg = svg_markup(shapes, skies, box, peaks)
    css = scene_css(colours)
    print(f"{len(shapes)} shapes, {len(svg) / 1024:.0f} KB of SVG, {len(colours)} colours")
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
