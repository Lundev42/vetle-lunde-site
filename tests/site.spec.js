// @ts-check
const { test, expect } = require("@playwright/test");

// Paths are resolved against baseURL (see playwright.config.js)
const PAGE_URL = "/index.html";
const BACHELOR_URL = "/bacheloroppgave.html";
const STARSTEER_URL = "/starsteer.html";
const COP2025_URL = "/conocophillips-2025.html";
const COP2024_URL = "/conocophillips-2024.html";

test.describe("Bacheloroppgave section", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(BACHELOR_URL);
  });

  test("has two images in the bachelor gallery", async ({ page }) => {
    const images = page.locator("#bachelor .gallery-grid img");
    await expect(images).toHaveCount(2);
  });

  test("bachelor images use local sources", async ({ page }) => {
    const images = page.locator("#bachelor .gallery-grid img");
    const src1 = await images.nth(0).getAttribute("src");
    const src2 = await images.nth(1).getAttribute("src");
    // Optimised WebP copies of IMG_3906.JPG and IMG_7509.jpeg
    expect(src1).toContain("images/optimized/bachelor-trondelag");
    expect(src2).toContain("images/optimized/bachelor-fjellsider");
  });

  test("first image has caption 'Den vakre naturen i Trøndelag'", async ({ page }) => {
    const caption = page.locator("#bachelor .gallery-grid figure:nth-child(1) figcaption");
    await expect(caption).toHaveText("Den vakre naturen i Trøndelag");
  });

  test("second image has caption 'Bratte fjellsider'", async ({ page }) => {
    const caption = page.locator("#bachelor .gallery-grid figure:nth-child(2) figcaption");
    await expect(caption).toHaveText("Bratte fjellsider");
  });
});

test.describe("Hero section", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(PAGE_URL);
  });

  test("shows the geological mountain scene instead of a photo", async ({ page }) => {
    const scene = page.locator("#hjem svg.hero-scene");
    await expect(scene).toBeVisible();
    await expect(scene).toHaveAttribute("aria-hidden", "true");
    const bg = await page.locator("#hjem").evaluate((el) => getComputedStyle(el).backgroundImage);
    expect(bg).toContain("linear-gradient");
    expect(bg).not.toContain("url(");
  });

  test("scene has layered rocks, an unconformity, snow, a glacier and huts", async ({ page }) => {
    const scene = page.locator("#hjem svg.hero-scene");
    for (const layer of ["geo-t0", "geo-t1", "geo-t2", "geo-t3", "geo-t4", "geo-t5"]) {
      await expect(scene.locator("." + layer)).toHaveCount(1);
    }
    await expect(scene.locator(".geo-basement")).toHaveCount(1);
    expect(await scene.locator(".geo-snow").count()).toBeGreaterThanOrEqual(3);
    await expect(scene.locator(".geo-ice")).toHaveCount(1);
    expect(await scene.locator(".hut").count()).toBeGreaterThanOrEqual(2);
    // The unconformity is drawn as a visible line on top of the old basement rocks
    const stroke = await scene.locator(".geo-basement").evaluate((el) => getComputedStyle(el).strokeWidth);
    expect(parseFloat(stroke)).toBeGreaterThan(0);
  });

  test("has no photo caption", async ({ page }) => {
    await expect(page.locator("#hjem .hero-caption")).toHaveCount(0);
    await expect(page.locator("#hjem")).not.toContainText("Galdhøgpiggen");
  });

  for (const [width, height] of [[1920, 1080], [1440, 900], [1280, 720], [1024, 768], [768, 1024], [390, 844], [375, 667], [320, 568]]) {
    test(`text stays above the mountains at ${width}x${height}`, async ({ page }) => {
      await page.setViewportSize({ width, height });
      await page.goto(PAGE_URL);
      // wait for the fade-in (it moves the text 20px) to finish
      await expect(page.locator("#hjem .hero-content")).toHaveClass(/visible/);
      await page.waitForTimeout(700);
      const gap = await page.evaluate(() => {
        const svg = document.querySelector("#hjem .hero-scene");
        const box = svg.getBoundingClientRect();
        // viewBox is 0 0 2400 900 and scaled to the element height;
        // the highest peak is at y = 285
        const peakTop = box.bottom - (900 - 285) * (box.height / 900);
        const text = document.querySelector("#hjem .hero-content").getBoundingClientRect();
        return peakTop - text.bottom;
      });
      expect(gap).toBeGreaterThan(0);
    });
  }

  test("scene sits at the bottom of the hero and spans its full width", async ({ page }) => {
    for (const [width, height] of [[2560, 1080], [1440, 900], [390, 844]]) {
      await page.setViewportSize({ width, height });
      await page.goto(PAGE_URL);
      const r = await page.evaluate(() => {
        const hero = document.querySelector("#hjem").getBoundingClientRect();
        const svg = document.querySelector("#hjem .hero-scene").getBoundingClientRect();
        return { left: svg.left - hero.left, right: hero.right - svg.right, bottom: hero.bottom - svg.bottom };
      });
      expect(r.left).toBeLessThanOrEqual(0.5);
      expect(r.right).toBeLessThanOrEqual(0.5);
      expect(Math.abs(r.bottom)).toBeLessThanOrEqual(0.5);
    }
  });
});

