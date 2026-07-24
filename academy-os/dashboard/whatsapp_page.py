"""WhatsApp analytics page: conversation statuses, funnel, conversion rates,
and FAQ topic breakdown — computed from the comms agent's event log."""

import html

import analytics

E = html.escape

STATUS_COLORS = {
    "escalated": "#E10600",
    "booked": "#D2FF00",
    "registered": "#4fc3f7",
    "new lead": "#e8c84a",
    "quiet lead": "#7C8460",
}

TOPIC_LABELS = {
    "booking": "Booking requests", "pricing": "Pricing", "schedule": "Schedule & times",
    "logistics": "What to bring / ages", "progress": "Child's progress",
    "payment": "Payments & invoices", "other": "Other",
}


def _status_pill(status):
    color = STATUS_COLORS.get(status, "#7C8460")
    return (f'<span class="pill" style="background:{color}22;color:{color};'
            f'border:1px solid {color}55">{E(status)}</span>')


def _bar(label, value, max_value, color="#D2FF00", suffix=""):
    pct = round(100 * value / max_value) if max_value else 0
    return (f'<div class="fun-row"><div class="fun-label">{E(label)}</div>'
            f'<div class="fun-track"><div class="fun-fill" '
            f'style="width:{max(pct, 2)}%;background:{color}"></div></div>'
            f'<div class="fun-val">{value}{suffix}</div></div>')


def page_whatsapp():
    s = analytics.summary()

    if not s["total_conversations"]:
        return ('<div class="card muted">No WhatsApp activity recorded yet. '
                'Stats appear automatically once the comms agent starts '
                'handling messages.</div>')

    tiles = f"""
    <div class="tiles">
      <div class="tile"><div class="label">Conversations</div>
        <div class="value">{s['total_conversations']}</div></div>
      <div class="tile"><div class="label">New leads</div>
        <div class="value" style="color:#e8c84a">{s['new_leads']}</div></div>
      <div class="tile"><div class="label">Bookings via WhatsApp</div>
        <div class="value" style="color:#D2FF00">{s['bookings_via_whatsapp']}</div></div>
      <div class="tile"><div class="label">Conversion to booking</div>
        <div class="value">{s['conversion_rate']}%</div></div>
      <div class="tile{' alert' if s['escalation_rate'] > 30 else ''}">
        <div class="label">Escalation rate</div>
        <div class="value">{s['escalation_rate']}%</div></div>
    </div>"""

    top = s["funnel"][0][1]
    funnel = ('<div class="card"><h2>Funnel <span class="sub">contact → booking</span></h2>'
              + "".join(_bar(label, n, top) for label, n in s["funnel"])
              + '</div>')

    max_topic = s["faq"][0][1] if s["faq"] else 1
    faq = ('<div class="card"><h2>What parents ask about</h2>'
           + "".join(_bar(TOPIC_LABELS.get(t, t), n, max_topic, "#4fc3f7")
                     for t, n in s["faq"])
           + '<p class="note">Counted per inbound message, keyword-classified '
             '(English + Arabic). Use this to decide what belongs on the '
             'website, in ads, and in the agent\'s standard answers.</p></div>')

    rows = ""
    for c in s["conversations"]:
        who = E(c["student"]) if c["student"] else '<span class="muted">unregistered</span>'
        rows += (f"<tr><td>{_status_pill(c['status'])}</td>"
                 f"<td><a href='/conversations/{E(c['phone'])}'>{E(c['phone'])}</a></td>"
                 f"<td>{who}</td><td>{c['msgs_in']} in / {c['msgs_out']} out</td>"
                 f"<td>{c['bookings']}</td>"
                 f"<td>{E(TOPIC_LABELS.get(c['top_topic'], c['top_topic']))}</td>"
                 f"<td class='muted'>{E(c['last_seen'][:16].replace('T', ' '))}</td></tr>")
    table = (f'<div class="card"><h2>Conversations</h2><table><thead><tr>'
             f'<th>Status</th><th>Phone</th><th>Student</th><th>Messages</th>'
             f'<th>Bookings</th><th>Top topic</th><th>Last activity</th>'
             f'</tr></thead><tbody>{rows}</tbody></table></div>')

    return tiles + funnel + faq + table
