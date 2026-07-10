(() => {
  const list = document.getElementById("achievements-list");
  if (!list || !window.RLM_ACHIEVEMENTS) return;

  // js/lang.js defines RLM_T (returns the fallback when the language is English)
  const T = window.RLM_T || ((key, fallback) => fallback);

  const placeWordEn = { 1: "1st", 2: "2nd", 3: "3rd", 4: "4th", 5: "5th" };
  const placeWord = (place) => T("achievements.place." + place, placeWordEn[place] || String(place));
  // gold for wins, silver for podium places; anything below the podium keeps
  // the plain badge (no medal color)
  const placeModifier = (place) =>
    place === 1 ? " achievement-row__place--gold" : place <= 3 ? " achievement-row__place--silver" : "";
  const results = window.RLM_ACHIEVEMENTS;

  results.forEach((r) => {
    const row = document.createElement("article");
    row.className = "achievement-row";
    row.setAttribute("data-reveal", "");
    row.innerHTML = `
      <div class="achievement-row__year">${r.year}</div>
      <div class="achievement-row__series">
        <p class="achievement-row__series-name">${T("achievements.series." + r.series, r.series)}</p>
        <p class="achievement-row__category">${T("achievements.cat." + r.category, r.category)}</p>
      </div>
      <div class="achievement-row__place${placeModifier(r.place)}">
        <span class="achievement-row__place-num">${placeWord(r.place)}</span>
        <span class="achievement-row__place-label">${T("achievements.place", "Place")}</span>
      </div>
      <div class="achievement-row__driver">
        <span class="achievement-row__driver-first">${r.driver}</span>
        <span class="achievement-row__driver-last">${r.driverLast}</span>
      </div>
      <div class="achievement-row__media" data-media-reveal>
        <img src="${r.image}" alt="${r.driver} ${r.driverLast}" width="600" height="750" loading="lazy"${r.imagePosition ? ` style="object-position: ${r.imagePosition};"` : ""} />
      </div>
    `;
    list.appendChild(row);
  });

  // Aspirational stat strip: championship titles (from results), total podiums + years (manual overrides)
  const titlesEl = document.querySelector('[data-achievement-stat="titles"]');
  const podiumCountEl = document.querySelector('[data-achievement-stat="podiums"]');
  const yearsEl = document.querySelector('[data-achievement-stat="years"]');

  // titles = podium finishes in a championship (1st–3rd); results below the
  // podium appear in the ledger but don't count as titles
  if (titlesEl) titlesEl.setAttribute("data-count-to", String(results.filter((r) => r.place <= 3).length));
  if (podiumCountEl) podiumCountEl.setAttribute("data-count-to", String(window.RLM_ACHIEVEMENT_TOTAL_PODIUMS || 0));
  if (yearsEl) yearsEl.textContent = window.RLM_ACHIEVEMENT_YEARS_LABEL || "";
})();
