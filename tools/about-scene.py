#!/usr/bin/env python3
"""Trace the About-me background scene from tools/about-scene-source.png.

The source is a flat-vector picture of Dolomite towers above snow and grassy
hills. This script turns it into layered SVG shapes whose colours come from
CSS, so every colour theme can repaint the scene:

  1. smooth the picture and reduce it to a few dozen flat colours,
  2. find the skyline and repaint the sky behind the mountains (inpainting),
  3. sort every patch of colour into a group (sky, haze, rock, snow, grass,
     dirt, foreground) by where it sits and what colour it has,
  4. trace each patch to a polygon and give it a class "s-<group>-<tone>",
     where the tone keeps the original light and shadow (0 = darkest).

The CSS in index.html maps each class to a mix of three theme colours per
group (--sc-<group>-lo / -mid / -hi). The tower group on the right is moved
down and scaled so it stands at the same depth as the three towers on the
left. The edges are mirrored (without the towers) so the scene can fill wide
screens.

Run from the repo root:  python3 tools/about-scene.py   (needs numpy, opencv,
scikit-learn). It rewrites the <svg class="about-scene"> element and the
generated tone rules in index.html. Use --debug DIR to write check images.
"""
import argparse
import re
import sys

import cv2
import numpy as np
from sklearn.cluster import MiniBatchKMeans

SRC = "tools/about-scene-source.png"
HTML = "index.html"

PAD = 540          # extension on each side for wide screens, in source pixels
TOP = 100          # crop: first source row that is drawn
GROUPS = ["sky", "haze", "rock", "snow", "grass", "dirt", "fore"]

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
# point where they meet the hill, then shift down.
RIGHT_SCALE = 0.93
RIGHT_ANCHOR = (1080, 470)
RIGHT_SHIFT = (0, 34)


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
    ys = np.array([er[i:i + 2 * k + 1].max() for i in range(w)])
    return ys


def quantise(img, mask, k, seed):
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB).reshape(-1, 3).astype(np.float32)
    sel = mask.reshape(-1)
    km = MiniBatchKMeans(k, random_state=seed, batch_size=8192, n_init=4).fit(lab[sel][::3])
    labels = np.full(mask.shape, -1, np.int32)
    labels.reshape(-1)[sel] = km.predict(lab[sel])
    return labels, km.cluster_centers_


def despeckle(labels, min_area):
    """Merge patches smaller than min_area into their most common neighbour."""
    out = labels.copy()
    kernel = np.ones((3, 3), np.uint8)
    for _ in range(2):
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


def lab_to_lch(c):
    L = c[0] * 100 / 255
    a, b = c[1] - 128, c[2] - 128
    return L, float(np.hypot(a, b)), float(np.degrees(np.arctan2(b, a)) % 360)


def classify(labels, centres, land):
    """Group (index into GROUPS, -1 = sky) and drawing layer for every pixel.

    Layers, back to front: 1 haze, 2 right towers, 3 left towers, 4 snow,
    5 hills, 6 foreground.
    """
    h, w = labels.shape
    yy, xx = np.mgrid[0:h, 0:w]
    lch = np.array([lab_to_lch(c) for c in centres])
    L, C, hue = (lch[np.clip(labels, 0, None), i] for i in range(3))
    grass = (C >= 22) & (hue >= 70) & ~((C < 30) & (hue < 80)) & (L < 72)
    grass |= (L < 20) & (yy < 600)          # small dark trees on the slopes
    dark = (L < 20) & (yy >= 600)

    def in_poly(poly):
        m = np.zeros((h, w), np.uint8)
        cv2.fillPoly(m, [poly], 1)
        return m.astype(bool)

    right = in_poly(RIGHT_ZONE)
    haze = [in_poly(z) for z in HAZE_ZONES]
    snow_y = snowline_y(np.arange(w))[None, :]
    trio = in_poly(TRIO_ZONE)
    snowz = (xx < 760) & (yy >= snow_y) & (yy < 650) & ~haze[1]

    groups = np.full((h, w), -1, np.int32)
    layer = np.zeros((h, w), np.int32)

    def put(m, g, ly):
        m = m & land & (groups < 0)
        groups[m] = GROUPS.index(g)
        layer[m] = ly

    put(dark, "fore", 6)
    put(right & ~(grass & (yy > 420)), "rock", 2)
    put(trio, "rock", 3)
    put(haze[2] & ~grass & (L > 74) & (C < 18), "snow", 4)
    for z in haze:
        put(z & ~grass, "haze", 1)
    put(snowz & ~grass, "snow", 4)
    put(grass, "grass", 5)
    put((L < 42) & (C < 18), "rock", 5)
    put(land & (yy < 430), "haze", 1)
    put(land, "dirt", 5)

    # a patch the snow line cuts in two joins its larger part when the
    # smaller part is a sliver (keeps tower bases and snow edges clean)
    for lab in range(len(centres)):
        n, comp, stats, _ = cv2.connectedComponentsWithStats(((labels == lab) & land).astype(np.uint8), 8)
        for i in range(1, n):
            x, y, cw, ch = stats[i, :4]
            sub = comp[y:y + ch, x:x + cw] == i
            ly = layer[y:y + ch, x:x + cw][sub]
            n3, n4 = (ly == 3).sum(), (ly == 4).sum()
            if n3 and n4 and min(n3, n4) < 0.35 * (n3 + n4):
                keep = 3 if n3 > n4 else 4
                g = GROUPS.index("rock" if keep == 3 else "snow")
                gsub = groups[y:y + ch, x:x + cw]
                lsub = layer[y:y + ch, x:x + cw]
                move = sub & ((lsub == 3) | (lsub == 4))
                gsub[move] = g
                lsub[move] = keep
    return groups, layer


