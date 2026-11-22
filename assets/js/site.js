/*
 * Shared behaviour for every page:
 *   - Norwegian/English translations (strings live in each page's
 *     <script type="application/json" id="i18n-data"> block)
 *   - dark/light theme toggle
 *   - scroll reveal animation
 *   - active section highlighting in the navigation
 *   - mobile (hamburger) menu
 *   - image lightbox (only on pages that have one)
 *
 * Plain ES5, no dependencies, no inline event handlers (keeps the
 * Content-Security-Policy strict: script-src 'self').
 */
(function () {
  "use strict";

  var root = document.documentElement;

  function storageGet(key) {
    try { return localStorage.getItem(key); } catch (e) { return null; }
  }

  function storageSet(key, value) {
    try { localStorage.setItem(key, value); } catch (e) { /* storage unavailable */ }
  }

  function forEach(list, fn) {
    Array.prototype.forEach.call(list, fn);
  }

  /* ── Translations ── */
  var translations = {};
  var dataEl = document.getElementById("i18n-data");
  if (dataEl) {
    try {
      translations = JSON.parse(dataEl.textContent);
    } catch (e) {
      if (window.console) console.error("Could not parse translations", e);
    }
  }

  function currentDict() {
    return translations[root.lang] || translations.nb || {};
  }

  function setMeta(selector, value) {
    var el = document.querySelector(selector);
    if (el && value) el.setAttribute("content", value);
  }

  function setLanguage(lang) {
    var dict = translations[lang];
    if (!dict) return;

    root.lang = lang;
    storageSet("lang", lang);

    if (dict["page.title"]) document.title = dict["page.title"];
    setMeta('meta[name="description"]', dict["meta.description"]);
    setMeta('meta[property="og:title"]', dict["page.title"]);
    setMeta('meta[property="og:description"]', dict["meta.description"]);
    setMeta('meta[property="og:locale"]', lang === "en" ? "en_US" : "nb_NO");
    setMeta('meta[property="og:locale:alternate"]', lang === "en" ? "nb_NO" : "en_US");

    forEach(document.querySelectorAll("[data-i18n]"), function (el) {
      var value = dict[el.getAttribute("data-i18n")];
      if (value != null) el.textContent = value;
    });

    // Only used for static, author-written strings that contain markup
    // (links, line breaks, the course table). Never feed user input here.
    forEach(document.querySelectorAll("[data-i18n-html]"), function (el) {
      var value = dict[el.getAttribute("data-i18n-html")];
      if (value != null) el.innerHTML = value;
    });

    forEach(document.querySelectorAll("[data-i18n-alt]"), function (el) {
      var value = dict[el.getAttribute("data-i18n-alt")];
      if (value != null) el.alt = value;
    });

    forEach(document.querySelectorAll("[data-i18n-aria-label]"), function (el) {
      var value = dict[el.getAttribute("data-i18n-aria-label")];
      if (value != null) el.setAttribute("aria-label", value);
    });
  }

  var langToggle = document.querySelector(".lang-toggle");
  if (langToggle) {
    langToggle.addEventListener("click", function () {
      setLanguage(root.lang === "en" ? "nb" : "en");
    });
  }

  var savedLang = storageGet("lang");
  setLanguage(savedLang && translations[savedLang] ? savedLang : (root.lang in translations ? root.lang : "nb"));

  /* ── Theme toggle ── */
  (function () {
    var toggle = document.getElementById("theme-toggle");
    if (!toggle) return;

    function applyTheme(theme, persist) {
      root.setAttribute("data-theme", theme);
      if (persist) storageSet("theme", theme);

      var ariaKey = theme === "light" ? "theme.toggle.light" : "theme.toggle.dark";
      toggle.setAttribute("data-i18n-aria-label", ariaKey);
      var label = currentDict()[ariaKey];
      if (label != null) toggle.setAttribute("aria-label", label);
    }

    toggle.addEventListener("click", function () {
      applyTheme(root.getAttribute("data-theme") === "light" ? "dark" : "light", true);
    });

    // theme-init.js already picked saved > system preference > dark.
    // Only an explicit click is persisted, so visitors who never choose
    // keep following their operating system setting.
    var saved = storageGet("theme");
    if (saved === "light" || saved === "dark") {
      applyTheme(saved, false);
    } else {
      applyTheme(root.getAttribute("data-theme") === "light" ? "light" : "dark", false);
    }
  })();

  /* Re-enable transitions once the initial theme is in place */
  requestAnimationFrame(function () {
    document.body.classList.remove("no-transition");
  });

  /* ── Hero fade-in (index page only) ── */
  var hero = document.getElementById("hjem");
  if (hero) {
    requestAnimationFrame(function () { hero.classList.add("loaded"); });
  }

  /* ── Scroll reveal ── */
  (function () {
    var reveals = document.querySelectorAll(".reveal");
    if (!("IntersectionObserver" in window)) {
      forEach(reveals, function (el) { el.classList.add("visible"); });
      return;
    }
    var obs = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add("visible");
          obs.unobserve(entry.target);
        }
      });
    }, { threshold: 0.15 });
    forEach(reveals, function (el) { obs.observe(el); });
  })();

  /* ── Active nav highlighting (in-page links only) ── */
  (function () {
    var sections = document.querySelectorAll("section[id]");
    var navLinks = document.querySelectorAll('nav ul a[href^="#"]');
    if (!sections.length || !navLinks.length) return;

    var scrollLocked = false;
    var unlockTimer = null;

    var linkedIds = {};
    forEach(navLinks, function (link) { linkedIds[link.getAttribute("href").substring(1)] = true; });

    function setActive(id) {
      forEach(navLinks, function (link) {
        var isActive = link.getAttribute("href") === "#" + id;
        link.classList.toggle("nav-active", isActive);
        if (isActive) {
          link.setAttribute("aria-current", "location");
        } else {
          link.removeAttribute("aria-current");
        }
      });
    }

    // Work out the current section from scratch on every scroll, in both
    // directions: it is the last section whose top has passed a line 30 %
    // down the viewport (or the last section once the page bottom is
    // reached). A section without its own nav link (Kontakt) keeps the
    // link of the nearest section above it highlighted.
    function update() {
      if (scrollLocked) return;
      var line = window.innerHeight * 0.3;
      var index = 0;
      for (var i = 0; i < sections.length; i++) {
        if (sections[i].getBoundingClientRect().top <= line) index = i;
      }
      if ((window.innerHeight + window.scrollY) >= (document.documentElement.scrollHeight - 2)) {
        index = sections.length - 1;
      }
      while (index > 0 && !linkedIds[sections[index].id]) index--;
      setActive(sections[index].id);
    }

    // Highlight a clicked link immediately and pause tracking while the
    // smooth scroll is running.
    forEach(navLinks, function (link) {
      link.addEventListener("click", function () {
        setActive(link.getAttribute("href").substring(1));
        scrollLocked = true;
        clearTimeout(unlockTimer);
        unlockTimer = setTimeout(function () { scrollLocked = false; update(); }, 800);
      });
    });

    var ticking = false;
    function onScroll() {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(function () {
        ticking = false;
        update();
      });
    }
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    update();
  })();

  /* ── Mobile menu ── */
  (function () {
    var hamburger = document.getElementById("hamburger");
    var navMenu = document.getElementById("nav-menu");
    if (!hamburger || !navMenu) return;

    function isOpen() {
      return navMenu.classList.contains("nav-open");
    }

    function toggleMenu(open) {
      var next = open !== undefined ? open : !isOpen();
      navMenu.classList.toggle("nav-open", next);
      hamburger.classList.toggle("active", next);
      hamburger.setAttribute("aria-expanded", next ? "true" : "false");
    }

    hamburger.addEventListener("click", function () { toggleMenu(); });

    forEach(navMenu.querySelectorAll("a"), function (link) {
      link.addEventListener("click", function () { toggleMenu(false); });
    });

    document.addEventListener("click", function (e) {
      if (isOpen() && !e.target.closest("nav")) toggleMenu(false);
    });

    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && isOpen()) {
        toggleMenu(false);
        hamburger.focus();
      }
    });

    // Close the menu if the viewport grows past the mobile breakpoint
    if (window.matchMedia) {
      var desktop = window.matchMedia("(min-width: 769px)");
      var onChange = function (mq) { if (mq.matches) toggleMenu(false); };
      if (desktop.addEventListener) desktop.addEventListener("change", onChange);
      else if (desktop.addListener) desktop.addListener(onChange);
    }
  })();

  /* ── Lightbox (native <dialog>: focus trap, Escape and top layer for free) ── */
  (function () {
    var dialog = document.getElementById("lightbox");
    if (!dialog || typeof dialog.showModal !== "function") return;

    var img = document.getElementById("lightbox-img");
    var caption = document.getElementById("lightbox-caption");
    var closeBtn = dialog.querySelector(".lightbox-close");
    var opener = null;

    function open(thumb) {
      var thumbImg = thumb.querySelector("img");
      var thumbCaption = thumb.querySelector("figcaption");
      if (!thumbImg) return;
      opener = thumb;
      img.src = thumb.getAttribute("data-full") || thumbImg.currentSrc || thumbImg.src;
      img.alt = thumbImg.alt;
      caption.textContent = thumbCaption ? thumbCaption.textContent : "";
      dialog.showModal();
      document.body.style.overflow = "hidden";
      closeBtn.focus();
    }

    function close() {
      if (dialog.open) dialog.close();
    }

    dialog.addEventListener("close", function () {
      document.body.style.overflow = "";
      img.removeAttribute("src");
      if (opener) opener.focus();
    });

    closeBtn.addEventListener("click", close);

    // Clicking the dark backdrop (outside the image) closes the viewer
    dialog.addEventListener("click", function (e) {
      if (e.target === dialog) close();
    });

    forEach(document.querySelectorAll("[data-lightbox]"), function (thumb) {
      thumb.addEventListener("click", function () { open(thumb); });
      thumb.addEventListener("keydown", function (e) {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          open(thumb);
        }
      });
    });
  })();
})();
