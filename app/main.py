"""SPS SecureDesk AI - FastAPI application.

Three intake channels (email, web form, AI chat) converge into ONE ticket
service (`create_ticket_service`). Humans (agents / security admins /
managers) own resolution and approvals; AI assists with answers, triage,
summaries and drafts only.

Run:  python -m uvicorn app.main:app --port 8000
Docs: http://localhost:8000/docs
"""
import csv
import io
import json
import os
import re
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Load .env before importing modules that read os.environ at import time
ROOT = Path(__file__).resolve().parent.parent
env_file = ROOT / ".env"
if env_file.exists():
    for line in env_file.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.split("#")[0].strip())

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr
from sqlalchemy import func

from . import ai, emailer
from .models import (CATEGORIES, PRIORITIES, ROLES, SOURCES, STATUSES, Approval, Attachment,
                     AuditLog, ChatSession, EmailThread, KBArticle, SessionLocal, SLAPolicy,
                     Team, Ticket, TicketEvent, User, init_db, next_ticket_id, utcnow)
from .security import (AGENT_ROLES, APPROVER_ROLES, create_scoped_token, create_token,
                       decode_scoped_token, get_current_user, get_db, hash_password,
                       require_role, sanitize_html, scan_input, verify_password)

app = FastAPI(title="SPS SecureDesk AI", version="1.0",
              description="AI-assisted enterprise helpdesk - email, web form and AI chat "
                          "intake into one unified ticket system. AI assists; humans decide.")

UPLOAD_DIR = ROOT / "uploads"
ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".gif", ".pdf", ".txt", ".csv", ".log", ".doc", ".docx", ".xls", ".xlsx", ".zip"}
MAX_UPLOAD = 10 * 1024 * 1024


# ---------------------------------------------------------------- helpers
def log_audit(db, event_type, actor=None, ticket_id=None, channel="system", ip=None, payload=None):
    db.add(AuditLog(event_type=event_type,
                    actor_id=actor.user_id if actor else None,
                    actor_email=actor.email if actor else None,
                    actor_role=actor.role if actor else None,
                    ticket_id=ticket_id, channel=channel, ip_address=ip,
                    payload=json.dumps(payload or {}, default=str)))


def add_event(db, ticket_id, event_type, actor=None, actor_email=None, content=None,
              is_internal=False, channel="system", ip=None, meta=None):
    ev = TicketEvent(ticket_id=ticket_id, event_type=event_type,
                     actor_id=actor.user_id if actor else None,
                     actor_email=actor.email if actor else (actor_email or None),
                     content=content, is_internal=is_internal, channel=channel,
                     ip_address=ip, meta=json.dumps(meta or {}, default=str))
    db.add(ev)
    return ev


def run_security_scan(db, text, actor, ticket_id, channel, ip):
    for event_type, label in scan_input(text or ""):
        log_audit(db, event_type, actor=actor, ticket_id=ticket_id, channel=channel, ip=ip,
                  payload={"pattern": label, "note": "flagged by security input scanner"})


def match_sla(db, category, priority):
    pol = (db.query(SLAPolicy).filter(SLAPolicy.priority == priority)
           .filter((SLAPolicy.category == category) | (SLAPolicy.category.is_(None)))
           .order_by(SLAPolicy.category.desc()).first())
    return pol


def ticket_to_dict(t: Ticket, db, include_internal=False):
    assignee = db.get(User, t.assignee_id) if t.assignee_id else None
    team = db.get(Team, t.team_id) if t.team_id else None
    approval = db.query(Approval).filter(Approval.ticket_id == t.ticket_id).first()
    return {
        "ticket_id": t.ticket_id, "source": t.source, "status": t.status, "subject": t.subject,
        "description": t.description, "category": t.category, "priority": t.priority,
        "risk_level": t.risk_level, "requester_email": t.requester_email,
        "assignee": {"id": assignee.user_id, "name": assignee.full_name} if assignee else None,
        "team": team.name if team else None, "ai_summary": t.ai_summary,
        "sla_due_at": t.sla_due_at.isoformat() if t.sla_due_at else None,
        "sla_breached": t.sla_breached, "resolution_note": t.resolution_note,
        "chat_session_id": t.chat_session_id,
        "created_at": t.created_at.isoformat(), "updated_at": t.updated_at.isoformat(),
        "approval": {"approval_id": approval.approval_id, "status": approval.status,
                     "reason": approval.reason, "risk_factors": approval.risk_factors,
                     "decided_at": approval.decided_at.isoformat() if approval.decided_at else None}
        if approval else None,
    }


def notify_approvers(db, ticket: Ticket):
    approvers = db.query(User).filter(User.role.in_(APPROVER_ROLES), User.is_active.is_(True)).all()
    for ap in approvers:
        emailer.send_email(db, ap.email, f"Approval required: {ticket.subject}",
                           [f"A high-risk request <b>{ticket.ticket_id}</b> is waiting for human approval.",
                            f"Subject: {ticket.subject}", f"Risk level: {ticket.risk_level.upper()}",
                            "AI flagged this request. Per SPS policy, AI never approves - your decision is required.",
                            "Review it in the Security workspace."],
                           ticket_id=ticket.ticket_id, title="Approval Required")


def trigger_approval_workflow(db, ticket: Ticket, risk_factors: str, requested_by: str):
    """High-risk -> Waiting Approval + approval record + approver emails. Never AI-decided."""
    if db.query(Approval).filter(Approval.ticket_id == ticket.ticket_id).first():
        return
    ticket.status = "waiting_approval"
    db.add(Approval(ticket_id=ticket.ticket_id, requested_by=requested_by, risk_factors=risk_factors))
    add_event(db, ticket.ticket_id, "approval_requested", actor_email="system",
              content=f"High-risk request detected ({ticket.risk_level}). Status set to Waiting Approval. "
                      f"Human security review required - AI cannot approve.", channel="system")
    log_audit(db, "approval_requested", ticket_id=ticket.ticket_id, channel="system",
              payload={"risk_level": ticket.risk_level, "risk_factors": risk_factors})
    notify_approvers(db, ticket)
    emailer.send_email(db, ticket.requester_email, f"Re: {ticket.subject}",
                       [f"Your request <b>{ticket.ticket_id}</b> requires security approval.",
                        "It has been placed in <b>Waiting Approval</b> and routed to the SPS security team.",
                        "You will be notified by email once a decision is made."],
                       ticket_id=ticket.ticket_id, title="Approval Pending")