def build(debug=None):
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
    rows = np.arange(h)[:, None]
    land = rows >= ys[None, :]

    # smooth sky behind the mountains: blur of the visible sky, normalised
    sky = (~land).astype(np.float32)
    num = cv2.GaussianBlur(ms.astype(np.float32) * sky[..., None], (0, 0), 28)
    den = cv2.GaussianBlur(sky, (0, 0), 28)[..., None]
    sky_img = np.clip(num / np.maximum(den, 1e-4), 0, 255).astype(np.uint8)

    # the soft glow along the tower edges belongs to the sky
    near = cv2.dilate((~land).astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool) & land
    d = np.linalg.norm(cv2.cvtColor(ms, cv2.COLOR_BGR2LAB).astype(np.float32)
                       - cv2.cvtColor(sky_img, cv2.COLOR_BGR2LAB).astype(np.float32), axis=2)
    land &= ~(near & (d < 14))

    labels, centres = quantise(ms, land, 24, seed=3)
    labels = despeckle(labels, 36)
    groups, layer = classify(labels, centres, land)

    # the haze right of the big tower continues behind it, so nothing opens
    # up when the tower is moved
    hz = GROUPS.index("haze")
    for y in range(380, 560):
        if layer[y, 1252] == 1:
            behind = (layer[y, 1150:1252] == 2)
            layer[y, 1150:1252][behind] = 1
            groups[y, 1150:1252][behind] = hz
            labels[y, 1150:1252][behind] = labels[y, 1252]

    # sky: repaint the land with sky colours, then a few smooth bands
    sky_labels, sky_centres = quantise(sky_img, np.ones((h, w), bool), 7, seed=5)
    sky_labels = despeckle(sky_labels, 400)

    if debug:
        palette = np.array([(200, 120, 255), (120, 170, 220), (90, 90, 90), (245, 245, 245),
                            (60, 170, 90), (90, 150, 210), (20, 30, 30)], np.uint8)
        dbg = np.where(groups[..., None] >= 0, palette[np.clip(groups, 0, None)], (255, 210, 160)).astype(np.uint8)
        cv2.imwrite(f"{debug}/groups.png", dbg)
        lay = (layer * 40).astype(np.uint8)
        cv2.imwrite(f"{debug}/layers.png", cv2.applyColorMap(lay, cv2.COLORMAP_JET))
    return img, labels, centres, groups, layer, sky_labels, sky_centres, ys


