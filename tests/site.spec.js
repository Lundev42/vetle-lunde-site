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

  test("has a background image (optimised copy of IMG_7173.JPG)", async ({ page }) => {
    const bg = await page.locator("#hjem").evaluate((el) =>
      getComputedStyle(el).backgroundImage
    );
    expect(bg).toContain("hero-galdhopiggen");
  });

  test("has a dark overlay for readability", async ({ page }) => {
    const overlay = page.locator("#hjem .hero-overlay");
    await expect(overlay).toBeVisible();
  });

  test("has no photo caption", async ({ page }) => {
    await expect(page.locator("#hjem .hero-caption")).toHaveCount(0);
    await expect(page.locator("#hjem")).not.toContainText("Galdhøgpiggen");
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
  // Themes are geological periods, in time order
  const THEMES = {
    hadean: { mode: "dark", bg: "rgb(22, 12, 10)", meta: "#160c0a" },
    cambrian: { mode: "dark", bg: "rgb(12, 22, 18)", meta: "#0c1612" },
    cretaceous: { mode: "dark", bg: "rgb(15, 17, 23)", meta: "#0f1117" },
    quaternary: { mode: "light", bg: "rgb(232, 235, 240)", meta: "#e8ebf0" },
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
    await expect(toggle).toHaveAttribute("aria-label", "Velg fargetema");
    await expect(toggle).toHaveAttribute("aria-expanded", "false");
    await expect(toggle).toHaveAttribute("aria-controls", "theme-menu");
    await expect(page.locator("#theme-menu")).toBeHidden();
  });

  test("defaults to Kritt (cretaceous, dark)", async ({ page }) => {
    await expect(page.locator("html")).toHaveAttribute("data-theme", "cretaceous");
    await expect(page.locator("html")).toHaveAttribute("data-mode", "dark");
    await expect(page.locator('.theme-option[data-theme-value="cretaceous"]')).toHaveAttribute("aria-pressed", "true");
  });

  test("opens a menu with four geological periods and focuses the current one", async ({ page }) => {
    await page.click("#theme-toggle");
    await expect(page.locator("#theme-toggle")).toHaveAttribute("aria-expanded", "true");
    await expect(page.locator("#theme-menu")).toBeVisible();
    await expect(page.locator(".theme-menu-title")).toHaveText("Geologisk periode");
    await expect(page.locator(".theme-label > span")).toHaveText(["Hadeikum", "Kambrium", "Kritt", "Kvartær"]);
    await expect(page.locator(".theme-label small")).toHaveText([
      "4,6–4,0 mrd. år siden", "539–487 mill. år siden", "145–66 mill. år siden", "2,6 mill. år siden – i dag",
    ]);
    await expect(page.locator('.theme-option[data-theme-value="cretaceous"]')).toBeFocused();
  });

  test("each period has its own icon, hidden from screen readers", async ({ page }) => {
    for (const theme of Object.keys(THEMES)) {
      const icon = page.locator(`.theme-option[data-theme-value="${theme}"] .theme-icon`);
      await expect(icon).toHaveAttribute("aria-hidden", "true");
      await expect(icon.locator("svg .ti-a").first()).toBeAttached();
    }
    // magma, trilobite, meteorite (with a fiery trail) and a woolly mammoth
    // with its curved tusk
    await expect(page.locator('.theme-option[data-theme-value="cretaceous"] .ti-trail line')).toHaveCount(3);
    await expect(page.locator('.theme-option[data-theme-value="quaternary"] .theme-icon svg .ti-tusk')).toHaveCount(1);
  });

  for (const [theme, expected] of Object.entries(THEMES)) {
    test(`choosing ${theme} applies, marks and saves it`, async ({ page }) => {
      if (theme === "cretaceous") await choose(page, "quaternary");
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

  test("the front photo stays the same in every colour theme", async ({ page }) => {
    for (const theme of Object.keys(THEMES)) {
      await page.evaluate((t) => document.documentElement.setAttribute("data-theme", t), theme);
      const bg = await page.locator("#hjem").evaluate((el) => getComputedStyle(el).backgroundImage);
      expect(bg).toContain("hero-galdhopiggen");
    }
  });

  test("saved theme is restored on reload and on other pages", async ({ page }) => {
    await choose(page, "hadean");
    await page.reload();
    await expect(page.locator("html")).toHaveAttribute("data-theme", "hadean");
    await page.goto(BACHELOR_URL);
    await expect(page.locator("html")).toHaveAttribute("data-theme", "hadean");
    await expect(page.locator('.theme-option[data-theme-value="hadean"]')).toHaveAttribute("aria-pressed", "true");
  });

  for (const [old, now] of [["dark", "cretaceous"], ["light", "quaternary"], ["white", "quaternary"], ["green", "cambrian"], ["purple", "hadean"]]) {
    test(`a choice saved under the old name ${old} becomes ${now}`, async ({ page }) => {
      await page.evaluate((v) => localStorage.setItem("theme", v), old);
      await page.goto(PAGE_URL);
      await expect(page.locator("html")).toHaveAttribute("data-theme", now);
      expect(await page.evaluate(() => localStorage.getItem("theme"))).toBe(now);
    });
  }

  test("Escape closes the menu and returns focus", async ({ page }) => {
    await page.click("#theme-toggle");
    await page.keyboard.press("Escape");
    await expect(page.locator("#theme-menu")).toBeHidden();
    await expect(page.locator("#theme-toggle")).toHaveAttribute("aria-expanded", "false");
    await expect(page.locator("#theme-toggle")).toBeFocused();
  });

  test("arrow keys move between periods and Enter picks one", async ({ page }) => {
    await page.focus("#theme-toggle");
    await page.keyboard.press("Enter");
    await page.keyboard.press("ArrowDown");
    await expect(page.locator('.theme-option[data-theme-value="quaternary"]')).toBeFocused();
    await page.keyboard.press("ArrowDown");
    await expect(page.locator('.theme-option[data-theme-value="hadean"]')).toBeFocused();
    await page.keyboard.press("ArrowUp");
    await page.keyboard.press("Home");
    await expect(page.locator('.theme-option[data-theme-value="hadean"]')).toBeFocused();
    await page.keyboard.press("End");
    await expect(page.locator('.theme-option[data-theme-value="quaternary"]')).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(page.locator("html")).toHaveAttribute("data-theme", "quaternary");
  });

  test("clicking outside closes the menu without changing the theme", async ({ page }) => {
    await page.click("#theme-toggle");
    await page.mouse.click(10, 400);
    await expect(page.locator("#theme-menu")).toBeHidden();
    await expect(page.locator("html")).toHaveAttribute("data-theme", "cretaceous");
  });

  test("period names follow the language", async ({ page }) => {
    await page.click(".lang-toggle");
    await expect(page.locator("#theme-toggle")).toHaveAttribute("aria-label", "Choose colour theme");
    await expect(page.locator(".theme-menu-title")).toHaveText("Geological period");
    await expect(page.locator(".theme-label > span")).toHaveText(["Hadean", "Cambrian", "Cretaceous", "Quaternary"]);
    await expect(page.locator(".theme-label small").last()).toHaveText("2.6 million years ago – today");
  });

  test("works on the mobile layout", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto(PAGE_URL);
    await choose(page, "cambrian");
    await expect(page.locator("html")).toHaveAttribute("data-theme", "cambrian");
    await expect(page.locator("#theme-menu")).toBeHidden();
  });

  test("the open menu fits on a small phone", async ({ page }) => {
    await page.setViewportSize({ width: 320, height: 568 });
    await page.goto(PAGE_URL);
    await page.click("#theme-toggle");
    const box = await page.locator("#theme-menu").boundingBox();
    expect(box.x).toBeGreaterThanOrEqual(0);
    expect(box.x + box.width).toBeLessThanOrEqual(320);
    expect(box.y + box.height).toBeLessThanOrEqual(568);
  });

  test("an unknown saved value falls back to the system preference", async ({ page }) => {
    await page.evaluate(() => localStorage.setItem("theme", "neon"));
    await page.emulateMedia({ colorScheme: "light" });
    await page.goto(PAGE_URL);
    await expect(page.locator("html")).toHaveAttribute("data-theme", "quaternary");
  });

  test("respects prefers-color-scheme light when no saved preference", async ({ page }) => {
    await page.evaluate(() => localStorage.removeItem("theme"));
    await page.emulateMedia({ colorScheme: "light" });
    await page.goto(PAGE_URL);
    await expect(page.locator("html")).toHaveAttribute("data-theme", "quaternary");
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
      document.documentElement.setAttribute("data-theme", "cretaceous");
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
      document.documentElement.setAttribute("data-theme", "quaternary");
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

test.describe("About me photos", () => {
  test("only the profile photo is left; the three small photos and the viewer are gone", async ({ page }) => {
    await page.goto(PAGE_URL);
    await expect(page.locator("#om-meg img")).toHaveCount(1);
    await expect(page.locator(".about-sub-gallery")).toHaveCount(0);
    await expect(page.locator("#lightbox")).toHaveCount(0);
    await expect(page.locator("[data-lightbox]")).toHaveCount(0);
  });
});

test.describe("About me mountain background", () => {
  const VIEWPORTS = [[2560, 1080], [1920, 1080], [1440, 900], [1280, 800], [1024, 768], [820, 1180], [390, 844], [375, 667], [320, 568]];
  const PERIODS = ["hadean", "cambrian", "cretaceous", "quaternary"];
  const LAYERS = ["haze", "right-towers", "left-towers", "snow", "hills", "fore"];

  function measure() {
    const section = document.querySelector("#om-meg").getBoundingClientRect();
    const next = document.querySelector("#bakgrunn").getBoundingClientRect();
    const svgEl = document.querySelector("#om-meg .about-scene");
    const svg = svgEl.getBoundingClientRect();
    const leftTop = svgEl.querySelector(".left-towers").getBoundingClientRect().top;
    const rightTop = svgEl.querySelector(".right-towers").getBoundingClientRect().top;
    const boxes = [];
    document.querySelectorAll("#om-meg h2, #om-meg p").forEach((el) => {
      const range = document.createRange();
      range.selectNodeContents(el);
      Array.from(range.getClientRects()).forEach((b) => boxes.push(b));
    });
    boxes.push(document.querySelector("#om-meg .media-col img").getBoundingClientRect());
    return {
      section: { top: section.top, bottom: section.bottom, left: section.left, right: section.right, height: section.height },
      next: next.top,
      svg: { top: svg.top, bottom: svg.bottom, left: svg.left, right: svg.right, height: svg.height },
      leftTop, rightTop,
      contentBottom: Math.max(...boxes.map((b) => b.bottom)),
    };
  }

  test("is the traced picture in depth layers over a gradient sky, hidden from screen readers", async ({ page }) => {
    await page.goto(PAGE_URL);
    const svg = page.locator("#om-meg svg.about-scene");
    await expect(svg).toHaveAttribute("aria-hidden", "true");
    for (const layer of LAYERS) {
      expect(await svg.locator(`g.${layer} > path`).count(), layer).toBeGreaterThan(0);
    }
    // the banded sky of the source is replaced by one smooth gradient
    await expect(svg.locator("rect.sky")).toHaveAttribute("fill", "url(#about-sky)");
    expect(await svg.locator("#about-sky stop").count()).toBeGreaterThanOrEqual(3);
    // the right towers are moved back to the depth of the left ones
    await expect(svg.locator("g.right-towers")).toHaveAttribute("transform", /scale\(/);
    await expect(page.locator("#om-meg .about-sun, #om-meg .about-mountains")).toHaveCount(0);
  });

  for (const [width, height] of VIEWPORTS) {
    test(`scene stands on the border to Bakgrunn, below the text, at ${width}x${height}`, async ({ page }) => {
      await page.setViewportSize({ width, height });
      await page.goto(PAGE_URL);
      await page.evaluate(() => document.querySelectorAll(".reveal").forEach((el) => el.classList.add("visible")));
      await page.waitForTimeout(700);
      const r = await page.evaluate(measure);
      // rests on the border and fills the width
      expect(Math.abs(r.section.bottom - r.svg.bottom)).toBeLessThanOrEqual(1);
      expect(Math.abs(r.next - r.section.bottom)).toBeLessThanOrEqual(1);
      expect(r.svg.left - r.section.left).toBeLessThanOrEqual(0.5);
      expect(r.section.right - r.svg.right).toBeLessThanOrEqual(0.5);
      // the towers start below the text and photo, and below the faded sky
      const towersTop = Math.min(r.leftTop, r.rightTop);
      expect(towersTop).toBeGreaterThanOrEqual(r.contentBottom);
      expect(towersTop).toBeGreaterThanOrEqual(r.svg.top + 0.11 * r.svg.height);
      // the scene fills the room below the text, from the border upwards
      const share = (r.section.bottom - towersTop) / r.section.height;
      expect(share).toBeGreaterThan(0.15);
      expect(share).toBeLessThan(0.62);
      // the right-hand towers stand at the same depth as the left ones
      expect(Math.abs(r.rightTop - r.leftTop)).toBeLessThanOrEqual(0.06 * r.svg.height);
      // on laptops and desktops the section is as tall as it was with the
      // three photos under the text (980 px)
      if (width >= 1280) expect(Math.abs(r.section.height - 980)).toBeLessThanOrEqual(20);
    });
  }

  test("the scene is repainted by every colour theme, and every shape has a colour", async ({ page }) => {
    await page.goto(PAGE_URL);
    const fills = new Set();
    const skies = new Set();
    for (const theme of PERIODS) {
      await page.evaluate((t) => document.documentElement.setAttribute("data-theme", t), theme);
      const r = await page.evaluate(() => {
        const paths = Array.from(document.querySelectorAll("#om-meg .about-scene path"));
        // a class without a colour for this theme would fall back to black
        const missing = paths.filter((el) => getComputedStyle(el).fill === "rgb(0, 0, 0)").map((el) => el.getAttribute("class"));
        return {
          missing,
          tower: getComputedStyle(document.querySelector("#om-meg .left-towers path")).fill,
          sky: Array.from(document.querySelectorAll("#about-sky stop")).map((el) => getComputedStyle(el).stopColor).join(),
        };
      });
      expect(r.missing, theme).toEqual([]);
      fills.add(r.tower);
      skies.add(r.sky);
    }
    expect(fills.size).toBe(PERIODS.length);
    expect(skies.size).toBe(PERIODS.length);
  });

  for (const theme of PERIODS) {
    test(`text stays readable over the sky in the ${theme} theme`, async ({ page }) => {
      await page.goto(PAGE_URL);
      await page.evaluate((t) => document.documentElement.setAttribute("data-theme", t), theme);
      const worst = await page.evaluate(() => {
        const ctx = document.createElement("canvas").getContext("2d", { willReadFrequently: true });
        function rgb(str) {
          ctx.clearRect(0, 0, 1, 1);
          ctx.fillStyle = "#000";
          ctx.fillStyle = str;
          ctx.fillRect(0, 0, 1, 1);
          const [r, g, b] = ctx.getImageData(0, 0, 1, 1).data;
          return { r, g, b };
        }
        function lum(c) {
          const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
          return 0.2126 * f(c.r) + 0.7152 * f(c.g) + 0.0722 * f(c.b);
        }
        function contrast(a, b) {
          const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p);
          return (x + 0.05) / (y + 0.05);
        }
        const text = rgb(getComputedStyle(document.querySelector("#om-meg .text-col p")).color);
        // the text only ever sits over the upper sky (the towers start 14 %
        // down the scene); check the sky down to 30 % and the section itself
        const sky = Array.from(document.querySelectorAll("#about-sky stop"))
          .filter((el) => parseFloat(el.getAttribute("offset")) <= 0.3)
          .map((el) => rgb(getComputedStyle(el).stopColor));
        if (sky.length < 2) return 0;
        const bg = rgb(getComputedStyle(document.querySelector("#om-meg")).backgroundColor);
        return Math.min(...sky.concat([bg]).map((c) => contrast(text, c)));
      });
      expect(worst).toBeGreaterThanOrEqual(4.5);
    });
  }
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

  test("About text no longer repeats the bachelor paragraph, in either language", async ({ page }) => {
    await page.goto(PAGE_URL);
    await expect(page.locator('[data-i18n="about.background.text"]')).toHaveCount(0);
    await expect(page.locator("#om-meg .text-col p")).toHaveCount(2);
    await expect(page.locator("#om-meg")).not.toContainText("treårige bachelorgraden");
    await page.locator(".lang-toggle").first().click();
    await expect(page.locator("html")).toHaveAttribute("lang", "en");
    await expect(page.locator("#om-meg")).not.toContainText("three-year bachelor");
  });

  test("the profile photo is smaller: 250 px wide on desktop, 220 px on phones", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto(PAGE_URL);
    let box = await page.locator("#om-meg .media-col img").boundingBox();
    expect(Math.round(box.width)).toBeLessThanOrEqual(250);
    expect(box.width).toBeGreaterThan(200);
    await page.setViewportSize({ width: 390, height: 844 });
    box = await page.locator("#om-meg .media-col img").boundingBox();
    expect(Math.round(box.width)).toBeLessThanOrEqual(220);
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
