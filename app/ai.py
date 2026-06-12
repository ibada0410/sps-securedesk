"""AI services via any OpenAI-compatible chat completions API
(Groq by default; OpenRouter and native xAI also work - see .env).

Human-first constraints enforced here and in the calling code:
- Chat answers ONLY from the published knowledge base (articles are injected
  into the prompt; the model is instructed to refuse outside that scope).
- AI suggests classification (category/priority/risk/team) - agents override.
- AI NEVER approves access, resets accounts, or closes incidents.
Every function has a deterministic keyword fallback so the app still works
if the AI API is unreachable.
"""
import json
import os
import re

import httpx

XAI_BASE = os.environ.get("XAI_BASE_URL", "https://api.groq.com/openai/v1")
XAI_MODEL = os.environ.get("XAI_MODEL", "llama-3.3-70b-versatile")


def _api_key():
    return os.environ.get("XAI_API_KEY", "")


def _complete(messages, temperature=0.2, max_tokens=700) -> str:
    """Single non-streaming completion against Grok. Raises on any failure."""
    resp = httpx.post(
        f"{XAI_BASE}/chat/completions",
        headers={"Authorization": f"Bearer {_api_key()}", "Content-Type": "application/json"},
        json={"model": XAI_MODEL, "messages": messages,
              "temperature": temperature, "max_tokens": max_tokens},
        timeout=45,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def _extract_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.S)
    return json.loads(match.group(0)) if match else {}


HIGH_RISK_RE = re.compile(
    r"(admin|root|privileged|elevated|production|prod)\s+(access|account|rights|privileges|credentials)"
    r"|(access|permission)s?\s+to\s+(production|prod|admin)"
    r"|\b(grant|give|need|request)\b.{0,40}\b(admin|production|privileged|root)\b"
    r"|reset\s+(the\s+)?(admin|service|privileged)\s+(account|password)", re.I)
PHISH_RE = re.compile(r"phish|suspicious (email|link)|malware|ransomware|breach|compromis", re.I)


def keyword_classify(subject: str, description: str) -> dict:
    """Deterministic fallback classifier used when the AI API is unavailable."""
    text = f"{subject} {description or ''}"
    cat = "general_it"
    rules = [("cloud", r"(?i)\b(vm|azure|aws|cloud|deploy|kubernetes|server down)\b"),
             ("cybersecurity", r"(?i)\b(phish|malware|virus|breach|incident|suspicious)\b"),
             ("identity_access", r"(?i)\b(access|password|account|login|mfa|sso|permission)\b"),
             ("devops", r"(?i)\b(pipeline|ci/cd|jenkins|git|build|release)\b"),
             ("hr_internship", r"(?i)\b(intern|onboarding|timesheet|hr|badge)\b")]
    for c, pattern in rules:
        if re.search(pattern, text):
            cat = c
            break
    risk = "low"
    priority = "medium"
    if PHISH_RE.search(text):
        risk, priority, cat = "critical", "critical", "cybersecurity"
    elif HIGH_RISK_RE.search(text):
        risk, priority, cat = "high", "high", "identity_access"
    elif re.search(r"(?i)\b(down|outage|cannot work|urgent|critical)\b", text):
        priority = "high"
    return {"category": cat, "priority": priority, "risk_level": risk,
            "reasoning": "Keyword-based classification (AI unavailable or fallback)."}


def classify_ticket(subject: str, description: str) -> dict:
    """Suggest category/priority/risk for a ticket. Agent can override every field."""
    try:
        out = _complete([
            {"role": "system", "content":
                "You are the triage classifier for SPS SecureDesk, an IT helpdesk. "
                "Classify the ticket and respond with ONLY a JSON object: "
                '{"category": one of [cloud, cybersecurity, identity_access, devops, hr_internship, general_it], '
                '"priority": one of [low, medium, high, critical], '
                '"risk_level": one of [low, medium, high, critical], '
                '"reasoning": "one short sentence"}. '
                "Rules: requests for admin/privileged/production access => risk_level high or critical and category identity_access. "
                "Phishing/security incidents => category cybersecurity, priority critical. "
                "You only SUGGEST - a human agent makes final decisions."},
            {"role": "user", "content": f"Subject: {subject}\n\nDescription: {description or '(none)'}"},
        ], max_tokens=300)
        data = _extract_json(out)
        result = keyword_classify(subject, description)
        for key in ("category", "priority", "risk_level", "reasoning"):
            if data.get(key):
                result[key] = data[key]
        # Safety net: regex high-risk detection can only raise risk, never lower it
        fallback = keyword_classify(subject, description)
        order = ["low", "medium", "high", "critical"]
        if order.index(fallback["risk_level"]) > order.index(result.get("risk_level", "low")):
            result["risk_level"] = fallback["risk_level"]
        return result
    except Exception:
        return keyword_classify(subject, description)


def summarize_ticket(subject: str, events_text: str) -> str:
    try:
        return _complete([
            {"role": "system", "content": "Summarize this IT helpdesk ticket in 2-3 plain sentences for a support "
             "agent: what the user needs, current state, and any blocker. No preamble."},
            {"role": "user", "content": f"Subject: {subject}\n\nTimeline:\n{events_text[:6000]}"},
        ], max_tokens=200).strip()
    except Exception:
        return f"Ticket about: {subject}. (AI summary unavailable - showing subject only.)"