def path_data(mask, eps):
    """SVG path data for a boolean mask (outer shapes and holes, even-odd)."""
    m = cv2.dilate(mask.astype(np.uint8), np.ones((3, 3), np.uint8))  # overlap neighbours: no seams
    contours, _ = cv2.findContours(m, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    out = []
    for c in contours:
        if cv2.contourArea(c) < 6 and len(c) < 8:
            continue
        a = cv2.approxPolyDP(c, eps, True).reshape(-1, 2)
        if len(a) < 3:
            continue
        pts = a - np.array([PAD, -TOP])
        d = [f"M{pts[0][0]} {pts[0][1]}"]
        rel = np.diff(pts, axis=0)
        d.append("l" + " ".join(f"{dx} {dy}" for dx, dy in rel))
        out.append(("".join(d) + "z").replace(" -", "-"))
    return "".join(out)


def fill_down(mask):
    """Every pixel at or below the top of the mask in each column (thin
    strays are ignored so they do not start a column)."""
    mask = cv2.morphologyEx(mask.astype(np.uint8), cv2.MORPH_OPEN, np.ones((7, 7), np.uint8)).astype(bool)
    has = mask.any(axis=0)
    first = np.where(has, mask.argmax(axis=0), mask.shape[0])
    return np.arange(mask.shape[0])[:, None] >= first[None, :]


def tones(values, n=10):
    if not values:
        return []
    lo, hi = min(values), max(values)
    return [int(round((v - lo) / (hi - lo) * n)) if hi > lo else n // 2 for v in values]


def trace(debug=None):
    img, labels, centres, groups, layer, sky_labels, sky_centres, ys = build(debug)
    h, w = labels.shape

    # wide screens: the outer strip of the picture is mirrored and stretched
    # four times, so the land rolls on in long, gentle shapes (towers are left
    # out there; the sky shows instead)
    d = np.arange(PAD)
    src_l = np.minimum(d // 4, w - 1)                 # column for x = -1 - d
    src_r = np.maximum(w - 1 - d // 4, 0)             # column for x = w + d

    def pad(a, fill):
        left = a[:, src_l][:, ::-1]
        right = a[:, src_r]
        return np.concatenate([left, a, right], axis=1)

    layer_p = pad(layer, 0)
    side = np.ones(layer_p.shape[1], bool)
    side[PAD:PAD + w] = False
    layer_p[:, side] = np.where(np.isin(layer_p[:, side], (2, 3)), 0, layer_p[:, side])
    groups_p, labels_p = pad(groups, -1), pad(labels, -1)

    # the stretch turns diagonal edges into stairs: smooth the edge strips
    key = layer_p * 10000 + (groups_p + 1) * 100 + (labels_p + 1)
    for sl in (np.s_[:, :PAD], np.s_[:, PAD + w:]):
        part = key[sl]
        best = np.full(part.shape, -1.0, np.float32)
        out = part.copy()
        for k in np.unique(part):
            score = cv2.GaussianBlur((part == k).astype(np.float32), (0, 0), 3.5)
            better = score > best
            out[better] = k
            best[better] = score[better]
        key[sl] = out
    layer_p, groups_p, labels_p = key // 10000, (key // 100) % 100 - 1, key % 100 - 1
    sky_p = np.concatenate([np.repeat(sky_labels[:, :1], PAD, 1), sky_labels,
                            np.repeat(sky_labels[:, -1:], PAD, 1)], axis=1)
    img_p = np.concatenate([np.repeat(img[:, :1], PAD, 1), img, np.repeat(img[:, -1:], PAD, 1)], axis=1)
    crop = slice(TOP, h)

    # tone of every (group, colour) pair from the lightness of the colour
    # (the right towers get their own range so they read at the same depth
    # as the left ones instead of darker and nearer)
    L = [lab_to_lch(c)[0] for c in centres]
    tone = {}
    for gi, g in enumerate(GROUPS[1:], 1):
        for right in (False, True):
            sel = (layer == 2) if right else (layer != 2)
            labs = sorted(set(np.unique(labels[(groups == gi) & sel]).tolist()) - {-1})
            for lab, t in zip(labs, tones([L[x] for x in labs])):
                tone[(gi, lab, right)] = t
    # sky bands: tone by height (nearer the horizon = higher tone), not by
    # the source's sunset colours
    rows_ = np.arange(h)[:, None].repeat(w, 1)
    sky_y = [float(rows_[TOP:][sky_labels[TOP:] == k].mean()) if (sky_labels[TOP:] == k).any() else 0.0
             for k in range(len(sky_centres))]
    sky_tone = dict(enumerate(tones(sky_y)))

    shapes = []          # (layer, class, path data, mean BGR of the source)

    def add(ly, cls, mask, eps):
        mask = mask[crop]
        if not mask.any():
            return
        d = path_data(mask, eps)
        if d:
            col = img_p[crop][mask].mean(axis=0) if mask.any() else (0, 0, 0)
            shapes.append((ly, cls, d, col, int(mask.sum())))

    for lab, t in sky_tone.items():
        add(0, f"s-sky-{t}", sky_p == lab, 2.0)
    for ly in range(1, 7):
        lm = layer_p == ly
        if not lm.any():
            continue
        classes = {}
        for gi in range(1, len(GROUPS)):
            for lab in np.unique(labels_p[lm & (groups_p == gi)]):
                cls = f"s-{GROUPS[gi]}-{tone[(gi, int(lab), ly == 2)]}"
                classes.setdefault(cls, np.zeros_like(lm))
                classes[cls] |= lm & (groups_p == gi) & (labels_p == lab)
        order = sorted(classes.items(), key=lambda kv: -kv[1].sum())
        # base: the layer filled down to the bottom in its main colour (no gaps)
        add(ly, order[0][0], fill_down(lm), 1.2)
        for cls, m in order:
            add(ly, cls, m, 0.8)
    return shapes, (w, h)


def svg_markup(shapes, size):
    w, h = size
    x0, vw, vh = -PAD, w + 2 * PAD, h - TOP
    sx, sy = RIGHT_ANCHOR
    tx, ty = RIGHT_SHIFT
    right = (f'<g transform="translate({sx + tx} {sy + ty}) scale({RIGHT_SCALE}) '
             f'translate({-sx} {-sy})">')
    lines = [f'<svg class="about-scene" viewBox="{x0} {TOP} {vw} {vh}" '
             'preserveAspectRatio="xMidYMax slice" aria-hidden="true" focusable="false">']
    for ly in range(0, 7):
        items = [s for s in shapes if s[0] == ly]
        if not items:
            continue
        if ly == 2:
            lines.append(right)
        for _, cls, d, _, _ in items:
            lines.append(f'<path class="{cls}" d="{d}"/>')
        if ly == 2:
            lines.append("</g>")
    lines.append("</svg>")
    return "\n".join(lines)


def tone_css(shapes):
    rules = []
    for cls in sorted({s[1] for s in shapes}, key=lambda c: (GROUPS.index(c.split("-")[1]), int(c.split("-")[2]))):
        _, g, t = cls.split("-")
        t = int(t) / 10
        if t <= 0.5:
            mix = f"var(--sc-{g}-mid) {round(t * 200)}%, var(--sc-{g}-lo)"
        else:
            mix = f"var(--sc-{g}-hi) {round((t - 0.5) * 200)}%, var(--sc-{g}-mid)"
        rules.append(f".about-scene .{cls} {{ fill: color-mix(in oklab, {mix}); }}")
    return "\n".join(rules)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--debug", help="folder for check images and a preview with the source colours")
    ap.add_argument("--no-write", action="store_true")
    args = ap.parse_args()
    shapes, size = trace(args.debug)
    svg = svg_markup(shapes, size)
    css = tone_css(shapes)
    print(f"{len(shapes)} shapes, {len(svg) / 1024:.0f} KB of SVG, {css.count(chr(10)) + 1} tone rules")
    if args.debug:
        orig = svg
        for _, cls, _, col, _ in shapes:
            pass
        # preview in the source colours: one style per path
        prev = []
        for line in svg.split("\n"):
            prev.append(line)
        cols = {}
        for _, cls, _, col, area in shapes:
            cols.setdefault(cls, []).append((col, area))
        style = "".join(
            f".{c}{{fill:rgb({int(sum(cc[2] * a for cc, a in v) / sum(a for _, a in v))},"
            f"{int(sum(cc[1] * a for cc, a in v) / sum(a for _, a in v))},"
            f"{int(sum(cc[0] * a for cc, a in v) / sum(a for _, a in v))})}}" for c, v in cols.items())
        with open(f"{args.debug}/preview.html", "w") as f:
            f.write(f"<!doctype html><style>body{{margin:0;background:#888}}svg{{display:block;width:100%}}{style}</style>{orig}")
    if args.no_write:
        return
    html = open(HTML, encoding="utf-8").read()
    html, n = re.subn(r'<svg class="about-(?:scene|mountains)".*?</svg>', lambda m: svg, html, count=1, flags=re.S)
    if n != 1:
        sys.exit("could not find the About background <svg> in index.html")
    css_block = "\n".join("    " + r for r in css.split("\n"))
    html, n = re.subn(r"/\* scene-tones:start \*/.*?/\* scene-tones:end \*/",
                      lambda m: "/* scene-tones:start */\n" + css_block + "\n    /* scene-tones:end */",
                      html, count=1, flags=re.S)
    if n != 1:
        print("note: no scene-tones markers in index.html; tone rules not written")
    open(HTML, "w", encoding="utf-8").write(html)


if __name__ == "__main__":
    main()
