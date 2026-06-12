"""Tests for signup / forgot-reset password / profile / SSO status (live server)."""
import glob
import quopri
import re

import httpx

BASE = "http://localhost:8010/api"
ok = fail = 0

def check(name, cond, extra=""):
    global ok, fail
    ok += cond; fail += (not cond)
    print(("PASS" if cond else "FAIL"), name, extra)

# --- signup ---
r = httpx.post(BASE + "/auth/signup", json={"full_name": "Nina New", "email": "nina@spsnet.com",
                                            "role": "intern", "password": "Welcome@123"})
check("signup", r.status_code == 201)
r = httpx.post(BASE + "/auth/signup", json={"full_name": "Nina New", "email": "nina@spsnet.com",
                                            "role": "intern", "password": "Welcome@123"})
check("duplicate signup blocked", r.status_code == 409)
r = httpx.post(BASE + "/auth/signup", json={"full_name": "Bad", "email": "bad@spsnet.com",
                                            "role": "administrator", "password": "Welcome@123"})
check("admin self-signup blocked", r.status_code == 422)
r = httpx.post(BASE + "/auth/signup", json={"full_name": "Bad", "email": "bad2@spsnet.com",
                                            "role": "intern", "password": "weak"})
check("weak password blocked", r.status_code == 422)
r = httpx.post(BASE + "/auth/login", json={"email": "nina@spsnet.com", "password": "Welcome@123"})
check("new account can log in", r.status_code == 200)

# --- forgot + reset ---
r = httpx.post(BASE + "/auth/forgot-password", json={"email": "nina@spsnet.com"})
check("forgot password generic ok", r.status_code == 200)
r2 = httpx.post(BASE + "/auth/forgot-password", json={"email": "ghost@nowhere.com"})
check("no account enumeration", r2.status_code == 200 and r2.json() == r.json())

eml = sorted(glob.glob("outbox/*Reset*.eml"))[-1]
raw = quopri.decodestring(open(eml, "rb").read()).decode(errors="replace")
token = re.search(r"token=([A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+)", raw).group(1)
r = httpx.post(BASE + "/auth/reset-password", json={"token": token, "new_password": "Changed@456"})
check("reset password via emailed token", r.status_code == 200, r.text[:80])
check("old password rejected",
      httpx.post(BASE + "/auth/login", json={"email": "nina@spsnet.com", "password": "Welcome@123"}).status_code == 401)
r = httpx.post(BASE + "/auth/login", json={"email": "nina@spsnet.com", "password": "Changed@456"})
check("new password works", r.status_code == 200)
check("bad reset token rejected",
      httpx.post(BASE + "/auth/reset-password", json={"token": "garbage.x", "new_password": "Changed@456"}).status_code == 400)

# --- profile ---
tok = {"Authorization": "Bearer " + r.json()["token"]}
r = httpx.patch(BASE + "/profile", headers=tok,
                json={"full_name": "Nina Newman", "department": "Cloud", "phone": "+1 301 555 0100"})
check("profile update", r.status_code == 200 and r.json()["user"]["name"] == "Nina Newman")
r = httpx.patch(BASE + "/profile", headers=tok, json={"current_password": "wrong", "new_password": "Another@789"})
check("password change needs current password", r.status_code == 403)
r = httpx.patch(BASE + "/profile", headers=tok, json={"current_password": "Changed@456", "new_password": "Another@789"})
check("password change from profile", r.status_code == 200)
r = httpx.get(BASE + "/profile", headers=tok)
check("profile readback", r.json()["department"] == "Cloud" and r.json()["phone"] == "+1 301 555 0100")

# --- sso ---
r = httpx.get(BASE + "/auth/sso")
check("sso reports not configured", r.status_code == 200 and r.json()["enabled"] is False)

print(f"\n=== {ok} passed, {fail} failed ===")
raise SystemExit(1 if fail else 0)
