#!/usr/bin/env python3
"""Build the About-me background scene from the hand-off picture.

Sources (both in tools/, neither is deployed):

  about-scene-labels.png  the Dolomites SVG we were given (dolomites_background.svg,
                          70 flat colours, 7 MB), rendered at 2752 x 1536 without
                          anti-aliasing (tools/about-scene-render.js), so every
                          pixel holds one of its colours exactly
  about-scene-source.png  the original 1376 x 768 picture the SVG was traced
                          from; its smooth sky gives a clean skyline and the
                          depth layers

The script turns the labels back into smooth, light SVG paths whose colours
come from CSS, so every colour theme repaints the scene:

  1. clean the labels (thin slivers and specks join their neighbours),
  2. split land from sky and sort the land into depth layers (distant haze,
     right towers, left towers, snow, hills, foreground),
  3. trace each colour of each layer with potrace (curves, not pixels),
  4. drop the banded sky of the SVG: a smooth gradient takes its place,
  5. write one class per colour ("c<n>", or "h<n>" for the distant haze)
     and one colour per class and theme as CSS custom properties.

The theme colours keep the light and shadow of the picture: lightness,
chroma and hue of each colour are mapped in OKLCH by a rule per period. The
distant haze is coloured relative to the theme's sky, so it always sits in it.
The tower group on the right is scaled and moved down so it stands at the
same depth as the three towers on the left, and the outer strips of the
picture are mirrored and stretched (without the towers) to fill wide screens.

Run from the repo root:  python3 tools/about-scene.py
Needs numpy, opencv, scikit-learn, Pillow and the potrace command
(apt install potrace). It rewrites the <svg class="about-scene"> element and
the generated CSS between the scene-tones markers in index.html. Use
--debug DIR to write check images and a preview in the original colours.
"""
import argparse
import re
import subprocess
import sys

import cv2
import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt
from sklearn.cluster import MiniBatchKMeans

SRC = "tools/about-scene-source.png"
LABELS = "tools/about-scene-labels.png"
HTML = "index.html"

S = 2              # the labels are twice the size of the source picture
PAD = 900          # extension on each side for wide screens, in source pixels
TOP = 100          # crop: first source row that is drawn
LAYERS = [None, "haze", "right-towers", "left-towers", "snow", "hills", "fore"]

# Zones in source pixels (1376 x 768), drawn by eye from the picture.
TRIO_SNOWLINE = [(0, 472), (60, 468), (100, 462), (150, 474), (200, 470), (250, 458),
                 (300, 478), (350, 474), (400, 484), (450, 497), (500, 506), (550, 495),
                 (600, 500), (630, 508), (655, 508), (700, 548), (745, 580)]
TRIO_RIGHT = [(560, 140), (575, 380), (612, 395), (628, 415), (652, 448), (655, 508)]
TRIO_ZONE = np.array([(66, 140)] + TRIO_RIGHT
                     + [p for p in reversed(TRIO_SNOWLINE) if 66 < p[0] < 655]
                     + [(66, 468)], np.int32)
RIGHT_ZONE = np.array([(900, 360), (905, 350), (930, 345), (985, 300), (1000, 280),
                       (1030, 140), (1245, 140), (1243, 340), (1249, 360), (1249, 462),
                       (1200, 450), (1100, 436), (1056, 466), (1040, 458), (1000, 480),
                       (940, 462), (900, 458)], np.int32)
HAZE_ZONES = [np.array(p, np.int32) for p in (
    [(0, 340), (66, 340), (66, 468), (0, 472)],
    [(560, 140), (990, 140), (985, 300), (900, 360), (898, 440), (840, 452), (790, 470),
     (760, 500), (745, 560), (700, 548)] + TRIO_RIGHT[::-1][:-1],
    [(1249, 320), (1376, 320), (1376, 560), (1340, 560), (1249, 462)],
)]

# Moving the right-hand towers to the depth of the left ones: scale about the
# point where they meet the hill, then shift down (source pixels).
RIGHT_SCALE = 0.93
RIGHT_ANCHOR = (1080, 470)
RIGHT_SHIFT = (0, 34)

