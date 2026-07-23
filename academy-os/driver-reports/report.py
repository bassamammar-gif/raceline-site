"""Render a driver progress report as a self-contained HTML file,
styled to match the Race Line Motorsports brand."""

import html

from analyze import fmt_time

# Brand palette (mirrors css/main.css on the main site)
BG = "#0C1002"
BG_ALT = "#141B06"
TEXT = "#FFFFFF"
TEXT_DIM = "#7C8460"
LIME = "#D2FF00"
RED = "#E10600"
BORDER = "rgba(210, 255, 0, 0.16)"


def _svg_progress_chart(history, width=640, height=220):
    """Best lap per session — single-series line chart in brand lime."""
    pad_l, pad_r, pad_t, pad_b = 56, 20, 16, 40
    bests = [st.best for st in history]
    days = [st.session.day for st in history]
    lo, hi = min(bests), max(bests)
    span = max(hi - lo, 0.5)
    lo, hi = lo - span * 0.15, hi + span * 0.15

    def x(i):
        n = max(len(bests) - 1, 1)
        return pad_l + i * (width - pad_l - pad_r) / n

    def y(v):
        return pad_t + (v - lo) / (hi - lo) * (height - pad_t - pad_b)

    pts = [(x(i), y(v)) for i, v in enumerate(bests)]
    path = "M " + " L ".join(f"{px:.1f} {py:.1f}" for px, py in pts)
    best_idx = bests.index(min(bests))

    parts = [f'<svg viewBox="0 0 {width} {height}" role="img" '
             f'aria-label="Best lap time per session">']
    # y-axis gridlines + labels (3 ticks)
    for frac in (0.15, 0.5, 0.85):
        v = lo + (hi - lo) * frac
        gy = y(v)
        parts.append(f'<line x1="{pad_l}" y1="{gy:.1f}" x2="{width - pad_r}" '
                     f'y2="{gy:.1f}" stroke="{BORDER}" stroke-width="1"/>')
        parts.append(f'<text x="{pad_l - 8}" y="{gy + 4:.1f}" text-anchor="end" '
                     f'class="axis">{fmt_time(v)}</text>')
    parts.append(f'<path d="{path}" fill="none" stroke="{LIME}" '
                 f'stroke-width="2" stroke-linejoin="round"/>')
    for i, (px, py) in enumerate(pts):
        is_best = i == best_idx
        r = 6 if is_best else 4.5
        fill = RED if is_best else LIME
        parts.append(
            f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{r}" fill="{fill}" '
            f'stroke="{BG}" stroke-width="2">'
            f'<title>{days[i].strftime("%d %b")}: {fmt_time(bests[i])}</title></circle>'
        )
        if is_best:
            parts.append(f'<text x="{px:.1f}" y="{py - 12:.1f}" text-anchor="middle" '
                         f'class="pb-label">PB {fmt_time(bests[i])}</text>')
        parts.append(f'<text x="{px:.1f}" y="{height - 16}" text-anchor="middle" '
                     f'class="axis">{days[i].strftime("%d %b")}</text>')
    parts.append("</svg>")
    return "".join(parts)


