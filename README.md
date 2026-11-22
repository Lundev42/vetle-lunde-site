# vetle-lunde-site

Personal portfolio website showcasing geology studies and bachelor thesis work at Høgskulen på Vestlandet in Sogndal.

Live site: `https://Lundev42.github.io/vetle-lunde-site/`

## Structure

| Path | What it is |
| --- | --- |
| `index.html`, `bacheloroppgave.html`, `conocophillips-2024.html`, `conocophillips-2025.html`, `starsteer.html`, `geologi.html` | Pages. Page-specific styles live in each page's `<style>` block; Norwegian/English strings live in its `<script type="application/json" id="i18n-data">` block. |
| `404.html` | Not-found page served by GitHub Pages. |
| `assets/css/site.css` | Shared styles: fonts, colour tokens, navigation, toggles, footer, reveal animation. |
| `assets/css/subpage.css` | Layout for the secondary pages. |
| `assets/css/geology.css` | Extra styles for the geology introduction (`geologi.html`). |
| `assets/js/theme-init.js` | Runs in `<head>` before paint: applies saved/system theme. |
| `assets/js/site.js` | Shared behaviour: translations, theme toggle, mobile menu, nav highlighting, lightbox. |
| `assets/fonts/` | Self-hosted Inter and Courgette (SIL Open Font License). |
| `images/optimized/` | Resized WebP images used by the site (metadata stripped). |
| `images/` | Original photos. Kept in the repo but **not deployed** (several contain GPS data). |
| `robots.txt`, `sitemap.xml` | Search engine files. Add new pages to the sitemap. |

### Adding or changing images

Put the original in `images/`, then add a resized WebP copy (max ~2× the displayed width, EXIF stripped) to `images/optimized/` and reference that copy.

### Adding text

Every visible string needs both an `nb` and an `en` entry in the page's `i18n-data` block, referenced with `data-i18n="key"` (or `data-i18n-alt`, `data-i18n-aria-label`). `data-i18n-html` is for trusted, hand-written markup only.

## Security

Each page sets a Content-Security-Policy `<meta>` tag (`script-src 'self'`), so do not add inline `<script>` code or `onclick=` attributes; put behaviour in `assets/js/site.js`. GitHub Pages cannot send custom HTTP headers, so headers such as `frame-ancestors`, HSTS preload or `Permissions-Policy` are not available without putting a proxy/CDN (e.g. Cloudflare) in front of the site.

## Testing

```bash
npm install
npx playwright install chromium   # or use Microsoft Edge locally
npx playwright test
```

The tests start a small local server (`tests/serve.js`) and run against `http://127.0.0.1:4173`.

## Deployment

`.github/workflows/deploy.yml` deploys on every push to `main`. It copies only the public files (pages, `assets/`, `images/optimized/`, `images/og-image.jpg`, robots/sitemap) into `_site/` and publishes that.
