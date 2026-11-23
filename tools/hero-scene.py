"""Generate the geological hero scene (inline SVG) on the front page.

Usage (from the repository root):  python3 tools/hero-scene.py
Rewrites the <svg class="hero-scene"> element inside index.html in place.
Colours are not set here; they live in index.html's CSS (one palette per theme).

A cross-section through a mountain range: folded, layered rocks are cut by the
present-day topography (so every layer continues across the valley), an angular
unconformity near the base separates them from older, steeply tilted strata,
there is a cirque glacier, snow on some peaks and a few huts.

The viewBox is 2400x900, but the land continues 1500 units beyond each side so
wide screens (preserveAspectRatio="xMidYMax meet" on a wider element) never
show an empty edge. All colours come from CSS so the scene follows the theme.
"""
import math
import pathlib
import re

W, H = 2400, 900
X0, X1 = -1500, 3900   # drawn extent

SURFACE = [
    # left extension (lower hills)
    (-1500, 520), (-1380, 480), (-1260, 445), (-1160, 462), (-1040, 420), (-940, 380),
    (-860, 360), (-780, 392), (-680, 430), (-580, 455), (-480, 418), (-400, 392),
    (-320, 412), (-220, 448), (-120, 476),
    # main range
    (0, 470), (40, 455), (100, 430), (170, 385), (230, 345), (270, 360),
    (330, 395), (390, 420), (440, 390), (500, 340), (560, 300),          # P2
    (600, 322), (640, 350), (680, 372), (720, 381), (750, 372),          # shoulder (hut)
    (790, 340), (830, 310),                                               # P3
    (880, 365), (925, 440), (965, 520), (1005, 590), (1045, 645),
    (1090, 685), (1140, 701), (1200, 706), (1260, 705), (1300, 698),     # valley floor
    (1335, 682), (1375, 650), (1415, 590), (1450, 520), (1485, 445),
    (1515, 385), (1535, 345),                                             # P4
    (1560, 372), (1585, 405), (1610, 432), (1635, 445), (1660, 440),     # cirque
    (1685, 420), (1705, 385), (1725, 330), (1740, 285),                  # P5
    (1780, 312), (1820, 345), (1860, 372), (1900, 380), (1940, 368),
    (1990, 345), (2060, 318),                                             # P6
    (2120, 352), (2180, 392), (2240, 415), (2300, 404), (2350, 425), (2400, 445),
    # right extension
    (2480, 422), (2560, 384), (2640, 350), (2720, 378), (2800, 412), (2900, 440),
    (3000, 408), (3080, 376), (3160, 398), (3280, 446), (3400, 428), (3520, 462),
    (3640, 440), (3760, 470), (3900, 488),
]

FAR = [
    (-1500, 590), (-1300, 560), (-1100, 600), (-900, 565), (-700, 595), (-500, 570),
    (-300, 600), (-120, 572),
    (0, 560), (120, 530), (260, 575), (420, 540), (600, 585), (760, 560),
    (900, 600), (1010, 585), (1090, 600), (1150, 578), (1205, 596), (1255, 570),
    (1320, 598), (1400, 582), (1520, 610), (1700, 575), (1900, 600), (2100, 560),
    (2250, 590), (2400, 565), (2600, 600), (2800, 568), (3000, 598), (3200, 562),
    (3400, 596), (3650, 570), (3900, 600),
]


def surface_y(x, pts=SURFACE):
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x0 <= x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return pts[-1][1]


def fold(x):
    """Upward offset shared by every layer above the unconformity."""
    regional = 52 * math.cos(2 * math.pi * (x - 560) / 1300)   # anticlines under P2 and P5/P6
    tight = 38 * math.sin(2 * math.pi * (x - 1520) / 210) * math.exp(-((x - 1520) / 150) ** 2)  # tight fold in P4
    return regional + tight


UNCONFORMITY = 800
BOUNDARIES = [410, 490, 565, 650, 720]   # tops of t1..t5 (t5 = basal conglomerate)


def xs(step):
    out = list(range(X0, X1 + 1, step))
    # extra samples through the tight fold
    out += [x for x in range(1300, 1760, 6) if x % step]
    return sorted(set(out))


def boundary(c):
    return [(x, c - fold(x)) for x in xs(20)]


def unconformity():
    return [(x, UNCONFORMITY - fold(x) + 5 * math.sin(x / 31) + 3 * math.sin(x / 13 + 1)) for x in xs(12)]


def fmt(points):
    return " ".join(f"{x:.0f},{y:.0f}" for x, y in points)


def below(points):
    return f"M{fmt(points)} L{X1},{H + 20} L{X0},{H + 20} Z"