def _svg_lap_chart(session_stats, width=640, height=200):
    """Lap-by-lap times for the latest session. Excluded (traffic) laps are
    hollow; the best lap is marked in red with a label."""
    pad_l, pad_r, pad_t, pad_b = 56, 20, 20, 34
    laps = session_stats.session.laps
    best = session_stats.best
    cutoff = best * 1.07
    lo = best - (max(laps) - best) * 0.1 - 0.1
    hi = min(max(laps), cutoff * 1.02) + 0.1

    def x(i):
        n = max(len(laps) - 1, 1)
        return pad_l + i * (width - pad_l - pad_r) / n

    def y(v):
        v = min(v, hi)
        return pad_t + (v - lo) / (hi - lo) * (height - pad_t - pad_b)

    parts = [f'<svg viewBox="0 0 {width} {height}" role="img" '
             f'aria-label="Lap times, latest session">']
    for frac in (0.2, 0.8):
        v = lo + (hi - lo) * frac
        gy = y(v)
        parts.append(f'<line x1="{pad_l}" y1="{gy:.1f}" x2="{width - pad_r}" '
                     f'y2="{gy:.1f}" stroke="{BORDER}" stroke-width="1"/>')
        parts.append(f'<text x="{pad_l - 8}" y="{gy + 4:.1f}" text-anchor="end" '
                     f'class="axis">{fmt_time(v)}</text>')

    clean_pts = [(x(i), y(t)) for i, t in enumerate(laps) if t <= cutoff]
    if len(clean_pts) > 1:
        path = "M " + " L ".join(f"{px:.1f} {py:.1f}" for px, py in clean_pts)
        parts.append(f'<path d="{path}" fill="none" stroke="{LIME}" '
                     f'stroke-width="2" stroke-opacity="0.55"/>')

    for i, t in enumerate(laps):
        px, py = x(i), y(t)
        excluded = t > cutoff
        is_best = t == best
        if excluded:
            parts.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="4.5" fill="none" '
                         f'stroke="{TEXT_DIM}" stroke-width="1.5">'
                         f'<title>Lap {i + 1}: {fmt_time(t)} (traffic/incident — excluded)</title></circle>')
        else:
            fill = RED if is_best else LIME
            r = 6 if is_best else 4.5
            parts.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{r}" fill="{fill}" '
                         f'stroke="{BG}" stroke-width="2">'
                         f'<title>Lap {i + 1}: {fmt_time(t)}</title></circle>')
        if is_best:
            parts.append(f'<text x="{px:.1f}" y="{py - 12:.1f}" text-anchor="middle" '
                         f'class="pb-label">Best</text>')
        if (i + 1) % 2 == 1:
            parts.append(f'<text x="{px:.1f}" y="{height - 12}" text-anchor="middle" '
                         f'class="axis">{i + 1}</text>')
    parts.append("</svg>")
    return "".join(parts)


def _sector_table(latest):
    if not latest.best_sectors:
        return ""
    rows = ""
    for i, (b, a) in enumerate(zip(latest.best_sectors, latest.avg_sectors), 1):
        rows += (f"<tr><td>Sector {i}</td><td>{fmt_time(b)}</td>"
                 f"<td>{fmt_time(a)}</td><td>+{a - b:.3f}s</td></tr>")
    return f"""
    <div class="card">
      <h2>Sector analysis <span class="sub">latest session</span></h2>
      <table>
        <thead><tr><th>Sector</th><th>Best</th><th>Average</th><th>Avg gap to best</th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
      <p class="note">Theoretical best lap (all best sectors combined):
        <strong>{fmt_time(latest.theoretical_best)}</strong></p>
    </div>"""


