/**
 * IAME Series Egypt 2026 calendar — 6 rounds, July-August 2026, one champion.
 * All rounds run at Autovrooom, Egypt.
 *
 * No status fields: js/calendar-render.js computes Complete / Next Round /
 * Upcoming from the dates at load time, and retargets the countdown to the
 * next round automatically — nothing here needs editing as the season runs.
 *
 * TEMPORARY: hardcoded here for Phase 1A. Once Supabase is provisioned (Phase 1B),
 * replace this with a fetch against a `series_calendar` table so the Phase 2 app
 * can share the same source. Shape is kept identical on purpose.
 */
window.RLM_RACE_START_TIME = "09:00:00+03:00"; // local race-day start, Egypt time

window.RLM_CALENDAR = [
  { round: "R1", date: "2026-07-16", venue: "Autovrooom", location: "Egypt" },
  { round: "R2", date: "2026-07-21", venue: "Autovrooom", location: "Egypt" },
  { round: "R3", date: "2026-07-28", venue: "Autovrooom", location: "Egypt" },
  { round: "R4", date: "2026-08-04", venue: "Autovrooom", location: "Egypt" },
  { round: "R5", date: "2026-08-11", venue: "Autovrooom", location: "Egypt" },
  { round: "R6", date: "2026-08-25", venue: "Autovrooom", location: "Egypt" },
];
