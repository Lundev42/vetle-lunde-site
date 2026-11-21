// @ts-check
// Regression tests for the site-wide audit: layout overflow, console/CSP
// errors, broken links/assets, mobile menu, lightbox, no-JS fallback and SEO files.
const { test, expect } = require("@playwright/test");

const PAGES = [
  "/index.html",
  "/bacheloroppgave.html",
  "/conocophillips-2024.html",
  "/conocophillips-2025.html",
  "/starsteer.html",
];

test.describe("Layout: no horizontal overflow", () => {
  for (const width of [320, 375, 768, 1024, 1440]) {
    for (const path of PAGES) {
      test(`${path} at ${width}px`, async ({ page }) => {
        await page.setViewportSize({ width, height: 800 });
        await page.goto(path);
        const overflow = await page.evaluate(
          () => document.documentElement.scrollWidth - document.documentElement.clientWidth
        );
        expect(overflow).toBeLessThanOrEqual(0);
      });
    }
  }
});

test.describe("No console errors or CSP violations", () => {
  for (const path of PAGES.concat(["/404.html"])) {
    test(path, async ({ page }) => {
      const errors = [];
      page.on("console", (msg) => { if (msg.type() === "error") errors.push(msg.text()); });
      page.on("pageerror", (err) => errors.push(err.message));
      await page.goto(path, { waitUntil: "networkidle" });
      if (await page.locator(".lang-toggle").count()) await page.click(".lang-toggle");
      if (await page.locator("#theme-toggle").count()) await page.click("#theme-toggle");
      expect(errors).toEqual([]);
    });
  }
});

test.describe("Links and assets", () => {
  test("every internal link, image and stylesheet resolves", async ({ page, request }) => {
    const urls = new Set();
    for (const path of PAGES) {
      await page.goto(path);
      const found = await page.evaluate(() => {
        const out = [];
        document.querySelectorAll("a[href], img[src], link[href], script[src], [data-full]").forEach((el) => {
          const raw = el.getAttribute("href") || el.getAttribute("src") || el.getAttribute("data-full");
          if (!raw || raw.startsWith("data:") || raw.startsWith("mailto:")) return;
          const url = new URL(raw, location.href);
          if (url.origin === location.origin) out.push(url.pathname);
        });
        // background images in CSS (hero)
        document.querySelectorAll("section").forEach((el) => {
          const m = getComputedStyle(el).backgroundImage.match(/url\("(.+?)"\)/);
          if (m) out.push(new URL(m[1]).pathname);
        });
        return out;
      });
      found.forEach((u) => urls.add(u));
    }
    for (const u of urls) {
      const res = await request.get(u);
      expect(res.status(), u).toBe(200);
    }
  });

  test("in-page anchors point at existing ids", async ({ page }) => {
    for (const path of PAGES) {
      await page.goto(path);
      const missing = await page.evaluate(() =>
        Array.from(document.querySelectorAll('a[href^="#"]'))
          .map((a) => a.getAttribute("href").slice(1))
          .filter((id) => id && !document.getElementById(id))
      );
      expect(missing, path).toEqual([]);
    }
  });

  test("links that open a new tab use rel=noopener noreferrer", async ({ page }) => {
    for (const path of PAGES) {
      await page.goto(path);
      await page.click(".lang-toggle"); // English strings contain links too
      const bad = await page.evaluate(() =>
        Array.from(document.querySelectorAll('a[target="_blank"]'))
          .filter((a) => !/noopener/.test(a.rel) || !/noreferrer/.test(a.rel))
          .map((a) => a.href)
      );
      expect(bad, path).toEqual([]);
    }
  });

  test("no third-party requests are made", async ({ page }) => {
    const external = [];
    page.on("request", (req) => {
      const url = new URL(req.url());
      if (!["127.0.0.1", "localhost"].includes(url.hostname) && url.protocol !== "data:") external.push(req.url());
    });
    for (const path of PAGES) await page.goto(path, { waitUntil: "networkidle" });
    expect(external).toEqual([]);
  });
});

