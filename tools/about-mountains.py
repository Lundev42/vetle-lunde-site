"""Draw the flat Lofoten-style mountains behind the "Om meg" section.

Usage (from the repository root):  python3 tools/about-mountains.py
Rewrites the <svg class="about-mountains"> element inside index.html.

Three ranges (far, middle, near) of steep, pointed peaks joined by saddles,
each peak with a flat shadowed right-hand face; the tallest far peaks
have a little snow. The viewBox is
1600x400 and the mountains stand on its bottom edge; the ranges continue
1000 units past each side so wide screens never show an empty edge.
Colours are not set here: each range is filled with a gradient whose
stops are coloured from index.html's CSS (one palette per theme).
"""
import pathlib
import random

W, H = 1600, 400
X0, X1 = -1000, 2600


def make_range(seed, spacing, summit, saddle):
    """Summits and saddles along a ridge, left to right.

    spacing: (min, max) distance between saddles; summit: (min, max)
    summit height; saddle: (min, max) saddle height as a fraction of the
    lower neighbouring summit. Heights are measured up from the base."""
    rnd = random.Random(seed)
    pts = []
    x = X0 - 200
    prev_summit = rnd.uniform(*summit)
    while x < X1 + 200:
        h = rnd.uniform(*summit)
        sad = min(h, prev_summit) * rnd.uniform(*saddle)
        pts.append((x, sad, "saddle"))
        dx = rnd.uniform(*spacing)
        pts.append((x + dx * rnd.uniform(0.38, 0.62), h, "summit"))
        prev_summit = h
        x += dx
    return pts, rnd


def detail(pts, rnd, jag):
    """Add a shoulder on each flank so the ridges look jagged, not smooth."""
    out = [pts[0]]
    for (xa, ha, ka), (xb, hb, kb) in zip(pts, pts[1:]):
        t = rnd.uniform(0.4, 0.6)
        xm = xa + (xb - xa) * t
        hm = ha + (hb - ha) * t + rnd.uniform(-1, 1) * jag
        # a small notch just below some summits
        out.append((xm, hm, "flank"))
        out.append((xb, hb, kb))
    return out


def to_path(pts):
    line = " ".join(f"{x:.0f},{H - h:.0f}" for x, h, _ in pts)
    return f"M{X0 - 200},{H} L{line} L{X1 + 400},{H} Z"


def shadows(pts):
    """Shadowed right-hand face of every summit (flat two-tone shading)."""
    faces = []
    for i, (x, h, kind) in enumerate(pts):
        if kind != "summit":
            continue
        ridge = [(x, h)]
        for xj, hj, kj in pts[i + 1:]:
            ridge.append((xj, hj))
            if kj == "saddle":
                break
        rx, rh = ridge[-1]
        # the shadow line runs from the summit down and slightly right;
        # the face fades out towards the base (see the am-shade gradient)
        foot = x + (rx - x) * 0.22
        poly = ridge + [(rx, rh * 0.35), (foot, 0)]
        faces.append("M" + " L".join(f"{px:.0f},{H - ph:.0f}" for px, ph in poly) + " Z")
    return "".join(faces)


def height_at(pts, x):
    for (xa, ha, _), (xb, hb, _) in zip(pts, pts[1:]):
        if xa <= x <= xb:
            return ha + (hb - ha) * (x - xa) / (xb - xa)
    return 0.0


def snow(pts, min_height, depth):
    """Small jagged snow caps on the tallest summits."""
    caps = []
    for x, h, kind in pts:
        if kind != "summit" or h < min_height:
            continue
        limit = h - depth
        xl = x
        while height_at(pts, xl - 1) > limit:
            xl -= 1
        xr = x
        while height_at(pts, xr + 1) > limit:
            xr += 1
        top = [(xl, limit)] + [(px, ph) for px, ph, _ in pts if xl < px < xr] + [(xr, limit)]
        n = 4
        edge = [(xr - (xr - xl) * i / n, limit + (6 if i % 2 else -5)) for i in range(1, n)]
        caps.append("M" + " L".join(f"{px:.0f},{H - ph:.0f}" for px, ph in top + edge) + " Z")
    return "".join(caps)


FAR, rf = make_range(3, (180, 300), (265, 375), (0.38, 0.58))
MID, rm = make_range(11, (220, 320), (185, 260), (0.4, 0.56))
NEAR, rn = make_range(5, (330, 460), (95, 140), (0.45, 0.65))
FAR = detail(FAR, rf, 14)
MID = detail(MID, rm, 12)
NEAR = detail(NEAR, rn, 8)


def gradient(name):
    return (f'<linearGradient id="am-{name}" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="0" y2="{H}">'
            f'<stop offset="0" class="am-{name}-top"/><stop offset="1" class="am-{name}-base"/>'
            f'</linearGradient>')


svg = "\n".join([
    f'<svg class="about-mountains" viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMax meet" aria-hidden="true" focusable="false">',
    f'<defs>{gradient("far")}{gradient("mid")}{gradient("near")}{gradient("shade")}</defs>',
    f'<path class="am-far" d="{to_path(FAR)}"/>',
    f'<path class="am-snow" d="{snow(FAR, 320, 30)}"/>',
    f'<path class="am-shade" d="{shadows(FAR)}"/>',
    f'<path class="am-mid" d="{to_path(MID)}"/>',
    f'<path class="am-shade" d="{shadows(MID)}"/>',
    f'<path class="am-near" d="{to_path(NEAR)}"/>',
    '</svg>',
])

index = pathlib.Path(__file__).resolve().parent.parent / "index.html"
html = index.read_text(encoding="utf-8")
start = html.index('<svg class="about-mountains"')
end = html.index("</svg>", start) + len("</svg>")
indented = "\n".join(("      " + line) if i else line for i, line in enumerate(svg.split("\n")))
index.write_text(html[:start] + indented + html[end:], encoding="utf-8")
print(f"index.html updated ({len(svg)} bytes of SVG)")
