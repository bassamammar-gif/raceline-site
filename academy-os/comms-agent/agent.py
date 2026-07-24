"""The front-desk agent: takes an inbound parent message, returns the reply.

Safety is layered:
  1. A code-level pre-filter catches injury/incident/refund topics BEFORE the
     model sees them and escalates immediately — this never depends on the
     model following instructions.
  2. Once a conversation is escalated, the agent stays silent until staff
     resolve it (has_open_escalation gate).
  3. The model's tools physically cannot change prices, mark invoices paid,
     or read other families' data.
"""

from datetime import date

import academy_data as db_mod
import analytics
from tools import TOOL_DEFINITIONS, execute_tool

MODEL = "claude-opus-4-8"
MAX_TOOL_ROUNDS = 8

# Topics that must reach a human unfiltered by model judgement.
# Checked as lowercase substrings; Arabic terms included.
ESCALATION_KEYWORDS = [
    "injur", "hurt", "accident", "crash", "hospital", "bleed", "broke",
    "twist", "sprain", "ambulance", "unsafe", "dangerous",
    "refund", "money back", "lawyer", "sue", "legal",
    "إصابة", "مصاب", "اتصاب", "حادث", "مستشفى", "استرداد", "فلوسي", "محامي",
]

HANDOFF_REPLY = (
    "Thank you for your message. A member of the Race Line Academy team will "
    "contact you personally as soon as possible about this.\n\n"
    "شكراً لرسالتك. سيتواصل معك أحد أعضاء فريق Race Line Academy شخصياً في "
    "أقرب وقت بخصوص هذا الموضوع."
)

SYSTEM_PROMPT = """You are the front desk of Race Line Academy, Egypt's leading \
karting academy (part of Race Line Motorsports, the IAME and LN Racing Kart \
distributor and IAME Series Egypt promoter). You chat with parents over WhatsApp.

Style:
- Reply in the language the parent writes in — Egyptian Arabic or English. If \
they mix, mirror them.
- WhatsApp-appropriate: warm, short, no corporate filler. Use short paragraphs \
or dashes, never markdown headers or tables.
- One question at a time when you need information.

Rules:
- Use your tools for every factual claim about schedule, pricing, bookings, or \
invoices. Never answer those from memory or guess.
- Prices are fixed. You cannot offer discounts, waive fees, or promise refunds \
— for any such request, use escalate_to_human.
- Anything about injuries, incidents, safety complaints, or dissatisfaction: \
escalate_to_human immediately, and reply with empathy, without admitting fault \
or making commitments.
- Before booking or cancelling, confirm the exact session (date and time) with \
the parent.
- If the phone number isn't registered, be welcoming: share info freely, and \
offer to have the team set them up (escalate_to_human with their details).
- Never reveal information about other families or students.
- If you genuinely cannot help with the tools you have, escalate rather than \
improvise."""


def _pre_filter(text):
    lower = text.lower()
    return next((kw for kw in ESCALATION_KEYWORDS if kw in lower), None)


def _run_claude(phone, history, user_text):
    import anthropic

    client = anthropic.Anthropic()
    context = (f"[Context for you, not from the parent: today is "
               f"{date.today().isoformat()}; the parent's WhatsApp number is "
               f"{phone}.]\n\n{user_text}")
    messages = [{"role": h["role"], "content": h["content"]} for h in history]
    messages.append({"role": "user", "content": context})

    for _ in range(MAX_TOOL_ROUNDS):
        response = client.messages.create(
            model=MODEL,
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            tools=TOOL_DEFINITIONS,
            messages=messages,
        )
        if response.stop_reason != "tool_use":
            return next((b.text for b in response.content if b.type == "text"),
                        HANDOFF_REPLY)

        messages.append({"role": "assistant", "content": response.content})
        results = []
        for block in response.content:
            if block.type == "tool_use":
                result = execute_tool(block.name, block.input, phone,
                                      last_user_message=user_text)
                results.append({"type": "tool_result",
                                "tool_use_id": block.id, "content": result})
        messages.append({"role": "user", "content": results})

    return HANDOFF_REPLY


def handle_message(phone, text):
    """Process one inbound WhatsApp message; return the reply to send,
    or None if the conversation is with a human and the bot must stay silent."""
    db_mod.append_conversation(phone, "user", text)
    analytics.record("message_in", phone, topic=analytics.classify_topic(text))

    if db_mod.has_open_escalation(phone):
        return None                      # a human owns this conversation

    keyword = _pre_filter(text)
    if keyword:
        db_mod.log_escalation(phone, f"Auto-escalated (matched '{keyword}')", text)
        analytics.record("escalated", phone, reason=f"keyword:{keyword}")
        db_mod.append_conversation(phone, "assistant", HANDOFF_REPLY)
        analytics.record("message_out", phone)
        return HANDOFF_REPLY

    try:
        history = db_mod.load_conversation(phone)[:-1]   # exclude msg just stored
        reply = _run_claude(phone, history, text)
    except Exception as exc:
        db_mod.log_escalation(phone, f"Agent error: {exc}", text)
        analytics.record("escalated", phone, reason="agent_error")
        reply = HANDOFF_REPLY

    db_mod.append_conversation(phone, "assistant", reply)
    analytics.record("message_out", phone)
    return reply