def classify_async(ticket_id: str):
    """Background AI classification (suggestion only - agents override any field)."""
    def work():
        with SessionLocal() as db:
            t = db.get(Ticket, ticket_id)
            if not t:
                return
            result = ai.classify_ticket(t.subject, t.description or "")
            t.category = t.category or result["category"]
            if result["category"] and not t.ai_classified_at:
                t.category = result["category"]
            t.priority = result["priority"]
            t.risk_level = result["risk_level"]
            t.ai_classified_at = utcnow()
            team = db.query(Team).filter(Team.default_category == t.category).first()
            if team and not t.team_id:
                t.team_id = team.team_id
            pol = match_sla(db, t.category, t.priority)
            if pol:
                t.sla_due_at = t.created_at + timedelta(minutes=pol.resolution_minutes)
            add_event(db, ticket_id, "ai_classification", actor_email="ai",
                      content=f"AI suggested: category={result['category']}, priority={result['priority']}, "
                              f"risk={result['risk_level']}. {result.get('reasoning','')} (Agent may override.)",
                      channel="system", meta=result)
            log_audit(db, "ai_classification", ticket_id=ticket_id, channel="system", payload=result)
            if result["risk_level"] in ("high", "critical") and t.status in ("open", "in_progress"):
                trigger_approval_workflow(db, t, result.get("reasoning", "AI risk assessment"), "ai_classifier")
            db.commit()
    threading.Thread(target=work, daemon=True).start()


def create_ticket_service(db, *, source, subject, description, requester_email,
                          requester_user=None, category=None, priority=None,
                          chat_session_id=None, channel="portal", ip=None) -> Ticket:
    """THE single intake pipeline - email, form and chat all land here."""
    subject = sanitize_html(subject.strip())[:500] or "(no subject)"
    description = sanitize_html(description or "")
    ticket = Ticket(ticket_id=next_ticket_id(db), source=source, subject=subject,
                    description=description, category=category,
                    priority=priority or "medium",
                    requester_id=requester_user.user_id if requester_user else None,
                    requester_email=requester_email.lower(), chat_session_id=chat_session_id)
    pol = match_sla(db, category, ticket.priority)
    if pol:
        ticket.sla_due_at = utcnow() + timedelta(minutes=pol.resolution_minutes)
    db.add(ticket)
    db.flush()
    add_event(db, ticket.ticket_id, "ticket_created", actor=requester_user,
              actor_email=requester_email, channel=channel,
              content=f"Ticket created via {source.replace('_', ' ')}. {subject}", ip=ip)
    log_audit(db, "ticket_created", actor=requester_user, ticket_id=ticket.ticket_id,
              channel=channel, ip=ip, payload={"source": source, "subject": subject})
    run_security_scan(db, f"{subject}\n{description}", requester_user, ticket.ticket_id, channel, ip)
    emailer.send_email(db, requester_email, f"We received your request: {subject}",
                       [f"Thanks for contacting SPS SecureDesk. Your ticket <b>{ticket.ticket_id}</b> has been created.",
                        f"Subject: {subject}",
                        "Track progress, add comments and upload files in the portal. "
                        "Reply to this email to add information to the same ticket."],
                       ticket_id=ticket.ticket_id, title="Request Received")
    db.commit()
    classify_async(ticket.ticket_id)
    return ticket


def ingest_inbound_email(db, from_address, subject, body, message_id="", in_reply_to=""):
    """Inbound email pipeline: thread to existing ticket or create a new one."""
    body = sanitize_html(body or "")
    existing_id = emailer.match_ticket_id(subject, in_reply_to, db)
    message_id = message_id or f"<dev-{utcnow().timestamp()}@spsnet.com>"
    user = db.query(User).filter(User.email == from_address.lower()).first()
    if existing_id and db.get(Ticket, existing_id):
        ticket = db.get(Ticket, existing_id)
        add_event(db, ticket.ticket_id, "requester_reply", actor=user, actor_email=from_address,
                  content=body, channel="email")
        db.add(EmailThread(ticket_id=ticket.ticket_id, message_id=message_id, in_reply_to=in_reply_to or None,
                           subject=subject, from_address=from_address,
                           to_addresses=emailer.helpdesk_addr(), direction="inbound", body_text=body))
        log_audit(db, "email_received", ticket_id=ticket.ticket_id, channel="email",
                  payload={"from": from_address, "threaded": True})
        run_security_scan(db, body, user, ticket.ticket_id, "email", None)
        if ticket.status in ("resolved", "closed"):
            ticket.status = "open"
        db.commit()
        return ticket, False
    ticket = create_ticket_service(db, source="email", subject=re.sub(r"^\s*(re|fwd?):\s*", "", subject, flags=re.I),
                                   description=body, requester_email=from_address,
                                   requester_user=user, channel="email")
    db.add(EmailThread(ticket_id=ticket.ticket_id, message_id=message_id, subject=subject,
                       from_address=from_address, to_addresses=emailer.helpdesk_addr(),
                       direction="inbound", body_text=body))
    db.commit()
    return ticket, True


# ---------------------------------------------------------------- schemas
class LoginIn(BaseModel):
    email: EmailStr
    password: str

