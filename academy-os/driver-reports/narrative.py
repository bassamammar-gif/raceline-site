"""Turn computed stats into words.

Two paths:
  - Claude (Anthropic API) when the `anthropic` SDK and credentials are
    available — richer, more personal narrative.
  - A deterministic rule-based fallback otherwise, so the pipeline always
    produces a complete report.

All numbers come from analyze.py; this layer must never do arithmetic.
"""

import json

from analyze import fmt_delta, fmt_time

MODEL = "claude-opus-4-8"

NARRATIVE_SCHEMA = {
    "type": "object",
    "properties": {
        "coach_points": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Exactly 3 specific focus points for the next session",
        },
        "parent_summary": {
            "type": "string",
            "description": "Warm, jargon-free 3-4 sentence summary for parents",
        },
    },
    "required": ["coach_points", "parent_summary"],
    "additionalProperties": False,
}


def _stats_digest(progress):
    latest = progress.latest
    lines = [
        f"Driver: {progress.driver}",
        f"Sessions on record: {len(progress.history)}",
        f"Latest session: {latest.session.day} ({latest.session.session_type})",
        f"Best lap: {fmt_time(latest.best)} (lap {latest.best_lap_index} of {len(latest.session.laps)})",
        f"Average clean lap: {fmt_time(latest.avg_clean)}",
        f"Consistency (std dev of clean laps): {latest.stdev_clean:.3f}s",
        f"Laps excluded as traffic/incidents: {latest.excluded}",
        f"Personal best across all sessions: {fmt_time(progress.personal_best)}"
        + (" — SET THIS SESSION" if progress.is_personal_best else ""),
    ]
    if progress.delta_vs_last is not None:
        lines.append(f"Best lap vs previous session: {fmt_delta(progress.delta_vs_last)}")
    if progress.delta_vs_first is not None:
        lines.append(f"Best lap vs first session: {fmt_delta(progress.delta_vs_first)}")
    if latest.theoretical_best:
        lines.append(
            f"Theoretical best (sum of best sectors): {fmt_time(latest.theoretical_best)} "
            f"({fmt_delta(latest.theoretical_best - latest.best)} vs actual best)"
        )
    if progress.weakest_sector:
        lines.append(
            f"Weakest sector: S{progress.weakest_sector} "
            f"(average {progress.weakest_sector_gap:.3f}s off its best)"
        )
    return "\n".join(lines)


def _claude_narrative(progress):
    import anthropic

    client = anthropic.Anthropic()
    response = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=(
            "You are a professional karting coach at Race Line Academy writing a "
            "post-session driver development report. Base every claim strictly on "
            "the provided statistics — never invent numbers or events. Coach points "
            "are for the driver and coaching staff: specific and actionable. The "
            "parent summary is for a parent with no motorsport background: warm, "
            "clear, no jargon, honest about areas to work on."
        ),
        messages=[{"role": "user", "content": _stats_digest(progress)}],
        output_config={"format": {"type": "json_schema", "schema": NARRATIVE_SCHEMA}},
    )
    text = next(b.text for b in response.content if b.type == "text")
    return json.loads(text)


def _fallback_narrative(progress):
    latest = progress.latest
    points = []

    if progress.weakest_sector:
        points.append(
            f"Sector {progress.weakest_sector} is where the most time is available — "
            f"laps average {progress.weakest_sector_gap:.3f}s slower there than the "
            f"best effort. Next session: dedicated work on that section of the track."
        )
    if latest.theoretical_best and latest.theoretical_best < latest.best:
        points.append(
            f"The theoretical best from combining best sectors is "
            f"{fmt_time(latest.theoretical_best)} — "
            f"{abs(latest.theoretical_best - latest.best):.3f}s faster than the actual "
            f"best lap. The speed is there; the focus is putting it together in one lap."
        )
    if latest.stdev_clean > 0.5:
        points.append(
            f"Lap-to-lap consistency ({latest.stdev_clean:.3f}s spread) is the "
            f"priority — aim for repeated laps within 0.3s before chasing outright pace."
        )
    else:
        points.append(
            f"Consistency is strong ({latest.stdev_clean:.3f}s spread on clean laps). "
            f"Ready to work on qualifying-style single-lap pace and race craft."
        )
    points = points[:3]
    while len(points) < 3:
        points.append(
            "Keep building seat time — repetition at current pace will convert "
            "directly into lap time."
        )

    if progress.delta_vs_last is not None and progress.delta_vs_last < 0:
        trend = (
            f"improved their best lap by {abs(progress.delta_vs_last):.3f} seconds "
            f"since the last session"
        )
    elif progress.delta_vs_last is not None:
        trend = "consolidated their pace from the last session"
    else:
        trend = "completed their first recorded session"

    pb = " — a new personal best" if progress.is_personal_best else ""
    summary = (
        f"{progress.driver} {trend}, with a best lap of {fmt_time(latest.best)}{pb}. "
        f"They completed {len(latest.session.laps)} laps, and their driving was "
        f"{'very consistent' if latest.stdev_clean < 0.4 else 'increasingly consistent'} "
        f"throughout the session. "
    )
    if progress.delta_vs_first is not None and progress.delta_vs_first < 0:
        summary += (
            f"Since starting with us, they have found {abs(progress.delta_vs_first):.1f} "
            f"seconds per lap — excellent progress. "
        )
    summary += "The coaching team has set clear focus points for the next session."

    return {"coach_points": points, "parent_summary": summary}


def build_narrative(progress):
    """Return {'coach_points': [...], 'parent_summary': str} for a driver."""
    try:
        result = _claude_narrative(progress)
        if result.get("coach_points") and result.get("parent_summary"):
            return result, "claude"
    except Exception:
        pass
    return _fallback_narrative(progress), "rules"
