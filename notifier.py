"""
notifier.py — Updated May 20, 2026
5 daily goals: DSA + SQL + Python + CS Core + DevOps reading
"""
import os, requests
from datetime import datetime, timezone, timedelta, date as date_cls

SUPABASE_URL  = os.environ["SUPABASE_URL"]
SUPABASE_KEY  = os.environ["SUPABASE_KEY"]
TWILIO_SID    = os.environ["TWILIO_SID"]
TWILIO_TOKEN  = os.environ["TWILIO_TOKEN"]
TWILIO_FROM   = os.environ["TWILIO_FROM"]
TWILIO_TO     = os.environ["TWILIO_TO"]
NAME          = os.environ.get("USER_NAME", "Dev")
DSA_TARGET    = int(os.environ.get("DSA_DAILY_TARGET", "3"))
SQL_TARGET    = int(os.environ.get("SQL_DAILY_TARGET", "3"))
PY_TARGET     = int(os.environ.get("PY_DAILY_TARGET", "3"))
CS_TARGET     = int(os.environ.get("CS_DAILY_TARGET", "10"))

IST         = timezone(timedelta(hours=5, minutes=30))
QUIET_START = 0.0
QUIET_END   = 6.5

# ── DSA Daily Rotation ────────────────────────────────────────────────────
DSA_ROTATION = {
    "2026-05-20": ("Trees",  ["Same Tree", "Balanced Binary Tree", "LCA of Binary Tree"]),
    "2026-05-21": ("Trees",  ["Level Order Traversal", "Right Side View", "Diameter of BT"]),
    "2026-05-22": ("Graphs", ["Number of Islands", "Clone Graph", "Max Area of Island"]),
    "2026-05-23": ("Graphs", ["Pacific Atlantic", "Surrounded Regions", "Rotting Oranges"]),
    "2026-05-24": ("Graphs", ["Course Schedule I", "Course Schedule II", "Connected Components"]),
    "2026-05-25": ("DP",     ["Climbing Stairs", "House Robber", "House Robber II"]),
    "2026-05-26": ("DP",     ["Longest Palindromic Substring", "Coin Change", "Word Break"]),
    "2026-05-27": ("DP",     ["LIS", "Partition Equal Subset", "Decode Ways"]),
    "2026-05-28": ("Trees",  ["Validate BST", "Construct from Preorder", "Max Path Sum"]),
    "2026-05-29": ("Graphs", ["Word Search", "Graph Valid Tree", "Alien Dictionary"]),
    "2026-05-30": ("DP",     ["Min Cost Climbing", "Jump Game", "Unique Paths"]),
}

# ── SQL 14-day plan ───────────────────────────────────────────────────────
SQL_DAYS = {
    1: "SELECT & WHERE", 2: "GROUP BY & HAVING", 3: "JOINs",
    4: "Subqueries", 5: "Window Functions", 6: "CTEs",
    7: "Date Functions", 8: "String Functions", 9: "CASE WHEN",
    10: "NULL Handling", 11: "Advanced Joins", 12: "Analytical Patterns",
    13: "Performance & Indexing", 14: "Mixed Hard Problems",
}

# ── Python 14-day plan ────────────────────────────────────────────────────
PY_DAYS = {
    1: "Lists & Loops", 2: "Strings", 3: "Dicts & Sets",
    4: "Comprehensions & Lambda", 5: "Functions & Closures", 6: "OOP Basics",
    7: "Pandas Basics", 8: "Pandas GroupBy", 9: "Pandas Merge",
    10: "Pandas Time Series", 11: "NumPy", 12: "Regex & String Parse",
    13: "File I/O & JSON", 14: "Mixed DS Problems",
}

# ── DevOps Daily Topics ───────────────────────────────────────────────────
DEVOPS_TOPICS = {
    "2026-05-20": "Docker Fundamentals — Image vs container, Dockerfile, docker run/build/ps",
    "2026-05-21": "Docker Internals — namespaces, cgroups, overlay filesystem",
    "2026-05-22": "Docker Compose — multi-container, service deps, env vars",
    "2026-05-23": "Kubernetes Basics — Pod, Node, Cluster, kubectl, Deployment",
    "2026-05-24": "Kubernetes Advanced — Services, HPA, liveness/readiness probes",
    "2026-05-25": "CI/CD — GitHub Actions vs Jenkins, pipeline stages, deploy strategies",
    "2026-05-26": "Linux Essentials — df -h, ps aux, kill -9, chmod, grep/awk/sed",
    "2026-05-27": "Networking — TCP handshake, DNS walkthrough, what happens at google.com",
    "2026-05-28": "System Design — Load balancers, scaling, CAP theorem, SQL vs NoSQL",
    "2026-05-29": "Microservices — vs monolith, API gateway, circuit breaker, trade-offs",
    "2026-05-30": "Cloud Concepts — IaaS/PaaS/SaaS, S3/EC2/RDS, auto-scaling",
}

