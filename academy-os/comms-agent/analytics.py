"""WhatsApp conversation analytics: event log, topic classification, and
funnel/conversion stats.

Events are appended by the agent and tools as things happen (message in/out,
booking made, cancellation, escalation), so the dashboard reads them for
free — no separate tracking pipeline. Topic classification is keyword-based
(English + Egyptian Arabic) so it costs nothing and works offline; it powers
the "what do parents ask about" breakdown.
"""

import json
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

import academy_data as db_mod

EVENTS_FILE = Path(__file__).parent / "data" / "events.json"

# Topic priority matters: first match wins.
TOPICS = [
    ("booking", ["book", "reserve", "sign up", "join", "احجز", "حجز", "اشترك"]),
    ("pricing", ["price", "cost", "how much", "fee", "بكام", "سعر", "تكلفة", "اسعار", "أسعار"]),
    ("schedule", ["when", "time", "schedule", "available", "open", "مواعيد",
                  "امتى", "متى", "الساعة", "فاضي"]),
    ("logistics", ["bring", "wear", "helmet", "suit", "age", "old", "shoes",
                   "يلبس", "عمر", "سن", "خوذة", "هدوم", "يجيب"]),
    ("progress", ["progress", "level", "improve", "doing", "development",
                  "مستوى", "تقدم", "بيتحسن", "شاطر"]),
    ("payment", ["invoice", "pay", "paid", "transfer", "فاتورة", "دفع", "ادفع", "حول"]),
]


def classify_topic(text):
    lower = text.lower()
    for topic, keywords in TOPICS:
        if any(kw in lower for kw in keywords):
            return topic
    return "other"


def record(event_type, phone, **meta):
    EVENTS_FILE.parent.mkdir(exist_ok=True)
    events = []
    if EVENTS_FILE.exists():
        events = json.loads(EVENTS_FILE.read_text(encoding="utf-8"))
    events.append({"type": event_type, "phone": phone,
                   "at": datetime.now().isoformat(timespec="seconds"), **meta})
    EVENTS_FILE.write_text(json.dumps(events, indent=2, ensure_ascii=False),
                           encoding="utf-8")


def _events():
    if not EVENTS_FILE.exists():
        return []
    return json.loads(EVENTS_FILE.read_text(encoding="utf-8"))


def conversation_overview():
    """Per-phone rollup joining events, conversations, students, bookings,
    and escalations. Returns a list of dicts, most recent activity first."""
    db = db_mod.load()
    events = _events()
    phones = {}

    for ev in events:
        c = phones.setdefault(ev["phone"], {
            "phone": ev["phone"], "msgs_in": 0, "msgs_out": 0,
            "topics": Counter(), "bookings": 0, "cancellations": 0,
            "escalations": 0, "first_seen": ev["at"], "last_seen": ev["at"],
        })
        c["last_seen"] = max(c["last_seen"], ev["at"])
        c["first_seen"] = min(c["first_seen"], ev["at"])
        if ev["type"] == "message_in":
            c["msgs_in"] += 1
            c["topics"][ev.get("topic", "other")] += 1
        elif ev["type"] == "message_out":
            c["msgs_out"] += 1
        elif ev["type"] == "booking":
            c["bookings"] += 1
        elif ev["type"] == "cancellation":
            c["cancellations"] += 1
        elif ev["type"] == "escalated":
            c["escalations"] += 1

    week_ago = (datetime.now() - timedelta(days=7)).isoformat(timespec="seconds")
    out = []
    for phone, c in phones.items():
        student = db_mod.student_by_phone(db, phone)
        c["student"] = student["name"] if student else None
        c["registered"] = student is not None
        if db_mod.has_open_escalation(phone):
            c["status"] = "escalated"
        elif c["bookings"] > 0:
            c["status"] = "booked"
        elif c["registered"]:
            c["status"] = "registered"
        elif c["last_seen"] < week_ago:
            c["status"] = "quiet lead"
        else:
            c["status"] = "new lead"
        c["top_topic"] = c["topics"].most_common(1)[0][0] if c["topics"] else "—"
        out.append(c)
    return sorted(out, key=lambda c: c["last_seen"], reverse=True)


def summary():
    """Aggregate stats for the dashboard tiles, funnel, and FAQ breakdown."""
    convs = conversation_overview()
    total = len(convs)
    engaged = [c for c in convs if c["msgs_in"] >= 2]
    registered = [c for c in convs if c["registered"]]
    booked = [c for c in convs if c["bookings"] > 0]
    escalated_ever = [c for c in convs if c["escalations"] > 0]
    leads = [c for c in convs if not c["registered"]]

    topics = Counter()
    for c in convs:
        topics.update(c["topics"])

    def pct(part, whole):
        return round(100 * part / whole) if whole else 0

    return {
        "total_conversations": total,
        "new_leads": len(leads),
        "bookings_via_whatsapp": sum(c["bookings"] for c in convs),
        "conversion_rate": pct(len(booked), total),
        "escalation_rate": pct(len(escalated_ever), total),
        "funnel": [
            ("Contacted", total),
            ("Engaged (2+ messages)", len(engaged)),
            ("Registered", len(registered)),
            ("Booked", len(booked)),
        ],
        "faq": topics.most_common(),
        "conversations": convs,
    }
