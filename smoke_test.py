"""End-to-end smoke test for SPS SecureDesk AI (run against a live server)."""
import time
import httpx

BASE = "http://localhost:8010/api"
ok = fail = 0

def check(name, cond, extra=""):
    global ok, fail
    ok += cond; fail += (not cond)
    print(f"{'PASS' if cond else 'FAIL'}  {name} {extra}")

def login(email, pw):
    r = httpx.post(f"{BASE}/auth/login", json={"email": email, "password": pw})
    r.raise_for_status()
    return {"Authorization": "Bearer " + r.json()["token"]}

admin = login("admin@spsnet.com", "Admin@123")
agent = login("agent@spsnet.com", "Agent@123")
sec = login("security@spsnet.com", "Security@123")
emp = login("employee@spsnet.com", "Employee@123")
intern = login("intern@spsnet.com", "Intern@123")
check("login all roles", True)

bad = httpx.post(f"{BASE}/auth/login", json={"email": "admin@spsnet.com", "password": "wrong"})
check("bad password rejected", bad.status_code == 401)

# --- RBAC ---
check("intern blocked from audit", httpx.get(f"{BASE}/audit", headers=intern).status_code == 403)
check("intern blocked from approvals", httpx.get(f"{BASE}/approvals", headers=intern).status_code == 403)

# --- Channel 1: web form ---
r = httpx.post(f"{BASE}/tickets", headers=emp, json={
    "subject": "Cloud VM is down in production cluster",
    "description": "Our Azure VM sps-app-02 stopped responding after deployment. Logs attached later.",
    "category": "cloud", "source": "portal_form"})
form_ticket = r.json()["ticket_id"]
check("form ticket created", r.status_code == 201, form_ticket)

# --- Channel 2: email (simulator -> same pipeline as IMAP) ---
r = httpx.post(f"{BASE}/email/inbound", headers=admin, json={
    "from_email": "employee@spsnet.com", "subject": "My laptop will not boot",
    "body": "Laptop stopped booting this morning, demo at 3pm. Asset SPS-LT-0421."})
email_ticket = r.json()["ticket_id"]
check("email ticket created", r.json()["created_new"], email_ticket)

r = httpx.post(f"{BASE}/email/inbound", headers=admin, json={
    "from_email": "employee@spsnet.com", "subject": f"Re: [{email_ticket}] My laptop will not boot",
    "body": "Adding info: the power LED blinks twice."})
check("email reply threads to same ticket", r.json()["ticket_id"] == email_ticket and not r.json()["created_new"])

# --- Channel 3: AI chat (real Grok call) ---
r = httpx.post(f"{BASE}/chat/message", headers=intern,
               json={"message": "How do I connect to the SPS VPN?"}, timeout=60)
chat = r.json()
check("chat KB answer", r.status_code == 200 and len(chat["reply"]) > 20,
      f"citations={chat['citations']}")

r = httpx.post(f"{BASE}/chat/message", headers=intern,
               json={"session_id": chat["session_id"],
                     "message": "I need admin access to the production environment"}, timeout=60)
chat2 = r.json()
check("high-risk chat triggers escalation", chat2["escalate"] and chat2["high_risk"])

r = httpx.post(f"{BASE}/chat/escalate-prefill", headers=intern,
               json={"session_id": chat["session_id"], "message": ""}, timeout=60)
pre = r.json()
r = httpx.post(f"{BASE}/tickets", headers=intern, json={
    "subject": "Request: admin access to production", "description": pre["description"],
    "source": "chat", "chat_session_id": chat["session_id"]})
chat_ticket = r.json()["ticket_id"]
check("chat escalation creates ticket", r.status_code == 201, chat_ticket)

print("  ...waiting for async AI classification...")
time.sleep(12)

t = httpx.get(f"{BASE}/tickets/{chat_ticket}", headers=agent).json()
check("high-risk -> waiting_approval", t["status"] == "waiting_approval",
      f"risk={t['risk_level']}")
check("approval record exists", t["approval"] is not None and t["approval"]["status"] == "pending")

# resolve must be blocked while waiting approval
r = httpx.patch(f"{BASE}/tickets/{chat_ticket}", headers=agent,
                json={"status": "resolved", "resolution_note": "trying to bypass"})
check("agent blocked from resolving while waiting approval", r.status_code == 409)

