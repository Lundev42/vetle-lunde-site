// Render the hand-off SVG (dolomites_background.svg) to tools/about-scene-labels.png
// for tools/about-scene.py: 2752 x 1536 px (twice the original picture), no
// anti-aliasing, so every pixel holds exactly one of the SVG's flat colours.
//
//   node tools/about-scene-render.js path/to/dolomites_background.svg /tmp/labels-rgb.png
//   python3 -c "import numpy as np; from PIL import Image; \
//     a = np.array(Image.open('/tmp/labels-rgb.png').convert('RGB')); \
//     c, i = np.unique(a.reshape(-1, 3), axis=0, return_inverse=True); \
//     p = Image.fromarray(i.reshape(a.shape[:2]).astype(np.uint8), 'P'); \
//     p.putpalette(c.astype(np.uint8).ravel().tolist()); p.save('tools/about-scene-labels.png', optimize=True)"
//
// Needs Playwright with Chromium. The SVG's picture sits at x 0.0335..728.17,
// y 26.42..432.82 of its own viewBox.
const { chromium } = require("playwright");
const fs = require("fs");

(async () => {
  const [file, out] = process.argv.slice(2);
  const W = 1376 * 2, H = 768 * 2;
  let svg = fs.readFileSync(file, "utf8");
  svg = svg.replace(/<svg([\s\S]*?)width="[^"]*"([\s\S]*?)height="[^"]*"([\s\S]*?)viewBox="[^"]*"/,
    `<svg$1width="${W}"$2height="${H}"$3viewBox="0.0335 26.4231 728.1334 406.4" preserveAspectRatio="none" shape-rendering="crispEdges"`);
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: W, height: H } });
  await page.setContent(`<!doctype html><style>html,body{margin:0}svg{display:block}</style>${svg}`);
  await page.waitForTimeout(800);
  await page.screenshot({ path: out });
  await browser.close();
})();
