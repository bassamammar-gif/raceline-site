/**
 * Centralized WhatsApp deep-link config.
 * Confirmed number: +201225388501 (all 5 contexts share it — one WhatsApp line).
 */
window.RLM_WHATSAPP_LINKS = {
  "general-contact": { phone: "201225388501", message: "Hey Race Line! 👋 I'd love to know more about what you guys do." },
  "academy-enroll": { phone: "201225388501", message: "Hey! I'm keen to join Race Line Academy — how do I get started? 🏁" },
  "iame-series-inquiry": { phone: "201225388501", message: "Hey! Want to find out more about racing IAME Series Egypt — dates, categories, sign-up 🏎️" },
  "equipment-inquiry": { phone: "201225388501", message: "Hi! Interested in IAME engines / LN Racing Kart chassis — can you help with pricing and availability?" },
  "team-inquiry": { phone: "201225388501", message: "Hi! I'd love to chat about the Race Line Motorsports team." },
  "floating-button": { phone: "201225388501", message: "Hey Race Line! 👋 I'd love to know more about what you guys do." },
};

function rlmBuildWhatsAppHref(config) {
  return `https://wa.me/${config.phone}?text=${encodeURIComponent(config.message)}`;
}

(() => {
  document.querySelectorAll("[data-whatsapp-cta]").forEach((el) => {
    const key = el.dataset.whatsappCta;
    const config = window.RLM_WHATSAPP_LINKS[key];
    if (!config) return;
    el.setAttribute("href", rlmBuildWhatsAppHref(config));
  });

  // Context-aware floating button: swap its message to match whichever section is in view.
  const floatBtn = document.querySelector('[data-whatsapp-cta="floating-button"]');
  if (!floatBtn) return;

  const sectionContextMap = {
    hero: "general-contact",
    equipment: "equipment-inquiry",
    calendar: "iame-series-inquiry",
    academy: "academy-enroll",
    team: "team-inquiry",
    achievements: "general-contact",
    gallery: "general-contact",
    instagram: "general-contact",
    contact: "general-contact",
  };

  const sectionObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        const key = sectionContextMap[entry.target.id];
        const config = key && window.RLM_WHATSAPP_LINKS[key];
        if (config) floatBtn.setAttribute("href", rlmBuildWhatsAppHref(config));
      });
    },
    { threshold: 0.5 }
  );

  Object.keys(sectionContextMap).forEach((id) => {
    const el = document.getElementById(id);
    if (el) sectionObserver.observe(el);
  });
})();