test.describe("i18n language switching", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(PAGE_URL);
  });

  test("page defaults to Norwegian Bokmål", async ({ page }) => {
    await expect(page.locator("html")).toHaveAttribute("lang", "nb");
    await expect(page.locator("[data-i18n='nav.home']")).toHaveText("Hjem");
    await expect(page.locator("[data-i18n='hero.title']")).toHaveText("Vetle Øyvind Larsen Lunde");
    await expect(page.locator("[data-i18n='nav.bachelor']")).toHaveText("Bacheloroppgave");
  });

  test("switches to English when toggle is clicked", async ({ page }) => {
    await page.click(".lang-toggle");
    await expect(page.locator("html")).toHaveAttribute("lang", "en");
    await expect(page.locator("[data-i18n='nav.home']")).toHaveText("Home");
    await expect(page.locator("[data-i18n='hero.title']")).toHaveText("Vetle Øyvind Larsen Lunde");
    await expect(page.locator("[data-i18n='nav.bachelor']")).toHaveText("Bachelor Thesis");
  });

  test("switches back to Norwegian when toggle is clicked twice", async ({ page }) => {
    await page.click(".lang-toggle");
    await page.click(".lang-toggle");
    await expect(page.locator("html")).toHaveAttribute("lang", "nb");
    await expect(page.locator("[data-i18n='nav.home']")).toHaveText("Hjem");
    await expect(page.locator("[data-i18n='nav.bachelor']")).toHaveText("Bacheloroppgave");
  });

  test("updates page title on language switch", async ({ page }) => {
    await expect(page).toHaveTitle("Vetle – Geologi og Geofare");
    await page.click(".lang-toggle");
    await expect(page).toHaveTitle(/Geology and Geo-Hazards/);
  });

  test("updates image alt texts on language switch", async ({ page }) => {
    await page.goto(BACHELOR_URL);
    const img = page.locator("[data-i18n-alt='bachelor.img1.alt']");
    await expect(img).toHaveAttribute("alt", "Bacheloroppgave – feltarbeid bilde 1");
    await page.click(".lang-toggle");
    await expect(img).toHaveAttribute("alt", "Bachelor thesis – fieldwork photo 1");
  });

  test("bachelor page defaults to Norwegian and switches to English", async ({ page }) => {
    await page.goto(BACHELOR_URL);
    await expect(page.locator("[data-i18n='bachelor.title']")).toHaveText("Bacheloroppgave");
    await page.click(".lang-toggle");
    await expect(page.locator("[data-i18n='bachelor.title']")).toHaveText("Bachelor Thesis");
    await expect(page.locator("[data-i18n='bachelor.caption1']")).toHaveText("The beautiful nature of Trøndelag");
    await expect(page.locator("[data-i18n='bachelor.caption2']")).toHaveText("Steep mountain sides");
  });

  test("language toggle button shows correct label", async ({ page }) => {
    await expect(page.locator(".lang-toggle")).toHaveText("EN");
    await page.click(".lang-toggle");
    await expect(page.locator(".lang-toggle")).toHaveText("NO");
  });
});

test.describe("About section – content", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(PAGE_URL);
  });

  test("displays updated about text in Om meg section", async ({ page }) => {
    const text = page.locator('#om-meg [data-i18n="about.text"]');
    await expect(text).toBeVisible();
    await expect(text).toContainText("Hei, mitt navn er Vetle!");
  });

  test("about text switches to English", async ({ page }) => {
    await page.click(".lang-toggle");
    const text = page.locator('#om-meg [data-i18n="about.text"]');
    await expect(text).toContainText("Hi, my name is Vetle!");
  });

  test("displays job history entries in Bakgrunn section", async ({ page }) => {
    const titles = page.locator('#bakgrunn h4.job-title');
    await expect(titles).toHaveCount(4);
    const job1Text = page.locator('#bakgrunn [data-i18n="about.job1.text"]');
    await expect(job1Text).toBeVisible();
    await expect(job1Text).toContainText("biostratigrafisk database");
    const job2Text = page.locator('#bakgrunn [data-i18n-html="about.job2.text"]');
    await expect(job2Text).toBeVisible();
    await expect(job2Text).toContainText("Well Delivery");
  });

  test("displays ConocoPhillips text titles beside job entries", async ({ page }) => {
    const titles = page.locator('#bakgrunn h4.job-title');
    await expect(titles).toHaveCount(4);
    await expect(titles.nth(0)).toHaveText("ConocoPhillips");
    await expect(titles.nth(1)).toHaveText("ConocoPhillips");
    await expect(titles.nth(2)).toHaveText("Vaktsoldat – Akershus Festning");
    await expect(titles.nth(3)).toHaveText("Renovasjonen IKS");
  });

  test("timeline container is visible in Bakgrunn section", async ({ page }) => {
    const timeline = page.locator('#bakgrunn .timeline');
    await expect(timeline).toBeVisible();
    const entries = page.locator('#bakgrunn .timeline-entry');
    await expect(entries).toHaveCount(4);
  });

  test("timeline displays year range labels on the left", async ({ page }) => {
    const dates = page.locator('#bakgrunn .timeline-date');
    await expect(dates).toHaveCount(4);
    await expect(dates.nth(0)).toHaveText("2025");
    await expect(dates.nth(1)).toHaveText("2024");
    await expect(dates.nth(2)).toHaveText("2022–2023");
    await expect(dates.nth(3)).toHaveText("2020–2022");
  });

  test("timeline markers are visible", async ({ page }) => {
    const markers = page.locator('#bakgrunn .timeline-marker');
    await expect(markers).toHaveCount(4);
    await expect(markers.nth(0)).toBeVisible();
    await expect(markers.nth(1)).toBeVisible();
    await expect(markers.nth(2)).toBeVisible();
    await expect(markers.nth(3)).toBeVisible();
  });

  test("job history switches to English", async ({ page }) => {
    await page.click(".lang-toggle");
    const job1Text = page.locator('#bakgrunn [data-i18n="about.job1.text"]');
    await expect(job1Text).toContainText("biostratigraphic database");
    const job2Text = page.locator('#bakgrunn [data-i18n-html="about.job2.text"]');
    await expect(job2Text).toContainText("Well Delivery");
    await expect(job2Text).toContainText("Ekofisk field");
  });

  test("job2 text contains Ekofisk description", async ({ page }) => {
    const job2Text = page.locator('#bakgrunn [data-i18n-html="about.job2.text"]');
    await expect(job2Text).toContainText("Ekofiskfeltet");
    await expect(job2Text).toContainText("StarSteer");
  });

  test("job0 text contains Akershus Festning description", async ({ page }) => {
    const job0Text = page.locator('#bakgrunn [data-i18n="about.job0.text"]');
    await expect(job0Text).toContainText("Akershus festning");
    await expect(job0Text).toContainText("vaktsoldat");
  });

  test("job0 switches to English", async ({ page }) => {
    await page.click(".lang-toggle");
    const job0Text = page.locator('#bakgrunn [data-i18n="about.job0.text"]');
    await expect(job0Text).toContainText("Akershus Fortress");
    await expect(job0Text).toContainText("guard soldier");
  });
});

test.describe("Norwegian Bokmål content", () => {
  test("all text is in Bokmål (not Nynorsk)", async ({ page }) => {
    await page.goto(PAGE_URL);
    const html = await page.content();
    // These Nynorsk words should NOT be present in the rendered HTML
    // (excluding proper nouns like "Høgskulen på Vestlandet")
    expect(html).not.toContain("Bacheloroppgåva");
    expect(html).not.toContain("korleis");
    expect(html).not.toContain("lausmassar");
    expect(html).not.toContain("Ikkje");
  });
});