class SignupIn(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    role: str = "employee"  # self-signup limited to intern|employee
    department: str | None = None

class ForgotIn(BaseModel):
    email: EmailStr

class ResetIn(BaseModel):
    token: str
    new_password: str

class ProfileIn(BaseModel):
    full_name: str | None = None
    department: str | None = None
    phone: str | None = None
    current_password: str | None = None
    new_password: str | None = None


def validate_password(pw: str):
    if len(pw) < 8 or not re.search(r"[A-Z]", pw) or not re.search(r"\d", pw):
        raise HTTPException(422, "Password must be 8+ characters with an uppercase letter and a number")

class TicketIn(BaseModel):
    subject: str
    description: str = ""
    category: str | None = None
    priority: str | None = None
    contact_email: EmailStr | None = None
    source: str = "portal_form"
    chat_session_id: str | None = None

class ReplyIn(BaseModel):
    content: str
    is_internal: bool = False
    send_email: bool = False

class PatchTicketIn(BaseModel):
    status: str | None = None
    priority: str | None = None
    category: str | None = None
    risk_level: str | None = None
    assignee_id: str | None = None
    ai_summary: str | None = None
    resolution_note: str | None = None

class ChatIn(BaseModel):
    session_id: str | None = None
    message: str

class EscalateIn(BaseModel):
    session_id: str
    subject: str
    description: str

class DecisionIn(BaseModel):
    decision: str  # approved | rejected
    reason: str = ""

class UserIn(BaseModel):
    email: EmailStr
    full_name: str
    role: str
    password: str
    department: str | None = None

class KBIn(BaseModel):
    title: str
    content: str
    category: str
    status: str = "draft"

class InboundEmailIn(BaseModel):
    from_email: EmailStr
    subject: str
    body: str


# ---------------------------------------------------------------- auth
@app.post("/api/auth/login", tags=["auth"])
def login(data: LoginIn, request: Request, db=Depends(get_db)):
    user = db.query(User).filter(User.email == data.email.lower()).first()
    if not user or not user.is_active or not verify_password(data.password, user.hashed_password):
        log_audit(db, "login_failed", channel="portal", ip=request.client.host,
                  payload={"email": data.email})
        db.commit()
        raise HTTPException(status_code=401, detail="Invalid email or password")
    user.last_login_at = utcnow()
    log_audit(db, "user_login", actor=user, channel="portal", ip=request.client.host, payload={})
    db.commit()
    return {"token": create_token(user),
            "user": {"id": user.user_id, "email": user.email, "name": user.full_name, "role": user.role}}


@app.get("/api/me", tags=["auth"])
def me(user: User = Depends(get_current_user)):
    return {"id": user.user_id, "email": user.email, "name": user.full_name, "role": user.role}


@app.post("/api/auth/signup", status_code=201, tags=["auth"])
def signup(data: SignupIn, request: Request, db=Depends(get_db)):
    """Public self-registration for SPS staff and interns (requester roles only)."""
    if data.role not in ("intern", "employee"):
        raise HTTPException(422, "Self sign-up is limited to intern or employee accounts")
    if db.query(User).filter(User.email == data.email.lower()).first():
        raise HTTPException(409, "An account with this email already exists - try signing in")
    validate_password(data.password)
    user = User(email=data.email.lower(), full_name=sanitize_html(data.full_name.strip())[:200],
                role=data.role, hashed_password=hash_password(data.password),
                department=data.department)
    db.add(user)
    log_audit(db, "user_signup", actor=user, channel="portal", ip=request.client.host,
              payload={"email": data.email, "role": data.role})
    db.flush()
    emailer.send_email(db, user.email, "Welcome to SPS SecureDesk",
                       [f"Hi {user.full_name}, your SecureDesk account is ready.",
                        "You can now submit requests by web form, email helpdesk@spsnet.com, "
                        "or ask the AI assistant in the portal."],
                       title="Account Created")
    db.commit()
    return {"ok": True, "message": "Account created - you can sign in now"}


@app.post("/api/auth/forgot-password", tags=["auth"])
def forgot_password(data: ForgotIn, request: Request, db=Depends(get_db)):
    """Always returns the same response (no account enumeration). Sends a 1h reset link."""
    user = db.query(User).filter(User.email == data.email.lower(), User.is_active.is_(True)).first()
    if user:
        token = create_scoped_token(user.user_id, "password_reset", 3600)
        base = os.environ.get("APP_BASE_URL", "http://localhost:8000")
        emailer.send_email(db, user.email, "Reset your SecureDesk password",
                           [f"Hi {user.full_name}, we received a request to reset your password.",
                            f"<a href='{base}/#/reset?token={token}'>Click here to choose a new password</a> "
                            f"(link valid for 1 hour).",
                            f"Or open {base}/#/reset and paste this code:",
                            f"<code style='word-break:break-all'>{token}</code>",
                            "If you didn't request this, you can ignore this email."],
                           title="Password Reset")
        log_audit(db, "password_reset_requested", actor=user, channel="portal",
                  ip=request.client.host, payload={})
        db.commit()
    return {"ok": True, "message": "If an account exists for that email, a reset link has been sent"}


@app.post("/api/auth/reset-password", tags=["auth"])
def reset_password(data: ResetIn, request: Request, db=Depends(get_db)):
    user_id = decode_scoped_token(data.token, "password_reset")
    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(400, "Account not found or deactivated")
    validate_password(data.new_password)
    user.hashed_password = hash_password(data.new_password)
    log_audit(db, "password_reset_completed", actor=user, channel="portal",
              ip=request.client.host, payload={})
    db.commit()
    return {"ok": True, "message": "Password reset successfully. Please sign in."}


# ---- Microsoft SSO (TRD: integration point behind env flag; local auth is the V1 default) ----
def _sso_enabled():
    return bool(os.environ.get("AZURE_CLIENT_ID", "").strip())


@app.get("/api/auth/sso", tags=["auth"])
def sso_status():
    if not _sso_enabled():
        return {"enabled": False,
                "message": "Microsoft sign-in is not configured. An administrator must set "
                           "AZURE_CLIENT_ID, AZURE_CLIENT_SECRET and AZURE_TENANT_ID in .env"}
    tenant = os.environ.get("AZURE_TENANT_ID", "common")
    base = os.environ.get("APP_BASE_URL", "http://localhost:8000")
    auth_url = (f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize"
                f"?client_id={os.environ['AZURE_CLIENT_ID']}&response_type=code"
                f"&redirect_uri={base}/api/auth/sso/callback&scope=openid%20profile%20email%20User.Read")
    return {"enabled": True, "auth_url": auth_url}


@app.get("/api/auth/sso/callback", tags=["auth"])
def sso_callback(code: str, request: Request, db=Depends(get_db)):
    """OAuth2 code exchange -> Microsoft Graph /me -> local account -> session token."""
    import httpx as _httpx
    from fastapi.responses import RedirectResponse
    if not _sso_enabled():
        raise HTTPException(503, "SSO not configured")
    tenant = os.environ.get("AZURE_TENANT_ID", "common")
    base = os.environ.get("APP_BASE_URL", "http://localhost:8000")
    tok = _httpx.post(f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token", data={
        "client_id": os.environ["AZURE_CLIENT_ID"],
        "client_secret": os.environ.get("AZURE_CLIENT_SECRET", ""),
        "code": code, "grant_type": "authorization_code",
        "redirect_uri": f"{base}/api/auth/sso/callback"}, timeout=30)
    tok.raise_for_status()
    graph = _httpx.get("https://graph.microsoft.com/v1.0/me",
                       headers={"Authorization": "Bearer " + tok.json()["access_token"]}, timeout=30)
    graph.raise_for_status()
    info = graph.json()
    email = (info.get("mail") or info.get("userPrincipalName") or "").lower()
    if not email:
        raise HTTPException(400, "Microsoft account has no email")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(email=email, full_name=info.get("displayName") or email,
                    role="employee", hashed_password=hash_password(os.urandom(16).hex() + "Aa1!"))
        db.add(user)
        db.flush()
    if not user.is_active:
        raise HTTPException(403, "Account is deactivated")
    user.last_login_at = utcnow()
    log_audit(db, "user_login", actor=user, channel="portal", ip=request.client.host,
              payload={"method": "microsoft_sso"})
    db.commit()
    return RedirectResponse(url=f"{base}/#/sso?token={create_token(user)}")


