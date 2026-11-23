/*
 * Runs synchronously in <head>, before first paint.
 * - Marks the document as JS-enabled (enables reveal animations).
 * - Applies the saved colour theme, or the operating system preference, so
 *   the page never flashes the wrong colours.
 *
 * data-theme is one of dark, light, purple, green, white.
 * data-mode is dark or light and drives the few styles shared by all
 * light (light, white) or all dark (dark, purple, green) themes.
 */
(function () {
  var root = document.documentElement;
  root.classList.add("js");

  var MODES = { dark: "dark", light: "light", purple: "dark", green: "dark", white: "light" };

  var theme = null;
  try { theme = localStorage.getItem("theme"); } catch (e) { /* storage unavailable */ }

  if (!theme || !Object.prototype.hasOwnProperty.call(MODES, theme)) {
    theme = window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
  }
  root.setAttribute("data-theme", theme);
  root.setAttribute("data-mode", MODES[theme]);

  var lang = null;
  try { lang = localStorage.getItem("lang"); } catch (e) { /* storage unavailable */ }
  if (lang === "en" || lang === "nb") root.lang = lang;
})();