# CS Core schedule
CS_SCHEDULE = {
    "2026-05-05": ("OS", "OS — Processes & Threads", "Focus: fork/exec, mutex vs semaphore, race conditions"),
    "2026-05-06": ("OS", "OS — Memory Management", "Focus: paging, TLB, LRU, virtual memory"),
    "2026-05-07": ("OS", "OS — Scheduling & Deadlocks", "Focus: Banker's algo, FCFS/RR, starvation"),
    "2026-05-08": ("OS", "OS — File Systems & I/O", "Focus: inodes, journaling, DMA, file descriptors"),
    "2026-05-09": ("CN", "CN — OSI & TCP/IP", "Focus: 7 layers, PDUs, ARP, encapsulation"),
    "2026-05-10": ("CN", "CN — TCP vs UDP", "Focus: 3-way handshake, flow control, when to use UDP"),
    "2026-05-11": ("CN", "CN — HTTP & DNS", "Focus: HTTP methods, status codes, DNS resolution"),
    "2026-05-12": ("CN", "CN — Routing & Subnetting", "Focus: CIDR, NAT, BGP vs OSPF, default gateway"),
    "2026-05-20": ("CS", "OS Revision", "Focus: revise all OS topics — pick weak MCQs"),
    "2026-05-21": ("CS", "CN Revision", "Focus: revise all CN topics — pick weak MCQs"),
    "2026-05-22": ("CS", "C Programming Revision", "Focus: pointers, structs, bitwise ops"),
}

def supa(table, params=None):
    hdrs = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    r = requests.get(f"{SUPABASE_URL}/rest/v1/{table}", headers=hdrs, params=params, timeout=10)
    return r.json() if r.ok else []

def supa_patch(table, match_params, data):
    hdrs = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json", "Prefer": "return=minimal"}
    requests.patch(f"{SUPABASE_URL}/rest/v1/{table}", headers=hdrs, params=match_params, json=data, timeout=10)

def send_whatsapp(body):
    from twilio.rest import Client
    Client(TWILIO_SID, TWILIO_TOKEN).messages.create(body=body, from_=TWILIO_FROM, to=TWILIO_TO)
    print(f"  ✅ Sent: {body[:80].replace(chr(10),' ')}...")

def get_sql_day(today_str):
    """Calculate which SQL day we're on (started May 20)"""
    start = date_cls(2026, 5, 20)
    today = date_cls.fromisoformat(today_str)
    diff = (today - start).days + 1
    return max(1, min(14, diff))

def get_py_day(today_str):
    """Calculate which Python day we're on (started May 20)"""
    start = date_cls(2026, 5, 20)
    today = date_cls.fromisoformat(today_str)
    diff = (today - start).days + 1
    return max(1, min(14, diff))