# ---- profile (every role) ----
@app.get("/api/profile", tags=["auth"])
def get_profile(user: User = Depends(get_current_user)):
    return {"email": user.email, "full_name": user.full_name, "role": user.role,
            "department": user.department, "phone": user.phone,
            "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None}


@app.patch("/api/profile", tags=["auth"])
def update_profile(data: ProfileIn, request: Request, db=Depends(get_db),
                   user: User = Depends(get_current_user)):
    changed = []
    if data.full_name and data.full_name.strip():
        user.full_name = sanitize_html(data.full_name.strip())[:200]
        changed.append("full_name")
    if data.department is not None:
        user.department = sanitize_html(data.department.strip())[:100] or None
        changed.append("department")
    if data.phone is not None:
        user.phone = re.sub(r"[^0-9+ ()-]", "", data.phone)[:30] or None
        changed.append("phone")
    if data.new_password:
        if not data.current_password or not verify_password(data.current_password, user.hashed_password):
            raise HTTPException(403, "Current password is incorrect")
        validate_password(data.new_password)
        user.hashed_password = hash_password(data.new_password)
        changed.append("password")
    log_audit(db, "profile_updated", actor=user, channel="portal", ip=request.client.host,
              payload={"fields": changed})
    db.commit()
    return {"ok": True, "changed": changed,
            "user": {"id": user.user_id, "email": user.email, "name": user.full_name, "role": user.role}}


# ---------------------------------------------------------------- tickets
@app.post("/api/tickets", status_code=201, tags=["tickets"])
def create_ticket(data: TicketIn, request: Request, db=Depends(get_db),
                  user: User = Depends(get_current_user)):
    if data.source not in ("portal_form", "chat"):
        raise HTTPException(400, "source must be portal_form or chat (email tickets arrive via the mail pipeline)")
    if data.category and data.category not in CATEGORIES:
        raise HTTPException(422, "invalid category")
    if data.priority and data.priority not in PRIORITIES:
        raise HTTPException(422, "invalid priority")
    channel = "chat" if data.source == "chat" else "portal"
    ticket = create_ticket_service(db, source=data.source, subject=data.subject,
                                   description=data.description,
                                   requester_email=(data.contact_email or user.email),
                                   requester_user=user, category=data.category,
                                   priority=data.priority, chat_session_id=data.chat_session_id,
                                   channel=channel, ip=request.client.host)
    if data.chat_session_id:
        session = db.get(ChatSession, data.chat_session_id)
        if session:
            session.ticket_id = ticket.ticket_id
            session.escalated_at = utcnow()
            add_event(db, ticket.ticket_id, "escalation", actor=user,
                      content="Escalated from AI chat session. Full transcript linked to this ticket.",
                      channel="chat")
            db.commit()
    return ticket_to_dict(ticket, db)


@app.get("/api/tickets", tags=["tickets"])
def list_tickets(status: str = "", source: str = "", category: str = "", q: str = "",
                 queue: str = "", page: int = 1, db=Depends(get_db),
                 user: User = Depends(get_current_user)):
    query = db.query(Ticket)
    if user.role in ("intern", "employee"):
        query = query.filter((Ticket.requester_id == user.user_id) |
                             (Ticket.requester_email == user.email))
    elif user.role == "manager" and queue == "high_risk":
        query = query.filter(Ticket.risk_level.in_(["high", "critical"]))
    if queue == "mine" and user.role in AGENT_ROLES:
        query = query.filter(Ticket.assignee_id == user.user_id)
    if queue == "unassigned":
        query = query.filter(Ticket.assignee_id.is_(None), Ticket.status.notin_(["resolved", "closed"]))
    if queue == "high_risk":
        query = query.filter(Ticket.risk_level.in_(["high", "critical"]))
    if status:
        query = query.filter(Ticket.status == status)
    if source:
        query = query.filter(Ticket.source == source)
    if category:
        query = query.filter(Ticket.category == category)
    if q:
        like = f"%{q}%"
        query = query.filter((Ticket.subject.like(like)) | (Ticket.ticket_id.like(like)))
    total = query.count()
    rows = query.order_by(Ticket.created_at.desc()).offset((page - 1) * 50).limit(50).all()
    return {"total": total, "page": page, "tickets": [ticket_to_dict(t, db) for t in rows]}


@app.get("/api/tickets/{ticket_id}", tags=["tickets"])
def get_ticket(ticket_id: str, db=Depends(get_db), user: User = Depends(get_current_user)):
    t = db.get(Ticket, ticket_id)
    if not t:
        raise HTTPException(404, "Ticket not found")
    is_requester = t.requester_id == user.user_id or t.requester_email == user.email
    if user.role in ("intern", "employee") and not is_requester:
        raise HTTPException(403, "You can only view your own tickets")
    include_internal = user.role in AGENT_ROLES
    evq = db.query(TicketEvent).filter(TicketEvent.ticket_id == ticket_id)
    if not include_internal:
        evq = evq.filter(TicketEvent.is_internal.is_(False))
    events = [{"event_id": e.event_id, "event_type": e.event_type, "actor_email": e.actor_email,
               "content": e.content, "is_internal": e.is_internal, "channel": e.channel,
               "created_at": e.created_at.isoformat()} for e in evq.order_by(TicketEvent.created_at).all()]
    atts = [{"attachment_id": a.attachment_id, "file_name": a.file_name, "size_bytes": a.size_bytes,
             "uploader_email": a.uploader_email}
            for a in db.query(Attachment).filter(Attachment.ticket_id == ticket_id).all()]
    out = ticket_to_dict(t, db, include_internal)
    out["events"] = events
    out["attachments"] = atts
    if include_internal and t.chat_session_id:
        session = db.get(ChatSession, t.chat_session_id)
        if session:
            out["chat_transcript"] = json.loads(session.transcript)
    return out


@app.patch("/api/tickets/{ticket_id}", tags=["tickets"])
def patch_ticket(ticket_id: str, data: PatchTicketIn, request: Request, db=Depends(get_db),
                 user: User = Depends(require_role(*AGENT_ROLES))):
    t = db.get(Ticket, ticket_id)
    if not t:
        raise HTTPException(404, "Ticket not found")
    changes = {}
    if data.status:
        if data.status not in STATUSES:
            raise HTTPException(422, "invalid status")
        if data.status in ("resolved", "closed") and not (data.resolution_note or t.resolution_note):
            raise HTTPException(422, "A resolution note is required to resolve or close a ticket")
        if t.status == "waiting_approval" and data.status in ("resolved", "closed", "approved"):
            approval = db.query(Approval).filter(Approval.ticket_id == ticket_id).first()
            if approval and approval.status == "pending":
                raise HTTPException(409, "Blocked: this ticket is waiting for human approval. "
                                         "A security admin or manager must decide first.")
        changes["status"] = (t.status, data.status)
        t.status = data.status
        if data.status == "resolved":
            t.resolved_at = utcnow()
            emailer.send_email(db, t.requester_email, f"Re: {t.subject}",
                               [f"Good news - your ticket <b>{t.ticket_id}</b> has been <b>resolved</b>.",
                                f"Resolution: {data.resolution_note or t.resolution_note}",
                                "Reply to this email if the issue is not fixed and the ticket will reopen."],
                               ticket_id=t.ticket_id, title="Ticket Resolved")
    for field in ("priority", "category", "risk_level", "ai_summary", "resolution_note"):
        value = getattr(data, field)
        if value is not None:
            changes[field] = (getattr(t, field), value)
            setattr(t, field, value)
    if data.assignee_id is not None:
        assignee = db.get(User, data.assignee_id) if data.assignee_id else None
        changes["assignee"] = (t.assignee_id, data.assignee_id or None)
        t.assignee_id = data.assignee_id or None
        if assignee:
            if t.status == "open":
                t.status = "in_progress"
            emailer.send_email(db, assignee.email, f"Assigned to you: {t.subject}",
                               [f"Ticket <b>{t.ticket_id}</b> has been assigned to you.",
                                f"Priority: {t.priority} · Source: {t.source}"],
                               ticket_id=t.ticket_id, title="Ticket Assigned")
    desc = ", ".join(f"{k}: {v[0]} → {v[1]}" for k, v in changes.items())
    add_event(db, ticket_id, "status_change", actor=user, content=f"Updated by {user.full_name}: {desc}",
              channel="portal", ip=request.client.host, meta=changes)
    log_audit(db, "ticket_updated", actor=user, ticket_id=ticket_id, channel="portal",
              ip=request.client.host, payload=changes)
    db.commit()
    return ticket_to_dict(t, db)


@app.post("/api/tickets/{ticket_id}/reply", tags=["tickets"])
def reply(ticket_id: str, data: ReplyIn, request: Request, db=Depends(get_db),
          user: User = Depends(get_current_user)):
    t = db.get(Ticket, ticket_id)
    if not t:
        raise HTTPException(404, "Ticket not found")
    is_requester = t.requester_id == user.user_id or t.requester_email == user.email
    if user.role in ("intern", "employee"):
        if not is_requester:
            raise HTTPException(403, "Not your ticket")
        data.is_internal = data.send_email = False
        event_type = "requester_reply"
    else:
        if user.role not in AGENT_ROLES:
            raise HTTPException(403, "Managers have read-only access to tickets")
        event_type = "internal_note" if data.is_internal else "agent_reply"
    content = sanitize_html(data.content)
    run_security_scan(db, content, user, ticket_id, "portal", request.client.host)
    channel = "email" if data.send_email else "portal"
    add_event(db, ticket_id, event_type, actor=user, content=content,
              is_internal=data.is_internal, channel=channel, ip=request.client.host)
    log_audit(db, event_type, actor=user, ticket_id=ticket_id, channel=channel,
              ip=request.client.host, payload={"internal": data.is_internal, "emailed": data.send_email})
    if data.send_email and not data.is_internal:
        emailer.send_email(db, t.requester_email, f"Re: {t.subject}",
                           [content.replace("\n", "<br>"),
                            f"<i>— {user.full_name}, SPS SecureDesk Support</i>"],
                           ticket_id=t.ticket_id, title="New reply on your ticket")
        add_event(db, ticket_id, "email_sent", actor=user,
                  content=f"Reply emailed to {t.requester_email}", channel="email")
    if event_type == "agent_reply" and t.status == "open":
        t.status = "in_progress"
    db.commit()
    return {"ok": True}


# ---------------------------------------------------------------- attachments
@app.post("/api/tickets/{ticket_id}/attachments", status_code=201, tags=["tickets"])
def upload_attachment(ticket_id: str, file: UploadFile = File(...), db=Depends(get_db),
                      user: User = Depends(get_current_user)):
    t = db.get(Ticket, ticket_id)
    if not t:
        raise HTTPException(404, "Ticket not found")
    ext = Path(file.filename or "file").suffix.lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(422, f"File type {ext or '(none)'} not allowed")
    blob = file.file.read()
    if len(blob) > MAX_UPLOAD:
        raise HTTPException(422, "File exceeds 10MB limit")
    folder = UPLOAD_DIR / ticket_id
    folder.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", file.filename or "file")
    path = folder / f"{int(time.time())}_{safe}"
    path.write_bytes(blob)
    att = Attachment(ticket_id=ticket_id, uploader_email=user.email, file_name=file.filename,
                     stored_path=str(path), size_bytes=len(blob),
                     mime_type=file.content_type or "application/octet-stream")
    db.add(att)
    add_event(db, ticket_id, "attachment_added", actor=user,
              content=f"File uploaded: {file.filename} ({len(blob)//1024} KB)", channel="portal")
    log_audit(db, "attachment_added", actor=user, ticket_id=ticket_id, channel="portal",
              payload={"file": file.filename, "bytes": len(blob)})
    db.commit()
    return {"attachment_id": att.attachment_id, "file_name": att.file_name}


@app.get("/api/attachments/{attachment_id}", tags=["tickets"])
def download_attachment(attachment_id: str, db=Depends(get_db), user: User = Depends(get_current_user)):
    att = db.get(Attachment, attachment_id)
    if not att:
        raise HTTPException(404, "Attachment not found")
    return FileResponse(att.stored_path, filename=att.file_name, media_type=att.mime_type)


# ---------------------------------------------------------------- AI assist (agent tools)
@app.post("/api/tickets/{ticket_id}/classify", tags=["ai"])
def reclassify(ticket_id: str, db=Depends(get_db), user: User = Depends(require_role(*AGENT_ROLES))):
    if not db.get(Ticket, ticket_id):
        raise HTTPException(404, "Ticket not found")
    classify_async(ticket_id)
    return {"ok": True, "note": "Classification running - refresh in a few seconds"}


def _events_text(db, ticket_id):
    events = (db.query(TicketEvent).filter(TicketEvent.ticket_id == ticket_id)
              .order_by(TicketEvent.created_at).all())
    return "\n".join(f"[{e.event_type}/{e.actor_email or 'system'}] {e.content or ''}" for e in events)


@app.get("/api/tickets/{ticket_id}/summary", tags=["ai"])
def ai_summary(ticket_id: str, db=Depends(get_db), user: User = Depends(require_role(*AGENT_ROLES))):
    t = db.get(Ticket, ticket_id)
    if not t:
        raise HTTPException(404, "Ticket not found")
    t.ai_summary = ai.summarize_ticket(t.subject, _events_text(db, ticket_id))
    db.commit()
    return {"summary": t.ai_summary}


@app.post("/api/tickets/{ticket_id}/draft-reply", tags=["ai"])
def ai_draft(ticket_id: str, db=Depends(get_db), user: User = Depends(require_role(*AGENT_ROLES))):
    t = db.get(Ticket, ticket_id)
    if not t:
        raise HTTPException(404, "Ticket not found")
    return {"draft": ai.draft_reply(t.subject, _events_text(db, ticket_id)),
            "note": "AI draft - review and edit before sending"}


# ---------------------------------------------------------------- AI chat channel
@app.post("/api/chat/message", tags=["chat"])
def chat_message(data: ChatIn, request: Request, db=Depends(get_db),
                 user: User = Depends(get_current_user)):
    session = db.get(ChatSession, data.session_id) if data.session_id else None
    if not session:
        session = ChatSession(user_id=user.user_id)
        db.add(session)
        db.flush()
    transcript = json.loads(session.transcript)
    run_security_scan(db, data.message, user, session.ticket_id, "chat", request.client.host)
    articles = db.query(KBArticle).filter(KBArticle.status == "published").all()
    result = ai.chat_answer(sanitize_html(data.message), transcript, articles)
    transcript.append({"role": "user", "content": data.message, "at": utcnow().isoformat()})
    transcript.append({"role": "assistant", "content": result["reply"],
                       "citations": result["citations"], "at": utcnow().isoformat()})
    session.transcript = json.dumps(transcript)
    cited = set(json.loads(session.kb_articles_cited or "[]")) | set(result["citations"])
    session.kb_articles_cited = json.dumps(sorted(cited))
    for art in articles:
        if art.title in result["citations"]:
            art.citation_count += 1
    log_audit(db, "chat_message", actor=user, channel="chat", ip=request.client.host,
              payload={"session": session.session_id, "escalate_suggested": result["escalate"],
                       "high_risk": result["high_risk"]})
    db.commit()
    return {"session_id": session.session_id, "reply": result["reply"],
            "citations": result["citations"], "escalate": result["escalate"],
            "high_risk": result["high_risk"]}


@app.post("/api/chat/escalate-prefill", tags=["chat"])
def chat_prefill(data: ChatIn, db=Depends(get_db), user: User = Depends(get_current_user)):
    """Build a suggested subject/description from the chat transcript (user reviews before submit)."""
    session = db.get(ChatSession, data.session_id or "")
    if not session:
        raise HTTPException(404, "Chat session not found")
    transcript = json.loads(session.transcript)
    summary = ai.escalation_summary(transcript)
    session.escalation_summary = summary
    first_user = next((m["content"] for m in transcript if m["role"] == "user"), "Support request")
    db.commit()
    return {"subject": first_user[:120], "description": summary}


# ---------------------------------------------------------------- approvals
@app.get("/api/approvals", tags=["approvals"])
def list_approvals(status: str = "pending", db=Depends(get_db),
                   user: User = Depends(require_role(*APPROVER_ROLES, "administrator"))):
    query = db.query(Approval)
    if status:
        query = query.filter(Approval.status == status)
    out = []
    for ap in query.order_by(Approval.requested_at.desc()).all():
        t = db.get(Ticket, ap.ticket_id)
        out.append({"approval_id": ap.approval_id, "ticket_id": ap.ticket_id, "status": ap.status,
                    "risk_factors": ap.risk_factors, "reason": ap.reason,
                    "requested_at": ap.requested_at.isoformat(),
                    "decided_at": ap.decided_at.isoformat() if ap.decided_at else None,
                    "subject": t.subject if t else "", "risk_level": t.risk_level if t else "",
                    "requester_email": t.requester_email if t else "", "source": t.source if t else ""})
    return out


@app.patch("/api/approvals/{approval_id}", tags=["approvals"])
def decide_approval(approval_id: str, data: DecisionIn, request: Request, db=Depends(get_db),
                    user: User = Depends(require_role(*APPROVER_ROLES))):
    """HUMAN-ONLY decision endpoint. Immutable once decided. Rejection requires a reason."""
    ap = db.get(Approval, approval_id)
    if not ap:
        raise HTTPException(404, "Approval not found")
    if ap.status != "pending":
        raise HTTPException(409, f"This request has already been {ap.status}")
    if data.decision not in ("approved", "rejected"):
        raise HTTPException(422, "decision must be approved or rejected")
    if data.decision == "rejected" and not data.reason.strip():
        raise HTTPException(422, "A reason is required when rejecting a request")
    ap.status = data.decision
    ap.reason = data.reason.strip() or None
    ap.approver_id = user.user_id
    ap.decided_at = utcnow()
    t = db.get(Ticket, ap.ticket_id)
    t.status = "approved" if data.decision == "approved" else "rejected"
    add_event(db, ap.ticket_id, "approval_decided", actor=user,
              content=f"Request {data.decision.upper()} by {user.full_name} ({user.role})."
                      + (f" Reason: {ap.reason}" if ap.reason else ""), channel="portal",
              ip=request.client.host)
    log_audit(db, f"approval_{data.decision}", actor=user, ticket_id=ap.ticket_id, channel="portal",
              ip=request.client.host, payload={"reason": ap.reason, "decision": data.decision})
    emailer.send_email(db, t.requester_email, f"Re: {t.subject}",
                       [f"Your request <b>{t.ticket_id}</b> has been <b>{data.decision.upper()}</b> "
                        f"by the SPS security team."]
                       + ([f"Reason: {ap.reason}"] if ap.reason else []),
                       ticket_id=t.ticket_id, title=f"Request {data.decision.title()}")
    db.commit()
    return {"ok": True, "status": ap.status}


# ---------------------------------------------------------------- knowledge base
@app.get("/api/kb", tags=["kb"])
def list_kb(db=Depends(get_db), user: User = Depends(get_current_user)):
    query = db.query(KBArticle)
    if user.role != "administrator":
        query = query.filter(KBArticle.status == "published")
    return [{"article_id": a.article_id, "title": a.title, "category": a.category,
             "status": a.status, "version": a.version, "citation_count": a.citation_count,
             "content": a.content, "updated_at": a.updated_at.isoformat()}
            for a in query.order_by(KBArticle.updated_at.desc()).all()]


@app.post("/api/kb", status_code=201, tags=["kb"])
def create_kb(data: KBIn, db=Depends(get_db), user: User = Depends(require_role("administrator"))):
    art = KBArticle(title=data.title, content=data.content, category=data.category,
                    status=data.status, author_id=user.user_id,
                    published_at=utcnow() if data.status == "published" else None)
    db.add(art)
    log_audit(db, "kb_created", actor=user, channel="admin", payload={"title": data.title})
    db.commit()
    return {"article_id": art.article_id}


@app.put("/api/kb/{article_id}", tags=["kb"])
def update_kb(article_id: str, data: KBIn, db=Depends(get_db),
              user: User = Depends(require_role("administrator"))):
    art = db.get(KBArticle, article_id)
    if not art:
        raise HTTPException(404, "Article not found")
    art.title, art.content, art.category = data.title, data.content, data.category
    if data.status != art.status:
        art.status = data.status
        if data.status == "published":
            art.published_at = utcnow()
        log_audit(db, "kb_published" if data.status == "published" else "kb_status_changed",
                  actor=user, channel="admin", payload={"title": art.title, "status": data.status})
    art.version += 1
    db.commit()
    return {"ok": True, "version": art.version}


# ---------------------------------------------------------------- email center (admin)
@app.post("/api/email/inbound", tags=["email"])
def simulate_inbound(data: InboundEmailIn, db=Depends(get_db),
                     user: User = Depends(require_role("administrator"))):
    """Dev simulator: feeds the same ingestion pipeline as the IMAP poller."""
    ticket, created = ingest_inbound_email(db, data.from_email, data.subject, data.body)
    return {"ticket_id": ticket.ticket_id, "created_new": created,
            "note": "New ticket created + ACK emailed" if created else "Threaded into existing ticket"}


@app.get("/api/email/outbox", tags=["email"])
def outbox(db=Depends(get_db), user: User = Depends(require_role("administrator", "security_admin"))):
    rows = (db.query(EmailThread).order_by(EmailThread.sent_at.desc()).limit(100).all())
    return [{"direction": r.direction, "subject": r.subject, "from": r.from_address,
             "to": r.to_addresses, "body": r.body_text, "sent_at": r.sent_at.isoformat(),
             "ticket_id": r.ticket_id} for r in rows]


# ---------------------------------------------------------------- audit log
@app.get("/api/audit", tags=["audit"])
def audit(channel: str = "", event_type: str = "", page: int = 1, export: bool = False,
          db=Depends(get_db), user: User = Depends(require_role("administrator", "security_admin"))):
    query = db.query(AuditLog)
    if channel:
        query = query.filter(AuditLog.channel == channel)
    if event_type:
        query = query.filter(AuditLog.event_type == event_type)
    query = query.order_by(AuditLog.created_at.desc())
    if export:
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["created_at", "event_type", "actor_email", "actor_role", "ticket_id",
                         "channel", "ip_address", "payload"])
        for r in query.limit(5000).all():
            writer.writerow([r.created_at.isoformat(), r.event_type, r.actor_email, r.actor_role,
                             r.ticket_id, r.channel, r.ip_address, r.payload])
        buf.seek(0)
        return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                                 headers={"Content-Disposition": "attachment; filename=audit_log.csv"})
    total = query.count()
    rows = query.offset((page - 1) * 50).limit(50).all()
    return {"total": total, "rows": [
        {"created_at": r.created_at.isoformat(), "event_type": r.event_type,
         "actor_email": r.actor_email, "actor_role": r.actor_role, "ticket_id": r.ticket_id,
         "channel": r.channel, "ip_address": r.ip_address, "payload": json.loads(r.payload)}
        for r in rows]}


