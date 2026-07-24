#!/usr/bin/env python3
"""Generate driver progress reports from a folder of timing CSVs.

Usage:
    python3 main.py <data_dir> [--out <reports_dir>]

Expects CSVs named "<Driver Name>_<YYYY-MM-DD>_<session type>.csv" containing
lap times (and optionally sector times) exported from Alfano / MyChron /
MyLaps. One HTML report is produced per driver, covering their full history
with the most recent session analyzed in detail.
"""

import argparse
import sys
from pathlib import Path

from analyze import analyze_driver, fmt_time
from ingest import load_driver_sessions
from narrative import build_narrative
from report import render_report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("data_dir", help="Folder of timing CSV exports")
    parser.add_argument("--out", default="reports", help="Output folder for HTML reports")
    args = parser.parse_args()

    drivers = load_driver_sessions(args.data_dir)
    if not drivers:
        print(f"No parsable timing CSVs found in {args.data_dir}", file=sys.stderr)
        sys.exit(1)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    for name, sessions in drivers.items():
        progress = analyze_driver(sessions)
        narrative, source = build_narrative(progress)
        path = out_dir / f"{name.replace(' ', '_')}_{progress.latest.session.day}.html"
        path.write_text(render_report(progress, narrative), encoding="utf-8")
        print(f"{name}: {len(sessions)} sessions, best {fmt_time(progress.personal_best)} "
              f"→ {path} (narrative: {source})")


if __name__ == "__main__":
    main()
