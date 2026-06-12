"""SPS SecureDesk AI - database models, engine and seed data (SQLAlchemy 2.0).

Source-agnostic ticket model: email, portal_form and chat all create rows in
the same `tickets` table, distinguished by `source`. `ticket_events` is the
unified timeline; `audit_log` is the write-once compliance log.
"""
import json
import os
import uuid
from datetime import datetime, timezone

from sqlalchemy import (Boolean, Column, DateTime, ForeignKey, Integer,
                        String, Text, create_engine, event)
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///securedesk.db")
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
Base = declarative_base()


def uid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


ROLES = ["intern", "employee", "support_agent", "security_admin", "manager", "administrator"]
CATEGORIES = ["cloud", "cybersecurity", "identity_access", "devops", "hr_internship", "general_it"]
PRIORITIES = ["low", "medium", "high", "critical"]
RISKS = ["low", "medium", "high", "critical"]
STATUSES = ["open", "in_progress", "waiting_approval", "approved", "rejected", "escalated", "resolved", "closed"]
SOURCES = ["email", "portal_form", "chat"]


class User(Base):
    __tablename__ = "users"
    user_id = Column(String, primary_key=True, default=uid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(200), nullable=False)
    role = Column(String(50), nullable=False, index=True)
    department = Column(String(100))
    phone = Column(String(30))
    team_id = Column(String, ForeignKey("teams.team_id"))
    is_active = Column(Boolean, nullable=False, default=True)
    last_login_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)


class Team(Base):
    __tablename__ = "teams"
    team_id = Column(String, primary_key=True, default=uid)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    default_category = Column(String(50))


class Ticket(Base):
    __tablename__ = "tickets"
    ticket_id = Column(String(20), primary_key=True)          # SPS-2026-001
    source = Column(String(20), nullable=False, index=True)   # email|portal_form|chat
    status = Column(String(30), nullable=False, default="open", index=True)
    subject = Column(String(500), nullable=False)
    description = Column(Text)
    category = Column(String(50), index=True)
    priority = Column(String(20), nullable=False, default="medium", index=True)
    risk_level = Column(String(20), nullable=False, default="low")
    requester_id = Column(String, ForeignKey("users.user_id"))
    requester_email = Column(String(255), nullable=False, index=True)
    assignee_id = Column(String, ForeignKey("users.user_id"), index=True)
    team_id = Column(String, ForeignKey("teams.team_id"))
    ai_summary = Column(Text)
    ai_classified_at = Column(DateTime(timezone=True))
    sla_due_at = Column(DateTime(timezone=True))
    sla_breached = Column(Boolean, nullable=False, default=False)
    resolution_note = Column(Text)
    chat_session_id = Column(String, ForeignKey("chat_sessions.session_id"))
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    resolved_at = Column(DateTime(timezone=True))


class TicketEvent(Base):
    """Immutable timeline / primary audit source for ticket activity."""
    __tablename__ = "ticket_events"
    event_id = Column(String, primary_key=True, default=uid)
    ticket_id = Column(String(20), ForeignKey("tickets.ticket_id"), nullable=False, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    actor_id = Column(String, ForeignKey("users.user_id"))
    actor_email = Column(String(255))
    content = Column(Text)
    is_internal = Column(Boolean, nullable=False, default=False)
    channel = Column(String(20), index=True)  # email|portal|chat|system
    email_message_id = Column(String(500))
    ip_address = Column(String(64))
    meta = Column(Text)  # JSON string
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, index=True)


class EmailThread(Base):
    __tablename__ = "email_threads"
    thread_id = Column(String, primary_key=True, default=uid)
    ticket_id = Column(String(20), ForeignKey("tickets.ticket_id"), nullable=False, index=True)
    message_id = Column(String(500), unique=True, nullable=False)
    in_reply_to = Column(String(500))
    subject = Column(String(1000), nullable=False)
    from_address = Column(String(255), nullable=False)
    to_addresses = Column(Text, nullable=False)
    direction = Column(String(10), nullable=False)  # inbound|outbound
    body_text = Column(Text)
    sent_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, index=True)


class ChatSession(Base):
    __tablename__ = "chat_sessions"
    session_id = Column(String, primary_key=True, default=uid)
    user_id = Column(String, ForeignKey("users.user_id"))
    ticket_id = Column(String(20))
    started_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    escalated_at = Column(DateTime(timezone=True))
    transcript = Column(Text, nullable=False, default="[]")     # JSON array
    kb_articles_cited = Column(Text, default="[]")              # JSON array of titles
    escalation_summary = Column(Text)