# ---------------------------------------------------------------- reports
@app.get("/api/reports/summary", tags=["reports"])
def reports(days: int = 30, export: bool = False, db=Depends(get_db),
            user: User = Depends(require_role("manager", "security_admin", "administrator"))):
    since = utcnow() - timedelta(days=days)
    base = db.query(Ticket).filter(Ticket.created_at >= since)
    tickets = base.all()
    def count_by(attr):
        out = {}
        for t in tickets:
            key = getattr(t, attr) or "unset"
            out[key] = out.get(key, 0) + 1
        return out
    resolved = [t for t in tickets if t.resolved_at]
    within = [t for t in resolved if not t.sla_due_at or t.resolved_at <= t.sla_due_at]
    high_risk = [t for t in tickets if t.risk_level in ("high", "critical")]
    approvals = db.query(Approval).filter(Approval.requested_at >= since).all()
    agent_stats = {}
    for t in resolved:
        if t.assignee_id:
            agent = db.get(User, t.assignee_id)
            name = agent.full_name if agent else "?"
            agent_stats[name] = agent_stats.get(name, 0) + 1
    summary = {
        "period_days": days, "total_tickets": len(tickets),
        "by_source": count_by("source"), "by_category": count_by("category"),
        "by_status": count_by("status"), "by_priority": count_by("priority"),
        "resolved_count": len(resolved),
        "sla_compliance_pct": round(100 * len(within) / len(resolved), 1) if resolved else 100.0,
        "sla_breached_open": sum(1 for t in tickets if t.sla_breached and t.status not in ("resolved", "closed")),
        "high_risk_count": len(high_risk),
        "high_risk_tickets": [{"ticket_id": t.ticket_id, "subject": t.subject, "status": t.status,
                               "risk_level": t.risk_level, "source": t.source} for t in high_risk],
        "approvals": {"total": len(approvals),
                      "approved": sum(1 for a in approvals if a.status == "approved"),
                      "rejected": sum(1 for a in approvals if a.status == "rejected"),
                      "pending": sum(1 for a in approvals if a.status == "pending")},
        "agent_resolved": agent_stats,
    }
    if export:
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["metric", "value"])
        for key in ("period_days", "total_tickets", "resolved_count", "sla_compliance_pct", "high_risk_count"):
            writer.writerow([key, summary[key]])
        for section in ("by_source", "by_category", "by_status", "by_priority", "agent_resolved"):
            for k, v in summary[section].items():
                writer.writerow([f"{section}.{k}", v])
        for k, v in summary["approvals"].items():
            writer.writerow([f"approvals.{k}", v])
        buf.seek(0)
        return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                                 headers={"Content-Disposition": "attachment; filename=sps_report.csv"})
    return summary


