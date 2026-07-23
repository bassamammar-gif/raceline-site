"""The academy's operational data: students, schedule, pricing, invoices,
bookings, and the escalation queue.

Stored as plain JSON under data/ so it's inspectable and hand-editable.
This is the v1 stand-in for the real database — every accessor here maps
directly onto a future table, so swapping in Postgres later means changing
this module only.
"""

import json
from datetime import date, datetime, timedelta
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
DB_FILE = DATA_DIR / "academy.json"
ESCALATIONS_FILE = DATA_DIR / "escalations.json"
CONVERSATIONS_DIR = DATA_DIR / "conversations"


def _seed():
    """Demo dataset: a few students, two weeks of sessions, open invoices."""
    today = date.today()
    sessions = []
    sid = 1
    for offset in range(1, 15):
        d = today + timedelta(days=offset)
        if d.weekday() in (4, 5):          # Friday and Saturday programs
            for time, group in (("10:00", "Cadet (7-12)"), ("13:00", "Junior (12-15)")):
                sessions.append({
                    "id": f"S{sid:03d}", "date": d.isoformat(), "time": time,
                    "group": group, "capacity": 8, "booked": [],
                })
                sid += 1
    return {
        "academy": {
            "name": "Race Line Academy",
            "location": "Race Line Circuit, Cairo",
            "hours": "Friday & Saturday, 09:00-17:00",
            "what_to_bring": (
                "Closed shoes, comfortable sports clothes, and water. Helmets, "
                "race suits, and gloves are provided by the academy. Long hair "
                "must be tied back."
            ),
        },
        "pricing": [
            {"item": "Single session (2 hours)", "price_egp": 1500},
            {"item": "Monthly program (4 sessions)", "price_egp": 5000},
            {"item": "Race team development program", "price_egp": "by assessment"},
        ],
        "students": [
            {"id": "D001", "name": "Omar Khaled", "group": "Junior (12-15)",
             "parent_phone": "+201001112233"},
            {"id": "D002", "name": "Layla Hassan", "group": "Cadet (7-12)",
             "parent_phone": "+201004445566"},
        ],
        "invoices": [
            {"id": "INV-2026-041", "student_id": "D001", "amount_egp": 5000,
             "description": "Monthly program — July", "status": "paid"},
            {"id": "INV-2026-052", "student_id": "D001", "amount_egp": 5000,
             "description": "Monthly program — August", "status": "unpaid",
             "due": (today + timedelta(days=5)).isoformat()},
            {"id": "INV-2026-049", "student_id": "D002", "amount_egp": 1500,
             "description": "Single session", "status": "unpaid",
             "due": (today - timedelta(days=3)).isoformat()},
        ],
        "sessions": sessions,
    }


def load():
    DATA_DIR.mkdir(exist_ok=True)
    if not DB_FILE.exists():
        save(_seed())
    return json.loads(DB_FILE.read_text(encoding="utf-8"))


def save(db):
    DATA_DIR.mkdir(exist_ok=True)
    DB_FILE.write_text(json.dumps(db, indent=2, ensure_ascii=False), encoding="utf-8")


# --- queries -----------------------------------------------------------------

def student_by_phone(db, phone):
    return next((s for s in db["students"] if s["parent_phone"] == phone), None)


def upcoming_sessions(db, group=None, limit=6):
    today = date.today().isoformat()
    out = [s for s in db["sessions"]
           if s["date"] >= today and (group is None or s["group"] == group)]
    return sorted(out, key=lambda s: (s["date"], s["time"]))[:limit]


def invoices_for_student(db, student_id):
    return [i for i in db["invoices"] if i["student_id"] == student_id]


# --- mutations (booking rules live here, not in the model) -------------------

def book_session(db, session_id, student_id):
    session = next((s for s in db["sessions"] if s["id"] == session_id), None)
    if session is None:
        return None, "No session with that ID exists."
    if session["date"] < date.today().isoformat():
        return None, "That session is in the past."
    if student_id in session["booked"]:
        return None, "This student is already booked on that session."
    if len(session["booked"]) >= session["capacity"]:
        return None, "That session is full."
    session["booked"].append(student_id)
    save(db)
    return session, None


def cancel_booking(db, session_id, student_id):
    session = next((s for s in db["sessions"] if s["id"] == session_id), None)
    if session is None or student_id not in session["booked"]:
        return None, "No booking found for this student on that session."
    session["booked"].remove(student_id)
    save(db)
    return session, None


# --- escalations -------------------------------------------------------------

def log_escalation(phone, reason, last_message):
    DATA_DIR.mkdir(exist_ok=True)
    queue = []
    if ESCALATIONS_FILE.exists():
        queue = json.loads(ESCALATIONS_FILE.read_text(encoding="utf-8"))
    queue.append({
        "phone": phone, "reason": reason, "last_message": last_message,
        "at": datetime.now().isoformat(timespec="seconds"), "resolved": False,
    })
    ESCALATIONS_FILE.write_text(json.dumps(queue, indent=2, ensure_ascii=False),
                                encoding="utf-8")


def has_open_escalation(phone):
    if not ESCALATIONS_FILE.exists():
        return False
    queue = json.loads(ESCALATIONS_FILE.read_text(encoding="utf-8"))
    return any(e["phone"] == phone and not e["resolved"] for e in queue)


def resolve_escalations(phone):
    if not ESCALATIONS_FILE.exists():
        return
    queue = json.loads(ESCALATIONS_FILE.read_text(encoding="utf-8"))
    for e in queue:
        if e["phone"] == phone:
            e["resolved"] = True
    ESCALATIONS_FILE.write_text(json.dumps(queue, indent=2, ensure_ascii=False),
                                encoding="utf-8")


# --- conversation history ----------------------------------------------------

def _conv_file(phone):
    return CONVERSATIONS_DIR / f"{phone.replace('+', '')}.json"


def load_conversation(phone, max_turns=30):
    f = _conv_file(phone)
    if not f.exists():
        return []
    return json.loads(f.read_text(encoding="utf-8"))[-max_turns:]


def append_conversation(phone, role, text):
    CONVERSATIONS_DIR.mkdir(parents=True, exist_ok=True)
    f = _conv_file(phone)
    history = json.loads(f.read_text(encoding="utf-8")) if f.exists() else []
    history.append({"role": role, "content": text})
    f.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")
