# Race Line Academy OS — WhatsApp Comms Agent (Module 2)

The academy's front desk in software. Parents message the academy's WhatsApp
number; the agent answers questions about schedule, pricing, and what to
bring, looks up their own bookings and invoices, books and cancels sessions
against real availability, and hands anything sensitive to a human.

## Safety model — enforced in code, not just in the prompt

1. **Keyword pre-filter before the model.** Messages mentioning injuries,
   accidents, refunds, or legal matters (English and Arabic) are escalated to
   staff *before* Claude ever sees them, with a fixed bilingual holding reply.
2. **Silence gate.** Once a conversation is escalated, the bot stays
   completely silent on that number until staff mark it resolved
   (`academy_data.resolve_escalations(phone)`). A human owns it.
3. **Capability limits.** The agent's tools physically cannot change prices,
   mark invoices paid, issue refunds, or read another family's data — those
   actions don't exist as tools.
4. **Fail-safe errors.** Any agent error escalates and sends the holding
   reply rather than leaving a parent unanswered.

## Try it now (no WhatsApp setup needed)

```bash
cd academy-os/comms-agent
pip install anthropic
export ANTHROPIC_API_KEY=sk-ant-...
python3 chat.py                    # chat as a registered demo parent
python3 chat.py +201099887766      # chat as an unknown number
```

Demo data (students, two weeks of Friday/Saturday sessions, invoices) is
seeded automatically into `data/academy.json` on first run — edit it freely.

Things to try: "What sessions are available for my son?", "Book him on
Friday", "How much is the monthly program?", "هو ابني ممكن ييجي امتى؟",
"My son was hurt at the track" (watch it escalate instantly).

## Going live on WhatsApp

Uses the Meta WhatsApp Business Cloud API (free tier covers an academy's
volume comfortably).

1. Create a Meta for Developers app → add the WhatsApp product → get a
   permanent token and phone number ID.
2. ```bash
   export WHATSAPP_TOKEN=...
   export WHATSAPP_PHONE_ID=...
   export WHATSAPP_VERIFY_TOKEN=any-secret-string
   python3 whatsapp.py --port 8080
   ```
3. Expose the port over HTTPS and register `https://<host>/webhook` as the
   callback URL (subscribed to `messages`), entering the same verify token.

## Daily back-office run

```bash
python3 reminders.py           # print tomorrow's session reminders + invoice
                               # nudges as drafts
python3 reminders.py --send    # actually send them via WhatsApp
```

Schedule with cron, e.g. `0 18 * * * cd .../comms-agent && python3 reminders.py --send`.

## Files

| File | Role |
|---|---|
| `academy_data.py` | Students, schedule, pricing, invoices, escalation queue, conversation history (JSON storage — swappable for a real DB later) |
| `tools.py` | Tool definitions + dispatcher; booking rules enforced here |
| `agent.py` | Safety pre-filter, escalation gate, Claude agent loop |
| `chat.py` | Terminal simulator — demo without WhatsApp |
| `whatsapp.py` | Meta Cloud API webhook server + sender (stdlib only) |
| `reminders.py` | Daily session reminders and invoice chases |

## Escalation workflow for staff (v1)

Open escalations live in `data/escalations.json`. When staff have handled
one, resolve it so the bot resumes:

```bash
python3 -c "import academy_data; academy_data.resolve_escalations('+2010...')"
```

A proper staff dashboard is part of module 3.
