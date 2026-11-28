#!/usr/bin/env python3
"""Draw the geological cross-section between About me and Bakgrunn.

The Dolomites picture ends at the bottom of About me. Bakgrunn starts with a
cut straight down through that ground: a dark band of topsoil, then the
Dolomites' own rocks, gently folded and broken by one normal fault, cut off
flat by the soil (an angular unconformity). Top to bottom:

  * Sciliar dolomite: pale reef rock with a few vertical joints
  * Wengen beds: dark volcanic sand and shale
  * Werfen beds: thin red and grey-green layers, with a small ammonite
  * Bellerophon beds: dark grey with white gypsum lenses
  * Val Gardena sandstone: red
  * Bolzano porphyry: dark purple-red lava

The section fades into the page colour as it goes down, so Bakgrunn's text
stands on the plain background. Devon keeps the colours below; the other
periods map them with the same rule as the About picture (theme_colour in
tools/about-scene.py), so the rocks match each period's picture.

Run from the repo root:  python3 tools/strata.py
It rewrites the <svg class="strata"> element and the CSS between the
strata-tones markers in index.html.
"""
import importlib.util
import re

import numpy as np

HTML = "index.html"
W, HB = 5250, 700          # the About picture's width in its units; band height

_spec = importlib.util.spec_from_file_location("about_scene", "tools/about-scene.py")
_scene = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_scene)
THEMES = ["cretaceous", "hadean", "cambrian", "devonian", "quaternary"]   # first = default

# Devon colours of the cut face (in shade, so darker than the sunlit picture)
TONES = {
    "soil": "#2b2117",
    "soil2": "#3a2e1f",      # the lighter root zone at the soil's foot
    "dolo": "#7d6d57",
    "dolo2": "#66584a",      # joints
    "dolo3": "#8a7a62",      # a lighter top to each dolomite bank
    "weng": "#3f382f",
    "werr": "#76412f",
    "werg": "#5c5946",
    "bell": "#463d36",
    "gyps": "#8d8576",
    "gard": "#7f4430",
    "porf": "#55303a",
    "fault": "#33291f",
    "ammo": "#9a6a4c",
}

# beds from the top: (tone, thickness)
BEDS = [("dolo", 175), ("weng", 70), ("werr", 26), ("werg", 22), ("werr", 30), ("werg", 20),
        ("werr", 26), ("bell", 66), ("gard", 92), ("porf", 400)]
TOP0 = -40                 # top of the dolomite where the folds are level
FAULT_X, FAULT_K, FAULT_D = 3480, 0.42, 48   # foot at the surface, lean per unit depth, throw


def fold(x):
    """The beds' bend: a broad anticline under Tre Cime, smaller waves."""
    return (62 * np.sin(2 * np.pi * x / 2900 + 2.2) + 18 * np.sin(2 * np.pi * x / 880 + 0.6)
            + 7 * np.sin(2 * np.pi * x / 310 + 1.9))


def surface(top, xs):
    """A bed's top along xs, dropped by the fault's throw east of the fault."""
    y0 = top + fold(xs)
    y1 = y0 + FAULT_D
    hanging = xs > FAULT_X + FAULT_K * y1
    return np.where(hanging, y1, y0)


def fmt(v):
    return str(int(round(v)))


def poly(pts):
    return "M" + " ".join(f"{fmt(x)} {fmt(y)}" for x, y in pts) + "z"


