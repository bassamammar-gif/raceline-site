"""Ingest kart timing exports into normalized session data.

Accepts CSV lap exports in the loose formats produced by Alfano, AiM MyChron
and MyLaps ("Lap, Time, S1, S2, S3" style). Header names and time formats vary
between devices, so parsing is deliberately tolerant:

  - lap time columns: "Time", "Lap Time", "LapTime", "Lap Tm"
  - sector columns:   "S1"/"S2"/"S3", "Sector 1", "Sect 1", "T1"
  - time values:      "58.123", "0:58.123", "1:02.45"

Session metadata comes from the filename convention:

    <Driver Name>_<YYYY-MM-DD>_<session type>.csv
    e.g. "Omar Khaled_2026-07-19_Practice.csv"
"""

import csv
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path


@dataclass
class Session:
    driver: str
    day: date
    session_type: str
    laps: list = field(default_factory=list)      # lap times in seconds
    sectors: list = field(default_factory=list)   # per lap: [s1, s2, s3] or []
    source: str = ""


_TIME_RE = re.compile(r"^(?:(\d+):)?(\d{1,2}(?:[.,]\d+)?)$")

_LAPTIME_HEADERS = {"time", "lap time", "laptime", "lap tm", "lap_time"}
_SECTOR_RE = re.compile(r"^(?:s|t|sect(?:or)?\s*)(\d)$")


def parse_time(value):
    """'1:02.45' or '58.123' -> seconds as float, or None."""
    m = _TIME_RE.match(value.strip())
    if not m:
        return None
    minutes = int(m.group(1)) if m.group(1) else 0
    return minutes * 60 + float(m.group(2).replace(",", "."))


def _classify_headers(headers):
    time_col, sector_cols = None, {}
    for i, raw in enumerate(headers):
        h = raw.strip().lower()
        if h in _LAPTIME_HEADERS:
            time_col = i
        else:
            m = _SECTOR_RE.match(h)
            if m:
                sector_cols[int(m.group(1))] = i
    return time_col, [sector_cols[k] for k in sorted(sector_cols)]


def parse_session_file(path):
    """Parse one timing CSV into a Session, or None if the file is unusable."""
    path = Path(path)
    parts = path.stem.split("_")
    if len(parts) < 2:
        return None
    driver = parts[0].strip()
    try:
        day = date.fromisoformat(parts[1])
    except ValueError:
        return None
    session_type = parts[2] if len(parts) > 2 else "Session"

    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = [r for r in csv.reader(f) if any(c.strip() for c in r)]
    if len(rows) < 2:
        return None

    time_col, sector_cols = _classify_headers(rows[0])
    if time_col is None:
        return None

    session = Session(driver=driver, day=day, session_type=session_type,
                      source=path.name)
    for row in rows[1:]:
        if time_col >= len(row):
            continue
        lap = parse_time(row[time_col])
        if lap is None or lap <= 0:
            continue
        session.laps.append(lap)
        secs = [parse_time(row[i]) for i in sector_cols if i < len(row)]
        session.sectors.append(secs if secs and all(s for s in secs) else [])
    return session if session.laps else None


def load_driver_sessions(data_dir):
    """Load every parsable session in a directory, grouped by driver.

    Returns {driver_name: [Session, ...]} with sessions sorted by date.
    """
    drivers = {}
    for path in sorted(Path(data_dir).glob("*.csv")):
        session = parse_session_file(path)
        if session:
            drivers.setdefault(session.driver, []).append(session)
    for sessions in drivers.values():
        sessions.sort(key=lambda s: s.day)
    return drivers
