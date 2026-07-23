#!/usr/bin/env python3
"""Back-office daily run: session reminders and polite invoice chases.

Run once a day (cron). For every booking tomorrow it sends the parent a
reminder; for every unpaid invoice at or past its due date, a polite nudge.
Messages are template-based — no AI needed for these.

With WhatsApp configured (WHATSAPP_TOKEN etc.) messages are actually sent;
otherwise they're printed as drafts for manual sending.

    python3 reminders.py            # print drafts
    python3 reminders.py --send     # send via WhatsApp Cloud API
"""

import argparse
import os
from datetime import date, timedelta

import academy_data as db_mod

REMINDER = (
    "Hi! Reminder from Race Line Academy: {name} is booked for a session "
    "tomorrow ({date}) at {time} ({group}). Please arrive 15 minutes early "
    "with closed shoes, sports clothes, and water. See you at the track! 🏁"
)

INVOICE_NUDGE = (
    "Hello from Race Line Academy — a friendly reminder that invoice "
    "{invoice_id} ({description}, EGP {amount}) is due. You can settle it at "
    "the front desk before your next session, or reply here and we'll help. "
    "Thank you!"
)


def build_messages(db):
    """Return [(phone, text)] for tomorrow's reminders and due invoices."""
    out = []
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    students = {s["id"]: s for s in db["students"]}

    for session in db["sessions"]:
        if session["date"] != tomorrow:
            continue
        for student_id in session["booked"]:
            student = students.get(student_id)
            if student:
                out.append((student["parent_phone"], REMINDER.format(
                    name=student["name"], date=session["date"],
                    time=session["time"], group=session["group"])))

    today = date.today().isoformat()
    for inv in db["invoices"]:
        if inv["status"] == "unpaid" and inv.get("due", "9999") <= today:
            student = students.get(inv["student_id"])
            if student:
                out.append((student["parent_phone"], INVOICE_NUDGE.format(
                    invoice_id=inv["id"], description=inv["description"],
                    amount=inv["amount_egp"])))
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--send", action="store_true",
                        help="Send via WhatsApp instead of printing drafts")
    args = parser.parse_args()

    messages = build_messages(db_mod.load())
    if not messages:
        print("Nothing to send today.")
        return

    if args.send and os.environ.get("WHATSAPP_TOKEN"):
        from whatsapp import send_whatsapp
        for phone, text in messages:
            send_whatsapp(phone, text)
            print(f"sent → {phone}")
    else:
        for phone, text in messages:
            print(f"--- draft for {phone} ---\n{text}\n")


if __name__ == "__main__":
    main()
