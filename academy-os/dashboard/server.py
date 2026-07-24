#!/usr/bin/env python3
"""Race Line Academy staff dashboard (Academy OS module 3).

Server-rendered web app over the comms-agent data layer — standard library
only. Staff see open escalations (and resolve them, which un-mutes the
WhatsApp bot for that parent), the session schedule with bookings, full
conversation transcripts, and invoices (with mark-as-paid).

Usage:
    export DASHBOARD_PASSWORD=some-secret     # omit for open dev mode
    python3 server.py --port 8090

Auth is HTTP Basic (user: staff). v1 is intended for the academy's own
network or behind a reverse proxy with TLS.
"""

import argparse
import base64
import html
import json
import os
import sys
import urllib.parse
from datetime import date
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "comms-agent"))
import academy_data as db_mod  # noqa: E402

E = html.escape

# --- data helpers -------------------------------------------------------------

def all_escalations():
    if not db_mod.ESCALATIONS_FILE.exists():
        return []
    return json.loads(db_mod.ESCALATIONS_FILE.read_text(encoding="utf-8"))


def all_conversations():
    if not db_mod.CONVERSATIONS_DIR.exists():
        return []
    out = []
    for f in sorted(db_mod.CONVERSATIONS_DIR.glob("*.json")):
        history = json.loads(f.read_text(encoding="utf-8"))
        out.append({"phone": "+" + f.stem, "turns": len(history),
                    "last": history[-1]["content"][:90] if history else ""})
    return out


def mark_invoice_paid(invoice_id):
    db = db_mod.load()
    for inv in db["invoices"]:
        if inv["id"] == invoice_id:
            inv["status"] = "paid"
            db_mod.save(db)
            return True
    return False


# --- rendering ----------------------------------------------------------------

STYLE = """
  :root { color-scheme: dark; }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { background: #0C1002; color: #FFF;
         font-family: "Inter", -apple-system, sans-serif; }
  a { color: #D2FF00; text-decoration: none; }
  nav { display: flex; gap: 1.5rem; align-items: baseline; padding: 1rem 1.5rem;
        border-bottom: 2px solid #D2FF00; flex-wrap: wrap; }
  nav .brand { font-family: "Archivo Black", "Arial Black", sans-serif;
               letter-spacing: .15em; color: #D2FF00; font-size: .85rem;
               text-transform: uppercase; margin-right: 1rem; }
  nav a.active { border-bottom: 2px solid #E10600; padding-bottom: 2px; }
  main { max-width: 960px; margin: 0 auto; padding: 1.5rem; }
  h1 { font-family: "Archivo Black", "Arial Black", sans-serif; font-size: 1.4rem;
       text-transform: uppercase; margin-bottom: 1.25rem; }
  .tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
           gap: .75rem; margin-bottom: 1.5rem; }
  .tile { background: #141B06; border: 1px solid rgba(210,255,0,.16);
          border-radius: 8px; padding: 1rem; display: block; color: #FFF; }
  .tile .label { color: #7C8460; font-size: .72rem; text-transform: uppercase;
                 letter-spacing: .1em; }
  .tile .value { font-family: "Archivo Black", "Arial Black", sans-serif;
                 font-size: 1.7rem; margin-top: .25rem; }
  .tile.alert .value { color: #E10600; }
  .card { background: #141B06; border: 1px solid rgba(210,255,0,.16);
          border-radius: 8px; padding: 1.25rem; margin-bottom: 1.25rem; }
  table { width: 100%; border-collapse: collapse; font-size: .9rem; }
  th { text-align: left; color: #7C8460; font-size: .72rem; text-transform: uppercase;
       letter-spacing: .1em; padding: .45rem .5rem;
       border-bottom: 1px solid rgba(210,255,0,.16); }
  td { padding: .55rem .5rem; border-bottom: 1px solid rgba(210,255,0,.16);
       vertical-align: top; }
  .pill { display: inline-block; font-size: .7rem; font-weight: 700;
          letter-spacing: .08em; padding: .25em .6em; border-radius: 3px;
          text-transform: uppercase; }
  .pill.open { background: #E10600; color: #FFF; }
  .pill.resolved { background: rgba(210,255,0,.15); color: #D2FF00; }
  .pill.unpaid { background: #E10600; color: #FFF; }
  .pill.paid { background: rgba(210,255,0,.15); color: #D2FF00; }
  button { background: #D2FF00; color: #0C1002; border: 0; border-radius: 4px;
           padding: .45em .9em; font-weight: 700; cursor: pointer;
           font-family: inherit; font-size: .8rem; }
  .muted { color: #7C8460; }
  .chat { display: flex; flex-direction: column; gap: .6rem; }
  .msg { max-width: 75%; padding: .6rem .85rem; border-radius: 10px;
         line-height: 1.5; white-space: pre-wrap; font-size: .9rem; }
  .msg.user { background: #1E2A0B; align-self: flex-start; }
  .msg.assistant { background: rgba(210,255,0,.12); align-self: flex-end; }
  .banner { background: #E10600; color: #FFF; padding: .5rem 1.5rem;
            font-size: .85rem; font-weight: 600; }
"""