test.describe("SEO and accessibility must-haves", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(PAGE_URL);
  });

  test("has a meta description tag", async ({ page }) => {
    const desc = page.locator('meta[name="description"]');
    await expect(desc).toHaveAttribute("content", /Vetle/);
  });

  test("has Open Graph meta tags", async ({ page }) => {
    await expect(page.locator('meta[property="og:title"]')).toHaveAttribute("content", /Vetle/);
    await expect(page.locator('meta[property="og:type"]')).toHaveAttribute("content", "website");
    await expect(page.locator('meta[property="og:url"]')).toHaveAttribute("content", /vetle-lunde-site/);
  });

  test("has a theme-color meta tag matching the theme", async ({ page }) => {
    await page.emulateMedia({ colorScheme: "dark" });
    await page.goto(PAGE_URL);
    await expect(page.locator('meta[name="theme-color"]')).toHaveAttribute("content", "#0f1117");
  });

  test("has a skip-to-content link targeting main content", async ({ page }) => {
    const skipLink = page.locator(".skip-link");
    await expect(skipLink).toHaveAttribute("href", "#hovedinnhold");
    await expect(skipLink).toHaveText("Hopp til hovedinnhold");
    await expect(page.locator("#hovedinnhold")).toHaveCount(1);
  });

  test("skip-to-content link text switches language", async ({ page }) => {
    await page.click(".lang-toggle");
    await expect(page.locator(".skip-link")).toHaveText("Skip to main content");
  });

  test("meta description updates on language switch", async ({ page }) => {
    const desc = page.locator('meta[name="description"]');
    await expect(desc).toHaveAttribute("content", /geologistudent/);
    await page.click(".lang-toggle");
    await expect(desc).toHaveAttribute("content", /geology student/);
  });
});

test.describe("Contact section link buttons", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(PAGE_URL);
  });

  test("contact section has email, GitHub, and LinkedIn buttons", async ({ page }) => {
    const emailBtn = page.locator('.contact-link-btn[href^="mailto:"]');
    const githubBtn = page.locator('.contact-link-btn[href*="github.com"]');
    const linkedinBtn = page.locator('.contact-link-btn[href*="linkedin.com"]');
    await expect(emailBtn).toBeVisible();
    await expect(githubBtn).toBeVisible();
    await expect(linkedinBtn).toBeVisible();
  });

  test("email button has correct mailto link", async ({ page }) => {
    const emailBtn = page.locator('.contact-link-btn[href^="mailto:"]');
    await expect(emailBtn).toHaveAttribute("href", "mailto:vetleoyvind@yahoo.com");
  });

  test("GitHub button links to correct profile", async ({ page }) => {
    const githubBtn = page.locator('.contact-link-btn[href*="github.com"]');
    await expect(githubBtn).toHaveAttribute("href", "https://github.com/Lundev42");
  });

  test("LinkedIn button links to correct profile", async ({ page }) => {
    const linkedinBtn = page.locator('.contact-link-btn[href*="linkedin.com"]');
    await expect(linkedinBtn).toHaveAttribute("href", "https://www.linkedin.com/in/vetle-lunde-3844753b6/");
  });

  test("buttons have text labels", async ({ page }) => {
    await expect(page.locator('.contact-link-btn[href^="mailto:"]')).toContainText("E-post");
    await expect(page.locator('.contact-link-btn[href*="github.com"]')).toContainText("GitHub");
    await expect(page.locator('.contact-link-btn[href*="linkedin.com"]')).toContainText("LinkedIn");
  });

  test("button labels switch to English", async ({ page }) => {
    await page.click(".lang-toggle");
    await expect(page.locator('.contact-link-btn[href^="mailto:"]')).toContainText("Email");
    await expect(page.locator('.contact-link-btn[href*="github.com"]')).toContainText("GitHub");
    await expect(page.locator('.contact-link-btn[href*="linkedin.com"]')).toContainText("LinkedIn");
  });

  test("external links open in new tab", async ({ page }) => {
    const githubBtn = page.locator('.contact-link-btn[href*="github.com"]');
    const linkedinBtn = page.locator('.contact-link-btn[href*="linkedin.com"]');
    await expect(githubBtn).toHaveAttribute("target", "_blank");
    await expect(linkedinBtn).toHaveAttribute("target", "_blank");
  });

  test("external links have rel noopener noreferrer", async ({ page }) => {
    const githubBtn = page.locator('.contact-link-btn[href*="github.com"]');
    const linkedinBtn = page.locator('.contact-link-btn[href*="linkedin.com"]');
    await expect(githubBtn).toHaveAttribute("rel", "noopener noreferrer");
    await expect(linkedinBtn).toHaveAttribute("rel", "noopener noreferrer");
  });

  test("buttons have aria-labels", async ({ page }) => {
    await expect(page.locator('.contact-link-btn[href^="mailto:"]')).toHaveAttribute("aria-label", "Send e-post");
    await expect(page.locator('.contact-link-btn[href*="github.com"]')).toHaveAttribute("aria-label", "GitHub");
    await expect(page.locator('.contact-link-btn[href*="linkedin.com"]')).toHaveAttribute("aria-label", "LinkedIn");
  });

  test("contact text is displayed on a single line", async ({ page }) => {
    const p = page.locator("#kontakt p");
    const style = await p.evaluate(el => getComputedStyle(el).whiteSpace);
    expect(style).toBe("nowrap");
  });

  test("email button has envelope icon", async ({ page }) => {
    const icon = page.locator('.contact-link-btn[href^="mailto:"] svg.icon-envelope');
    await expect(icon).toBeAttached();
    await expect(icon).toHaveAttribute("aria-hidden", "true");
  });

  test("GitHub button has GitHub icon", async ({ page }) => {
    const icon = page.locator('.contact-link-btn[href*="github.com"] svg.icon-github');
    await expect(icon).toBeAttached();
    await expect(icon).toHaveAttribute("aria-hidden", "true");
  });

  test("LinkedIn button has LinkedIn icon", async ({ page }) => {
    const icon = page.locator('.contact-link-btn[href*="linkedin.com"] svg.icon-linkedin');
    await expect(icon).toBeAttached();
    await expect(icon).toHaveAttribute("aria-hidden", "true");
  });

  test("icons appear before text in buttons", async ({ page }) => {
    const emailBtn = page.locator('.contact-link-btn[href^="mailto:"]');
    const firstChild = emailBtn.locator('> :first-child');
    await expect(firstChild).toHaveClass(/icon-envelope/);
  });
});

