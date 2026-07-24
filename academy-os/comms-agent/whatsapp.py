#!/usr/bin/env python3
"""WhatsApp Business (Meta Cloud API) transport for the front-desk agent.

Runs a small webhook server (standard library only) that receives inbound
WhatsApp messages, passes them to agent.handle_message, and sends the reply
back through the Cloud API.

Setup (Meta for Developers → WhatsApp → API Setup):
    export WHATSAPP_TOKEN=...        # permanent access token
    export WHATSAPP_PHONE_ID=...     # the business phone number ID
    export WHATSAPP_VERIFY_TOKEN=... # any secret string; enter the same value
                                     # when registering the webhook URL
    python3 whatsapp.py --port 8080

Expose the port publicly (reverse proxy / tunnel) and register
https://<your-host>/webhook as the callback URL, subscribed to `messages`.
"""

import argparse
import json
import os
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

from agent import handle_message

GRAPH_URL = "https://graph.facebook.com/v21.0"


def send_whatsapp(phone, text):
    token = os.environ["WHATSAPP_TOKEN"]
    phone_id = os.environ["WHATSAPP_PHONE_ID"]
    payload = json.dumps({
        "messaging_product": "whatsapp",
        "to": phone.lstrip("+"),
        "type": "text",
        "text": {"body": text},
    }).encode()
    req = urllib.request.Request(
        f"{GRAPH_URL}/{phone_id}/messages", data=payload, method="POST",
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def _extract_messages(event):
    """Yield (phone, text) for each inbound text message in a webhook event."""
    for entry in event.get("entry", []):
        for change in entry.get("changes", []):
            for msg in change.get("value", {}).get("messages", []):
                if msg.get("type") == "text":
                    yield "+" + msg["from"], msg["text"]["body"]


class WebhookHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Meta's webhook verification handshake
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        if (parsed.path == "/webhook"
                and params.get("hub.verify_token", [""])[0]
                == os.environ.get("WHATSAPP_VERIFY_TOKEN")):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(params.get("hub.challenge", [""])[0].encode())
        else:
            self.send_response(403)
            self.end_headers()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        # Acknowledge immediately; Meta retries on non-200
        self.send_response(200)
        self.end_headers()
        try:
            event = json.loads(body)
        except json.JSONDecodeError:
            return
        for phone, text in _extract_messages(event):
            try:
                reply = handle_message(phone, text)
                if reply:
                    send_whatsapp(phone, reply)
            except Exception as exc:
                print(f"[error] {phone}: {exc}")

    def log_message(self, fmt, *args):
        pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    for var in ("WHATSAPP_TOKEN", "WHATSAPP_PHONE_ID", "WHATSAPP_VERIFY_TOKEN"):
        if not os.environ.get(var):
            raise SystemExit(f"Missing environment variable: {var}")
    print(f"Listening for WhatsApp webhooks on :{args.port}/webhook")
    HTTPServer(("0.0.0.0", args.port), WebhookHandler).serve_forever()


if __name__ == "__main__":
    main()