NAV = [("/", "Overview"), ("/escalations", "Escalations"), ("/sessions", "Sessions"),
       ("/conversations", "Conversations"), ("/invoices", "Invoices")]


def layout(title, body, active="/", dev_mode=False):
    links = "".join(
        f"<a href='{p}'{' class=active' if p == active else ''}>{label}</a>"
        for p, label in NAV)
    banner = ('<div class="banner">DASHBOARD_PASSWORD not set — dashboard is '
              'open to anyone who can reach this port</div>' if dev_mode else "")
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(title)} — Race Line Academy</title><style>{STYLE}</style></head>
<body>{banner}<nav><span class="brand">Race Line Academy · Staff</span>{links}</nav>
<main><h1>{E(title)}</h1>{body}</main></body></html>"""


def page_overview():
    db = db_mod.load()
    today = date.today().isoformat()
    open_esc = [e for e in all_escalations() if not e["resolved"]]
    unpaid = [i for i in db["invoices"] if i["status"] == "unpaid"]
    upcoming = db_mod.upcoming_sessions(db, limit=4)
    students = {s["id"]: s for s in db["students"]}

    rows = "".join(
        f"<tr><td>{s['date']}{' <strong>(today)</strong>' if s['date'] == today else ''}</td>"
        f"<td>{s['time']}</td><td>{E(s['group'])}</td>"
        f"<td>{len(s['booked'])}/{s['capacity']} — "
        f"{E(', '.join(students[b]['name'] for b in s['booked'] if b in students)) or '<span class=muted>empty</span>'}</td></tr>"
        for s in upcoming)

    return f"""
    <div class="tiles">
      <a class="tile{' alert' if open_esc else ''}" href="/escalations">
        <div class="label">Open escalations</div><div class="value">{len(open_esc)}</div></a>
      <a class="tile" href="/sessions">
        <div class="label">Upcoming sessions</div>
        <div class="value">{len(db_mod.upcoming_sessions(db, limit=99))}</div></a>
      <a class="tile{' alert' if unpaid else ''}" href="/invoices">
        <div class="label">Unpaid invoices</div><div class="value">{len(unpaid)}</div></a>
      <a class="tile" href="/conversations">
        <div class="label">Conversations</div><div class="value">{len(all_conversations())}</div></a>
    </div>
    <div class="card"><table>
      <thead><tr><th>Date</th><th>Time</th><th>Group</th><th>Booked</th></tr></thead>
      <tbody>{rows}</tbody></table></div>"""


def page_escalations():
    items = sorted(all_escalations(), key=lambda e: (e["resolved"], e["at"]),
                   reverse=False)
    if not items:
        return '<div class="card muted">No escalations — all quiet.</div>'
    rows = ""
    for e in items:
        action = ("" if e["resolved"] else
                  f'<form method="post" action="/escalations/resolve" style="display:inline">'
                  f'<input type="hidden" name="phone" value="{E(e["phone"])}">'
                  f'<button>Resolve &amp; un-mute bot</button></form>')
        pill = ('<span class="pill resolved">resolved</span>' if e["resolved"]
                else '<span class="pill open">open</span>')
        rows += (f"<tr><td>{pill}</td><td>{E(e['at'])}</td>"
                 f"<td><a href='/conversations/{E(e['phone'])}'>{E(e['phone'])}</a></td>"
                 f"<td>{E(e['reason'])}<br><span class='muted'>“{E(e['last_message'][:120])}”</span></td>"
                 f"<td>{action}</td></tr>")
    return (f'<div class="card"><table><thead><tr><th></th><th>When</th><th>Phone</th>'
            f'<th>Reason</th><th></th></tr></thead><tbody>{rows}</tbody></table>'
            f'<p class="muted" style="margin-top:.8rem">While an escalation is open, '
            f'the WhatsApp bot stays silent on that number — resolving hands the '
            f'conversation back to the bot.</p></div>')


def page_sessions():
    db = db_mod.load()
    students = {s["id"]: s for s in db["students"]}
    rows = "".join(
        f"<tr><td>{s['id']}</td><td>{s['date']}</td><td>{s['time']}</td>"
        f"<td>{E(s['group'])}</td><td>{len(s['booked'])}/{s['capacity']}</td>"
        f"<td>{E(', '.join(students[b]['name'] for b in s['booked'] if b in students)) or '<span class=muted>—</span>'}</td></tr>"
        for s in db_mod.upcoming_sessions(db, limit=99))
    return (f'<div class="card"><table><thead><tr><th>ID</th><th>Date</th><th>Time</th>'
            f'<th>Group</th><th>Booked</th><th>Students</th></tr></thead>'
            f'<tbody>{rows}</tbody></table></div>')


def page_conversations():
    convs = all_conversations()
    if not convs:
        return '<div class="card muted">No conversations yet.</div>'
    rows = "".join(
        f"<tr><td><a href='/conversations/{E(c['phone'])}'>{E(c['phone'])}</a></td>"
        f"<td>{c['turns']}</td><td class='muted'>{E(c['last'])}…</td></tr>"
        for c in convs)
    return (f'<div class="card"><table><thead><tr><th>Phone</th><th>Messages</th>'
            f'<th>Last message</th></tr></thead><tbody>{rows}</tbody></table></div>')


def page_transcript(phone):
    history = db_mod.load_conversation(phone, max_turns=200)
    db = db_mod.load()
    student = db_mod.student_by_phone(db, phone)
    who = f" — parent of {E(student['name'])}" if student else " — unregistered number"
    msgs = "".join(f'<div class="msg {h["role"]}">{E(h["content"])}</div>'
                   for h in history)
    return (f'<p class="muted" style="margin-bottom:1rem">{E(phone)}{who}</p>'
            f'<div class="card chat">{msgs or "<span class=muted>Empty.</span>"}</div>'
            f'<a href="/conversations">← All conversations</a>')


def page_invoices():
    db = db_mod.load()
    students = {s["id"]: s for s in db["students"]}
    rows = ""
    for inv in db["invoices"]:
        student = students.get(inv["student_id"], {})
        pill = f'<span class="pill {inv["status"]}">{inv["status"]}</span>'
        action = ("" if inv["status"] == "paid" else
                  f'<form method="post" action="/invoices/paid" style="display:inline">'
                  f'<input type="hidden" name="invoice_id" value="{E(inv["id"])}">'
                  f'<button>Mark paid</button></form>')
        rows += (f"<tr><td>{E(inv['id'])}</td><td>{E(student.get('name', '?'))}</td>"
                 f"<td>{E(inv['description'])}</td><td>EGP {inv['amount_egp']}</td>"
                 f"<td>{E(inv.get('due', '—'))}</td><td>{pill}</td><td>{action}</td></tr>")
    return (f'<div class="card"><table><thead><tr><th>Invoice</th><th>Student</th>'
            f'<th>Description</th><th>Amount</th><th>Due</th><th>Status</th><th></th>'
            f'</tr></thead><tbody>{rows}</tbody></table></div>')


# --- server -------------------------------------------------------------------

class DashboardHandler(BaseHTTPRequestHandler):
    @property
    def password(self):
        return os.environ.get("DASHBOARD_PASSWORD", "")

    def _authorized(self):
        if not self.password:
            return True
        header = self.headers.get("Authorization", "")
        expected = base64.b64encode(f"staff:{self.password}".encode()).decode()
        return header == f"Basic {expected}"

    def _deny(self):
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="Race Line Academy Staff"')
        self.end_headers()

    def _html(self, body, status=200):
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _redirect(self, path):
        self.send_response(303)
        self.send_header("Location", path)
        self.end_headers()

    def do_GET(self):
        if not self._authorized():
            return self._deny()
        dev = not self.password
        path = urllib.parse.urlparse(self.path).path.rstrip("/") or "/"

        if path == "/":
            return self._html(layout("Overview", page_overview(), "/", dev))
        if path == "/escalations":
            return self._html(layout("Escalations", page_escalations(), path, dev))
        if path == "/sessions":
            return self._html(layout("Sessions", page_sessions(), path, dev))
        if path == "/conversations":
            return self._html(layout("Conversations", page_conversations(), path, dev))
        if path.startswith("/conversations/"):
            phone = urllib.parse.unquote(path.split("/conversations/", 1)[1])
            return self._html(layout("Transcript", page_transcript(phone),
                                     "/conversations", dev))
        if path == "/invoices":
            return self._html(layout("Invoices", page_invoices(), path, dev))
        return self._html(layout("Not found", '<p class="muted">Nothing here.</p>'),
                          status=404)

    def do_POST(self):
        if not self._authorized():
            return self._deny()
        length = int(self.headers.get("Content-Length", 0))
        form = urllib.parse.parse_qs(self.rfile.read(length).decode())
        path = urllib.parse.urlparse(self.path).path

        if path == "/escalations/resolve" and form.get("phone"):
            db_mod.resolve_escalations(form["phone"][0])
            return self._redirect("/escalations")
        if path == "/invoices/paid" and form.get("invoice_id"):
            mark_invoice_paid(form["invoice_id"][0])
            return self._redirect("/invoices")
        return self._redirect("/")

    def log_message(self, fmt, *args):
        pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8090)
    args = parser.parse_args()
    if not os.environ.get("DASHBOARD_PASSWORD"):
        print("WARNING: DASHBOARD_PASSWORD not set — running in open dev mode.")
    print(f"Staff dashboard on http://localhost:{args.port}")
    HTTPServer(("0.0.0.0", args.port), DashboardHandler).serve_forever()


if __name__ == "__main__":
    main()