# Sky per period, top to horizon, at these heights (fractions of the drawn
# scene). The top colour is the section background (--bg-secondary).
SKY_AT = [0.0, 0.3, 0.55, 0.8]
SKY = {
    "cretaceous": ["#181a20", "#1b1f2c", "#252c44", "#2f3955"],
    "hadean": ["#21110d", "#2e120c", "#5a1d0c", "#7a2c0f"],
    "cambrian": ["#13211b", "#162a22", "#1f3d31", "#28503f"],
    "quaternary": ["#dde1e8", "#d9dfe8", "#cfd9e6", "#c6d3e3"],
}
THEMES = list(SKY)


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


def lab_hex(lab):
    L, a, b = lab
    return lch_hex(L, float(np.hypot(a, b)), float(np.degrees(np.arctan2(b, a))))


def hex_lab(h):
    h = h.lstrip("#")
    return srgb_to_oklab([int(h[i:i + 2], 16) for i in (0, 2, 4)])


def theme_colour(theme, lab):
    """Map one colour of the picture (OKLab) into a period's palette.

    The picture is a sunset: rock and sky are orange (hue about 55), grass is
    olive (about 85). Each rule keeps the lightness order and the difference
    between rock and grass, and moves them to the period's hues."""
    L, a, b = lab
    C = float(np.hypot(a, b))
    h = float(np.degrees(np.arctan2(b, a)) % 360)
    # 0 = sunlit rock, 30 = grass; greys (little chroma, unreliable hue) count as rock
    warm = float(np.clip((C - 0.02) / 0.03, 0, 1)) if 25 <= h <= 115 else 0.0
    hh = (float(np.clip(h, 45, 95)) - 55) * warm
    if theme == "cretaceous":                 # moonlit night, blue rock, teal grass
        return lch_hex(0.16 + 0.58 * L ** 1.35, 0.014 + 0.42 * C, 262 - 2.3 * hh)
    if theme == "hadean":                     # dark rock, the light parts glow like magma
        g = float(np.clip((L - 0.7) / 0.22, 0, 1))
        return lch_hex(0.13 + 0.5 * L ** 1.9 + 0.2 * g, 0.03 + 0.75 * C + 0.13 * g,
                       30 + 0.5 * hh + 30 * g)
    if theme == "cambrian":                   # green life
        return lch_hex(0.15 + 0.6 * L ** 1.25, 0.016 + 0.72 * C, 170 - 1.2 * hh)
    if theme == "quaternary":                 # ice age: blue-grey rock and snow, sage steppe
        return lch_hex(0.36 + 0.58 * L, 0.008 + 0.3 * C, 245 - 3.2 * hh)
    raise ValueError(theme)


def sky_colour(theme, t):
    """The period's sky at height t (0 = top of the scene, 1 = bottom), OKLab."""
    stops = [hex_lab(c) for c in SKY[theme]]
    t = float(np.clip(t, SKY_AT[0], SKY_AT[-1]))
    for i in range(len(SKY_AT) - 1):
        if t <= SKY_AT[i + 1]:
            f = (t - SKY_AT[i]) / (SKY_AT[i + 1] - SKY_AT[i])
            return stops[i] * (1 - f) + stops[i + 1] * f
    return stops[-1]


# ── depth layers from the original picture (source pixels) ───────────────

def snowline_y(x):
    xs, ys = zip(*TRIO_SNOWLINE)
    return np.interp(x, xs, ys)