# ---------------------------------------------------------------- admin: users / agents / SLA
@app.get("/api/users", tags=["admin"])
def list_users(db=Depends(get_db), user: User = Depends(require_role("administrator", *AGENT_ROLES, "manager"))):
    rows = db.query(User).order_by(User.created_at).all()
    return [{"id": u.user_id, "email": u.email, "name": u.full_name, "role": u.role,
             "department": u.department, "is_active": u.is_active,
             "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None} for u in rows]


@app.post("/api/users", status_code=201, tags=["admin"])
def create_user(data: UserIn, db=Depends(get_db), user: User = Depends(require_role("administrator"))):
    if data.role not in ROLES:
        raise HTTPException(422, "invalid role")
    if db.query(User).filter(User.email == data.email.lower()).first():
        raise HTTPException(409, "Email already registered")
    if len(data.password) < 8 or not re.search(r"[A-Z]", data.password) or not re.search(r"\d", data.password):
        raise HTTPException(422, "Password must be 8+ chars with an uppercase letter and a number")
    u = User(email=data.email.lower(), full_name=data.full_name, role=data.role,
             hashed_password=hash_password(data.password), department=data.department)
    db.add(u)
    log_audit(db, "user_created", actor=user, channel="admin",
              payload={"email": data.email, "role": data.role})
    db.commit()
    return {"id": u.user_id}


@app.patch("/api/users/{user_id}", tags=["admin"])
def patch_user(user_id: str, body: dict, db=Depends(get_db),
               user: User = Depends(require_role("administrator"))):
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(404, "User not found")
    if "is_active" in body:
        if target.user_id == user.user_id and not body["is_active"]:
            raise HTTPException(409, "Admins cannot deactivate their own account")
        target.is_active = bool(body["is_active"])
    if body.get("role"):
        if body["role"] not in ROLES:
            raise HTTPException(422, "invalid role")
        log_audit(db, "user_role_changed", actor=user, channel="admin",
                  payload={"user": target.email, "from": target.role, "to": body["role"]})
        target.role = body["role"]
    db.commit()
    return {"ok": True}


@app.get("/api/sla-policies", tags=["admin"])
def list_sla(db=Depends(get_db), user: User = Depends(get_current_user)):
    return [{"policy_id": p.policy_id, "category": p.category or "all", "priority": p.priority,
             "response_minutes": p.response_minutes, "resolution_minutes": p.resolution_minutes,
             "warning_minutes": p.warning_minutes} for p in db.query(SLAPolicy).all()]


@app.get("/api/meta", tags=["admin"])
def meta(db=Depends(get_db), user: User = Depends(get_current_user)):
    agents = db.query(User).filter(User.role.in_(AGENT_ROLES), User.is_active.is_(True)).all()
    return {"categories": CATEGORIES, "priorities": PRIORITIES, "statuses": STATUSES,
            "sources": SOURCES, "roles": ROLES,
            "agents": [{"id": a.user_id, "name": a.full_name, "role": a.role} for a in agents],
            "ai_model": ai.XAI_MODEL,
            "smtp_mode": "smtp" if os.environ.get("SMTP_HOST", "").strip() else "dev_outbox",
            "imap_mode": "imap" if os.environ.get("IMAP_HOST", "").strip() else "simulator"}


@app.get("/api/health", tags=["admin"])
def health():
    return {"status": "ok", "service": "SPS SecureDesk AI", "time": utcnow().isoformat()}


# ---------------------------------------------------------------- background: SLA monitor
def sla_monitor():
    while True:
        try:
            with SessionLocal() as db:
                now = utcnow()
                open_tickets = db.query(Ticket).filter(
                    Ticket.status.notin_(["resolved", "closed", "rejected"]),
                    Ticket.sla_due_at.isnot(None), Ticket.sla_breached.is_(False)).all()
                for t in open_tickets:
                    due = t.sla_due_at if t.sla_due_at.tzinfo else t.sla_due_at.replace(tzinfo=timezone.utc)
                    if due < now:
                        t.sla_breached = True
                        add_event(db, t.ticket_id, "sla_breach", actor_email="system",
                                  content=f"SLA breached - resolution was due {due.isoformat()}.",
                                  channel="system")
                        log_audit(db, "sla_breach", ticket_id=t.ticket_id, channel="system",
                                  payload={"due": due.isoformat()})
                db.commit()
        except Exception as exc:
            print(f"[sla] monitor error: {exc}")
        time.sleep(60)


@app.on_event("startup")
def startup():
    init_db()
    UPLOAD_DIR.mkdir(exist_ok=True)
    threading.Thread(target=sla_monitor, daemon=True, name="sla-monitor").start()
    emailer.start_imap_poller(ingest_inbound_email)
    print("SPS SecureDesk AI ready - open http://localhost:8000")


# Frontend (single-page app) - mounted last so /api keeps priority
app.mount("/", StaticFiles(directory=str(ROOT / "static"), html=True), name="static")