def build():
    xs = np.arange(-40, W + 41, 15.0)
    # where the fault crosses the section, the surfaces step: add points
    # exactly on both sides of it
    out = []
    tops = [TOP0]
    for _, t in BEDS[:-1]:
        tops.append(tops[-1] + t)
    for (tone, _), top in zip(BEDS, tops):
        ys = surface(top, xs)
        # the top bed reaches up to the soil wherever the folds dip below it
        pts = (list(zip(xs, np.minimum(ys, -10))) if top == TOP0 else list(zip(xs, ys))) \
            + [(W + 40, HB + 40), (-40, HB + 40)]
        out.append(f'<path class="{tone}" d="{poly(pts)}"/>')
        if tone == "dolo":
            # each bank of dolomite has a lighter top
            ys2 = surface(top + 40, xs)
            pts = list(zip(xs, ys)) + list(zip(xs[::-1], ys2[::-1]))
            out.append(f'<path class="dolo3" d="{poly(pts)}"/>')
            # vertical joints in the dolomite
            rng = np.random.default_rng(7)
            x = 60.0
            while x < W:
                y_top = float(surface(top, np.array([x]))[0])
                y_bot = float(surface(top + 175, np.array([x]))[0])
                lean = rng.uniform(-6, 6)
                h0 = y_top + rng.uniform(10, 40)
                h1 = y_bot - rng.uniform(0, 30)
                if h1 - h0 > 40 and abs(x - FAULT_X - FAULT_K * 120) > 90:
                    out.append(f'<path class="dolo2" d="{poly([(x, h0), (x + 5, h0), (x + 5 + lean, h1), (x + lean, h1)])}"/>')
                x += rng.uniform(110, 260)
        if tone == "bell":
            rng = np.random.default_rng(3)
            x = 140.0
            while x < W:
                yc = float(surface(top + 33, np.array([x]))[0])
                L, T = rng.uniform(50, 110), rng.uniform(7, 12)
                if abs(x - FAULT_X - FAULT_K * yc) > 80:
                    out.append(f'<path class="gyps" d="M{fmt(x - L)} {fmt(yc)}Q{fmt(x)} {fmt(yc - T)} {fmt(x + L)} {fmt(yc)}Q{fmt(x)} {fmt(yc + T)} {fmt(x - L)} {fmt(yc)}z"/>')
                x += rng.uniform(260, 520)

    # a small ammonite in the second red Werfen bed
    ax = 1530.0
    ay = float(surface(tops[4] + 15, np.array([ax]))[0])
    r = 13
    spiral = []
    for t in np.linspace(0, 4 * np.pi, 60):
        rr = r * (0.14 + 0.86 * t / (4 * np.pi))
        spiral.append((ax + rr * np.cos(t), ay + rr * np.sin(t)))
    out.append(f'<circle class="ammo" cx="{fmt(ax)}" cy="{fmt(ay)}" r="{r + 2}"/>')
    out.append('<path class="weng-line" d="M' + " ".join(f"{x:.1f} {y:.1f}" for x, y in spiral) + '"/>')

    # the fault: a dark line from the surface down
    y_end = HB + 40
    out.append(f'<path class="fault" d="{poly([(FAULT_X - 3, -10), (FAULT_X + 3, -10), (FAULT_X + 3 + FAULT_K * y_end, y_end), (FAULT_X - 3 + FAULT_K * y_end, y_end)])}"/>')

    # topsoil, cut flat at the top; its foot is uneven with a lighter root zone
    foot = 30 + 6 * np.sin(xs / 37) + 5 * np.sin(xs / 113 + 1)
    pts = [(-40, -10), (W + 40, -10)] + list(zip(xs[::-1], foot[::-1] + 9))
    out.append(f'<path class="soil2" d="{poly(pts)}"/>')
    pts = [(-40, -10), (W + 40, -10)] + list(zip(xs[::-1], foot[::-1]))
    out.append(f'<path class="soil" d="{poly(pts)}"/>')

    # fade into the page
    out.append('<rect class="fade" x="-40" y="0" width="5330" height="740" fill="url(#strata-fade)"/>')
    defs = ('<defs><linearGradient id="strata-fade" x1="0" y1="0" x2="0" y2="1">'
            '<stop offset="0.3" class="fade-0"/><stop offset="0.62" class="fade-1"/>'
            '<stop offset="0.95" class="fade-2"/></linearGradient></defs>')
    return ('<svg class="strata" viewBox="0 0 5250 700" preserveAspectRatio="xMidYMin slice" '
            'aria-hidden="true" focusable="false">' + defs + "".join(out) + "</svg>")


def css():
    names = list(TONES)
    blocks = []
    for i, th in enumerate(THEMES):
        sel = "#bakgrunn" if i == 0 else f'[data-theme="{th}"] #bakgrunn'
        vals = "; ".join(f"--st-{n}: {_scene.theme_colour(th, TONES[n])}" for n in names)
        blocks.append(f"    {sel} {{ {vals}; }}")
    rules = [f"    .strata .{n} {{ fill: var(--st-{n}); }}" for n in names]
    rules.append("    .strata .weng-line { fill: none; stroke: var(--st-soil); stroke-width: 3; }")
    rules.append("    .strata .fade-0 { stop-color: var(--bg-primary); stop-opacity: 0; }")
    rules.append("    .strata .fade-1 { stop-color: var(--bg-primary); stop-opacity: 0.72; }")
    rules.append("    .strata .fade-2 { stop-color: var(--bg-primary); stop-opacity: 1; }")
    return "\n".join(blocks + rules)


def main():
    html = open(HTML, encoding="utf-8").read()
    svg = build()
    html, n = re.subn(r'<svg class="strata".*?</svg>', lambda m: svg, html, flags=re.S)
    assert n == 1, "no <svg class=\"strata\"> in index.html"
    html, n = re.subn(r"(/\* strata-tones:start \*/\n).*?(    /\* strata-tones:end \*/)",
                      lambda m: m.group(1) + css() + "\n" + m.group(2), html, flags=re.S)
    assert n == 1, "no strata-tones markers in index.html"
    open(HTML, "w", encoding="utf-8").write(html)
    print(f"{svg.count('<path') + svg.count('<circle')} shapes, {len(svg) // 1024} KB")


if __name__ == "__main__":
    main()
