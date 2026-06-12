"""Email channel: outbound (SMTP or dev outbox) and inbound (IMAP poll or simulator).

Outbound: if SMTP_HOST is set, real SMTP is used. Either way every outbound
message is recorded in email_threads (powering the Admin > Email Center dev
outbox) and saved as a .eml file in /outbox.

Inbound: if IMAP_HOST is set, a background thread polls the mailbox. In dev,
POST /api/email/inbound (Email Center form) feeds the exact same ingestion
pipeline: ticket-ID threading -> update ticket, else create ticket + ACK +
AI classification. Subject convention: [SPS-2026-042] Short title.
"""
import email
import email.utils
import imaplib
import os
import re
import smtplib
import threading
import time
from email.message import EmailMessage
from pathlib import Path

from .models import EmailThread, SessionLocal, utcnow

OUTBOX_DIR = Path(__file__).resolve().parent.parent / "outbox"
TICKET_RE = re.compile(r"\[(SPS-\d{4}-\d{3})\]")


def helpdesk_addr() -> str:
    return os.environ.get("HELPDESK_EMAIL", "helpdesk@spsnet.com")


def _configured(host_var: str, password_var: str) -> bool:
    """True only when host is set AND the password is not a placeholder."""
    host = os.environ.get(host_var, "").strip()
    pw = os.environ.get(password_var, "").strip()
    return bool(host) and bool(pw) and "PASTE" not in pw.upper()


def _branded_html(title: str, body_lines: list, ticket_id: str = "") -> str:
    base = os.environ.get("APP_BASE_URL", "http://localhost:8000")
    rows = "".join(f"<p style='margin:8px 0;color:#333;font-size:14px;line-height:1.6'>{line}</p>"
                   for line in body_lines)
    link = (f"<p style='margin:16px 0'><a href='{base}' style='background:#2E75B6;color:#fff;padding:10px 20px;"
            f"border-radius:8px;text-decoration:none;font-weight:600'>Open SecureDesk Portal</a></p>")
    return (f"<div style='font-family:Inter,Segoe UI,Arial,sans-serif;max-width:560px;margin:auto;"
            f"border:1px solid #D5E8F0;border-radius:12px;overflow:hidden'>"
            f"<div style='background:#1A4B8C;color:#fff;padding:16px 24px;font-size:18px;font-weight:700'>"
            f"<span style='font-style:italic;font-weight:800;font-family:Arial'>sps</span> "
            f"SecureDesk{(' — ' + ticket_id) if ticket_id else ''}</div>"
            f"<div style='padding:24px;background:#fff'><h2 style='color:#1A4B8C;font-size:18px;margin:0 0 12px'>{title}</h2>"
            f"{rows}{link}</div>"
            f"<div style='background:#F4F6F9;color:#666;font-size:12px;padding:12px 24px'>"
            f"Software Productivity Strategists — IT Helpdesk · Do not share credentials by email.</div></div>")


def send_email(db, to_address: str, subject: str, body_lines: list, ticket_id: str = "",
               title: str = "Update from SPS SecureDesk") -> str:
    """Send (or dev-record) an outbound email; always log to email_threads + /outbox."""
    msg = EmailMessage()
    msg["From"] = f"SPS SecureDesk <{helpdesk_addr()}>"
    msg["To"] = to_address
    msg["Subject"] = f"[{ticket_id}] {subject}" if ticket_id and f"[{ticket_id}]" not in subject else subject
    msg["Message-ID"] = email.utils.make_msgid(domain="spsnet.com")
    plain = "\n".join(re.sub(r"<[^>]+>", "", line) for line in body_lines)
    msg.set_content(plain + "\n\n— SPS SecureDesk")
    msg.add_alternative(_branded_html(title, body_lines, ticket_id), subtype="html")

    if _configured("SMTP_HOST", "SMTP_PASSWORD"):
        smtp_host = os.environ.get("SMTP_HOST", "").strip()
        try:
            port = int(os.environ.get("SMTP_PORT", "587"))
            with smtplib.SMTP(smtp_host, port, timeout=20) as server:
                if os.environ.get("SMTP_TLS", "true").lower() == "true":
                    server.starttls()
                user = os.environ.get("SMTP_USER", "")
                if user:
                    server.login(user, os.environ.get("SMTP_PASSWORD", ""))
                server.send_message(msg)
        except Exception as exc:
            print(f"[emailer] SMTP send failed ({exc}); message kept in dev outbox")

    OUTBOX_DIR.mkdir(exist_ok=True)
    fname = re.sub(r"[^A-Za-z0-9_-]", "_", f"{utcnow().strftime('%Y%m%d_%H%M%S')}_{msg['Subject']}")[:80]
    (OUTBOX_DIR / f"{fname}.eml").write_bytes(bytes(msg))

    if ticket_id:
        db.add(EmailThread(ticket_id=ticket_id, message_id=msg["Message-ID"], subject=msg["Subject"],
                           from_address=helpdesk_addr(), to_addresses=to_address,
                           direction="outbound", body_text=plain))
    return msg["Message-ID"]


def match_ticket_id(subject: str, in_reply_to: str, db) -> str | None:
    """Threading: [SPS-YYYY-NNN] in subject, else In-Reply-To Message-ID lookup."""
    match = TICKET_RE.search(subject or "")
    if match:
        return match.group(1)
    if in_reply_to:
        row = db.query(EmailThread).filter(EmailThread.message_id == in_reply_to).first()
        if row:
            return row.ticket_id
    return None


def start_imap_poller(ingest_callback):
    """Background IMAP polling thread (only if IMAP_HOST configured)."""
    if not _configured("IMAP_HOST", "IMAP_PASSWORD"):
        print("[emailer] IMAP not configured - use Email Center inbound simulator for the email channel demo")
        return
    host = os.environ.get("IMAP_HOST", "").strip()

    def loop():
        interval = int(os.environ.get("EMAIL_POLL_SECONDS", "120"))
        while True:
            try:
                conn = imaplib.IMAP4_SSL(host)
                conn.login(os.environ.get("IMAP_USER", ""), os.environ.get("IMAP_PASSWORD", ""))
                conn.select("INBOX")
                _, data = conn.search(None, "UNSEEN")
                for num in data[0].split():
                    _, msg_data = conn.fetch(num, "(RFC822)")
                    parsed = email.message_from_bytes(msg_data[0][1])
                    body = ""
                    if parsed.is_multipart():
                        for part in parsed.walk():
                            if part.get_content_type() == "text/plain":
                                body = part.get_payload(decode=True).decode(errors="replace")
                                break
                    else:
                        body = parsed.get_payload(decode=True).decode(errors="replace")
                    from_addr = email.utils.parseaddr(parsed.get("From", ""))[1]
                    with SessionLocal() as db:
                        ingest_callback(db, from_addr, parsed.get("Subject", "(no subject)"),
                                        body, parsed.get("Message-ID", ""), parsed.get("In-Reply-To", ""))
                conn.logout()
            except Exception as exc:
                print(f"[emailer] IMAP poll error: {exc}")
            time.sleep(interval)

    threading.Thread(target=loop, daemon=True, name="imap-poller").start()
    print("[emailer] IMAP poller started")
