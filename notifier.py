"""
notifier.py — WhatsApp notification cron (Render, every 30 min)
Daily completion = ALL three:
  1. SQL topic questions done (daily_plan)
  2. SQL Drill done (5 Qs, binary)
  3. DSA questions >= 6
"""
import os, requests, json
from datetime import datetime, timezone, timedelta

SUPABASE_URL  = os.environ["SUPABASE_URL"]
SUPABASE_KEY  = os.environ["SUPABASE_KEY"]
TWILIO_SID    = os.environ["TWILIO_SID"]
TWILIO_TOKEN  = os.environ["TWILIO_TOKEN"]
TWILIO_FROM   = os.environ["TWILIO_FROM"]
TWILIO_TO     = os.environ["TWILIO_TO"]
NAME          = os.environ.get("USER_NAME", "Dev")
DSA_TARGET    = int(os.environ.get("DSA_DAILY_TARGET", "6"))

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

def plan_lines(plan, pending_only=False, done_only=False):
    lines = []
    for p in plan:
        if pending_only and p["done"]: continue
        if done_only   and not p["done"]: continue
        icon = "✅" if p["done"] else "⏳"
        lines.append(f"  {icon} {p['topic']} — {p['completed_qs']}/{p['target_qs']}")
    return "\n".join(lines) or "  (none)"

def main():
    now = datetime.now(IST)
    print(f"[{now.strftime('%Y-%m-%d %H:%M IST')}] Notifier running")

    h = now.hour + now.minute / 60
    if QUIET_START <= h < QUIET_END:
        print("  Quiet hours — skipping")
        return

    today = now.date().isoformat()

    # ── Fetch everything ──────────────────────────────────────────────
    status_rows = supa("daily_status", {"date": f"eq.{today}", "select": "*"})
    status      = status_rows[0] if status_rows else {}

    plan = supa("daily_plan", {
        "date":   f"eq.{today}",
        "select": "topic,subject,target_qs,completed_qs,done",
        "order":  "done.asc,subject.asc"
    })

    kb_rows  = supa("knowledge_base", {"select": "id", "limit": "1"})
    kb_empty = len(kb_rows) == 0

    drill_done = bool(status.get("drill_done", False))
    dsa_done   = int(status.get("dsa_done", 0))
    completion_sent = bool(status.get("completion_msg_sent", False))

    # ── Check each goal ───────────────────────────────────────────────
    sql_plan  = [p for p in plan if p.get("subject") == "SQL"]
    sql_done  = all(p["done"] for p in sql_plan) if sql_plan else False
    sql_qs    = sum(p["completed_qs"] for p in sql_plan)
    sql_total = sum(p["target_qs"]    for p in sql_plan)

    all_complete = sql_done and drill_done and (dsa_done >= DSA_TARGET)

    # Already done today?
    if all_complete and completion_sent:
        print("  All goals complete — completion already sent ✅")
        return

    # Onboarding (no KB yet)
    if kb_empty:
        h_val = now.hour
        if h_val < 8 or h_val >= 22:
            print("  KB empty — outside waking hours, skipping")
            return
        body = (f"👋 Good morning, {NAME}!\n\n"
                f"Open SuperApp and start today's practice.\n"
                f"localhost:7339")
        send_whatsapp(body); return

    # ── Completion message (once) ────────────────────────────────────
    if all_complete and not completion_sent:
        body = (
            f"🔥 DONE for today, {NAME}!\n\n"
            f"✅ SQL: {sql_qs}/{sql_total} questions\n"
            f"✅ SQL Drill: 5/5 complete\n"
            f"✅ DSA: {dsa_done}/{DSA_TARGET} questions\n\n"
            f"Streak extended 💪  Sites unblocked.\n"
            f"See you tomorrow!"
        )
        send_whatsapp(body)
        supa_patch("daily_status", {"date": f"eq.{today}"},
                   {"goals_met": True, "completion_msg_sent": True})
        return

    # ── Progress message — build based on what's pending ────────────
    quiet_end_dt  = now.replace(hour=6, minute=30, second=0, microsecond=0)
    mins_since    = max(0, int((now - quiet_end_dt).total_seconds() / 60))
    send_num      = mins_since // 30

    # Morning (first message)
    if send_num == 0:
        greeting = "Good morning" if now.hour < 12 else "Good afternoon" if now.hour < 17 else "Good evening"
        date_str = now.strftime("%A, %d %b")

        sql_section = ""
        if sql_plan:
            sql_section = f"\n🗄  SQL Questions:\n{plan_lines(sql_plan)}"
        drill_section = f"\n🎯 SQL Drill: {'✅ Done' if drill_done else '⏳ 0/1 (5 questions)'}"
        dsa_section   = f"\n⚔️  DSA: {'✅' if dsa_done >= DSA_TARGET else '⏳'} {dsa_done}/{DSA_TARGET} questions"

        body = (
            f"☀️ {greeting}, {NAME}!\n"
            f"📅 {date_str}\n"
            f"{sql_section}"
            f"{drill_section}"
            f"{dsa_section}\n\n"
            f"Open SuperApp and get started 🎯\n"
            f"localhost:7339"
        )

    else:
        # Reminder — only mention what's still pending
        pending_parts = []

        if not sql_done and sql_plan:
            pending = plan_lines(sql_plan, pending_only=True)
            pending_parts.append(f"🗄  SQL ({sql_qs}/{sql_total} done):\n{pending}")

        if not drill_done:
            pending_parts.append(f"🎯 SQL Drill: not done yet (5 quick questions)")

        if dsa_done < DSA_TARGET:
            left = DSA_TARGET - dsa_done
            pending_parts.append(f"⚔️  DSA: {dsa_done}/{DSA_TARGET} — {left} more needed")

        if not pending_parts:
            print("  All done — completion message will fire next cycle")
            return

        # Rotate through varied messages to avoid WhatsApp throttling
        nudge_templates = [
            f"⏰ Still waiting, {NAME}.",
            f"📌 Reminder, {NAME}.",
            f"🔔 Checking in, {NAME}.",
            f"⚡ Not done yet, {NAME}.",
            f"🎯 Keep going, {NAME}.",
            f"💪 Push through, {NAME}.",
            f"🕐 Time check, {NAME}.",
        ]
        urgency_header = nudge_templates[(send_num - 1) % len(nudge_templates)]
        body = (
            f"{urgency_header}\n\n"
            + "\n\n".join(pending_parts)
            + f"\n\nlocalhost:7339"
        )

    try:
        send_whatsapp(body)
        print(f"  Send #{send_num+1} | SQL:{sql_qs}/{sql_total} Drill:{'✓' if drill_done else '✗'} DSA:{dsa_done}/{DSA_TARGET}")
    except Exception as e:
        print(f"  ❌ WhatsApp failed: {e}")

if __name__ == "__main__":
    main()
