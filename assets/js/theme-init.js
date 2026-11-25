/*
 * Runs synchronously in <head>, before first paint.
 * - Marks the document as JS-enabled (enables reveal animations).
 * - Applies the saved colour theme, or the operating system preference, so
 *   the page never flashes the wrong colours.
 *
 * data-theme is a geological period: hadean, cambrian, cretaceous or
 * quaternary. data-mode is dark or light and drives the few styles shared by
 * all dark (hadean, cambrian, cretaceous) or light (quaternary) themes.
 * Choices saved under the old names (dark, light, ...) are carried over.
 */
(function () {
  var root = document.documentElement;
  root.classList.add("js");

  var MODES = { hadean: "dark", cambrian: "dark", cretaceous: "dark", quaternary: "light" };
  var OLD = { dark: "cretaceous", light: "quaternary", white: "quaternary", green: "cambrian", purple: "hadean" };

  var theme = null;
  try { theme = localStorage.getItem("theme"); } catch (e) { /* storage unavailable */ }
  if (theme && Object.prototype.hasOwnProperty.call(OLD, theme)) theme = OLD[theme];

  if (!theme || !Object.prototype.hasOwnProperty.call(MODES, theme)) {
    theme = window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches ? "quaternary" : "cretaceous";
  }
  root.setAttribute("data-theme", theme);
  root.setAttribute("data-mode", MODES[theme]);

  var lang = null;
  try { lang = localStorage.getItem("lang"); } catch (e) { /* storage unavailable */ }
  if (lang === "en" || lang === "nb") root.lang = lang;
})();