test.describe("Colour theme picker", () => {
  const THEMES = {
    dark: { mode: "dark", bg: "rgb(15, 17, 23)", meta: "#0f1117" },
    light: { mode: "light", bg: "rgb(238, 240, 246)", meta: "#eef0f6" },
    purple: { mode: "dark", bg: "rgb(21, 15, 32)", meta: "#150f20" },
    green: { mode: "dark", bg: "rgb(12, 22, 18)", meta: "#0c1612" },
    white: { mode: "light", bg: "rgb(255, 255, 255)", meta: "#ffffff" },
  };

  async function choose(page, theme) {
    await page.click("#theme-toggle");
    await page.click(`.theme-option[data-theme-value="${theme}"]`);
  }

  test.beforeEach(async ({ page }) => {
    await page.emulateMedia({ colorScheme: "dark" });
    await page.goto(PAGE_URL);
  });

  test("picker button is visible and labelled", async ({ page }) => {
    const toggle = page.locator("#theme-toggle");
    await expect(toggle).toBeVisible();
    await expect(toggle).toHaveAttribute("aria-label", "Velg bakgrunnsfarge");
    await expect(toggle).toHaveAttribute("aria-expanded", "false");
    await expect(toggle).toHaveAttribute("aria-controls", "theme-menu");
    await expect(page.locator("#theme-menu")).toBeHidden();
  });

  test("defaults to the dark theme", async ({ page }) => {
    await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
    await expect(page.locator("html")).toHaveAttribute("data-mode", "dark");
    await expect(page.locator('.theme-option[data-theme-value="dark"]')).toHaveAttribute("aria-pressed", "true");
  });

  test("opens a menu with five colours and focuses the current one", async ({ page }) => {
    await page.click("#theme-toggle");
    await expect(page.locator("#theme-toggle")).toHaveAttribute("aria-expanded", "true");
    await expect(page.locator("#theme-menu")).toBeVisible();
    await expect(page.locator(".theme-option")).toHaveText(["Mørk", "Lys", "Lilla", "Grønn", "Hvit"]);
    await expect(page.locator('.theme-option[data-theme-value="dark"]')).toBeFocused();
  });

  for (const [theme, expected] of Object.entries(THEMES)) {
    test(`choosing ${theme} applies, marks and saves it`, async ({ page }) => {
      if (theme === "dark") await choose(page, "white");
      await choose(page, theme);
      await expect(page.locator("html")).toHaveAttribute("data-theme", theme);
      await expect(page.locator("html")).toHaveAttribute("data-mode", expected.mode);
      await expect(page.locator(`.theme-option[data-theme-value="${theme}"]`)).toHaveAttribute("aria-pressed", "true");
      await expect(page.locator('.theme-option[aria-pressed="true"]')).toHaveCount(1);
      await expect(page.locator("body")).toHaveCSS("background-color", expected.bg);
      await expect(page.locator('meta[name="theme-color"]')).toHaveAttribute("content", expected.meta);
      expect(await page.evaluate(() => localStorage.getItem("theme"))).toBe(theme);
      // menu closes and focus returns to the button
      await expect(page.locator("#theme-menu")).toBeHidden();
      await expect(page.locator("#theme-toggle")).toBeFocused();
    });
  }

  test("each theme gives the mountain scene its own sky", async ({ page }) => {
    const skies = new Set();
    for (const theme of Object.keys(THEMES)) {
      await page.evaluate((t) => document.documentElement.setAttribute("data-theme", t), theme);
      skies.add(await page.locator("#hjem").evaluate((el) => getComputedStyle(el).backgroundImage));
    }
    expect(skies.size).toBe(5);
  });

  test("saved theme is restored on reload and on other pages", async ({ page }) => {
    await choose(page, "purple");
    await page.reload();
    await expect(page.locator("html")).toHaveAttribute("data-theme", "purple");
    await page.goto(BACHELOR_URL);
    await expect(page.locator("html")).toHaveAttribute("data-theme", "purple");
    await expect(page.locator('.theme-option[data-theme-value="purple"]')).toHaveAttribute("aria-pressed", "true");
  });

  test("Escape closes the menu and returns focus", async ({ page }) => {
    await page.click("#theme-toggle");
    await page.keyboard.press("Escape");
    await expect(page.locator("#theme-menu")).toBeHidden();
    await expect(page.locator("#theme-toggle")).toHaveAttribute("aria-expanded", "false");
    await expect(page.locator("#theme-toggle")).toBeFocused();
  });

  test("arrow keys move between colours and Enter picks one", async ({ page }) => {
    await page.focus("#theme-toggle");
    await page.keyboard.press("Enter");
    await page.keyboard.press("ArrowDown");
    await page.keyboard.press("ArrowDown");
    await expect(page.locator('.theme-option[data-theme-value="purple"]')).toBeFocused();
    await page.keyboard.press("ArrowUp");
    await page.keyboard.press("End");
    await expect(page.locator('.theme-option[data-theme-value="white"]')).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(page.locator("html")).toHaveAttribute("data-theme", "white");
  });

  test("clicking outside closes the menu without changing the theme", async ({ page }) => {
    await page.click("#theme-toggle");
    await page.mouse.click(10, 400);
    await expect(page.locator("#theme-menu")).toBeHidden();
    await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  });

  test("colour names follow the language", async ({ page }) => {
    await page.click(".lang-toggle");
    await expect(page.locator("#theme-toggle")).toHaveAttribute("aria-label", "Choose background colour");
    await expect(page.locator(".theme-option")).toHaveText(["Dark", "Light", "Purple", "Green", "White"]);
  });

  test("works on the mobile layout", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto(PAGE_URL);
    await choose(page, "green");
    await expect(page.locator("html")).toHaveAttribute("data-theme", "green");
    await expect(page.locator("#theme-menu")).toBeHidden();
  });

  test("an unknown saved value falls back to the system preference", async ({ page }) => {
    await page.evaluate(() => localStorage.setItem("theme", "neon"));
    await page.emulateMedia({ colorScheme: "light" });
    await page.goto(PAGE_URL);
    await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  });

  test("respects prefers-color-scheme light when no saved preference", async ({ page }) => {
    await page.evaluate(() => localStorage.removeItem("theme"));
    await page.emulateMedia({ colorScheme: "light" });
    await page.goto(PAGE_URL);
    await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
    await expect(page.locator("html")).toHaveAttribute("data-mode", "light");
  });
});