def render_report(progress, narrative):
    latest = progress.latest
    e = html.escape
    delta_txt = ""
    if progress.delta_vs_last is not None:
        d = progress.delta_vs_last
        cls = "good" if d < 0 else "flat"
        delta_txt = (f'<span class="delta {cls}">'
                     f'{"▼" if d < 0 else "•"} {abs(d):.3f}s vs last session</span>')

    points_html = "".join(f"<li>{e(p)}</li>" for p in narrative["coach_points"])
    pb_badge = '<span class="badge">NEW PERSONAL BEST</span>' if progress.is_personal_best else ""

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(progress.driver)} — Driver Progress Report</title>
<style>
  :root {{ color-scheme: dark; }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ background: {BG}; color: {TEXT};
         font-family: "Inter", -apple-system, sans-serif; padding: 2rem 1.25rem; }}
  .wrap {{ max-width: 720px; margin: 0 auto; }}
  header {{ border-bottom: 2px solid {LIME}; padding-bottom: 1.25rem; margin-bottom: 1.5rem; }}
  .brand {{ font-family: "Archivo Black", "Arial Black", sans-serif; font-size: .8rem;
            letter-spacing: .2em; color: {LIME}; text-transform: uppercase; }}
  h1 {{ font-family: "Archivo Black", "Arial Black", sans-serif; font-size: 1.9rem;
        margin-top: .4rem; text-transform: uppercase; }}
  .meta {{ color: {TEXT_DIM}; margin-top: .35rem; font-size: .9rem; }}
  .badge {{ display: inline-block; background: {RED}; color: {TEXT}; font-weight: 700;
            font-size: .7rem; letter-spacing: .12em; padding: .3em .7em;
            border-radius: 3px; margin-left: .6em; vertical-align: middle; }}
  .tiles {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
            gap: .75rem; margin-bottom: 1.5rem; }}
  .tile {{ background: {BG_ALT}; border: 1px solid {BORDER}; border-radius: 8px;
           padding: 1rem; }}
  .tile .label {{ color: {TEXT_DIM}; font-size: .72rem; text-transform: uppercase;
                  letter-spacing: .1em; }}
  .tile .value {{ font-family: "Archivo Black", "Arial Black", sans-serif;
                  font-size: 1.5rem; margin-top: .3rem; }}
  .delta {{ font-size: .8rem; display: block; margin-top: .25rem; }}
  .delta.good {{ color: {LIME}; }} .delta.flat {{ color: {TEXT_DIM}; }}
  .card {{ background: {BG_ALT}; border: 1px solid {BORDER}; border-radius: 8px;
           padding: 1.25rem; margin-bottom: 1.25rem; }}
  h2 {{ font-size: 1rem; text-transform: uppercase; letter-spacing: .08em;
        margin-bottom: .9rem; }}
  h2 .sub {{ color: {TEXT_DIM}; font-weight: 400; text-transform: none;
             letter-spacing: 0; font-size: .8rem; }}
  svg {{ width: 100%; height: auto; display: block; }}
  .axis {{ fill: {TEXT_DIM}; font-size: 11px; font-family: "Inter", sans-serif; }}
  .pb-label {{ fill: {TEXT}; font-size: 11px; font-weight: 700;
               font-family: "Inter", sans-serif; }}
  table {{ width: 100%; border-collapse: collapse; font-size: .9rem; }}
  th {{ text-align: left; color: {TEXT_DIM}; font-size: .72rem; text-transform: uppercase;
        letter-spacing: .1em; padding: .4rem .5rem; border-bottom: 1px solid {BORDER}; }}
  td {{ padding: .5rem; border-bottom: 1px solid {BORDER}; }}
  .note {{ color: {TEXT_DIM}; font-size: .85rem; margin-top: .8rem; }}
  .note strong {{ color: {LIME}; }}
  ol {{ padding-left: 1.25rem; }} ol li {{ margin-bottom: .7rem; line-height: 1.55; }}
  .summary p {{ line-height: 1.65; }}
  footer {{ color: {TEXT_DIM}; font-size: .78rem; text-align: center;
            margin-top: 2rem; border-top: 1px solid {BORDER}; padding-top: 1rem; }}
  footer .brand {{ font-size: .7rem; }}
</style></head><body><div class="wrap">
<header>
  <div class="brand">Race Line Academy — Driver Development</div>
  <h1>{e(progress.driver)}{pb_badge}</h1>
  <div class="meta">{latest.session.session_type} · {latest.session.day.strftime("%d %B %Y")}
    · Session {len(progress.history)} on record</div>
</header>

<div class="tiles">
  <div class="tile"><div class="label">Best lap</div>
    <div class="value">{fmt_time(latest.best)}</div>{delta_txt}</div>
  <div class="tile"><div class="label">Average (clean)</div>
    <div class="value">{fmt_time(latest.avg_clean)}</div></div>
  <div class="tile"><div class="label">Consistency</div>
    <div class="value">±{latest.stdev_clean:.2f}s</div></div>
  <div class="tile"><div class="label">Laps</div>
    <div class="value">{len(latest.session.laps)}</div></div>
</div>

<div class="card">
  <h2>Best lap progression <span class="sub">across sessions · lower is faster</span></h2>
  {_svg_progress_chart(progress.history)}
</div>

<div class="card">
  <h2>Lap-by-lap <span class="sub">latest session · hollow = traffic/incident</span></h2>
  {_svg_lap_chart(latest)}
</div>

{_sector_table(latest)}

<div class="card">
  <h2>Coach's focus points</h2>
  <ol>{points_html}</ol>
</div>

<div class="card summary">
  <h2>Summary for parents</h2>
  <p>{e(narrative["parent_summary"])}</p>
</div>

<footer>
  <div class="brand">Race Line Motorsports</div>
  <div>Karting, Reimagined · racelinemotorsports.com</div>
</footer>
</div></body></html>"""