def snowcap(apex_x, depth, jag=7):
    apex_y = surface_y(apex_x)
    limit = apex_y + depth
    left = apex_x
    while surface_y(left) < limit:
        left -= 1
    right = apex_x
    while surface_y(right) < limit:
        right += 1
    top = [(left, surface_y(left))] + [(x, y) for x, y in SURFACE if left < x < right] + [(right, surface_y(right))]
    n = max(3, (right - left) // 16)
    edge = []
    for i in range(1, n):
        x = right - (right - left) * i / n
        edge.append((x, limit + (-jag if i % 2 else jag * 0.6)))
    return "M" + fmt(top + edge) + "Z"


def hut(x, scale=1.0):
    y = surface_y(x) + 1
    w, h, r = 26 * scale, 15 * scale, 11 * scale
    left, right = x - w / 2, x + w / 2
    door_w, win = 6 * scale, 5 * scale
    f = lambda v: f"{v:.1f}".rstrip("0").rstrip(".")
    return (
        f'<g class="hut">'
        f'<rect class="hut-wall" x="{f(left)}" y="{f(y - h)}" width="{f(w)}" height="{f(h)}"/>'
        f'<path class="hut-roof" d="M{f(left - 3 * scale)},{f(y - h + 1)}L{f(x)},{f(y - h - r)}L{f(right + 3 * scale)},{f(y - h + 1)}Z"/>'
        f'<rect class="hut-window" x="{f(left + 4 * scale)}" y="{f(y - h + 4 * scale)}" width="{f(win)}" height="{f(win)}"/>'
        f'<rect class="hut-door" x="{f(right - 5 * scale - door_w)}" y="{f(y - 9 * scale)}" width="{f(door_w)}" height="{f(9 * scale)}"/>'
        f'</g>'
    )


ICE = [(1572, 388), (1600, 401), (1630, 407), (1660, 402), (1688, 390), (1706, 381),
       (1705, 385), (1685, 420), (1660, 440), (1635, 445), (1610, 432), (1585, 405), (1572, 390)]

land = "M" + fmt(SURFACE) + f" L{X1},{H + 20} L{X0},{H + 20} Z"
layers = "".join(f'<path class="geo-t{i}" d="{below(boundary(c))}"/>' for i, c in enumerate(BOUNDARIES, 1))

svg = f'''<svg class="hero-scene" viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMax meet" aria-hidden="true" focusable="false">
<defs>
<clipPath id="geo-land"><path d="{land}"/></clipPath>
<pattern id="geo-conglomerate" width="34" height="22" patternUnits="userSpaceOnUse">
<rect class="geo-t5-bg" width="34" height="22"/>
<circle class="geo-pebble" cx="6" cy="6" r="2.6"/><circle class="geo-pebble" cx="23" cy="15" r="2"/><circle class="geo-pebble" cx="30" cy="4" r="1.5"/>
</pattern>
<pattern id="geo-old-strata" width="26" height="26" patternUnits="userSpaceOnUse" patternTransform="rotate(64)">
<rect class="geo-old-a" width="26" height="26"/><rect class="geo-old-b" width="10" height="26"/>
</pattern>
</defs>
<path class="geo-far" d="M{fmt(FAR)} L{X1},{H + 20} L{X0},{H + 20} Z"/>
<g clip-path="url(#geo-land)">
<rect class="geo-t0" x="{X0}" y="0" width="{X1 - X0}" height="{H + 20}"/>
{layers}
<path class="geo-basement" d="{below(unconformity())}"/>
<path class="geo-snow" d="{snowcap(560, 34)}"/>
<path class="geo-snow" d="{snowcap(830, 22)}"/>
<path class="geo-snow" d="{snowcap(1740, 40)}"/>
<path class="geo-snow" d="{snowcap(2060, 24)}"/>
<path class="geo-snow" d="{snowcap(-860, 18)}"/>
<path class="geo-snow" d="{snowcap(2640, 18)}"/>
</g>
<path class="geo-ice" d="M{fmt(ICE)}Z"/>
<path class="geo-crevasse" d="M1612,410l10,14M1640,412l4,16M1668,406l-4,15"/>
<path class="geo-surface" d="M{fmt(SURFACE)}"/>
{hut(720, 1.05)}{hut(1165, 1.3)}{hut(1228, 1.15)}
</svg>'''

index = pathlib.Path(__file__).resolve().parent.parent / "index.html"
html = index.read_text(encoding="utf-8")
start = html.index('<svg class="hero-scene"')
end = html.index("</svg>", start) + len("</svg>")
indented = "\n".join(("      " + line) if i else line for i, line in enumerate(svg.split("\n")))
index.write_text(html[:start] + indented + html[end:], encoding="utf-8")
print(f"index.html updated ({len(svg)} bytes of SVG)")