test.describe("Navigation active highlighting", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(PAGE_URL);
  });

  test("bachelor nav link points to bacheloroppgave.html", async ({ page }) => {
    const bachelorLink = page.locator('nav a[href="bacheloroppgave.html"]');
    await expect(bachelorLink).toBeVisible();
    await expect(bachelorLink).toHaveAttribute("href", "bacheloroppgave.html");
  });

  test("there is no Kontakt link in the nav", async ({ page }) => {
    await expect(page.locator('nav a[href="#kontakt"]')).toHaveCount(0);
  });

  test("only one nav link is active at a time", async ({ page }) => {
    const hrefs = ['#hjem', '#om-meg', '#bakgrunn'];
    for (const href of hrefs) {
      await page.locator('nav ul a[href="' + href + '"]').click();
      await page.waitForTimeout(900);
      const activeLinks = page.locator('nav a.nav-active');
      await expect(activeLinks).toHaveCount(1);
    }
  });
});

test.describe("Multi-page navigation", () => {
  test("index.html bachelor nav link points to bacheloroppgave.html", async ({ page }) => {
    await page.goto(PAGE_URL);
    const link = page.locator('nav a[data-i18n="nav.bachelor"]');
    await expect(link).toHaveAttribute("href", "bacheloroppgave.html");
  });

  test("bacheloroppgave.html has nav links back to index.html", async ({ page }) => {
    await page.goto(BACHELOR_URL);
    await expect(page.locator('nav a[data-i18n="nav.home"]')).toHaveAttribute("href", "index.html#hjem");
    await expect(page.locator('nav a[data-i18n="nav.about"]')).toHaveAttribute("href", "index.html#om-meg");
    await expect(page.locator('nav a[data-i18n="nav.background"]')).toHaveAttribute("href", "index.html#bakgrunn");
    await expect(page.locator('nav a[data-i18n="nav.contact"]')).toHaveCount(0);
  });

  test("bacheloroppgave.html bachelor link points to #bachelor", async ({ page }) => {
    await page.goto(BACHELOR_URL);
    await expect(page.locator('nav a[data-i18n="nav.bachelor"]')).toHaveAttribute("href", "#bachelor");
  });
});

test.describe("Accordion component in Bakgrunn section", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(PAGE_URL);
  });

  test("accordion exists in the bakgrunn section", async ({ page }) => {
    const accordion = page.locator("#bakgrunn .accordion");
    await expect(accordion.first()).toBeVisible();
  });

  test("accordion is collapsed by default", async ({ page }) => {
    const details = page.locator("#bakgrunn details.accordion").first();
    await expect(details).not.toHaveAttribute("open", "");
  });

  test("study subsection heading has correct Norwegian title", async ({ page }) => {
    const heading = page.locator('h3[data-i18n="background.study.title"]');
    await expect(heading).toHaveText("Faglig bakgrunn");
  });

  test("nested accordion contains course table with correct courses", async ({ page }) => {
    const nestedSummary = page.locator('summary[data-i18n="study.accordion.title"]');
    await nestedSummary.click();
    const table = page.locator("#bakgrunn .degree-row .course-table");
    await expect(table).toBeVisible();
    const courseRows = page.locator("#bakgrunn .degree-row .course-table tbody tr:not(.semester-row)");
    await expect(courseRows).toHaveCount(18);
    await expect(courseRows.first()).toContainText("MA414");
  });

  test("study subsection heading switches to English", async ({ page }) => {
    await page.click(".lang-toggle");
    const heading = page.locator('h3[data-i18n="background.study.title"]');
    await expect(heading).toHaveText("Academic background");
  });

  test("nested accordion content switches to English", async ({ page }) => {
    await page.click(".lang-toggle");
    const nestedSummary = page.locator('summary[data-i18n="study.accordion.title"]');
    await nestedSummary.click();
    const firstCourse = page.locator("#bakgrunn .degree-row .course-table tbody tr:not(.semester-row)").first();
    await expect(firstCourse).toContainText("MA414");
    await expect(firstCourse).toContainText("Mathematics for Natural Sciences");
  });
});

test.describe("Footer copyright", () => {
  test("footer shows '© 2026 Vetle Lunde' on index", async ({ page }) => {
    await page.goto(PAGE_URL);
    const footer = page.locator("footer");
    await expect(footer).toContainText("2026 Vetle Lunde");
  });

  test("footer shows '© 2026 Vetle Lunde' on bacheloroppgave", async ({ page }) => {
    await page.goto(BACHELOR_URL);
    const footer = page.locator("footer");
    await expect(footer).toContainText("2026 Vetle Lunde");
  });
});

