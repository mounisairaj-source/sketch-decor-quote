#!/usr/bin/env python3
"""
Sketch intake app — form + optional email polling.

Requires deployment somewhere with a public URL and continuous execution.
See references/intake-automation.md for what you need to supply.

Env vars required:
  ANTHROPIC_API_KEY      - for venue photo analysis
  BASE_URL               - e.g. https://quotes.yourdomain.com (used in links/emails)
Optional (email intake only):
  IMAP_HOST, IMAP_USER, IMAP_PASS
  SMTP_HOST, SMTP_USER, SMTP_PASS, SMTP_PORT (default 587)

Run:
  pip install flask anthropic --break-system-packages
  export ANTHROPIC_API_KEY=...
  export BASE_URL=http://localhost:5000
  python intake_app.py
"""
import os
import re
import uuid
import base64
import imaplib
import email
import smtplib
import threading
import time
from email.message import EmailMessage
from flask import Flask, request, send_from_directory, render_template_string

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.generate_quote import generate  # noqa: E402

import anthropic

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GENERATED_DIR = os.path.join(APP_DIR, "generated")
os.makedirs(GENERATED_DIR, exist_ok=True)

app = Flask(__name__)
client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env

BASE_URL = os.environ.get("BASE_URL", "http://localhost:5000")

FORM_HTML = """
<!doctype html><title>Get a Sketch décor quote</title>
<h2>Upload your venue photo + event details</h2>
<form method=post enctype=multipart/form-data action="/submit">
  <p>Venue photo: <input type=file name=photo required></p>
  <p>Event type: <input type=text name=event_type value="Wedding" required></p>
  <p>Guest count: <input type=number name=guests required></p>
  <p>Budget range: <input type=text name=budget placeholder="$40K+" required></p>
  <p>Event date: <input type=text name=date placeholder="TBD"></p>
  <p>Email (to send your quote link): <input type=email name=email required></p>
  <p><button type=submit>Generate my quote</button></p>
</form>
"""


def analyze_venue_photo(image_bytes, media_type="image/jpeg"):
    """Calls Claude vision to describe the venue's architecture in text.
    Does not reproduce the image anywhere in output — description only."""
    b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=400,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64}},
                {"type": "text", "text": (
                    "Describe this venue's real architecture for a décor-planning brief: "
                    "layout, aisle/floor, existing structures, backdrop, sightlines, ceiling. "
                    "If it already has decor installed, note that explicitly and describe the "
                    "underlying space, not the current decorations. Then write one short phrase "
                    "(under 20 words) tying a décor arch/focal point to this space's specific "
                    "landmark (e.g. 'the arch sits at the water's edge'). "
                    "Respond as JSON: {\"headline\": str, \"description\": str, \"tie_in\": str}"
                )},
            ],
        }],
    )
    import json as _json
    text = msg.content[0].text
    try:
        return _json.loads(text)
    except Exception:
        return {"headline": "Venue", "description": text[:300], "tie_in": ""}


def build_quote(photo_bytes, media_type, event_type, guests, budget, date):
    venue = analyze_venue_photo(photo_bytes, media_type)
    quote_id = uuid.uuid4().hex[:10]
    out_path = os.path.join(GENERATED_DIR, f"{quote_id}.html")
    generate(
        event={"event_type": event_type, "guests": guests, "budget": budget, "date": date},
        venue=venue,
        out_path=out_path,
    )
    return quote_id


def send_reply_email(to_addr, quote_url):
    host = os.environ.get("SMTP_HOST")
    if not host:
        print(f"[no SMTP configured] Would email {to_addr}: {quote_url}")
        return
    msg = EmailMessage()
    msg["Subject"] = "Your Sketch décor quote is ready"
    msg["From"] = os.environ["SMTP_USER"]
    msg["To"] = to_addr
    msg.set_content(
        f"Your venue's décor concepts are ready — take a look and build your estimate:\n\n{quote_url}\n\n"
        "All pricing is an estimate until confirmed on-site."
    )
    with smtplib.SMTP(host, int(os.environ.get("SMTP_PORT", 587))) as s:
        s.starttls()
        s.login(os.environ["SMTP_USER"], os.environ["SMTP_PASS"])
        s.send_message(msg)


