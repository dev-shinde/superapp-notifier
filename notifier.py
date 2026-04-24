"""
notifier.py — WhatsApp notification cron job
Deploy to Render.com as a Cron Job (*/30 * * * *)
Env vars: SUPABASE_URL, SUPABASE_KEY, TWILIO_SID, TWILIO_TOKEN, TWILIO_FROM, TWILIO_TO
Quiet hours: 00:00 – 06:30 IST
"""
import os, requests
from datetime import datetime, timezone, timedelta

# ── Config ────────────────────────────────────────────────────────────────────
SUPABASE_URL  = os.environ["SUPABASE_URL"]
SUPABASE_KEY  = os.environ["SUPABASE_KEY"]
TWILIO_SID    = os.environ["TWILIO_SID"]
TWILIO_TOKEN  = os.environ["TWILIO_TOKEN"]
TWILIO_FROM   = os.environ["TWILIO_FROM"]
TWILIO_TO     = os.environ["TWILIO_TO"]
NAME          = os.environ.get("USER_NAME", "Zen")

IST         = timezone(timedelta(hours=5, minutes=30))
QUIET_START = 0.0   # midnight
QUIET_END   = 6.5   # 6:30 AM

# ── Supabase helpers ──────────────────────────────────────────────────────────
def supa_get(table: str, params: dict = None) -> list:
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    hdrs = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    r = requests.get(url, headers=hdrs, params=params, timeout=10)
    return r.json() if r.ok else []

# ── WhatsApp ──────────────────────────────────────────────────────────────────
def send_whatsapp(body: str):
    from twilio.rest import Client
    Client(TWILIO_SID, TWILIO_TOKEN).messages.create(
        body=body, from_=TWILIO_FROM, to=TWILIO_TO
    )
    print(f"  ✅ Sent: {body[:80].replace(chr(10),' ')}...")

# ── Message builders ──────────────────────────────────────────────────────────
def topic_lines(due_rows: list) -> str:
    lines = []
    sql_rows = [r for r in due_rows if r.get('subject') == 'SQL']
    dsa_rows = [r for r in due_rows if r.get('subject') == 'DSA']
    if sql_rows:
        lines.append(f"  🗄  SQL ({len(sql_rows)}): " + ", ".join(r['topic'] for r in sql_rows[:3])
                     + ("..." if len(sql_rows) > 3 else ""))
    if dsa_rows:
        lines.append(f"  🧮 DSA ({len(dsa_rows)}): " + ", ".join(r['topic'] for r in dsa_rows[:3])
                     + ("..." if len(dsa_rows) > 3 else ""))
    return "\n".join(lines)

def streak_info(due_rows: list) -> str:
    max_streak = max((r.get('streak', 0) for r in due_rows), default=0)
    if max_streak >= 7:  return f"🔥 {max_streak}-day streak on the line!"
    if max_streak >= 3:  return f"⚡ {max_streak}-day streak — don't break it."
    return ""

def build_message(now_ist: datetime, n: int, due_rows: list, send_count: int) -> str:
    h    = now_ist.hour
    date = now_ist.strftime("%A, %d %b")   # e.g. "Thursday, 24 Apr"
    topics = topic_lines(due_rows)
    streak = streak_info(due_rows)

    # ── First message of the day (morning) ───────────────────────────────────
    if send_count == 0:
        greeting = (
            "Good morning" if h < 12 else
            "Good afternoon" if h < 17 else
            "Good evening"
        )
        msg = (
            f"☀️ {greeting}, {NAME}!\n"
            f"📅 {date}\n\n"
            f"Today's target: *{n} question{'s' if n>1 else ''}* due for review.\n\n"
            f"{topics}\n\n"
        )
        if streak: msg += f"{streak}\n\n"
        msg += "Open SuperApp and clear them 🎯\nlocalhost:7339"
        return msg

    # ── Follow-up reminders ───────────────────────────────────────────────────
    if send_count == 1:
        return (
            f"⏰ Still {n} question{'s' if n>1 else ''} pending, {NAME}.\n\n"
            f"{topics}\n\n"
            f"15 minutes is all it takes. Open SuperApp now."
        )
    if send_count == 2:
        return (
            f"🚨 {NAME}, {n} question{'s' if n>1 else ''} still waiting.\n\n"
            f"{topics}\n\n"
            + (f"{streak}\n\n" if streak else "")
            + "Don't let today slip. localhost:7339"
        )
    # Final reminder (3+)
    return (
        f"🔔 Final nudge for now, {NAME}.\n"
        f"{n} question{'s' if n>1 else ''} due — whenever you're ready:\n\n"
        f"{topics}"
    )

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    now_ist = datetime.now(IST)
    print(f"[{now_ist.strftime('%Y-%m-%d %H:%M IST')}] Notifier running")

    # Quiet hours check
    h = now_ist.hour + now_ist.minute / 60
    if QUIET_START <= h < QUIET_END:
        print("  Quiet hours — skipping")
        return

    today = now_ist.date().isoformat()

    # Check total KB entries — if zero, app hasn't been used yet
    all_kb = supa_get("knowledge_base", {"select": "id", "limit": "1"})
    kb_empty = len(all_kb) == 0

    # Goals already met today?
    status = supa_get("daily_status", {"date": f"eq.{today}", "select": "*"})
    if not kb_empty and status and status[0].get("goals_met"):
        print("  Goals met — no message needed ✅")
        return

    # What's due?
    due_rows = supa_get(
        "knowledge_base",
        {"next_due": f"lte.{today}", "select": "topic,subject,next_due,streak",
         "order": "next_due.asc"}
    )
    n = len(due_rows)

    # If KB is empty or nothing due — nudge to open app and start practising
    if kb_empty or n == 0:
        body = (
            f"👋 Good morning, {NAME}!\n\n"
            f"Your SuperApp is set up but your Knowledge Base is empty.\n"
            f"Open the app and complete at least 5 practice questions today to start tracking your progress.\n\n"
            f"localhost:7339"
        )
        try:
            send_whatsapp(body)
            print("  KB empty — sent onboarding nudge")
        except Exception as e:
            print(f"  ❌ WhatsApp failed: {e}")
        return

    # How many times sent today? (track via a simple count from session_logs or just use hour)
    # Estimate: first message after quiet hours ends, then every 30 min
    # send_count = how many 30-min slots since 6:30 AM have passed
    quiet_end_dt = now_ist.replace(hour=6, minute=30, second=0, microsecond=0)
    mins_since_start = max(0, (now_ist - quiet_end_dt).seconds // 60)
    send_count = mins_since_start // 30   # 0=first, 1=second, etc.

    body = build_message(now_ist, n, due_rows, send_count)

    try:
        send_whatsapp(body)
        print(f"  Due items: {n} | Send #{send_count + 1}")
    except Exception as e:
        print(f"  ❌ WhatsApp failed: {e}")

if __name__ == "__main__":
    main()