test.describe("StarSteer link", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(PAGE_URL);
  });

  test("StarSteer text is a link to rogii.com", async ({ page }) => {
    const link = page.locator('#bakgrunn [data-i18n-html="about.job2.text"] a[href="https://www.rogii.com/products/starsteer"]');
    await expect(link).toBeVisible();
    await expect(link).toHaveText("StarSteer");
  });

  test("StarSteer link opens in new tab", async ({ page }) => {
    const link = page.locator('#bakgrunn [data-i18n-html="about.job2.text"] a[href="https://www.rogii.com/products/starsteer"]');
    await expect(link).toHaveAttribute("target", "_blank");
    await expect(link).toHaveAttribute("rel", /noopener/);
  });

  test("StarSteer link has no underline", async ({ page }) => {
    const link = page.locator('#bakgrunn [data-i18n-html="about.job2.text"] a[href="https://www.rogii.com/products/starsteer"]');
    const textDecoration = await link.evaluate(el => getComputedStyle(el).textDecorationLine);
    expect(textDecoration).toBe("none");
  });

  test("StarSteer link visited colour matches accent colour", async ({ page }) => {
    const link = page.locator('#bakgrunn [data-i18n-html="about.job2.text"] a[href="https://www.rogii.com/products/starsteer"]');
    // Verify the link color matches --accent (the :visited rule re-applies the accent colour)
    const { linkColor, accentColor } = await link.evaluate(el => {
      const accent = getComputedStyle(document.documentElement).getPropertyValue("--accent").trim();
      // Create a temporary element to resolve the CSS variable to an rgb value
      const tmp = document.createElement("span");
      tmp.style.color = "var(--accent)";
      document.body.appendChild(tmp);
      const resolved = getComputedStyle(tmp).color;
      document.body.removeChild(tmp);
      return { linkColor: getComputedStyle(el).color, accentColor: resolved };
    });
    expect(linkColor).toBe(accentColor);
  });

  test("StarSteer link is also present in English", async ({ page }) => {
    await page.click(".lang-toggle");
    const link = page.locator('#bakgrunn [data-i18n-html="about.job2.text"] a[href="https://www.rogii.com/products/starsteer"]');
    await expect(link).toBeVisible();
    await expect(link).toHaveText("StarSteer");
  });

  test("StarSteer link in English opens in new tab", async ({ page }) => {
    await page.click(".lang-toggle");
    const link = page.locator('#bakgrunn [data-i18n-html="about.job2.text"] a[href="https://www.rogii.com/products/starsteer"]');
    await expect(link).toHaveAttribute("target", "_blank");
  });
});

test.describe("StarSteer page", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(STARSTEER_URL);
  });

  test("has a footer with '© 2026 Vetle Lunde'", async ({ page }) => {
    const footer = page.locator("footer");
    await expect(footer).toContainText("2026 Vetle Lunde");
  });

  test("has nav links back to index.html", async ({ page }) => {
    await expect(page.locator('nav a[data-i18n="nav.home"]')).toHaveAttribute("href", "index.html#hjem");
  });

  test("contains StarSteer content", async ({ page }) => {
    const body = page.locator("body");
    await expect(body).toContainText("StarSteer");
  });
});

test.describe("ConocoPhillips 2025 page", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(COP2025_URL);
  });

  test("has a footer with '© 2026 Vetle Lunde'", async ({ page }) => {
    const footer = page.locator("footer");
    await expect(footer).toContainText("2026 Vetle Lunde");
  });

  test("has nav links back to index.html", async ({ page }) => {
    await expect(page.locator('nav a[data-i18n="nav.home"]')).toHaveAttribute("href", "index.html#hjem");
  });

  test("contains ConocoPhillips 2025 content", async ({ page }) => {
    const body = page.locator("body");
    await expect(body).toContainText("ConocoPhillips 2025");
  });

  test("has an h1 element", async ({ page }) => {
    await expect(page.locator("h1")).toHaveCount(1);
  });
});

test.describe("ConocoPhillips 2024 page", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(COP2024_URL);
  });

  test("has a footer with '© 2026 Vetle Lunde'", async ({ page }) => {
    const footer = page.locator("footer");
    await expect(footer).toContainText("2026 Vetle Lunde");
  });

  test("has nav links back to index.html", async ({ page }) => {
    await expect(page.locator('nav a[data-i18n="nav.home"]')).toHaveAttribute("href", "index.html#hjem");
  });

  test("contains ConocoPhillips 2024 content", async ({ page }) => {
    const body = page.locator("body");
    await expect(body).toContainText("ConocoPhillips 2024");
  });

  test("has an h1 element", async ({ page }) => {
    await expect(page.locator("h1")).toHaveCount(1);
  });
});

test.describe("Accessibility improvements", () => {
  test("nav has aria-label on index page", async ({ page }) => {
    await page.goto(PAGE_URL);
    await expect(page.locator("nav")).toHaveAttribute("aria-label", "Hovednavigasjon");
  });

  test("nav has aria-label on bacheloroppgave page", async ({ page }) => {
    await page.goto(BACHELOR_URL);
    await expect(page.locator("nav")).toHaveAttribute("aria-label", "Hovednavigasjon");
  });

  test("nav has aria-label on starsteer page", async ({ page }) => {
    await page.goto(STARSTEER_URL);
    await expect(page.locator("nav")).toHaveAttribute("aria-label", "Hovednavigasjon");
  });

  test("nav aria-label switches to English", async ({ page }) => {
    await page.goto(PAGE_URL);
    await page.click(".lang-toggle");
    await expect(page.locator("nav")).toHaveAttribute("aria-label", "Main navigation");
  });

  test("below-the-fold images have loading=lazy on index", async ({ page }) => {
    await page.goto(PAGE_URL);
    const aboutImg = page.locator('#om-meg img[src*="vetle-vinter"]');
    await expect(aboutImg).toHaveAttribute("loading", "lazy");
    const studyImg = page.locator('img[src*="hvl-campus-sogndal"]');
    await expect(studyImg).toHaveAttribute("loading", "lazy");
  });

  test("gallery images have loading=lazy on bacheloroppgave", async ({ page }) => {
    await page.goto(BACHELOR_URL);
    const imgs = page.locator("#bachelor .gallery-grid img");
    await expect(imgs.nth(0)).toHaveAttribute("loading", "lazy");
    await expect(imgs.nth(1)).toHaveAttribute("loading", "lazy");
  });

  test("images have width and height attributes on index", async ({ page }) => {
    await page.goto(PAGE_URL);
    const hvlImg = page.locator('img[src*="hvl-campus-sogndal"]');
    await expect(hvlImg).toHaveAttribute("width");
    await expect(hvlImg).toHaveAttribute("height");
  });

  test("images have width and height attributes on bacheloroppgave", async ({ page }) => {
    await page.goto(BACHELOR_URL);
    const imgs = page.locator("#bachelor .gallery-grid img");
    await expect(imgs.nth(0)).toHaveAttribute("width");
    await expect(imgs.nth(0)).toHaveAttribute("height");
  });

  test("bacheloroppgave page has an h1 element", async ({ page }) => {
    await page.goto(BACHELOR_URL);
    await expect(page.locator("h1")).toHaveCount(1);
  });

  test("starsteer page has an h1 element", async ({ page }) => {
    await page.goto(STARSTEER_URL);
    await expect(page.locator("h1")).toHaveCount(1);
  });
});

