"""
notifier.py — WhatsApp notification cron job
Deploy to Render.com as a Cron Job (*/30 * * * *)
Real-time progress-aware messages based on daily_plan + daily_status.
"""
import os, requests
from datetime import datetime, timezone, timedelta

SUPABASE_URL  = os.environ["SUPABASE_URL"]
SUPABASE_KEY  = os.environ["SUPABASE_KEY"]
TWILIO_SID    = os.environ["TWILIO_SID"]
TWILIO_TOKEN  = os.environ["TWILIO_TOKEN"]
TWILIO_FROM   = os.environ["TWILIO_FROM"]
TWILIO_TO     = os.environ["TWILIO_TO"]
NAME          = os.environ.get("USER_NAME", "Dev")

IST         = timezone(timedelta(hours=5, minutes=30))
QUIET_START = 0.0
QUIET_END   = 6.5

def supa(table, params=None):
    hdrs = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    r = requests.get(f"{SUPABASE_URL}/rest/v1/{table}",
                     headers=hdrs, params=params, timeout=10)
    return r.json() if r.ok else []

def supa_patch(table, match_params, data):
    hdrs = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json", "Prefer": "return=minimal"}
    requests.patch(f"{SUPABASE_URL}/rest/v1/{table}",
                   headers=hdrs, params=match_params, json=data, timeout=10)

def send_whatsapp(body):
    from twilio.rest import Client
    Client(TWILIO_SID, TWILIO_TOKEN).messages.create(
        body=body, from_=TWILIO_FROM, to=TWILIO_TO)
    print(f"  ✅ Sent: {body[:80].replace(chr(10),' ')}...")

def plan_lines(plan, done_only=False, pending_only=False):
    lines = []
    for p in plan:
        if done_only    and not p["done"]: continue
        if pending_only and p["done"]:     continue
        icon  = "✅" if p["done"] else "⏳"
        prog  = f"{p['completed_qs']}/{p['target_qs']}"
        lines.append(f"  {icon} {p['topic']} ({p['subject']}) — {prog}")
    return "\n".join(lines) if lines else "  (nothing)"

def main():
    now = datetime.now(IST)
    print(f"[{now.strftime('%Y-%m-%d %H:%M IST')}] Notifier running")

    h = now.hour + now.minute / 60
    if QUIET_START <= h < QUIET_END:
        print("  Quiet hours — skipping")
        return

    today = now.date().isoformat()

    # ── Get daily status ───────────────────────────────────────────────
    status_rows = supa("daily_status", {"date": f"eq.{today}", "select": "*"})
    status      = status_rows[0] if status_rows else {}

    # ── Get today's plan ───────────────────────────────────────────────
    plan = supa("daily_plan", {
        "date":   f"eq.{today}",
        "select": "topic,subject,target_qs,completed_qs,done",
        "order":  "done.asc,subject.asc"
    })

    # ── Check KB for content ───────────────────────────────────────────
    kb_rows = supa("knowledge_base", {"select": "id", "limit": "1"})
    kb_empty = len(kb_rows) == 0

    # ── Determine message type ─────────────────────────────────────────
    # All done today?
    if plan:
        all_done = all(p["done"] for p in plan)
    else:
        all_done = status.get("goals_met", False) and not kb_empty

    # Already sent completion message?
    if all_done and status.get("completion_msg_sent"):
        print("  Completion already sent — no more messages today ✅")
        return

    # All done — send completion message once
    if all_done and not kb_empty:
        done_lines = plan_lines(plan, done_only=True)
        body = (
            f"🔥 DONE for today, {NAME}!\n\n"
            f"All tasks complete:\n{done_lines}\n\n"
            f"Streak extended 💪\n"
            f"Sites unblocked. See you tomorrow!"
        )
        send_whatsapp(body)
        # Mark completion sent
        if status_rows:
            supa_patch("daily_status", {"date": f"eq.{today}"},
                       {"goals_met": True, "completion_msg_sent": True})
        return

    # ── Calculate progress ─────────────────────────────────────────────
    total_qs    = sum(p["target_qs"]    for p in plan) if plan else 0
    done_qs     = sum(p["completed_qs"] for p in plan) if plan else 0
    pending     = [p for p in plan if not p["done"]]

    # Estimate which send number this is (based on time since quiet hours ended)
    quiet_end_dt  = now.replace(hour=6, minute=30, second=0, microsecond=0)
    mins_elapsed  = max(0, int((now - quiet_end_dt).total_seconds() / 60))
    send_num      = mins_elapsed // 30   # 0=first, 1=second, etc.

    # ── Build message ──────────────────────────────────────────────────
    if kb_empty or not plan:
        # App not used yet — onboarding nudge
        body = (
            f"👋 Good morning, {NAME}!\n\n"
            f"Open SuperApp and start today's SQL practice.\n"
            f"The first session sets your baseline.\n\n"
            f"localhost:7339"
        )

    elif send_num == 0:
        # First message of the day — full plan overview
        greeting = "Good morning" if now.hour < 12 else "Good afternoon" if now.hour < 17 else "Good evening"
        date_str = now.strftime("%A, %d %b")
        plan_str = plan_lines(plan)
        body = (
            f"☀️ {greeting}, {NAME}!\n"
            f"📅 {date_str}\n\n"
            f"Today's plan ({total_qs} questions):\n"
            f"{plan_str}\n\n"
            f"Open SuperApp and get started 🎯\n"
            f"localhost:7339"
        )

    elif done_qs > 0:
        # Mid-day — show progress
        pending_str = plan_lines(plan, pending_only=True)
        body = (
            f"💪 Keep going, {NAME}!\n\n"
            f"Progress: {done_qs}/{total_qs} done\n\n"
            f"Still pending:\n{pending_str}\n\n"
            f"You're {round(done_qs/total_qs*100)}% there. Finish it!"
        )

    elif send_num == 1:
        # First reminder — nothing done yet
        pending_str = plan_lines(plan, pending_only=True)
        body = (
            f"⏰ Reminder, {NAME}.\n\n"
            f"0/{total_qs} questions done today.\n\n"
            f"Today's plan:\n{pending_str}\n\n"
            f"15 minutes is all it takes. localhost:7339"
        )

    elif send_num == 2:
        # Second reminder — getting urgent
        body = (
            f"🚨 {NAME}, {total_qs} questions still waiting.\n\n"
            f"{plan_lines(plan, pending_only=True)}\n\n"
            f"Don't break the streak. localhost:7339"
        )

    else:
        # Final nudge
        body = (
            f"🔔 Last nudge for now, {NAME}.\n"
            f"{total_qs - done_qs} questions pending whenever you're ready.\n\n"
            f"{plan_lines(plan, pending_only=True)}"
        )

    try:
        send_whatsapp(body)
        print(f"  Send #{send_num+1} | {done_qs}/{total_qs} done")
    except Exception as e:
        print(f"  ❌ WhatsApp failed: {e}")

if __name__ == "__main__":
    main()
