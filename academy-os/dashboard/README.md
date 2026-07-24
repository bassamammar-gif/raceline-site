# Race Line Academy OS — Staff Dashboard (Module 3)

Web dashboard for academy staff, sitting on top of the comms-agent data
layer. Standard library only — no dependencies, runs anywhere Python runs.

## What staff can do

- **Overview** — open escalations, upcoming sessions, unpaid invoices, and
  active conversations at a glance, with the next sessions and who's booked.
- **Escalations** — every conversation the WhatsApp bot handed to a human,
  with the triggering message. **Resolve & un-mute bot** hands the
  conversation back to the agent (while open, the bot stays silent on that
  number).
- **Sessions** — full upcoming schedule with capacity and booked students.
- **Conversations** — every WhatsApp thread, with full transcripts rendered
  as chat bubbles.
- **Invoices** — status per family, with one-click **Mark paid**.

## Run it

```bash
cd academy-os/dashboard
export DASHBOARD_PASSWORD=choose-a-secret   # login is user "staff" + this password
python3 server.py --port 8090
```

Open http://localhost:8090. Without `DASHBOARD_PASSWORD` the dashboard runs
in open dev mode and shows a red warning banner.

It reads and writes the same `../comms-agent/data/` files the WhatsApp agent
uses, so run it on the same machine (or shared volume) as the agent. If no
data exists yet, demo data seeds automatically on first load.

## Security notes (v1)

- HTTP Basic auth with a single shared staff password.
- Intended for the academy's own network, or behind a reverse proxy that
  terminates TLS. Don't expose it bare on the public internet.
- Per-staff accounts and an audit log are on the roadmap for when this moves
  to a real database.