test.describe("SEO improvements", () => {
  test("index has canonical URL", async ({ page }) => {
    await page.goto(PAGE_URL);
    const canonical = page.locator('link[rel="canonical"]');
    await expect(canonical).toHaveAttribute("href", "https://Lundev42.github.io/vetle-lunde-site/");
  });

  test("bacheloroppgave has correct canonical URL", async ({ page }) => {
    await page.goto(BACHELOR_URL);
    const canonical = page.locator('link[rel="canonical"]');
    await expect(canonical).toHaveAttribute("href", "https://Lundev42.github.io/vetle-lunde-site/bacheloroppgave.html");
  });

  test("starsteer has correct canonical URL", async ({ page }) => {
    await page.goto(STARSTEER_URL);
    const canonical = page.locator('link[rel="canonical"]');
    await expect(canonical).toHaveAttribute("href", "https://Lundev42.github.io/vetle-lunde-site/starsteer.html");
  });

  test("bacheloroppgave has correct og:url", async ({ page }) => {
    await page.goto(BACHELOR_URL);
    const ogUrl = page.locator('meta[property="og:url"]');
    await expect(ogUrl).toHaveAttribute("content", "https://Lundev42.github.io/vetle-lunde-site/bacheloroppgave.html");
  });

  test("all pages have og:image meta tag", async ({ page }) => {
    await page.goto(PAGE_URL);
    await expect(page.locator('meta[property="og:image"]')).toHaveCount(1);

    await page.goto(BACHELOR_URL);
    await expect(page.locator('meta[property="og:image"]')).toHaveCount(1);

    await page.goto(STARSTEER_URL);
    await expect(page.locator('meta[property="og:image"]')).toHaveCount(1);
  });
});

test.describe('Motion design (impeccable skill)', function () {
  test('CSS motion tokens are defined in :root', async function ({ page }) {
    await page.goto(PAGE_URL);
    var easeOutQuart = await page.evaluate(function () {
      return getComputedStyle(document.documentElement).getPropertyValue('--ease-out-quart').trim();
    });
    expect(easeOutQuart).toBe('cubic-bezier(0.25, 1, 0.5, 1)');
    var easeOutExpo = await page.evaluate(function () {
      return getComputedStyle(document.documentElement).getPropertyValue('--ease-out-expo').trim();
    });
    expect(easeOutExpo).toBe('cubic-bezier(0.16, 1, 0.3, 1)');
  });

  test('about sub-gallery contains three clickable figures', async function ({ page }) {
    await page.goto(PAGE_URL);
    var figures = page.locator('.about-sub-gallery .gallery-thumb');
    var count = await figures.count();
    expect(count).toBe(3);
  });

  test('interactive elements have active pressed states', async function ({ page }) {
    await page.goto(PAGE_URL);
    var hasActiveRule = await page.evaluate(function () {
      var sheets = document.styleSheets;
      for (var s = 0; s < sheets.length; s++) {
        try {
          var rules = sheets[s].cssRules;
          for (var r = 0; r < rules.length; r++) {
            if (rules[r].selectorText && rules[r].selectorText.indexOf('.contact-link-btn:active') !== -1) {
              return true;
            }
          }
        } catch (e) {}
      }
      return false;
    });
    expect(hasActiveRule).toBe(true);
  });

  test('images have hover lift transform', async function ({ page }) {
    await page.goto(PAGE_URL);
    var hasHoverRule = await page.evaluate(function () {
      var sheets = document.styleSheets;
      for (var s = 0; s < sheets.length; s++) {
        try {
          // Look inside @media blocks too (hover motion is gated behind
          // @media (hover: hover) and (pointer: fine))
          var stack = Array.prototype.slice.call(sheets[s].cssRules);
          while (stack.length) {
            var rule = stack.pop();
            if (rule.selectorText && rule.selectorText.indexOf('.media-col img:hover') !== -1) {
              return true;
            }
            if (rule.cssRules) stack.push.apply(stack, Array.prototype.slice.call(rule.cssRules));
          }
        } catch (e) {}
      }
      return false;
    });
    expect(hasHoverRule).toBe(true);
  });

  test('prefers-reduced-motion is respected', async function ({ page }) {
    await page.goto(PAGE_URL);
    var hasReducedMotion = await page.evaluate(function () {
      var sheets = document.styleSheets;
      for (var s = 0; s < sheets.length; s++) {
        try {
          var rules = sheets[s].cssRules;
          for (var r = 0; r < rules.length; r++) {
            if (rules[r].conditionText && rules[r].conditionText.indexOf('prefers-reduced-motion') !== -1) {
              return true;
            }
          }
        } catch (e) {}
      }
      return false;
    });
    expect(hasReducedMotion).toBe(true);
  });
});

/* ── CSS Fix Tests ── */