def main():
    now  = datetime.now(IST)
    h    = now.hour + now.minute / 60
    print(f"[{now.strftime('%Y-%m-%d %H:%M IST')}] Notifier running")

    if QUIET_START <= h < QUIET_END:
        print("  Quiet hours — skipping")
        return

    today = now.date().isoformat()
    send_num = max(0, int((h - QUIET_END) / 0.5))

    # ── Fetch status ─────────────────────────────────────────────────────
    status_rows = supa("daily_status", {"date": f"eq.{today}", "select": "*"})
    status      = status_rows[0] if status_rows else {}

    dsa_done   = int(status.get("dsa_done", 0))
    cs_done    = int(status.get("cs_done", 0))
    drill_done = bool(status.get("drill_done", False))
    sql_iq_done = int(status.get("sql_iq_done", 0))   # new: InterviewQuery SQL
    py_done    = int(status.get("py_done", 0))         # new: Python questions
    devops_read = bool(status.get("devops_read", False)) # new: DevOps topic read
    completion_sent = bool(status.get("completion_msg_sent", False))

    # ── Today's context ───────────────────────────────────────────────────
    dsa_today = DSA_ROTATION.get(today)
    devops_today = DEVOPS_TOPICS.get(today)
    cs_today  = CS_SCHEDULE.get(today)
    sql_day   = get_sql_day(today)
    py_day    = get_py_day(today)
    sql_topic = SQL_DAYS.get(sql_day, "SQL Practice")
    py_topic  = PY_DAYS.get(py_day, "Python Practice")

    # ── Check all goals ───────────────────────────────────────────────────
    dsa_ok    = dsa_done >= DSA_TARGET
    sql_ok    = sql_iq_done >= SQL_TARGET
    py_ok     = py_done >= PY_TARGET
    cs_ok     = not cs_today or cs_done >= CS_TARGET
    devops_ok = devops_read or not devops_today

    all_complete = dsa_ok and sql_ok and py_ok and cs_ok and devops_ok

    if all_complete and completion_sent:
        print("  All done — completion already sent ✅")
        return

    # ── Completion message ────────────────────────────────────────────────
    if all_complete and not completion_sent:
        msg = f"🔥 DONE for today, {NAME}!\n\n"
        msg += f"⚔️  DSA: {dsa_done}/{DSA_TARGET} problems ✅\n"
        msg += f"🗄  SQL Day {sql_day}: {sql_iq_done}/{SQL_TARGET} done ✅\n"
        msg += f"🐍 Python Day {py_day}: {py_done}/{PY_TARGET} done ✅\n"
        if cs_today: msg += f"📚 CS Core: {cs_done}/{CS_TARGET} MCQs ✅\n"
        if devops_today: msg += f"🐳 DevOps reading: done ✅\n"
        msg += "\nAnother seed planted 🌱 Keep going."
        send_whatsapp(msg)
        supa_patch("daily_status", {"date": f"eq.{today}"},
                   {"goals_met": True, "completion_msg_sent": True})
        return

    # ── Reminder message ──────────────────────────────────────────────────
    nudges = []
    if send_num == 0:
        nudges.append(f"☀️ Good morning, {NAME}! {now.strftime('%a %d %b')}\n")
        # Morning briefing — show today's full plan
        if dsa_today:
            pattern, probs = dsa_today
            nudges.append(f"⚔️  DSA ({pattern}) — 3 problems:")
            for p in probs:
                nudges.append(f"   • {p}")
        nudges.append(f"\n🗄  SQL Day {sql_day} — {sql_topic}")
        nudges.append(f"   → 3 questions on interviewquery.com")
        nudges.append(f"\n🐍 Python Day {py_day} — {py_topic}")
        nudges.append(f"   → 3 questions on interviewquery.com")
        if cs_today:
            _, cs_topic, cs_hint = cs_today
            nudges.append(f"\n📚 CS Core — {cs_topic}")
            nudges.append(f"   {cs_hint}")
        if devops_today:
            nudges.append(f"\n🐳 DevOps — {devops_today}")
        nudges.append(f"\nlocalhost:7339")
    else:
        # Subsequent reminders — show remaining goals only
        remaining = []
        if not dsa_ok:   remaining.append(f"⚔️  DSA: {dsa_done}/{DSA_TARGET} done")
        if not sql_ok:   remaining.append(f"🗄  SQL Day {sql_day}: {sql_iq_done}/{SQL_TARGET} done")
        if not py_ok:    remaining.append(f"🐍 Python Day {py_day}: {py_done}/{PY_TARGET} done")
        if not cs_ok:    remaining.append(f"📚 CS Core: {cs_done}/{CS_TARGET} MCQs")
        if not devops_ok: remaining.append(f"🐳 DevOps: not read yet")

        nudge_msgs = [
            f"⏰ Still pending, {NAME}.",
            f"📌 Reminder, {NAME}.",
            f"🔔 Checking in, {NAME}.",
            f"⚡ Not done yet, {NAME}.",
            f"💪 Push through, {NAME}.",
            f"🎯 Keep going, {NAME}.",
        ]
        nudges.append(nudge_msgs[(send_num - 1) % len(nudge_msgs)])
        nudges.extend(remaining)
        nudges.append(f"\nlocalhost:7339")

    try:
        send_whatsapp("\n".join(nudges))
        print(f"  Send #{send_num+1} | DSA:{dsa_done}/{DSA_TARGET} SQL:{sql_iq_done}/{SQL_TARGET} PY:{py_done}/{PY_TARGET} CS:{cs_done}")
    except Exception as e:
        print(f"  ❌ WhatsApp failed: {e}")

if __name__ == "__main__":
    main()
