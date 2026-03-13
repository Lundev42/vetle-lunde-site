# vetle-lunde-site

Personal portfolio website showcasing geology studies and bachelor thesis work at Høgskulen på Vestlandet in Sogndal.

## Deployment

The site is automatically deployed to GitHub Pages on every push to `main` via the included GitHub Actions workflow.

The live site is available at: `https://Lundev42.github.io/vetle-lunde-site/`

## Repository Rename

This repository was renamed from `website_builder` to `vetle-lunde-site`. The rename does **not** break the website because:

- The GitHub Pages deployment workflow uses standard actions with no hardcoded repository name.
- All links in the site are relative — no absolute URLs reference the repository name.
- GitHub automatically redirects the old repository URL to the new one.