test.describe("Mobile navigation", () => {
  for (const path of PAGES) {
    test(`hamburger menu works on ${path}`, async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 740 });
      await page.goto(path);
      const burger = page.locator("#hamburger");
      const menu = page.locator("#nav-menu");
      await expect(burger).toBeVisible();
      await expect(menu).toBeHidden();
      await burger.click();
      await expect(burger).toHaveAttribute("aria-expanded", "true");
      await expect(menu.locator('a[data-i18n="nav.contact"]')).toBeVisible();
      await page.keyboard.press("Escape");
      await expect(burger).toHaveAttribute("aria-expanded", "false");
      await expect(burger).toBeFocused();
    });
  }
});

test.describe("Lightbox", () => {
  test("opens from keyboard, closes with Escape and returns focus", async ({ page }) => {
    await page.goto("/index.html");
    const thumb = page.locator(".about-sub-gallery .gallery-thumb").first();
    await thumb.focus();
    await page.keyboard.press("Enter");
    const dialog = page.locator("#lightbox");
    await expect(dialog).toBeVisible();
    await expect(page.locator("#lightbox-img")).toHaveAttribute("src", /dumdalsgrottene/);
    await expect(page.locator("#lightbox-caption")).toContainText("Dumdalsgrottene");
    await expect(page.locator(".lightbox-close")).toBeFocused();
    await page.keyboard.press("Escape");
    await expect(dialog).toBeHidden();
    await expect(thumb).toBeFocused();
  });

  test("close button and backdrop click close the viewer", async ({ page }) => {
    await page.goto("/index.html");
    const thumb = page.locator(".about-sub-gallery .gallery-thumb").nth(1);
    await thumb.click();
    await page.locator(".lightbox-close").click();
    await expect(page.locator("#lightbox")).toBeHidden();
    await thumb.click();
    await page.mouse.click(5, 5);
    await expect(page.locator("#lightbox")).toBeHidden();
  });

  test("labels are translated", async ({ page }) => {
    await page.goto("/index.html");
    await page.click(".lang-toggle");
    await expect(page.locator(".lightbox-close")).toHaveAttribute("aria-label", "Close");
  });
});

test.describe("Robustness", () => {
  test("content is visible without JavaScript", async ({ browser }) => {
    const ctx = await browser.newContext({ javaScriptEnabled: false });
    const page = await ctx.newPage();
    await page.goto("/index.html");
    await expect(page.locator("#hjem")).toHaveCSS("opacity", "1");
    await expect(page.locator("#om-meg .section-inner")).toHaveCSS("opacity", "1");
    await ctx.close();
  });

  test("system theme is not stored until the visitor chooses", async ({ page }) => {
    await page.emulateMedia({ colorScheme: "light" });
    await page.goto("/index.html");
    await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
    expect(await page.evaluate(() => localStorage.getItem("theme"))).toBeNull();
    await page.click("#theme-toggle");
    expect(await page.evaluate(() => localStorage.getItem("theme"))).toBe("dark");
  });

  test("saved English is applied on other pages", async ({ page }) => {
    await page.goto("/index.html");
    await page.click(".lang-toggle");
    await page.goto("/bacheloroppgave.html");
    await expect(page.locator("html")).toHaveAttribute("lang", "en");
    await expect(page).toHaveTitle("Bachelor Thesis – Vetle Lunde");
  });
});

test.describe("SEO files", () => {
  test("robots.txt and sitemap.xml exist and list every page", async ({ request }) => {
    const robots = await request.get("/robots.txt");
    expect(robots.status()).toBe(200);
    expect(await robots.text()).toContain("sitemap.xml");
    const sitemap = await (await request.get("/sitemap.xml")).text();
    for (const path of PAGES) {
      const loc = path === "/index.html" ? "/vetle-lunde-site/</loc>" : "/vetle-lunde-site" + path + "</loc>";
      expect(sitemap).toContain(loc);
    }
  });

  test("each page has a unique title and one h1", async ({ page }) => {
    const titles = new Set();
    for (const path of PAGES) {
      await page.goto(path);
      titles.add(await page.title());
      await expect(page.locator("h1"), path).toHaveCount(1);
    }
    expect(titles.size).toBe(PAGES.length);
  });

  test("404 page renders with working links from a nested path", async ({ page }) => {
    await page.goto("/vetle-lunde-site/some/missing/page");
    await expect(page.locator("h1")).toHaveText("Fant ikke siden");
    await expect(page.locator("body")).toHaveCSS("background-color", /rgb/);
    const home = await page.locator(".home-link").evaluate((a) => a.href);
    expect(home).toMatch(/\/vetle-lunde-site\/index\.html$/);
  });
});
