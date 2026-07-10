(() => {
  const board = document.getElementById("calendar-board");
  if (!board || !window.RLM_CALENDAR) return;

  // js/lang.js defines RLM_T (returns the fallback when the language is English)
  const T = window.RLM_T || ((key, fallback) => fallback);
  const isAr = window.RLM_LANG === "ar";

  const dateFormatter = new Intl.DateTimeFormat(isAr ? "ar-EG" : "en-GB", { day: "2-digit", month: "short", year: "numeric" });
  const startTime = window.RLM_RACE_START_TIME || "09:00:00+03:00";
  const now = Date.now();

  // A round is complete once its race day (Egypt time) has fully passed;
  // the first non-complete round is "next", the rest stay "upcoming".
  const rounds = window.RLM_CALENDAR.map((round) => ({
    ...round,
    startsAt: new Date(round.date + "T" + startTime).getTime(),
    endOfDay: new Date(round.date + "T23:59:59+03:00").getTime(),
  }));
  const nextRound = rounds.find((r) => now <= r.endOfDay) || null;

  const locationLabel = (loc) => (loc === "Egypt" ? T("loc.egypt", loc) : loc);

  rounds.forEach((round) => {
    const status = now > round.endOfDay ? "complete" : round === nextRound ? "next" : "upcoming";
    const statusLabel =
      status === "next"
        ? T("calendar.status.next", "Next Round")
        : status === "complete"
          ? T("calendar.status.complete", "Complete")
          : T("calendar.status.upcoming", "Upcoming");
    const statusClass =
      status === "next"
        ? "timing-board__status timing-board__status--next"
        : status === "complete"
          ? "timing-board__status timing-board__status--complete"
          : "timing-board__status";

    const row = document.createElement("div");
    row.className = "timing-board__row" + (status === "complete" ? " timing-board__row--complete" : "");
    row.setAttribute("role", "row");
    row.innerHTML = `
      <span class="timing-board__round" role="cell">${round.round}</span>
      <span role="cell">${dateFormatter.format(new Date(round.date))}</span>
      <span role="cell">${round.venue}</span>
      <span role="cell">${locationLabel(round.location)}</span>
      <span class="${statusClass}" role="cell">${statusLabel}</span>
    `;
    board.appendChild(row);
  });

  // Retarget the countdown at the next round (main.js reads data-countdown
  // after this script runs — load order in index.html guarantees that).
  const countdownEl = document.querySelector("[data-countdown]");
  if (countdownEl) {
    const labelEl = countdownEl.querySelector("[data-countdown-label]");
    const digitsEl = countdownEl.querySelector(".countdown__digits");
    if (nextRound) {
      countdownEl.dataset.countdown = nextRound.date + "T" + startTime;
      if (labelEl) {
        const roundNum = nextRound.round.replace(/^R/, "");
        const roundWord = T("calendar.round", "Round");
        labelEl.textContent = `${roundWord} ${roundNum} — ${nextRound.venue}${isAr ? "،" : ","} ${locationLabel(nextRound.location)}`;
      }
    } else {
      // season over: no target to count to
      countdownEl.dataset.countdown = "";
      if (labelEl) labelEl.textContent = T("calendar.seasonOver", "2026 season complete — next season coming soon");
      if (digitsEl) digitsEl.style.display = "none";
    }
  }
})();
