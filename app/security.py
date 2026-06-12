"""Auth + security utilities: PBKDF2 password hashing, HMAC-signed JWT,
role-based access control dependencies, and security input scanning
(injection patterns + secret detection) feeding the audit log.
"""
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import time

from fastapi import Depends, HTTPException, Request

from .models import SessionLocal, User

JWT_SECRET = os.environ.get("JWT_SECRET_KEY", "dev-secret-change-me")
TOKEN_TTL_SECONDS = 60 * 60 * 8  # 8h session for the demo deployment


# ---------------- passwords ----------------
def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000)
    return f"pbkdf2${salt}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, salt, hexdigest = stored.split("$")
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000)
        return hmac.compare_digest(dk.hex(), hexdigest)
    except Exception:
        return False


# ---------------- tokens (compact HMAC-SHA256 JWT) ----------------
def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def create_token(user: User) -> str:
    payload = {"sub": user.user_id, "email": user.email, "role": user.role,
               "name": user.full_name, "exp": int(time.time()) + TOKEN_TTL_SECONDS}
    body = _b64(json.dumps(payload).encode())
    sig = _b64(hmac.new(JWT_SECRET.encode(), body.encode(), hashlib.sha256).digest())
    return f"{body}.{sig}"


def create_scoped_token(user_id: str, purpose: str, ttl_seconds: int = 3600) -> str:
    """Short-lived single-purpose token (e.g. password reset link)."""
    payload = {"sub": user_id, "purpose": purpose, "exp": int(time.time()) + ttl_seconds}
    body = _b64(json.dumps(payload).encode())
    sig = _b64(hmac.new(JWT_SECRET.encode(), body.encode(), hashlib.sha256).digest())
    return f"{body}.{sig}"


def decode_scoped_token(token: str, purpose: str) -> str:
    """Return user_id if the token is valid, unexpired and matches the purpose."""
    try:
        body, sig = token.split(".")
        expected = _b64(hmac.new(JWT_SECRET.encode(), body.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(sig, expected):
            raise ValueError
        payload = json.loads(_unb64(body))
        if payload.get("purpose") != purpose or payload["exp"] < time.time():
            raise ValueError
        return payload["sub"]
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid or expired link. Please request a new one.")


def decode_token(token: str) -> dict:
    try:
        body, sig = token.split(".")
        expected = _b64(hmac.new(JWT_SECRET.encode(), body.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(sig, expected):
            raise ValueError("bad signature")
        payload = json.loads(_unb64(body))
        if payload["exp"] < time.time():
            raise ValueError("expired")
        return payload
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired session")


# ---------------- FastAPI dependencies ----------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(request: Request, db=Depends(get_db)) -> User:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = decode_token(auth[7:])
    user = db.get(User, payload["sub"])
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Account not found or deactivated")
    return user


def require_role(*roles):
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="You don't have access to this area")
        return user
    return checker


AGENT_ROLES = ("support_agent", "security_admin", "administrator")
APPROVER_ROLES = ("security_admin", "manager")


# ---------------- security scanning (TRD: injection + secret detection) ----------------
SECRET_PATTERNS = [
    (r"AKIA[0-9A-Z]{16}", "aws_access_key"),
    (r"xai-[A-Za-z0-9]{20,}", "xai_api_key"),
    (r"sk-[A-Za-z0-9_\-]{20,}", "api_secret_key"),
    (r"ghp_[A-Za-z0-9]{30,}", "github_token"),
    (r"(?i)password\s*[:=]\s*\S{6,}", "plaintext_password"),
    (r"-----BEGIN (RSA |EC )?PRIVATE KEY-----", "private_key"),
]
INJECTION_PATTERNS = [
    (r"(?i)(\bunion\b.+\bselect\b|\bdrop\s+table\b|;\s*--|'\s*or\s+'1'\s*=\s*'1)", "sql_injection"),
    (r"(?i)<script[\s>]", "xss_script_tag"),
    (r"(?i)\bjavascript\s*:", "xss_js_uri"),
    (r"\$\{.*\}|\{\{.*\}\}", "template_injection"),
]


def scan_input(text: str):
    """Return list of (event_type, detail) security findings in user input."""
    findings = []
    if not text:
        return findings
    for pattern, label in SECRET_PATTERNS:
        if re.search(pattern, text):
            findings.append(("secret_detected", label))
    for pattern, label in INJECTION_PATTERNS:
        if re.search(pattern, text):
            findings.append(("injection_attempt", label))
    return findings


def sanitize_html(text: str) -> str:
    """Strip active HTML from user-supplied content before storage/display."""
    if not text:
        return text
    text = re.sub(r"(?is)<script.*?>.*?</script>", "[removed-script]", text)
    text = re.sub(r"(?i)on\w+\s*=", "data-removed=", text)
    text = re.sub(r"(?i)javascript\s*:", "removed:", text)
    return text