def skyline(img):
    lab = cv2.cvtColor(cv2.GaussianBlur(img, (0, 0), 1.0), cv2.COLOR_BGR2LAB).astype(np.float32)
    gx = cv2.Sobel(lab, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(lab, cv2.CV_32F, 0, 1, ksize=3)
    mag = np.sqrt((gx ** 2 + gy ** 2).sum(axis=2))
    h, w = mag.shape
    ys = np.full(w, h)
    for x in range(w):
        idx = np.where(mag[5:, x] > 30)[0]
        if len(idx):
            ys[x] = idx[0] + 5
    # opening of the profile removes thin leaks through soft tower edges
    k = 7
    pad = np.pad(ys, k, mode="edge")
    er = np.array([pad[i:i + 2 * k + 1].min() for i in range(w + 2 * k)])
    return np.array([er[i:i + 2 * k + 1].max() for i in range(w)])


def lab_to_lch(c):
    L = c[0] * 100 / 255
    a, b = c[1] - 128, c[2] - 128
    return L, float(np.hypot(a, b)), float(np.degrees(np.arctan2(b, a)) % 360)


def depth_layers():
    """Land mask and drawing layer for every source pixel.

    Layers, back to front: 1 haze, 2 right towers, 3 left towers, 4 snow,
    5 hills, 6 foreground (0 = sky)."""
    img = cv2.imread(SRC)
    if img is None:
        sys.exit("missing " + SRC)
    h, w = img.shape[:2]
    img[-3:] = img[-4]                       # the last rows are blurred by the frame
    ms = cv2.pyrMeanShiftFiltering(img, 8, 18, maxLevel=2)
    ys = skyline(img)
    # the light band right of the big tower is cloud; the hills behind it
    # slope gently down to the right
    ys[1249:] = np.maximum(ys[1249:], (405 + (np.arange(1249, w) - 1249) * 0.25).astype(int))
    land = np.arange(h)[:, None] >= ys[None, :]

    # the soft glow along the tower edges belongs to the sky
    sky = (~land).astype(np.float32)
    num = cv2.GaussianBlur(ms.astype(np.float32) * sky[..., None], (0, 0), 28)
    den = cv2.GaussianBlur(sky, (0, 0), 28)[..., None]
    sky_img = np.clip(num / np.maximum(den, 1e-4), 0, 255).astype(np.uint8)
    near = cv2.dilate((~land).astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool) & land
    d = np.linalg.norm(cv2.cvtColor(ms, cv2.COLOR_BGR2LAB).astype(np.float32)
                       - cv2.cvtColor(sky_img, cv2.COLOR_BGR2LAB).astype(np.float32), axis=2)
    land &= ~(near & (d < 14))

    # a few dozen flat colours tell rock, grass and dark foreground apart
    lab = cv2.cvtColor(ms, cv2.COLOR_BGR2LAB).reshape(-1, 3).astype(np.float32)
    sel = land.reshape(-1)
    km = MiniBatchKMeans(24, random_state=3, batch_size=8192, n_init=4).fit(lab[sel][::3])
    labels = np.full((h, w), -1, np.int32)
    labels.reshape(-1)[sel] = km.predict(lab[sel])
    lch = np.array([lab_to_lch(c) for c in km.cluster_centers_])
    L, C, hue = (lch[np.clip(labels, 0, None), i] for i in range(3))

    yy, xx = np.mgrid[0:h, 0:w]
    grass = (C >= 22) & (hue >= 70) & ~((C < 30) & (hue < 80)) & (L < 72)
    grass |= (L < 20) & (yy < 600)          # small dark trees on the slopes
    dark = (L < 20) & (yy >= 600)

    def in_poly(poly):
        m = np.zeros((h, w), np.uint8)
        cv2.fillPoly(m, [poly], 1)
        return m.astype(bool)

    right = in_poly(RIGHT_ZONE)
    haze = [in_poly(z) for z in HAZE_ZONES]
    trio = in_poly(TRIO_ZONE)
    snowz = (xx < 760) & (yy >= snowline_y(np.arange(w))[None, :]) & (yy < 650) & ~haze[1]

    layer = np.zeros((h, w), np.int32)
    done = np.zeros((h, w), bool)

    def put(m, ly):
        m = m & land & ~done
        layer[m] = ly
        done[m] = True

    put(dark, 6)
    put(right & ~(grass & (yy > 420)), 2)
    put(haze[2] & (yy < 440), 1)            # a thin cloud line along the haze
    put(trio, 3)
    put(haze[2] & ~grass & (L > 74) & (C < 18), 4)
    for z in haze:
        put(z & ~grass, 1)
    put(snowz & ~grass, 4)
    put(grass, 5)
    put((L < 42) & (C < 18), 5)
    put(land & (yy < 430), 1)
    put(land, 5)
    return land, layer


# ── labels (twice the source size) ───────────────────────────────────────

def vote(keys, sigma, values=None):
    """Smooth a label map: each pixel takes the label with the most weight
    under a Gaussian around it (removes slivers, rounds stair steps)."""
    values = np.unique(keys) if values is None else values
    best = np.full(keys.shape, -1.0, np.float32)
    out = keys.copy()
    for k in values:
        score = cv2.GaussianBlur((keys == k).astype(np.float32), (0, 0), sigma)
        better = score > best
        out[better] = k
        best[better] = score[better]
    return out


def despeckle(labels, min_area):
    """Merge patches smaller than min_area into their most common neighbour."""
    out = labels.copy()
    kernel = np.ones((3, 3), np.uint8)
    for lab in np.unique(out):
        if lab < 0:
            continue
        n, comp, stats, _ = cv2.connectedComponentsWithStats((out == lab).astype(np.uint8), 8)
        for i in range(1, n):
            if stats[i, cv2.CC_STAT_AREA] >= min_area:
                continue
            x, y, w, h = stats[i, :4]
            x0, y0, x1, y1 = max(x - 2, 0), max(y - 2, 0), x + w + 2, y + h + 2
            sub = comp[y0:y1, x0:x1] == i
            ring = cv2.dilate(sub.astype(np.uint8), kernel).astype(bool) & ~sub
            nb = out[y0:y1, x0:x1][ring]
            nb = nb[(nb >= 0) & (nb != lab)]
            if len(nb):
                vals, counts = np.unique(nb, return_counts=True)
                out[y0:y1, x0:x1][sub] = vals[counts.argmax()]
    return out


def despeckle_holes(lab, holes):
    """Fill pixels marked -1 with their most common labelled neighbour,
    working inwards from the edge of each hole."""
    lab = lab.copy()
    for _ in range(200):
        miss = lab < 0
        if not (miss & holes).any():
            break
        best = np.full(lab.shape, -1, np.int32)
        bestn = np.zeros(lab.shape, np.int32)
        edge = miss & holes & cv2.dilate((~miss).astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
        ys, xs = np.nonzero(edge)
        for y, x in zip(ys, xs):
            nb = lab[max(y - 1, 0):y + 2, max(x - 1, 0):x + 2].ravel()
            nb = nb[nb >= 0]
            if len(nb):
                vals, counts = np.unique(nb, return_counts=True)
                best[y, x] = vals[counts.argmax()]
        lab[edge & (best >= 0)] = best[edge & (best >= 0)]
    lab[lab < 0] = 0
    return lab


def build(debug=None):
    land1, layer1 = depth_layers()
    im = Image.open(LABELS)
    if im.mode != "P":
        sys.exit(LABELS + " must be a palette image")
    lab = np.array(im).astype(np.int32)
    palette = np.array(im.getpalette()[:3 * (lab.max() + 1)]).reshape(-1, 3)
    H, W = lab.shape
    lab[-6:] = lab[-7]                        # the last rows follow the blurred frame

    lab = vote(lab, 1.0)
    lab = despeckle(lab, 30)

    # land: the source's land mask, with its edge moved onto the edges of
    # the SVG's own colours (a colour that is mostly land is land)
    up = cv2.resize(land1.astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST).astype(bool)
    k5 = np.ones((5, 5), np.uint8)
    band = cv2.dilate(up.astype(np.uint8), k5).astype(bool) & ~cv2.erode(up.astype(np.uint8), k5).astype(bool)
    n = len(palette)
    total = np.bincount(lab[~band], minlength=n)
    on_land = np.bincount(lab[~band & up], minlength=n)
    landish = on_land > 0.5 * np.maximum(total, 1)
    land = up.copy()
    land[band] = landish[lab[band]]
    # a patch of one SVG colour is sky or land as a whole, by majority (this
    # removes boxes the column-wise skyline leaves in gaps between towers)
    for k in range(n):
        cnt, comp = cv2.connectedComponents((lab == k).astype(np.uint8), connectivity=4)
        if cnt < 2:
            continue
        flat = comp.ravel()
        frac = np.bincount(flat, weights=land.ravel(), minlength=cnt) / np.maximum(np.bincount(flat, minlength=cnt), 1)
        sel = comp > 0
        land[sel] = (frac >= 0.5)[comp[sel]]
    # the glow along the tower edges is sky: peel sky-coloured patches off
    # the towers from the outside in
    zone = np.zeros((H, W), np.uint8)
    cv2.fillPoly(zone, [TRIO_ZONE * S, RIGHT_ZONE * S], 1)
    zone = cv2.dilate(zone, np.ones((41, 41), np.uint8)).astype(bool)
    skyish = on_land < 0.4 * np.maximum(total, 1)
    cross = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))
    for _ in range(16):
        edge = cv2.dilate((~land).astype(np.uint8), cross).astype(bool) & land & zone & skyish[lab]
        if not edge.any():
            break
        land[edge] = False
    land = cv2.GaussianBlur(land.astype(np.float32), (0, 0), 1.0) > 0.5

    # layers: from the source, then each patch of one SVG colour that lies
    # mostly in one layer goes there whole (layer edges follow colour edges)
    layer = cv2.resize(layer1.astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST).astype(np.int32)
    # land the source called sky takes the layer of the nearest land
    _, (iy, ix) = distance_transform_edt(layer == 0, return_indices=True)
    layer = np.where(land, layer[iy, ix], 0)
    for k in range(n):
        cnt, comp, stats, _ = cv2.connectedComponentsWithStats(((lab == k) & land).astype(np.uint8), 8)
        for i in range(1, cnt):
            x, y, w, h = stats[i, :4]
            sub = comp[y:y + h, x:x + w] == i
            ly = layer[y:y + h, x:x + w]
            hist = np.bincount(ly[sub], minlength=7)
            top = hist.argmax()
            if top and hist[top] >= 0.7 * hist.sum() and (hist[top] < hist.sum()):
                if top == 2 or hist[2] == 0:      # never pull pieces into or out of the moved towers
                    ly[sub] = top

    # bright orange glow left inside the towers (between them, along their
    # edges) is sky: where it touches the sky it opens up, elsewhere the
    # rock around it closes over it
    ok = srgb_to_oklab(palette)
    chroma = np.hypot(ok[:, 1], ok[:, 2])
    hue = np.degrees(np.arctan2(ok[:, 2], ok[:, 1])) % 360
    isglow = (chroma > 0.1) & (hue > 44) & (hue < 64) & (ok[:, 0] > 0.72)
    glow = land & np.isin(layer, (2, 3)) & isglow[lab]
    cnt, comp = cv2.connectedComponents(glow.astype(np.uint8), connectivity=8)
    if cnt > 1:
        sky_near = cv2.dilate((~land).astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
        opens = np.zeros(cnt, bool)
        opens[np.unique(comp[sky_near & glow])] = True
        opens[0] = False
        land[opens[comp]] = False
        layer[~land] = 0
        rest = glow & ~opens[comp]
        lab[rest] = -1
        lab = despeckle_holes(lab, rest)

    # the haze right of the big tower continues behind it (and over the
    # glow along its edge), so nothing opens up when the tower is moved
    x0, x1 = 1150 * S, 1256 * S
    for y in range(380 * S, 560 * S):
        if layer[y, x1] == 1:
            behind = np.isin(layer[y, x0:x1], (0, 2))
            layer[y, x0:x1][behind] = 1
            land[y, x0:x1][behind] = True
            lab[y, x0:x1][behind] = lab[y, x1 + 1]

    # the distant haze is simplified further (thin cloud lines and narrow
    # bands melt into their surroundings): this is the atmosphere
    hz = layer == 1
    soft = vote(np.where(hz, lab, -1), 3.0 * S)
    lab[hz & (soft >= 0)] = soft[hz & (soft >= 0)]


    if debug:
        cols = np.array([(0, 0, 0), (200, 170, 120), (60, 60, 200), (60, 160, 60),
                         (240, 240, 240), (60, 200, 220), (40, 40, 40)], np.uint8)
        dbg = np.where(land[..., None], cols[layer], (255, 210, 160)).astype(np.uint8)
        cv2.imwrite(f"{debug}/layers.png", cv2.resize(dbg, (W // 2, H // 2), interpolation=cv2.INTER_NEAREST))
    return lab, palette, land, layer


# ── tracing ───────────────────────────────────────────────────────────────

def potrace_paths(mask):
    """Absolute cubic/line subpaths for a boolean mask (pixel coordinates)."""
    h, w = mask.shape
    pbm = b"P4\n%d %d\n" % (w, h) + np.packbits(mask.astype(np.uint8), axis=1).tobytes()
    out = subprocess.run(["potrace", "-b", "svg", "--flat", "-t", "16", "-a", "1.1", "-O", "1.0",
                          "-u", "10", "-o", "-"], input=pbm, capture_output=True, check=True).stdout.decode()
    d = " ".join(re.findall(r'<path d="([^"]*)"', out, re.S))
    toks = re.findall(r"[MmCcLlZz]|-?\d+(?:\.\d+)?", d)
    subpaths, cur, start, cmd, i = [], None, None, None, 0
    while i < len(toks):
        t = toks[i]
        if t in "MmCcLlZz":
            cmd = t
            i += 1
            if cmd in "Zz":
                if cur:
                    cur[1].append(("z",))
                cmd = None
            continue
        nums = {"M": 2, "m": 2, "C": 6, "c": 6, "L": 2, "l": 2}[cmd]
        v = [float(x) for x in toks[i:i + nums]]
        i += nums
        if cmd in "Mm":
            base = (0.0, 0.0) if cmd == "M" or start is None else last
            p = (base[0] + v[0], base[1] + v[1])
            cur = (p, [])
            subpaths.append(cur)
            start = last = p
            cmd = "l" if cmd == "m" else "L"
        elif cmd in "Cc":
            o = last if cmd == "c" else (0.0, 0.0)
            pts = [(o[0] + v[j], o[1] + v[j + 1]) for j in (0, 2, 4)]
            cur[1].append(("c", pts))
            last = pts[2]
        else:
            o = last if cmd == "l" else (0.0, 0.0)
            p = (o[0] + v[0], o[1] + v[1])
            cur[1].append(("l", [p]))
            last = p
    # potrace units: 1/10 pixel, y up from the bottom
    def tf(p):
        return (p[0] / 10.0, h - p[1] / 10.0)
    return [(tf(p0), [(s[0], [tf(q) for q in s[1]]) if s[0] != "z" else s for s in segs])
            for p0, segs in subpaths]


def fmt(nums):
    s = ""
    for v in nums:
        t = str(int(v))
        s += t if (not s or t.startswith("-")) else " " + t
    return s


def path_data(mask, ox, oy):
    """SVG path data for a mask whose top-left pixel sits at (ox, oy)."""
    ys, xs = np.nonzero(mask)
    if not len(xs):
        return ""
    m = 3
    x0, y0 = max(xs.min() - m, 0), max(ys.min() - m, 0)
    x1, y1 = min(xs.max() + m + 1, mask.shape[1]), min(ys.max() + m + 1, mask.shape[0])
    sub = mask[y0:y1, x0:x1]
    out = []
    for p0, segs in potrace_paths(sub):
        cur = (round(p0[0] + x0 + ox), round(p0[1] + y0 + oy))
        start = cur
        rels = []                 # (command, relative numbers), rounded
        for s in segs:
            if s[0] == "z":
                break
            pts = [(round(q[0] + x0 + ox), round(q[1] + y0 + oy)) for q in s[1]]
            rel = []
            for q in pts:
                rel += [q[0] - cur[0], q[1] - cur[1]]
            cur = pts[-1]
            if rel[-2:] == [0, 0] and (s[0] == "l" or rel == [0] * 6):
                continue
            if s[0] == "l" and rels and rels[-1][0] == "l":
                px, py = rels[-1][1]
                if px * rel[1] == py * rel[0] and px * rel[0] + py * rel[1] > 0:   # same direction
                    rels[-1] = ("l", [px + rel[0], py + rel[1]])
                    continue
            rels.append((s[0], rel))
        # the closing line is implied by z
        if rels and rels[-1][0] == "l" and cur == start:
            rels.pop()
        if not rels:
            continue
        d = [f"M{start[0]} {start[1]}"]
        prev = None
        for cmd, rel in rels:
            body = fmt(rel)
            d.append(body if prev == cmd and body.startswith("-") else
                     (" " + body if prev == cmd else cmd + body))
            prev = cmd
        out.append("".join(d) + "z")
    return "".join(out)


def fill_down(mask):
    """Every pixel at or below the top of the mask in each column (thin
    strays and small loose pieces are ignored so they do not start a column)."""
    mask = cv2.morphologyEx(mask.astype(np.uint8), cv2.MORPH_OPEN, np.ones((9, 9), np.uint8))
    cnt, comp, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    keep = stats[:, cv2.CC_STAT_AREA] >= max(4000, 0.02 * stats[1:, cv2.CC_STAT_AREA].sum())
    keep[0] = False
    mask = keep[comp]
    has = mask.any(axis=0)
    first = np.where(has, mask.argmax(axis=0), mask.shape[0])
    return np.arange(mask.shape[0])[:, None] >= first[None, :]


def trace(debug=None):
    lab, palette, land, layer = build(debug)
    H, W = lab.shape
    P = PAD * S

    # wide screens: the outer strip of the picture is mirrored and stretched
    # four times, so the land rolls on in long, gentle shapes (the towers are
    # left out there; the sky shows instead)
    key = np.where(land, layer * 128 + lab, -1)
    d = np.arange(P)
    left = key[:, np.minimum(d // 4, W - 1)][:, ::-1]
    right = key[:, np.maximum(W - 1 - d // 4, 0)]
    for part in (left, right):
        part[np.isin(part // 128, (2, 3))] = -1
    # the stretch turns diagonal edges into stairs: smooth the strips
    left, right = vote(left, 3.5 * S), vote(right, 3.5 * S)
    key = np.concatenate([left, key, right], axis=1)
    key = key[TOP * S:]
    land_p = key >= 0
    layer_p = np.where(land_p, key // 128, 0)
    lab_p = np.where(land_p, key % 128, -1)
    oy = TOP * S
    ox = -P

    # the SVG's own sky colour by height: the haze is coloured relative to it
    okpal = srgb_to_oklab(palette)
    rows = np.arange(H)
    sky_rows = np.zeros((H, 3))
    have = np.zeros(H, bool)
    skym = ~land
    for y in range(H):
        sel = lab[y][skym[y]]
        if len(sel) > 20:
            sky_rows[y] = okpal[sel].mean(axis=0)
            have[y] = True
    for c in range(3):
        sky_rows[:, c] = np.interp(rows, rows[have], sky_rows[have, c])
        sky_rows[:, c] = cv2.GaussianBlur(sky_rows[:, c].reshape(-1, 1), (1, 0), 40).ravel()
    scene_h = H - oy

    shapes = []          # (layer, class, path data)
    haze_colour = {}     # class -> {theme: hex}

    for ly in range(1, 7):
        lm = layer_p == ly
        if not lm.any():
            continue
        labs = np.unique(lab_p[lm])
        areas = {int(k): int((lm & (lab_p == k)).sum()) for k in labs}
        order = sorted(areas, key=lambda k: -areas[k])
        prefix = "h" if ly == 1 else "c"
        # base: the layer filled down to the bottom in its main colour (no
        # gaps); the moved towers only get their own outline filled, so the
        # haze behind them stays free
        if ly == 2:
            closed = cv2.morphologyEx(lm.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
            cnts, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            solid = np.zeros_like(closed)
            cv2.drawContours(solid, cnts, -1, 1, -1)
            base = path_data(solid.astype(bool), ox, oy)
        else:
            base = path_data(fill_down(lm), ox, oy)
        if base:
            shapes.append((ly, f"{prefix}{order[0]}", base))
        for k in order:
            m = lm & (lab_p == k)
            m = cv2.dilate(m.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)   # overlap: no seams
            dpath = path_data(m, ox, oy)
            if dpath:
                shapes.append((ly, f"{prefix}{k}", dpath))
            if ly == 1:
                ys_ = np.nonzero(m)[0] + oy
                yc = float(np.median(ys_))
                delta = okpal[k] - sky_rows[int(yc)]
                t = (yc - oy) / scene_h
                haze_colour[f"h{k}"] = {th: lab_hex(sky_colour(th, t) + delta * np.array([0.55, 0.15, 0.15]))
                                        for th in THEMES}
    used = sorted({int(c[1:]) for _, c, _ in shapes if c[0] == "c"})
    colours = {f"c{k}": {th: theme_colour(th, okpal[k]) for th in THEMES} for k in used}
    colours.update(haze_colour)
    source = {f"{p}{k}": "#%02x%02x%02x" % tuple(palette[k]) for k in range(len(palette)) for p in "ch"}
    size = (W + 2 * P, H - oy)
    return shapes, colours, source, size


def svg_markup(shapes, size):
    w, h = size
    x0, y0 = -PAD * S, TOP * S
    sx, sy = RIGHT_ANCHOR[0] * S, RIGHT_ANCHOR[1] * S
    tx, ty = RIGHT_SHIFT[0] * S, RIGHT_SHIFT[1] * S
    stops = "".join(f'<stop offset="{t:g}" class="k{i}"/>' for i, t in enumerate(SKY_AT))
    lines = [f'<svg class="about-scene" viewBox="{x0} {y0} {w} {h}" '
             'preserveAspectRatio="xMidYMax slice" aria-hidden="true" focusable="false">',
             f'<defs><linearGradient id="about-sky" gradientUnits="userSpaceOnUse" x1="0" y1="{y0}" '
             f'x2="0" y2="{y0 + h}">{stops}</linearGradient></defs>',
             f'<rect class="sky" x="{x0}" y="{y0}" width="{w}" height="{h}" fill="url(#about-sky)"/>']
    for ly in range(1, 7):
        items = [s for s in shapes if s[0] == ly]
        if not items:
            continue
        attr = (f' transform="translate({sx + tx} {sy + ty}) scale({RIGHT_SCALE}) translate({-sx} {-sy})"'
                if ly == 2 else "")
        lines.append(f'<g class="{LAYERS[ly]}"{attr}>')
        lines.extend(f'<path class="{cls}" d="{d}"/>' for _, cls, d in items)
        lines.append("</g>")
    lines.append("</svg>")
    return "\n".join(lines)


def scene_css(colours):
    """Custom properties per period (Kritt is the default) and one rule per class."""
    def sort_key(c):
        return (c[0], int(c[1:]))
    classes = sorted(colours, key=sort_key)
    blocks = []
    for th in ["cretaceous"] + [t for t in THEMES if t != "cretaceous"]:
        sel = "#om-meg" if th == "cretaceous" else f'[data-theme="{th}"] #om-meg'
        props = [f"--sk{i}: {c};" for i, c in enumerate(SKY[th]) if i]
        props += [f"--s{c}: {colours[c][th]};" for c in classes]
        lines, line = [], ""
        for p in props:
            if len(line) + len(p) > 100:
                lines.append(line.rstrip())
                line = ""
            line += p + " "
        lines.append(line.rstrip())
        blocks.append(sel + " {\n  " + "\n  ".join(lines) + "\n}")
    rules = [".about-scene .k0 { stop-color: var(--bg-secondary); }"]
    rules += [f".about-scene .k{i} {{ stop-color: var(--sk{i}); }}" for i in range(1, len(SKY_AT))]
    rules += [f".about-scene .{c} {{ fill: var(--s{c}); }}" for c in classes]
    return "\n".join(blocks + rules)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--debug", help="folder for check images and a preview in the original colours")
    ap.add_argument("--no-write", action="store_true")
    args = ap.parse_args()
    shapes, colours, source, size = trace(args.debug)
    svg = svg_markup(shapes, size)
    css = scene_css(colours)
    print(f"{len(shapes)} shapes, {len(svg) / 1024:.0f} KB of SVG, {len(colours)} colours")
    if args.debug:
        style = "".join(f".{c}{{fill:{source[c]}}}" for c in colours)
        with open(f"{args.debug}/preview.html", "w") as f:
            f.write("<!doctype html><style>body{margin:0;background:#888}svg{display:block;width:100%;height:auto}"
                    f".k0,.k1,.k2,.k3{{stop-color:#e9a070}}{style}</style>{svg}")
        with open(f"{args.debug}/scene.svg", "w") as f:
            f.write(svg)
        with open(f"{args.debug}/scene.css", "w") as f:
            f.write(css)
        bg = {"cretaceous": "#181a20", "hadean": "#21110d", "cambrian": "#13211b", "quaternary": "#dde1e8"}
        for th in THEMES:
            with open(f"{args.debug}/preview-{th}.html", "w") as f:
                f.write(f'<!doctype html><html data-theme="{th}"><style>body{{margin:0;background:{bg[th]}}}'
                        f'#om-meg{{--bg-secondary:{bg[th]}}}svg{{display:block;width:100%;height:auto}}{css}</style>'
                        f'<section id="om-meg">{svg}</section></html>')
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
