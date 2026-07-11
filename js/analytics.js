/**
 * Google Analytics 4 — custom business events.
 *
 * The gtag bootstrap itself lives verbatim in <head> (Google's official
 * snippet, kept unmodified so GA4's tag detector recognises the install).
 * This file adds the events that matter to the business on top of it:
 *
 *  - whatsapp_click { context }  — every WhatsApp CTA, tagged by which one
 *  - instagram_click             — any outbound Instagram link
 *  - language_switch { to }      — the عربي/EN toggle
 */
(() => {
  if (typeof window.gtag !== "function") return;

  document.addEventListener("click", (e) => {
    const wa = e.target.closest("[data-whatsapp-cta]");
    if (wa) {
      gtag("event", "whatsapp_click", { context: wa.dataset.whatsappCta });
      return;
    }
    const ig = e.target.closest('a[href*="instagram.com"]');
    if (ig) {
      gtag("event", "instagram_click", {});
      return;
    }
    const lang = e.target.closest("[data-lang-toggle]");
    if (lang) {
      gtag("event", "language_switch", { to: window.RLM_LANG === "ar" ? "en" : "ar" });
    }
  });
})();
