# Race Line Academy OS — Driver Progress Reports

First module of the Academy OS: turns raw kart timing exports into branded,
parent-friendly driver development reports.

**Why this exists:** timing data from practice sessions dies in a coach's head
or a printed sheet. This pipeline turns it into a visible development track —
progress charts, sector analysis, coach focus points, and a plain-language
summary parents can actually read. Parents who see progress don't pull their
kids out of the academy.

## Quick start

```bash
cd academy-os/driver-reports
python3 main.py sample_data --out reports
# open reports/Omar_Khaled_2026-07-19.html in a browser
```

No dependencies required for the core pipeline (Python 3.10+ standard library
only). Sample data for one driver across four sessions is included.

## Using real timing data

1. Export lap data from your timing system (Alfano, AiM MyChron, MyLaps) as CSV.
2. Name each file: `<Driver Name>_<YYYY-MM-DD>_<Session type>.csv`
   e.g. `Omar Khaled_2026-07-19_Practice.csv`
3. Drop all of a driver's sessions in one folder and run `main.py` on it.

The parser is tolerant of format differences:
- Lap time columns: `Time`, `Lap Time`, `LapTime`, `Lap Tm`
- Sector columns: `S1`/`S2`/`S3`, `Sector 1`, `T1`, etc. (optional)
- Time formats: `58.123`, `0:58.123`, `1:02.45`

## What the analysis does

- **107% rule**: laps slower than 1.07× the session best are treated as
  traffic/spins/in-out laps and excluded from pace and consistency stats.
- **Consistency**: standard deviation of clean laps (lower = better).
- **Theoretical best**: sum of best sectors — shows pace "left on the table".
- **Trends**: best-lap progression across every session on record, deltas vs
  the previous and first sessions, weakest-sector identification.

All numbers are computed deterministically in `analyze.py`. The narrative
layer only turns finished stats into words — it never does arithmetic.

## AI narrative (optional)

If the `anthropic` package is installed and API credentials are available
(`ANTHROPIC_API_KEY`), the coach focus points and parent summary are written
by Claude (`claude-opus-4-8`) from the computed stats. Without credentials the
pipeline falls back to a deterministic rule-based narrative, so it always
produces a complete report.

```bash
pip install anthropic
export ANTHROPIC_API_KEY=sk-ant-...
python3 main.py sample_data --out reports
```

## Files

| File | Role |
|---|---|
| `ingest.py` | Parse messy timing CSVs into normalized sessions |
| `analyze.py` | Deterministic stats: pace, consistency, sectors, trends |
| `narrative.py` | Claude-powered narrative with rule-based fallback |
| `report.py` | Branded HTML report with inline SVG charts |
| `main.py` | CLI entry point |
| `sample_data/` | Realistic demo data (one driver, four sessions) |

## Roadmap (Academy OS)

This is module 1 of 5 — the Driver Development Engine. Next: WhatsApp comms
agent, scheduling/payments, race operations (entries/points/comms for IAME
Series Egypt), and sponsor reporting.
