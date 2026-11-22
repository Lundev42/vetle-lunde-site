# Copilot Instructions – vetle-lunde-site

## Project Overview

This is a **static portfolio website** for Vetle Øyvind Larsen Lunde, showcasing geology studies and bachelor thesis work at Høgskulen på Vestlandet in Sogndal.

- **Stack**: Vanilla HTML, CSS, and JavaScript — no frameworks or build tools
- **Languages**: Bilingual — Norwegian Bokmål (`nb`) and English (`en`) with inline i18n
- **Testing**: Playwright end-to-end tests
- **Deployment**: GitHub Pages via GitHub Actions (push to `main`)
- **Live site**: `https://Lundev42.github.io/vetle-lunde-site/`

## Repository Structure & Conventions

Layout in short:
- Pages are plain HTML files in the repo root. Shared styles are in `assets/css/site.css` (+ `subpage.css`), shared behaviour in `assets/js/site.js`, and the pre-paint theme script in `assets/js/theme-init.js`.
- Page-specific CSS stays in the page's `<style>` block.
- Fonts (Inter, Source Serif 4) are self-hosted in `assets/fonts/`; do not add Google Fonts or CDN links.
- JavaScript is plain ES5-compatible (no modules, no transpilation, no libraries).
- Design: quiet editorial look. Colour tokens live in `assets/css/site.css` (warm neutrals, one iron-oxide accent); use hairline rules, not tinted cards, pills, gradients or glows.

### Content-Security-Policy
- Every page has a CSP `<meta>` with `script-src 'self'`: never add inline `<script>` code or inline event handlers (`onclick=` etc.).

### Internationalisation (i18n)
- Translations are stored as JSON in `<script type="application/json" id="i18n-data">` with `nb` and `en` keys
- HTML elements use `data-i18n`, `data-i18n-html`, `data-i18n-alt` and `data-i18n-aria-label` attributes
- `data-i18n-html` is only for trusted, hand-written markup
- Language and theme preference are saved to `localStorage`; default language is Norwegian Bokmål (`nb`)
- All user-facing text **must** have both `nb` and `en` translations

### Images
- Originals live in `images/` and are not deployed. The site uses resized, metadata-free WebP copies in `images/optimized/`.

## Testing

- **Framework**: Playwright (`npx playwright test`)
- **Config**: `playwright.config.js` — Chromium only, served over http by `tests/serve.js`
- **Tests**: `tests/site.spec.js` (content/feature tests) and `tests/audit.spec.js` (overflow, console/CSP errors, links, mobile menu, lightbox, SEO files). `site.spec.js` covers:
  - Bacheloroppgave section images and captions
  - Hero section background, overlay, and CTA button
  - i18n language switching (title, alt text, toggle label)
  - Norwegian Bokmål correctness (no Nynorsk words)

### Running Tests
```bash
npm install
npx playwright install chromium
npx playwright test
```

## Deployment

The site deploys automatically to GitHub Pages on push to `main` via `.github/workflows/deploy.yml`. No build step is needed; the workflow copies only the public files into `_site/` and uploads that.

## Important Rules

1. **Keep it static** — do not add build tools, frameworks, or bundlers
2. **Bilingual always** — every text change must update both `nb` and `en` translations
3. **Test before merging** — all Playwright tests must pass
4. **Accessibility** — use semantic HTML, alt text for images, and keyboard-navigable links
5. **Performance** — optimise image sizes; keep the page lightweight
6. **No Nynorsk** — Norwegian text must be Bokmål only
