"""Tools the front-desk agent can call, and the hard limits on what it can do.

The agent can read the schedule, pricing, and a family's own bookings and
invoices, and can book or cancel sessions within the rules enforced by
academy_data.py. It cannot change prices, mark invoices paid, issue refunds,
or see other families' data — those actions simply don't exist as tools.
"""

import json

import academy_data as db_mod
import analytics
import progression

TOOL_DEFINITIONS = [
    {
        "name": "get_academy_info",
        "description": (
            "General academy information: location, opening hours, what to "
            "bring to a session. Call this for any practical 'how does it "
            "work' question."
        ),
        "input_schema": {"type": "object", "properties": {},
                         "additionalProperties": False},
    },
    {
        "name": "get_pricing",
        "description": "Current session and program pricing. Prices are fixed — never offer discounts.",
        "input_schema": {"type": "object", "properties": {},
                         "additionalProperties": False},
    },
    {
        "name": "get_schedule",
        "description": (
            "Upcoming sessions with dates, times, age groups, and how many "
            "places remain. Call this before booking anything."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "group": {"type": "string",
                          "description": "Optional age-group filter, e.g. 'Cadet (7-12)'"},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "get_my_family",
        "description": (
            "The student, upcoming bookings, invoices, and academy-programme "
            "progress (level, months in level, coached sessions, current "
            "cycle) linked to the phone number you are chatting with. Call "
            "this for any 'how is my child doing/progressing' question. "
            "Returns nothing if the number is not registered."
        ),
        "input_schema": {"type": "object", "properties": {},
                         "additionalProperties": False},
    },
    {
        "name": "book_session",
        "description": (
            "Book this family's student onto a session by session ID. Confirm "
            "the exact session with the parent before calling. Fails if the "
            "session is full or already booked."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"session_id": {"type": "string"}},
            "required": ["session_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "cancel_booking",
        "description": "Cancel this family's booking on a session by session ID.",
        "input_schema": {
            "type": "object",
            "properties": {"session_id": {"type": "string"}},
            "required": ["session_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "escalate_to_human",
        "description": (
            "Hand this conversation to academy staff. Use for anything about "
            "injuries, incidents, refunds, discounts, complaints, or any "
            "request you cannot fulfil with your other tools. After calling "
            "this, tell the parent a team member will contact them."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"reason": {"type": "string",
                                      "description": "One line for staff on why this needs a human"}},
            "required": ["reason"],
            "additionalProperties": False,
        },
    },
]


def execute_tool(name, tool_input, phone, last_user_message=""):
    """Run a tool for the conversation with `phone`. Returns a string result."""
    db = db_mod.load()
    student = db_mod.student_by_phone(db, phone)

    if name == "get_academy_info":
        return json.dumps(db["academy"], ensure_ascii=False)

    if name == "get_pricing":
        return json.dumps(db["pricing"], ensure_ascii=False)

    if name == "get_schedule":
        sessions = db_mod.upcoming_sessions(db, group=tool_input.get("group"))
        return json.dumps([
            {"id": s["id"], "date": s["date"], "time": s["time"],
             "group": s["group"],
             "places_left": s["capacity"] - len(s["booked"])}
            for s in sessions
        ], ensure_ascii=False)

    if name == "get_my_family":
        if student is None:
            return ("This phone number is not registered with the academy. "
                    "Offer to take their details and escalate to staff to set "
                    "them up.")
        bookings = [
            {"id": s["id"], "date": s["date"], "time": s["time"], "group": s["group"]}
            for s in db["sessions"] if student["id"] in s["booked"]
        ]
        return json.dumps({
            "student": {"name": student["name"], "group": student["group"],
                        "kart": student.get("kart")},
            "programme_progress": progression.progression_summary(student),
            "upcoming_bookings": bookings,
            "invoices": db_mod.invoices_for_student(db, student["id"]),
        }, ensure_ascii=False)

    if name == "book_session":
        if student is None:
            return "Cannot book: this phone number is not registered. Escalate to staff."
        session, err = db_mod.book_session(db, tool_input["session_id"], student["id"])
        if err:
            return f"Booking failed: {err}"
        analytics.record("booking", phone, session_id=session["id"])
        return (f"Booked: {student['name']} on {session['id']} — "
                f"{session['date']} at {session['time']} ({session['group']}).")

    if name == "cancel_booking":
        if student is None:
            return "Cannot cancel: this phone number is not registered."
        session, err = db_mod.cancel_booking(db, tool_input["session_id"], student["id"])
        if err:
            return f"Cancellation failed: {err}"
        analytics.record("cancellation", phone, session_id=session["id"])
        return f"Cancelled: {session['id']} on {session['date']} at {session['time']}."

    if name == "escalate_to_human":
        db_mod.log_escalation(phone, tool_input["reason"], last_user_message)
        return ("Escalation logged. Staff have been notified and the "
                "conversation is now paused for a human to take over.")

    return f"Unknown tool: {name}"
