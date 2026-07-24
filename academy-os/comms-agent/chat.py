#!/usr/bin/env python3
"""Local simulator: chat with the front-desk agent in your terminal exactly as
a parent would over WhatsApp. No WhatsApp setup needed.

Usage:
    python3 chat.py                  # chat as a registered demo parent
    python3 chat.py +201099887766    # chat as an unregistered number

Requires ANTHROPIC_API_KEY (safety escalations work without it, but normal
replies need the model).
"""

import sys

from agent import handle_message

DEFAULT_PHONE = "+201001112233"      # Omar Khaled's parent in the seed data


def main():
    phone = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PHONE
    print(f"Chatting as {phone} — Ctrl-C or empty line to quit.\n")
    while True:
        try:
            text = input("parent> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not text:
            break
        reply = handle_message(phone, text)
        if reply is None:
            print("[conversation is escalated — bot is silent, a human owns it]\n")
        else:
            print(f"\nacademy> {reply}\n")


if __name__ == "__main__":
    main()
