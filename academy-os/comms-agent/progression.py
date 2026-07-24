"""Academy level progression — ported from the RL CRM prototype.

Levels and rules:
  INTRO         1 month  · 8 sessions per cycle  → INTERMEDIATE
  INTERMEDIATE  7+ months · 10 sessions per cycle → ADVANCED
  ADVANCED      4+ months · 10 sessions per month (monthly tracking)

A driver's training log is the list of coached sessions actually attended
(distinct from scheduled bookings). Cycle alerts fire every N logged
sessions; a monthly check-in falls due when the level end date passes; a
promotion review falls due once the level's minimum duration has elapsed.
"""

from datetime import date, datetime

LEVELS = {
    "intro": {
        "id": "intro", "label": "INTRO", "color": "#4fc3f7",
        "sessions_per_cycle": 8, "duration_months": 1,
        "description": "1 month · 8 sessions per cycle", "next": "intermediate",
    },
    "intermediate": {
        "id": "intermediate", "label": "INTERMEDIATE", "color": "#e8c84a",
        "sessions_per_cycle": 10, "duration_months": 7,
        "description": "7+ months · 10 sessions per cycle", "next": "advanced",
    },
    "advanced": {
        "id": "advanced", "label": "ADVANCED", "color": "#ff6b35",
        "sessions_per_cycle": 10, "duration_months": 4,
        "description": "4+ months · 10 sessions per month", "next": None,
    },
}

KART_CATEGORIES = ["Micro", "Mini", "Junior", "Senior", "Shifter"]


def add_months(date_str, n):
    d = date.fromisoformat(date_str)
    month = d.month - 1 + n
    year = d.year + month // 12
    month = month % 12 + 1
    day = min(d.day, [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
                      else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
    return date(year, month, day).isoformat()


def months_elapsed(start_date_str, today=None):
    if not start_date_str:
        return 0
    start = date.fromisoformat(start_date_str)
    now = today or date.today()
    return max(0, (now.year - start.year) * 12 + (now.month - start.month))


def total_sessions(student):
    return sum(e["sessions"] for e in student.get("training_log", []))


def sessions_this_month(student, today=None):
    mk = (today or date.today()).isoformat()[:7]
    return sum(e["sessions"] for e in student.get("training_log", [])
               if e.get("date", "").startswith(mk))


def cycle_position(student):
    """(filled_dots, cycle_size, cycles_done). A full row of dots means the
    driver just completed a cycle."""
    lv = LEVELS[student.get("level", "intro")]
    total = total_sessions(student)
    size = lv["sessions_per_cycle"]
    pos = total % size
    filled = size if (pos == 0 and total > 0) else pos
    return filled, size, total // size


def alerts_for(student, today=None):
    """Active, undismissed alerts: list of dicts with 'type' and 'message'."""
    today = today or date.today()
    lv = LEVELS[student.get("level", "intro")]
    total = total_sessions(student)
    dismissed = student.get("dismissed", {})
    out = []
    if (total > 0 and total % lv["sessions_per_cycle"] == 0
            and not dismissed.get("cycle")):
        out.append({"type": "cycle",
                    "message": f"{total} sessions — cycle complete"})
    if (student.get("level_end_date")
            and today.isoformat() > student["level_end_date"]
            and not dismissed.get("monthly")):
        out.append({"type": "monthly", "message": "Monthly check-in due"})
    if (lv["next"]
            and months_elapsed(student.get("level_start_date"), today) >= lv["duration_months"]
            and not dismissed.get("promotion")):
        out.append({"type": "promotion",
                    "message": f"Ready to advance to {LEVELS[lv['next']]['label']}"})
    return out


def log_training(student, sessions, day_date=None, notes=""):
    """Append a coached-session entry; a completed cycle re-arms its alert."""
    student.setdefault("training_log", []).append({
        "date": day_date or date.today().isoformat(),
        "sessions": int(sessions),
        "notes": notes,
        "logged_at": datetime.now().isoformat(timespec="seconds"),
    })
    lv = LEVELS[student.get("level", "intro")]
    if total_sessions(student) % lv["sessions_per_cycle"] == 0:
        student.setdefault("dismissed", {})["cycle"] = False


def promote(student, today=None):
    """Move to the next level; returns False if already at the top."""
    lv = LEVELS[student.get("level", "intro")]
    if not lv["next"]:
        return False
    next_lv = LEVELS[lv["next"]]
    start = (today or date.today()).isoformat()
    student["level"] = lv["next"]
    student["level_start_date"] = start
    student["level_end_date"] = add_months(start, next_lv["duration_months"])
    student["dismissed"] = {}
    return True


def extend_level(student, months=1):
    """Extend the current level by N months and re-arm its alerts."""
    base = student.get("level_end_date") or date.today().isoformat()
    student["level_end_date"] = add_months(base, months)
    student.setdefault("dismissed", {})["monthly"] = False
    student["dismissed"]["promotion"] = False


def ensure_progression_fields(student, today=None):
    """Migrate a pre-CRM student record in place; returns the student."""
    start = (today or date.today()).isoformat()
    student.setdefault("level", "intro")
    student.setdefault("kart", "Junior")
    student.setdefault("level_start_date", start)
    student.setdefault("level_end_date",
                       add_months(student["level_start_date"],
                                  LEVELS[student["level"]]["duration_months"]))
    student.setdefault("training_log", [])
    student.setdefault("dismissed", {})
    return student


def progression_summary(student, today=None):
    """Compact dict for the WhatsApp agent to describe a driver's progress."""
    lv = LEVELS[student.get("level", "intro")]
    filled, size, cycles = cycle_position(student)
    out = {
        "level": lv["label"],
        "month_in_level": months_elapsed(student.get("level_start_date"), today) + 1,
        "total_coached_sessions": total_sessions(student),
        "current_cycle": f"{filled}/{size} sessions",
        "cycles_completed": cycles,
    }
    if student.get("level") == "advanced":
        out["sessions_this_month"] = f"{sessions_this_month(student, today)}/{size}"
    return out