# --- agent workflow on email ticket ---
r = httpx.patch(f"{BASE}/tickets/{form_ticket}", headers=agent,
                json={"assignee_id": httpx.get(f"{BASE}/meta", headers=agent).json()["agents"][0]["id"]})
check("agent assignment", r.status_code == 200)
r = httpx.post(f"{BASE}/tickets/{email_ticket}/reply", headers=agent,
               json={"content": "Please hold power 10s and retry; we will swap the unit if needed.",
                     "send_email": True})
check("agent email reply", r.status_code == 200)
r = httpx.post(f"{BASE}/tickets/{email_ticket}/reply", headers=agent,
               json={"content": "Internal: likely battery controller, order spare.", "is_internal": True})
check("internal note", r.status_code == 200)

# mixed scenario per spec: user emailed first, now adds info via the portal
r = httpx.post(f"{BASE}/tickets/{email_ticket}/reply", headers=emp,
               json={"content": "Uploading the blink-code photo via the portal now."})
check("requester portal comment on email ticket", r.status_code == 200)

t = httpx.get(f"{BASE}/tickets/{email_ticket}", headers=emp).json()
check("requester cannot see internal note",
      not any(e["is_internal"] for e in t["events"]))
check("one unified timeline (email+portal events)",
      {"email", "portal"} <= {e["channel"] for e in t["events"] if e["channel"]})

r = httpx.patch(f"{BASE}/tickets/{email_ticket}", headers=agent, json={"status": "resolved"})
check("resolve without note rejected", r.status_code == 422)
r = httpx.patch(f"{BASE}/tickets/{email_ticket}", headers=agent,
                json={"status": "resolved", "resolution_note": "Hardware swapped, user confirmed boot."})
check("resolve with note", r.status_code == 200)

# --- approval decisions (human-only) ---
approvals = httpx.get(f"{BASE}/approvals?status=pending", headers=sec).json()
ap = next(a for a in approvals if a["ticket_id"] == chat_ticket)
r = httpx.patch(f"{BASE}/approvals/{ap['approval_id']}", headers=agent,
                json={"decision": "approved"})
check("agent cannot approve", r.status_code == 403)
r = httpx.patch(f"{BASE}/approvals/{ap['approval_id']}", headers=sec,
                json={"decision": "rejected", "reason": ""})
check("reject without reason rejected", r.status_code == 422)
r = httpx.patch(f"{BASE}/approvals/{ap['approval_id']}", headers=sec,
                json={"decision": "approved", "reason": "Time-boxed access approved for deployment window"})
check("security admin approves", r.status_code == 200)
r = httpx.patch(f"{BASE}/approvals/{ap['approval_id']}", headers=sec,
                json={"decision": "rejected", "reason": "changed my mind"})
check("decision immutable", r.status_code == 409)

# --- secret detection ---
httpx.post(f"{BASE}/tickets", headers=emp, json={
    "subject": "Leaked key check", "description": "Found this in repo: AKIA1234567890ABCDEF",
    "source": "portal_form"})
audit = httpx.get(f"{BASE}/audit?event_type=secret_detected", headers=sec).json()
check("secret detection audited", audit["total"] >= 1)

# --- audit channel tags ---
for ch in ("email", "chat", "portal"):
    a = httpx.get(f"{BASE}/audit?channel={ch}", headers=admin).json()
    check(f"audit log has channel={ch}", a["total"] >= 1, f"({a['total']} events)")

# --- outbox: ACKs + replies + approval mails ---
outbox = httpx.get(f"{BASE}/email/outbox", headers=admin).json()
subj = " | ".join(o["subject"] for o in outbox[:6])
check("outbound emails recorded (ACK/reply/approval)", len(outbox) >= 5, f"latest: {subj[:120]}")

# --- reports ---
rep = httpx.get(f"{BASE}/reports/summary?days=30", headers=login("manager@spsnet.com", "Manager@123")).json()
check("manager report", rep["total_tickets"] >= 3 and "by_source" in rep,
      f"sources={rep['by_source']} high_risk={rep['high_risk_count']}")
csv_r = httpx.get(f"{BASE}/reports/summary?days=30&export=true", headers=sec)
check("report CSV export", csv_r.status_code == 200 and "metric" in csv_r.text)

print(f"\n=== {ok} passed, {fail} failed ===")
raise SystemExit(1 if fail else 0)
