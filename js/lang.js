/**
 * Language switch: English is the page default; Arabic is applied on top.
 * The choice persists in localStorage and switching reloads the page so the
 * dynamic sections (calendar, achievements, countdown) re-render in the new
 * language — much simpler and more robust than live re-rendering.
 *
 * MUST load after data/i18n.js and before every render script and main.js:
 * the static-text swap has to happen before main.js splits headlines into
 * .word spans, and RLM_T must exist before the renderers run.
 */
(() => {
  const LANG_KEY = "rlm-lang";
  window.RLM_LANG = localStorage.getItem(LANG_KEY) === "ar" ? "ar" : "en";
  const isAr = window.RLM_LANG === "ar";

  window.RLM_T = (key, fallback) =>
    (isAr && window.RLM_I18N_AR && window.RLM_I18N_AR[key]) || fallback;

  if (isAr) {
    document.documentElement.lang = "ar";
    document.documentElement.dir = "rtl";
    if (window.RLM_I18N_AR["meta.title"]) document.title = window.RLM_I18N_AR["meta.title"];
    document.querySelectorAll("[data-i18n]").forEach((el) => {
      const t = window.RLM_I18N_AR[el.dataset.i18n];
      if (t) el.innerHTML = t;
    });
  }

  const toggle = document.querySelector("[data-lang-toggle]");
  if (toggle) {
    toggle.textContent = isAr ? "EN" : "عربي";
    toggle.setAttribute("aria-label", isAr ? "Switch to English" : "التبديل إلى العربية");
    toggle.addEventListener("click", () => {
      localStorage.setItem(LANG_KEY, isAr ? "en" : "ar");
      location.reload();
    });
  }
})();