class KBArticle(Base):
    __tablename__ = "kb_articles"
    article_id = Column(String, primary_key=True, default=uid)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String(50), nullable=False)
    tags = Column(Text, default="[]")
    status = Column(String(20), nullable=False, default="draft", index=True)  # draft|published|archived
    author_id = Column(String, ForeignKey("users.user_id"))
    version = Column(Integer, nullable=False, default=1)
    citation_count = Column(Integer, nullable=False, default=0)
    published_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)


class Approval(Base):
    """One record per high-risk ticket. Immutable once decided. AI never writes a decision."""
    __tablename__ = "approvals"
    approval_id = Column(String, primary_key=True, default=uid)
    ticket_id = Column(String(20), ForeignKey("tickets.ticket_id"), unique=True, nullable=False)
    approver_id = Column(String, ForeignKey("users.user_id"))
    requested_by = Column(String(255))
    status = Column(String(20), nullable=False, default="pending", index=True)  # pending|approved|rejected
    reason = Column(Text)
    risk_factors = Column(Text)
    requested_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    decided_at = Column(DateTime(timezone=True))


class AuditLog(Base):
    """Write-once compliance log. UPDATE/DELETE are blocked at the ORM layer."""
    __tablename__ = "audit_log"
    log_id = Column(String, primary_key=True, default=uid)
    event_type = Column(String(80), nullable=False, index=True)
    actor_id = Column(String)
    actor_email = Column(String(255))
    actor_role = Column(String(50))
    ticket_id = Column(String(20), index=True)
    channel = Column(String(20), index=True)  # email|portal|chat|system|admin
    ip_address = Column(String(64))
    payload = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, index=True)


class SLAPolicy(Base):
    __tablename__ = "sla_policies"
    policy_id = Column(String, primary_key=True, default=uid)
    category = Column(String(50))  # NULL = catch-all
    priority = Column(String(20), nullable=False)
    response_minutes = Column(Integer, nullable=False)
    resolution_minutes = Column(Integer, nullable=False)
    warning_minutes = Column(Integer, nullable=False, default=120)


class Attachment(Base):
    __tablename__ = "attachments"
    attachment_id = Column(String, primary_key=True, default=uid)
    ticket_id = Column(String(20), ForeignKey("tickets.ticket_id"), nullable=False, index=True)
    uploader_email = Column(String(255), nullable=False)
    file_name = Column(String(500), nullable=False)
    stored_path = Column(String(1000), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=False)
    uploaded_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)


# ---- Immutability guards: audit_log and decided approvals are write-once ----
@event.listens_for(SessionLocal, "before_flush")
def _immutability_guard(session, flush_context, instances):
    for obj in session.dirty:
        if isinstance(obj, AuditLog):
            raise ValueError("audit_log rows are immutable")
        if isinstance(obj, TicketEvent):
            raise ValueError("ticket_events rows are immutable")
    for obj in session.deleted:
        if isinstance(obj, (AuditLog, TicketEvent, Approval)):
            raise ValueError("this record type cannot be deleted")


def next_ticket_id(db) -> str:
    """SPS-{YEAR}-{NNN} sequential ticket id, generated at app layer."""
    year = utcnow().year
    prefix = f"SPS-{year}-"
    last = (db.query(Ticket.ticket_id).filter(Ticket.ticket_id.like(prefix + "%"))
            .order_by(Ticket.ticket_id.desc()).first())
    seq = int(last[0].split("-")[-1]) + 1 if last else 1
    return f"{prefix}{seq:03d}"


