/*
 * Runs synchronously in <head>, before first paint.
 * - Marks the document as JS-enabled (enables reveal animations).
 * - Applies the saved theme, or the operating system preference, so the
 *   page never flashes the wrong colour scheme.
 */
(function () {
  var root = document.documentElement;
  root.classList.add("js");

  var theme = null;
  try { theme = localStorage.getItem("theme"); } catch (e) { /* storage unavailable */ }

  if (theme !== "light" && theme !== "dark") {
    theme = window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
  }
  root.setAttribute("data-theme", theme);

  var lang = null;
  try { lang = localStorage.getItem("lang"); } catch (e) { /* storage unavailable */ }
  if (lang === "en" || lang === "nb") root.lang = lang;
})();