test.describe("Profile image dark-mode shadow (Fix 1)", () => {
  test("dark mode uses light shadow", async ({ page }) => {
    await page.goto(PAGE_URL);
    await page.evaluate(() => {
      document.documentElement.setAttribute("data-theme", "dark");
      document.documentElement.setAttribute("data-mode", "dark");
    });
    const figure = page.locator("#om-meg .media-col figure");
    const shadow = await figure.evaluate(el => getComputedStyle(el).boxShadow);
    // Dark mode default: light rgba(255,255,255,0.08) shadow
    expect(shadow).toMatch(/rgba?\(255,\s*255,\s*255/);
  });

  test("light mode uses dark shadow", async ({ page }) => {
    await page.goto(PAGE_URL);
    await page.evaluate(() => {
      document.documentElement.setAttribute("data-theme", "light");
      document.documentElement.setAttribute("data-mode", "light");
    });
    const figure = page.locator("#om-meg .media-col figure");
    const shadow = await figure.evaluate(el => getComputedStyle(el).boxShadow);
    // Light mode: dark rgba(0,0,0,0.25) shadow
    expect(shadow).toMatch(/rgba?\(0,\s*0,\s*0/);
  });
});

test.describe("Navigation active highlighting in light mode (Fix 2)", () => {
  function hasLightNavActiveRule() {
    var sheets = document.styleSheets;
    for (var s = 0; s < sheets.length; s++) {
      try {
        var rules = sheets[s].cssRules;
        for (var r = 0; r < rules.length; r++) {
          if (rules[r].selectorText &&
              rules[r].selectorText.indexOf('[data-mode="light"] nav a.nav-active') !== -1) {
            return true;
          }
        }
      } catch (e) {}
    }
    return false;
  }

  test("index.html has light-mode nav-active rule", async ({ page }) => {
    await page.goto(PAGE_URL);
    const hasRule = await page.evaluate(hasLightNavActiveRule);
    expect(hasRule).toBe(true);
  });

  test("bacheloroppgave.html has light-mode nav-active rule", async ({ page }) => {
    await page.goto(BACHELOR_URL);
    const hasRule = await page.evaluate(hasLightNavActiveRule);
    expect(hasRule).toBe(true);
  });
});

test.describe("Navigation bar vertical centering (Fix 3)", () => {
  test("index.html nav ul has align-items center", async ({ page }) => {
    await page.goto(PAGE_URL);
    const alignItems = await page.locator("nav ul").evaluate(el => getComputedStyle(el).alignItems);
    expect(alignItems).toBe("center");
  });

  test("bacheloroppgave.html nav ul has align-items center", async ({ page }) => {
    await page.goto(BACHELOR_URL);
    const alignItems = await page.locator("nav ul").evaluate(el => getComputedStyle(el).alignItems);
    expect(alignItems).toBe("center");
  });

  test("starsteer.html nav ul has align-items center", async ({ page }) => {
    await page.goto(STARSTEER_URL);
    const alignItems = await page.locator("nav ul").evaluate(el => getComputedStyle(el).alignItems);
    expect(alignItems).toBe("center");
  });
});

test.describe("Gallery captions always visible (Fix 4)", () => {
  test("caption is visible by default", async ({ page }) => {
    await page.goto(PAGE_URL);
    const caption = page.locator(".about-sub-gallery .gallery-thumb figcaption").first();
    const opacity = await caption.evaluate(el => getComputedStyle(el).opacity);
    expect(opacity).toBe("1");
  });

  test("caption remains visible on hover", async ({ page }) => {
    await page.goto(PAGE_URL);
    const thumb = page.locator(".about-sub-gallery .gallery-thumb").first();
    await thumb.hover();
    const caption = thumb.locator("figcaption");
    await expect(caption).toHaveCSS("opacity", "1");
  });
});

test.describe("Academic background split into BSc and MSc", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(PAGE_URL);
  });

  test("shows BSc and MSc headings", async ({ page }) => {
    await expect(page.locator('[data-i18n="background.bsc.title"]')).toHaveText("Bachelor i geologi og geofare – Sogndal 2023–2026");
    await expect(page.locator('[data-i18n="background.msc.title"]')).toHaveText("Master i geologi – Trondheim 2026–2028");
    await expect(page.locator('[data-i18n="msc.text"]')).toHaveText("Kommer ...");
  });

  test("BSc course table sits in the BSc block, MSc has its own accordion", async ({ page }) => {
    await expect(page.locator(".degree-row .course-table")).toHaveCount(1);
    await expect(page.locator('summary[data-i18n="msc.accordion.title"]')).toHaveText("Oppnådd faglig kompetanse");
  });

  test("campus photo only sits beside the BSc block", async ({ page }) => {
    await expect(page.locator('.degree-row img[src*="hvl-campus-sogndal"]')).toHaveCount(1);
    await expect(page.locator('#bakgrunn img[src*="hvl-campus-sogndal"]')).toHaveCount(1);
  });

  test("MSc strings switch to English", async ({ page }) => {
    await page.click(".lang-toggle");
    await expect(page.locator('[data-i18n="background.bsc.title"]')).toHaveText("Bachelor in Geology and Geohazards – Sogndal 2023–2026");
    await expect(page.locator('[data-i18n="background.msc.title"]')).toHaveText("Master in Geology – Trondheim 2026–2028");
  });
});

test.describe("Hero and About cleanup", () => {
  test("scroll hint is plain text, not a link", async ({ page }) => {
    await page.goto(PAGE_URL);
    await expect(page.locator("#hjem .scroll-hint")).toBeVisible();
    await expect(page.locator("#hjem a.scroll-hint")).toHaveCount(0);
  });

  test("About section has no geology intro button", async ({ page }) => {
    await page.goto(PAGE_URL);
    await expect(page.locator("#om-meg .geo-cta")).toHaveCount(0);
  });
});

test.describe("Nav highlighting follows the section being read", () => {
  async function activeHref(page) {
    await page.waitForTimeout(150);
    return page.locator("nav ul a.nav-active").getAttribute("href");
  }

  test("Kontakt section keeps Bakgrunn highlighted", async ({ page }) => {
    await page.goto(PAGE_URL);
    await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));
    expect(await activeHref(page)).toBe("#bakgrunn");
  });

  test("scrolling back up from the bottom passes through Bakgrunn and Om meg", async ({ page }) => {
    await page.goto(PAGE_URL);
    await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));
    await activeHref(page);
    // Somewhere in the middle of the (tall) Bakgrunn section
    await page.evaluate(() => {
      const bg = document.getElementById("bakgrunn");
      window.scrollTo(0, bg.offsetTop + bg.offsetHeight / 2);
    });
    expect(await activeHref(page)).toBe("#bakgrunn");
    await page.evaluate(() => window.scrollTo(0, document.getElementById("om-meg").offsetTop + 100));
    expect(await activeHref(page)).toBe("#om-meg");
    await page.evaluate(() => window.scrollTo(0, 0));
    expect(await activeHref(page)).toBe("#hjem");
  });
});

test.describe("Course tables", () => {
  test("semester 1 lists Matematikk naturfag", async ({ page }) => {
    await page.goto(PAGE_URL);
    await expect(page.locator(".degree-row .course-table")).toContainText("Matematikk naturfag");
    await expect(page.locator(".degree-row .course-table")).not.toContainText("Matematikk for naturfag");
  });

  test("MSc table lists the semester 1 courses and a pending semester 2", async ({ page }) => {
    await page.goto(PAGE_URL);
    const table = page.locator('[data-i18n-html="msc.accordion.content"] .course-table');
    for (const code of ["TPG4175", "TGB4266", "TGB4265", "TPG4255"]) {
      await expect(table).toContainText(code);
    }
    await expect(table).toContainText("Geomekanikk for CO₂-lagring");
    await expect(table.locator(".course-pending")).toHaveText("Kommer snart ...");
    await page.click(".lang-toggle");
    await expect(table).toContainText("Geomechanics for CO₂ Storage");
    await expect(table.locator(".course-pending")).toHaveText("Coming soon ...");
  });
});
