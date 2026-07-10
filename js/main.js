(() => {
  const motionOverride = new URLSearchParams(window.location.search).get("motion") === "on";
  const prefersReducedMotion = motionOverride
    ? false
    : window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* --------------------------------------------------------------------
     Mobile nav toggle
     -------------------------------------------------------------------- */
  const navToggle = document.querySelector(".site-nav__toggle");
  const navLinks = document.querySelector(".site-nav__links");
  if (navToggle && navLinks) {
    navToggle.addEventListener("click", () => {
      const isOpen = navLinks.classList.toggle("is-open");
      navToggle.setAttribute("aria-expanded", String(isOpen));
    });
  }

  /* --------------------------------------------------------------------
     Lazy videos (video[data-lazy]): the file only starts downloading after
     full page load, then loops automatically for everyone — no controls,
     no pause (owner's call: it's ambient footage, not playable media).
     -------------------------------------------------------------------- */
  document.querySelectorAll("video[data-lazy]").forEach((video) => {
    const source = video.querySelector("source[data-src]");
    if (!source) return;
    window.addEventListener("load", () => {
      source.src = source.dataset.src;
      video.load();
      video.play().catch(() => {});
    });
  });

  /* --------------------------------------------------------------------
     Word-split headlines (hero h1 + every section h2 marked data-split-words)
     -------------------------------------------------------------------- */
  document.querySelectorAll("[data-split-words]").forEach((el) => {
    const words = el.textContent.trim().split(/\s+/);
    el.innerHTML = words
      .map((w) => `<span class="word">${w}</span>`)
      .join(" ");
  });

  /* --------------------------------------------------------------------
     Animated stat counters (runs once per element, on view)
     -------------------------------------------------------------------- */
  function animateCounter(el) {
    const target = parseFloat(el.dataset.countTo || "0");
    const suffix = el.dataset.countSuffix || "";
    const duration = prefersReducedMotion ? 0 : 1400;
    const start = performance.now();

    if (duration === 0) {
      el.textContent = target + suffix;
      return;
    }

    function tick(now) {
      const progress = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      const value = Math.round(target * eased);
      el.textContent = value + suffix;
      if (progress < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  }

  const counterObserver = new IntersectionObserver(
    (entries, observer) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          animateCounter(entry.target);
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.4 }
  );
  document.querySelectorAll("[data-count-to]").forEach((el) => counterObserver.observe(el));

  /* --------------------------------------------------------------------
     Next-round countdown (runs regardless of motion preference — it's
     information, not decoration; the pulsing dot is killed by the global
     reduced-motion CSS rule)
     -------------------------------------------------------------------- */
  const countdownEl = document.querySelector("[data-countdown]");
  // calendar-render.js (loaded earlier) points data-countdown at the next
  // round, or clears it once the season is over — nothing to count then
  if (countdownEl && countdownEl.dataset.countdown) {
    const target = new Date(countdownEl.dataset.countdown).getTime();
    const slots = {
      days: countdownEl.querySelector("[data-countdown-days]"),
      hours: countdownEl.querySelector("[data-countdown-hours]"),
      mins: countdownEl.querySelector("[data-countdown-mins]"),
      secs: countdownEl.querySelector("[data-countdown-secs]"),
    };
    const pad = (n) => String(n).padStart(2, "0");
    let countdownInterval;
    const tick = () => {
      const diff = target - Date.now();
      if (diff <= 0) {
        slots.days.textContent = slots.hours.textContent = slots.mins.textContent = slots.secs.textContent = "00";
        if (countdownInterval) clearInterval(countdownInterval);
        return;
      }
      slots.days.textContent = pad(Math.floor(diff / 86400000));
      slots.hours.textContent = pad(Math.floor(diff / 3600000) % 24);
      slots.mins.textContent = pad(Math.floor(diff / 60000) % 60);
      slots.secs.textContent = pad(Math.floor(diff / 1000) % 60);
    };
    tick();
    countdownInterval = setInterval(tick, 1000);
  }

  /* --------------------------------------------------------------------
     GSAP + ScrollTrigger + Lenis wiring (libraries loaded via CDN in HTML)
     -------------------------------------------------------------------- */
  function initGsap() {
    // Preloader teardown must run on every path (including GSAP failing to
    // load), otherwise the overlay would block the whole site forever.
    const preloader = document.querySelector(".preloader");
    const finishPreloader = () => {
      if (!preloader || preloader.__done) return;
      preloader.__done = true;
      preloader.remove();
      document.dispatchEvent(new CustomEvent("rlm:preloader-done"));
    };
    setTimeout(finishPreloader, 4000); // safety net, whatever happens below

    if (typeof gsap === "undefined") {
      finishPreloader();
      return;
    }

    document.documentElement.classList.add("gsap-ready");

    if (typeof ScrollTrigger !== "undefined") {
      gsap.registerPlugin(ScrollTrigger);
    }

    // Smooth scroll via Lenis, skipped entirely under reduced motion
    let lenis;
    if (!prefersReducedMotion && typeof Lenis !== "undefined") {
      lenis = new Lenis({
        duration: 1.4,
        easing: (t) => 1 - Math.pow(1 - t, 4),
        smoothWheel: true,
        wheelMultiplier: 0.9,
      });
      lenis.on("scroll", ScrollTrigger && ScrollTrigger.update);
      gsap.ticker.add((time) => lenis.raf(time * 1000));
      gsap.ticker.lagSmoothing(0);
    }

    const heroMedia = document.querySelector(".hero__media img, .hero__media video");

    if (prefersReducedMotion) {
      // Reveal everything immediately, skip all scroll-triggered and entrance motion
      finishPreloader();
      gsap.set("[data-reveal]", { opacity: 1, y: 0 });
      gsap.set("[data-media-reveal]", { clipPath: "inset(0 0 0 0)" });
      gsap.set("[data-media-reveal] img", { scale: 1 });
      if (heroMedia) gsap.set(heroMedia, { scale: 1.08 });
      return;
    }

    // Preloader: logo fade-in, brief hold, then a clip-path wipe upward
    if (preloader) {
      const preloaderLogo = preloader.querySelector(".preloader__logo");
      gsap.timeline({ onComplete: finishPreloader })
        .fromTo(preloaderLogo, { opacity: 0, scale: 0.92 }, { opacity: 1, scale: 1, duration: 0.55, ease: "power2.out" })
        .to(preloader, { clipPath: "inset(0 0 100% 0)", duration: 0.7, ease: "power4.inOut", delay: 0.35 })
        .to(preloaderLogo, { opacity: 0, duration: 0.25 }, "<");
    }

    // Section stagger reveals
    document.querySelectorAll("[data-reveal-group]").forEach((group) => {
      const items = group.querySelectorAll("[data-reveal]");
      gsap.fromTo(
        items,
        { opacity: 0, y: 40 },
        {
          opacity: 1,
          y: 0,
          duration: 0.9,
          ease: "power3.out",
          stagger: 0.12,
          scrollTrigger: {
            trigger: group,
            start: "top 80%",
          },
        }
      );
    });

    // Hero title reveal (word-by-word for text, single rise for the logo
    // wordmark) — held until the preloader wipe finishes so the entrance is
    // actually seen, not spent behind the overlay
    const heroWords = document.querySelectorAll(".hero__title .word");
    const heroTitleTargets = [
      ...(heroWords.length ? heroWords : document.querySelectorAll(".hero__title--logo img")),
      ...document.querySelectorAll(".hero__slogan .word"),
    ];
    if (heroTitleTargets.length) {
      const heroEntrance = gsap.fromTo(
        heroTitleTargets,
        { yPercent: 120, opacity: 0 },
        { yPercent: 0, opacity: 1, duration: 1, ease: "power4.out", stagger: 0.06, paused: true }
      );
      if (!preloader || preloader.__done) {
        heroEntrance.play();
      } else {
        document.addEventListener("rlm:preloader-done", () => heroEntrance.play(), { once: true });
      }
    }

    // Section headline word reveal, scroll-triggered (every h2[data-split-words])
    document.querySelectorAll("h2[data-split-words] .word").forEach((word) => {
      const heading = word.closest("h2");
      gsap.fromTo(
        word,
        { yPercent: 120, opacity: 0 },
        {
          yPercent: 0,
          opacity: 1,
          duration: 0.9,
          ease: "power4.out",
          stagger: 0.04,
          scrollTrigger: {
            trigger: heading,
            start: "top 85%",
          },
        }
      );
    });

    // Hero parallax drift
    if (heroMedia) {
      gsap.to(heroMedia, {
        yPercent: 12,
        ease: "none",
        scrollTrigger: {
          trigger: ".hero",
          start: "top top",
          end: "bottom top",
          scrub: true,
        },
      });

      // Hero on-load scale-settle, then a continuous slow Ken Burns drift so the
      // hero never sits still (scale + horizontal drift; yPercent stays owned by
      // the scroll parallax above so the two never fight over a property)
      gsap.fromTo(heroMedia, { scale: 1.15 }, { scale: 1.08, duration: 1.8, ease: "power3.out", delay: 0.1 });
      gsap.to(heroMedia, {
        scale: 1.14,
        xPercent: 1.5,
        duration: 10,
        delay: 2,
        ease: "sine.inOut",
        yoyo: true,
        repeat: -1,
      });
    }

    // Clip-path curtain reveal + image scale-settle for card/gallery media
    document.querySelectorAll("[data-media-reveal]").forEach((container) => {
      const img = container.querySelector("img");
      const tl = gsap.timeline({
        scrollTrigger: {
          trigger: container,
          start: "top 88%",
          once: true,
        },
      });
      tl.fromTo(container, { clipPath: "inset(100% 0 0 0)" }, { clipPath: "inset(0% 0 0 0)", duration: 1.1, ease: "power4.inOut" });
      if (img) {
        gsap.set(img, { scale: 1.15 });
        tl.to(img, { scale: 1, duration: 1.1, ease: "power4.out" }, "<");
      }
    });

    // Mouse-tracking zoom + pan on hover for card/gallery media — inspired by lnracingkart.com
    document.querySelectorAll(".equipment-card__media, .team-card__media, .achievement-row__media, .gallery__item").forEach((container) => {
      const img = container.querySelector("img");
      if (!img) return;
      const xTo = gsap.quickTo(img, "xPercent", { duration: 0.7, ease: "power3.out" });
      const yTo = gsap.quickTo(img, "yPercent", { duration: 0.7, ease: "power3.out" });

      container.addEventListener("mouseenter", () => gsap.to(img, { scale: 1.15, duration: 0.5, ease: "power3.out" }));
      container.addEventListener("mousemove", (e) => {
        const rect = container.getBoundingClientRect();
        const relX = (e.clientX - rect.left) / rect.width - 0.5;
        const relY = (e.clientY - rect.top) / rect.height - 0.5;
        xTo(relX * -12);
        yTo(relY * -12);
      });
      container.addEventListener("mouseleave", () => {
        gsap.to(img, { scale: 1, duration: 0.5, ease: "power3.out" });
        xTo(0);
        yTo(0);
      });
    });

    // Gallery strip scrolls natively (drag/swipe sideways), same interaction as
    // the Instagram strip — the pinned scroll-scrub variant was retired after
    // it repeatedly confused real users into thinking the page was stuck.

    // Oversized section numerals drift slower than the content (depth parallax)
    document.querySelectorAll(".section-num").forEach((num) => {
      gsap.fromTo(
        num,
        { yPercent: -25 },
        {
          yPercent: 45,
          ease: "none",
          scrollTrigger: {
            trigger: num.parentElement,
            start: "top bottom",
            end: "bottom top",
            scrub: true,
          },
        }
      );
    });

    // Marquee infinite scroll. xPercent, not a measured pixel distance: the
    // track holds two identical item sets, so -50% is always exactly one set
    // and the loop stays seamless even if the webfont loads after init or the
    // viewport resizes (a once-measured scrollWidth went stale in both cases).
    document.querySelectorAll(".marquee__track").forEach((track) => {
      gsap.to(track, {
        xPercent: -50,
        duration: 18,
        ease: "none",
        repeat: -1,
      });
    });

    // Magnetic hover on primary/ghost buttons
    document.querySelectorAll(".btn--primary, .btn--ghost").forEach((btn) => {
      const xTo = gsap.quickTo(btn, "x", { duration: 0.4, ease: "power3.out" });
      const yTo = gsap.quickTo(btn, "y", { duration: 0.4, ease: "power3.out" });
      btn.addEventListener("mousemove", (e) => {
        const rect = btn.getBoundingClientRect();
        xTo((e.clientX - rect.left - rect.width / 2) * 0.3);
        yTo((e.clientY - rect.top - rect.height / 2) * 0.3);
      });
      btn.addEventListener("mouseleave", () => {
        xTo(0);
        yTo(0);
      });
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initGsap);
  } else {
    initGsap();
  }
})();