def draft_reply(subject: str, events_text: str) -> str:
    try:
        return _complete([
            {"role": "system", "content": "You draft replies for SPS IT support agents. Write a short, professional, "
             "friendly reply to the requester based on the ticket context. The agent will edit before sending. "
             "Never promise access grants or approvals - those need human security review. Sign as 'SPS SecureDesk Support'."},
            {"role": "user", "content": f"Subject: {subject}\n\nTimeline:\n{events_text[:6000]}\n\nDraft a helpful reply."},
        ], max_tokens=350).strip()
    except Exception:
        return ("Hi,\n\nThanks for reaching out to SPS SecureDesk. We are looking into your request and will update "
                "you shortly.\n\nBest regards,\nSPS SecureDesk Support")


def rank_kb(articles, message: str, limit=4):
    """Tiny keyword scorer to pick the most relevant published KB articles."""
    words = set(re.findall(r"[a-z]{3,}", message.lower()))
    scored = []
    for art in articles:
        body = f"{art.title} {art.content}".lower()
        score = sum(2 if w in art.title.lower() else 1 for w in words if w in body)
        if score:
            scored.append((score, art))
    scored.sort(key=lambda x: -x[0])
    return [a for _, a in scored[:limit]] or list(articles)[:2]


def chat_answer(message: str, history: list, articles) -> dict:
    """KB-grounded chat answer. Returns {reply, citations, escalate, high_risk}."""
    high_risk = bool(HIGH_RISK_RE.search(message)) or bool(PHISH_RE.search(message))
    relevant = rank_kb(articles, message)
    kb_block = "\n\n".join(f"### {a.title}\n{a.content}" for a in relevant) or "(knowledge base is empty)"
    sys_prompt = (
        "You are the SPS SecureDesk AI Assistant, a self-service helper for SPS employees and interns. "
        "STRICT RULES:\n"
        "1. Answer ONLY using the knowledge base articles below. Never use outside knowledge or the internet.\n"
        "2. If the KB does not cover the question, say you don't have that information and recommend creating a support ticket.\n"
        "3. You can NEVER grant access, approve requests, reset privileged accounts, or close security incidents - "
        "those always require a human. If asked, explain that and recommend a ticket (it will need human approval).\n"
        "4. Keep answers short and clear (under 150 words).\n"
        "5. End your reply with a line 'SOURCES: <article titles separated by |>' listing only articles you actually used, "
        "or 'SOURCES: none'.\n"
        "6. If the user should open a ticket, end with the exact token [ESCALATE] after the SOURCES line.\n\n"
        f"KNOWLEDGE BASE:\n{kb_block}")
    msgs = [{"role": "system", "content": sys_prompt}]
    for h in history[-8:]:
        msgs.append({"role": h["role"], "content": h["content"]})
    msgs.append({"role": "user", "content": message})
    try:
        raw = _complete(msgs, temperature=0.3, max_tokens=500)
    except Exception:
        # AI offline fallback: serve the best-matching approved KB article directly
        if high_risk:
            return {"reply": "This request needs human review - I can never grant access or approve "
                             "requests. Please create a ticket so the security team can decide.",
                    "citations": [], "escalate": True, "high_risk": True}
        best = rank_kb(articles, message, limit=1)
        if best:
            art = best[0]
            return {"reply": f"(AI assistant is offline - showing the closest knowledge base article)\n\n"
                             f"{art.title}\n\n{art.content[:900]}",
                    "citations": [art.title], "escalate": True, "high_risk": False}
        return {"reply": "I'm temporarily unavailable and found no matching article. "
                         "Would you like to submit a ticket instead?",
                "citations": [], "escalate": True, "high_risk": high_risk}
    escalate = "[ESCALATE]" in raw or high_risk
    raw = raw.replace("[ESCALATE]", "").strip()
    citations = []
    match = re.search(r"\**sources?\**\s*:\s*(.+)$", raw, re.M | re.I)
    if match:
        names = [s.strip() for s in match.group(1).split("|")]
        citations = [n for n in names if n.lower() not in ("none", "")]
        raw = raw[:match.start()].strip()
    if re.search(r"(?i)(create|open|submit).{0,20}ticket|don't have (that|this) information|recommend.{0,30}ticket", raw):
        escalate = True
    return {"reply": raw, "citations": citations, "escalate": escalate, "high_risk": high_risk}


def escalation_summary(transcript: list) -> str:
    text = "\n".join(f"{m['role']}: {m['content']}" for m in transcript[-12:])
    try:
        return _complete([
            {"role": "system", "content": "Summarize this helpdesk chat into a 2-4 sentence ticket description "
             "written from the user's perspective, stating what they need. No preamble."},
            {"role": "user", "content": text[:6000]},
        ], max_tokens=200).strip()
    except Exception:
        user_msgs = [m["content"] for m in transcript if m["role"] == "user"]
        return "Escalated from AI chat. User request: " + " | ".join(user_msgs[-3:])