@app.route("/")
def form():
    return FORM_HTML


@app.route("/submit", methods=["POST"])
def submit():
    photo = request.files["photo"]
    quote_id = build_quote(
        photo.read(),
        photo.mimetype or "image/jpeg",
        request.form["event_type"],
        int(request.form["guests"]),
        request.form["budget"],
        request.form.get("date", "TBD"),
    )
    quote_url = f"{BASE_URL}/quote/{quote_id}"
    send_reply_email(request.form["email"], quote_url)
    return render_template_string(
        "<h2>Your quote is ready</h2><p><a href='{{u}}'>{{u}}</a></p>"
        "<p>We've also emailed you this link.</p>", u=quote_url
    )


@app.route("/quote/<quote_id>")
def view_quote(quote_id):
    return send_from_directory(GENERATED_DIR, f"{quote_id}.html")


# ---- Optional: email intake via IMAP polling ----
EVENT_TYPE_RE = re.compile(r"event\s*type\s*[:\-]\s*(.+)", re.I)
GUESTS_RE = re.compile(r"guests?\s*[:\-]\s*(\d+)", re.I)
BUDGET_RE = re.compile(r"budget\s*[:\-]\s*(.+)", re.I)
DATE_RE = re.compile(r"date\s*[:\-]\s*(.+)", re.I)


def parse_event_body(body):
    def find(rx, default=""):
        m = rx.search(body)
        return m.group(1).strip() if m else default
    return {
        "event_type": find(EVENT_TYPE_RE, "Wedding"),
        "guests": int(find(GUESTS_RE, "0") or 0),
        "budget": find(BUDGET_RE, "Not specified"),
        "date": find(DATE_RE, "TBD"),
    }


def poll_inbox(interval_seconds=60):
    """Run this in a background thread/process. Requires IMAP_* env vars.
    NOTE: simple keyword parsing of the email body — for messier/free-form
    emails, replace parse_event_body() with a Claude text-extraction call."""
    host, user, pw = os.environ.get("IMAP_HOST"), os.environ.get("IMAP_USER"), os.environ.get("IMAP_PASS")
    if not host:
        print("IMAP not configured — skipping email polling.")
        return
    while True:
        try:
            m = imaplib.IMAP4_SSL(host)
            m.login(user, pw)
            m.select("inbox")
            _, ids = m.search(None, "UNSEEN")
            for eid in ids[0].split():
                _, data = m.fetch(eid, "(RFC822)")
                msg = email.message_from_bytes(data[0][1])
                from_addr = email.utils.parseaddr(msg["From"])[1]
                body, photo_bytes, media_type = "", None, "image/jpeg"
                for part in msg.walk():
                    ctype = part.get_content_type()
                    if ctype == "text/plain" and body == "":
                        body = part.get_payload(decode=True).decode(errors="ignore")
                    elif ctype.startswith("image/"):
                        photo_bytes = part.get_payload(decode=True)
                        media_type = ctype
                if photo_bytes:
                    details = parse_event_body(body)
                    quote_id = build_quote(photo_bytes, media_type, **details)
                    quote_url = f"{BASE_URL}/quote/{quote_id}"
                    send_reply_email(from_addr, quote_url)
                    print(f"Processed email from {from_addr} -> {quote_url}")
                m.store(eid, "+FLAGS", "\\Seen")
            m.logout()
        except Exception as e:
            print("IMAP poll error:", e)
        time.sleep(interval_seconds)


if __name__ == "__main__":
    if os.environ.get("IMAP_HOST"):
        threading.Thread(target=poll_inbox, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
