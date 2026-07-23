"""Deterministic session analysis. All numbers are computed here, in code —
the narrative layer (narrative.py) only turns finished stats into words.

Laps slower than OUTLIER_FACTOR x the session best are treated as traffic,
spins or in/out laps and excluded from pace and consistency stats (the 107%
rule, borrowed from qualifying).
"""

from dataclasses import dataclass, field
from statistics import mean, pstdev

OUTLIER_FACTOR = 1.07


@dataclass
class SessionStats:
    session: object                    # ingest.Session
    best: float = 0.0
    clean_laps: list = field(default_factory=list)
    avg_clean: float = 0.0
    stdev_clean: float = 0.0           # consistency: lower is better
    excluded: int = 0
    best_sectors: list = field(default_factory=list)
    avg_sectors: list = field(default_factory=list)
    theoretical_best: float = 0.0      # sum of best sectors, 0 if no sector data
    best_lap_index: int = 0            # 1-based lap number of the best lap


def analyze_session(session):
    best = min(session.laps)
    clean = [t for t in session.laps if t <= best * OUTLIER_FACTOR]
    stats = SessionStats(
        session=session,
        best=best,
        clean_laps=clean,
        avg_clean=mean(clean),
        stdev_clean=pstdev(clean) if len(clean) > 1 else 0.0,
        excluded=len(session.laps) - len(clean),
        best_lap_index=session.laps.index(best) + 1,
    )

    sectored = [s for s in session.sectors if s]
    if sectored:
        n = min(len(s) for s in sectored)
        stats.best_sectors = [min(s[i] for s in sectored) for i in range(n)]
        stats.avg_sectors = [mean(s[i] for s in sectored) for i in range(n)]
        stats.theoretical_best = sum(stats.best_sectors)
    return stats


@dataclass
class DriverProgress:
    driver: str
    history: list                      # [SessionStats, ...] oldest -> newest
    latest: SessionStats = None
    personal_best: float = 0.0
    delta_vs_last: float = None        # negative = improved
    delta_vs_first: float = None
    weakest_sector: int = None         # 1-based; largest avg-vs-best gap
    weakest_sector_gap: float = 0.0

    @property
    def is_personal_best(self):
        return self.latest.best <= self.personal_best


def analyze_driver(sessions):
    history = [analyze_session(s) for s in sessions]
    latest = history[-1]
    progress = DriverProgress(
        driver=latest.session.driver,
        history=history,
        latest=latest,
        personal_best=min(st.best for st in history),
    )
    if len(history) > 1:
        progress.delta_vs_last = latest.best - history[-2].best
        progress.delta_vs_first = latest.best - history[0].best
    if latest.best_sectors:
        gaps = [a - b for a, b in zip(latest.avg_sectors, latest.best_sectors)]
        progress.weakest_sector = gaps.index(max(gaps)) + 1
        progress.weakest_sector_gap = max(gaps)
    return progress


def fmt_time(seconds):
    """58.123 -> '58.123', 62.4 -> '1:02.400'."""
    if seconds >= 60:
        m, s = divmod(seconds, 60)
        return f"{int(m)}:{s:06.3f}"
    return f"{seconds:.3f}"


def fmt_delta(seconds, signed=True):
    sign = "+" if seconds >= 0 else "-"
    return f"{sign if signed else ''}{abs(seconds):.3f}s"
