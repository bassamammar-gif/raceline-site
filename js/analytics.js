/**
 * Google Analytics 4 wiring.
 *
 * RLM_GA_ID is empty until the owner supplies the Measurement ID from
 * analytics.google.com (looks like "G-XXXXXXXXXX") — with it empty this whole
 * file is a no-op, so it's safe to ship ahead of the account existing.
 *
 * Also gated off localhost so local development never pollutes the real data.
 *
 * Custom events (the numbers that actually matter to the business):
 *  - whatsapp_click { context }  — every WhatsApp CTA, tagged by which one
 *  - instagram_click             — any outbound Instagram link
 *  - language_switch { to }     — the عربي/EN toggle
 */
(() => {
  const RLM_GA_ID = "G-RESHFTPE7H";

  if (!RLM_GA_ID) return;
  if (/^(localhost|127\.|0\.0\.0\.0)/.test(location.hostname)) return;

  // standard gtag bootstrap
  const s = document.createElement("script");
  s.async = true;
  s.src = "https://www.googletagmanager.com/gtag/js?id=" + RLM_GA_ID;
  document.head.appendChild(s);
  window.dataLayer = window.dataLayer || [];
  function gtag() { window.dataLayer.push(arguments); }
  window.gtag = gtag;
  gtag("js", new Date());
  gtag("config", RLM_GA_ID, { language: window.RLM_LANG || "en" });

  // conversion events
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
