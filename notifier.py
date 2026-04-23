"""
notifier.py — WhatsApp notification cron job
Deploy this to Render.com as a background worker.
Set environment variables: SUPABASE_URL, SUPABASE_KEY, TWILIO_SID, TWILIO_TOKEN, TWILIO_FROM, TWILIO_TO
Quiet hours: 00:00 - 06:30 IST (no messages sent)
"""
import os, json, requests
from datetime import datetime, timezone, timedelta

# ── Config from env vars ───────────────────────────────────────────────────
SUPABASE_URL  = os.environ["SUPABASE_URL"]
SUPABASE_KEY  = os.environ["SUPABASE_KEY"]
TWILIO_SID    = os.environ["TWILIO_SID"]
TWILIO_TOKEN  = os.environ["TWILIO_TOKEN"]
TWILIO_FROM   = os.environ["TWILIO_FROM"]   # "whatsapp:+14155238886"
TWILIO_TO     = os.environ["TWILIO_TO"]     # "whatsapp:+91XXXXXXXXXX"

IST = timezone(timedelta(hours=5, minutes=30))

QUIET_START = 0    # midnight
QUIET_END   = 6.5  # 6:30 AM

MESSAGES = [
    # (hour_ist, message)
    (None, "\u26a1 {name}, you have {n} questions due today:\n{topics}\nOpen SuperApp and clear them."),
    (None, "\u23f0 Still {n} due, {name}. Your streak is at risk. 15 minutes is all it takes."),
    (None, "\ud83d\udea8 {n} questions still pending, {name}. Don\u2019t let today\u2019s streak break."),
    (None, "\ud83d\udd25 Last reminder for today, {name}. {n} questions. Just open the app and go."),
]

def supa_get(table: str, params: dict = None) -> list:
    url     = f"{SUPABASE_URL}/rest/v1/{table}"
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    r = requests.get(url, headers=headers, params=params, timeout=10)
    return r.json() if r.ok else []

def send_whatsapp(body: str):
    from twilio.rest import Client
    client = Client(TWILIO_SID, TWILIO_TOKEN)
    client.messages.create(body=body, from_=TWILIO_FROM, to=TWILIO_TO)
    print(f"  Sent: {body[:60]}...")

def in_quiet_hours(now_ist: datetime) -> bool:
    h = now_ist.hour + now_ist.minute / 60
    return h < QUIET_END or h >= 24 + QUIET_START  # midnight to 6:30

def build_topic_list(due_rows: list) -> str:
    if not due_rows:
        return "(none)"
    lines = []
    for r in due_rows[:5]:
        lines.append(f"\u2022 {r.get('topic','')} ({r.get('subject','')})")
    if len(due_rows) > 5:
        lines.append(f"  ...and {len(due_rows)-5} more")
    return "\n".join(lines)

def main():
    now_ist = datetime.now(IST)
    print(f"[{now_ist.strftime('%Y-%m-%d %H:%M IST')}] Notifier running")

    if in_quiet_hours(now_ist):
        print("  Quiet hours — skipping")
        return

    today = now_ist.date().isoformat()

    # Check daily status
    status_rows = supa_get("daily_status", {"date": f"eq.{today}", "select": "*"})
    if status_rows and status_rows[0].get("goals_met"):
        print("  Goals met — no message needed")
        return

    # Get due items
    due_rows = supa_get(
        "knowledge_base",
        {"next_due": f"lte.{today}", "select": "topic,subject,next_due", "order": "next_due.asc"}
    )
    n = len(due_rows)
    if n == 0:
        print("  Nothing due — skipping")
        return

    # Pick message based on time of day
    h = now_ist.hour
    if h < 10:   template = MESSAGES[0][1]
    elif h < 14: template = MESSAGES[1][1]
    elif h < 18: template = MESSAGES[2][1]
    else:        template = MESSAGES[3][1]

    body = template.format(
        name   = "Zen",
        n      = n,
        topics = build_topic_list(due_rows)
    )

    try:
        send_whatsapp(body)
        print(f"  Message sent. Due items: {n}")
    except Exception as e:
        print(f"  WhatsApp send failed: {e}")

if __name__ == "__main__":
    main()