SEED_KB = [
    ("How to connect to the SPS VPN", "general_it",
     "1. Install the SPS GlobalConnect VPN client from the software portal.\n"
     "2. Open the client and enter gateway vpn.spsnet.com.\n"
     "3. Sign in with your SPS email and password, then approve the MFA prompt.\n"
     "4. Once connected, the status icon turns green. If the connection fails, verify you are NOT on the office network, "
     "restart the client, and check that your password has not expired. For repeated failures, submit a ticket under General IT."),
    ("Email setup on phone and laptop", "general_it",
     "SPS email runs on Microsoft 365. On mobile, install Outlook and sign in with your SPS address. On a laptop, "
     "use Outlook desktop or outlook.office.com. IMAP/POP access is disabled by security policy. If you cannot sign in, "
     "reset your password at passwordreset.spsnet.com or contact helpdesk."),
    ("Laptop setup and troubleshooting", "general_it",
     "New laptops arrive pre-imaged with Windows 11, Office, Teams and the SPS security agent. First boot: connect to Wi-Fi, "
     "sign in with SPS credentials, allow 30 minutes for policies to apply. Common fixes: slow performance - reboot and check "
     "Windows updates; battery issues - run the battery report; broken hardware - submit a ticket with photos and asset tag."),
    ("Cloud deployment checklist", "cloud",
     "Before deploying to SPS cloud (Azure/AWS): 1) Resource request approved by team lead. 2) Tags applied: owner, project, "
     "cost-center. 3) No public IPs without security review. 4) Secrets in Key Vault only - never in code or pipelines. "
     "5) Monitoring/alerts configured. 6) Backup policy attached. VM outages or deployment failures should be reported as "
     "Cloud tickets with the deployment log attached."),
    ("How to report a phishing email", "cybersecurity",
     "If you receive a suspicious email: DO NOT click links or open attachments. Use the 'Report Phishing' button in Outlook, "
     "or forward the message as an attachment to helpdesk@spsnet.com with the word PHISHING in the subject. The SOC team "
     "treats phishing reports as critical incidents. If you already clicked a link or entered credentials, report immediately "
     "and change your password - this is urgent."),
    ("Intern onboarding guide", "hr_internship",
     "Welcome to SPS! Week 1: collect your laptop and badge, complete HR paperwork in the intern portal, finish the security "
     "awareness training, and meet your mentor. Your accounts (email, Teams, intern portal) are provisioned on day 1. "
     "Timesheets are due every Friday in the portal. Questions about program logistics go to the HR-Internship queue."),
    ("Access request and approval policy", "identity_access",
     "Access to production systems, admin roles, and privileged accounts requires a formal request and HUMAN approval by a "
     "security admin or manager. The AI assistant and helpdesk agents cannot grant access. Submit a ticket describing the "
     "system, the access level, the business justification, and the duration. High-risk requests enter the Waiting Approval "
     "state and are reviewed by the security team. Approvals are logged for compliance."),
    ("SPS product overview: MYID, CSM, BMS, Azalio", "general_it",
     "MYID - SPS identity and access management product (SSO, MFA, lifecycle). CSM - Cloud Service Manager for multi-cloud "
     "provisioning and cost control. BMS - Business Management Suite covering projects, billing and reporting. Azalio - the "
     "AI automation platform powering chat assistants and workflow bots. Product-specific bugs should be filed as tickets "
     "with the product name in the subject."),
]


def seed(db):
    """Idempotent seed: teams, SLA policies, demo users for all 6 roles, published KB."""
    from .security import hash_password
    if db.query(User).first():
        return
    teams = {}
    for name, cat in [("Cloud", "cloud"), ("SOC", "cybersecurity"), ("Identity", "identity_access"),
                      ("DevOps", "devops"), ("HR-Internship", "hr_internship"), ("IT-Ops", "general_it")]:
        t = Team(name=name, default_category=cat, description=f"{name} support team")
        db.add(t)
        teams[cat] = t
    db.flush()
    users = [
        ("admin@spsnet.com", "Admin@123", "Avery Admin", "administrator", None),
        ("agent@spsnet.com", "Agent@123", "Jordan Agent", "support_agent", teams["general_it"].team_id),
        ("security@spsnet.com", "Security@123", "Sam Security", "security_admin", teams["cybersecurity"].team_id),
        ("manager@spsnet.com", "Manager@123", "Morgan Manager", "manager", None),
        ("employee@spsnet.com", "Employee@123", "Eli Employee", "employee", None),
        ("intern@spsnet.com", "Intern@123", "Ira Intern", "intern", None),
    ]
    admin = None
    for email, pw, name, role, team_id in users:
        u = User(email=email, hashed_password=hash_password(pw), full_name=name, role=role, team_id=team_id)
        db.add(u)
        if role == "administrator":
            admin = u
    db.flush()
    for prio, resp, reso in [("critical", 30, 240), ("high", 60, 480), ("medium", 240, 1440), ("low", 480, 2880)]:
        db.add(SLAPolicy(category=None, priority=prio, response_minutes=resp, resolution_minutes=reso,
                         warning_minutes=int(os.environ.get("SLA_WARNING_MINUTES", "120"))))
    for title, cat, content in SEED_KB:
        db.add(KBArticle(title=title, category=cat, content=content, status="published",
                         author_id=admin.user_id, published_at=utcnow(), tags=json.dumps(title.lower().split())))
    db.commit()


def _auto_migrate():
    """Lightweight migration: add any model columns missing from existing tables."""
    from sqlalchemy import inspect, text
    inspector = inspect(engine)
    with engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            if not inspector.has_table(table.name):
                continue
            existing = {c["name"] for c in inspector.get_columns(table.name)}
            for col in table.columns:
                if col.name not in existing:
                    coltype = col.type.compile(engine.dialect)
                    conn.execute(text(f'ALTER TABLE {table.name} ADD COLUMN {col.name} {coltype}'))
                    print(f"[db] migrated: added {table.name}.{col.name}")


def init_db():
    Base.metadata.create_all(engine)
    _auto_migrate()
    with SessionLocal() as db:
        seed(db)
