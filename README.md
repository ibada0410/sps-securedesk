# 🎯 SPS SecureDesk AI
### AI-Assisted Enterprise Helpdesk

<div align="center">

**Unified ticket convergence** • **Human-first approval** • **Knowledge-grounded AI** • **Enterprise RBAC**

[Features](#-features) • [Tech Stack](#-tech-stack) • [Quick Start](#-quick-start) • [Architecture](#-architecture) • [Deploy Free](#-deploy-free) • [Security](#-security)

</div>

---

## 📌 Overview

**SPS SecureDesk AI** replaces legacy osTicket with a modern, AI-assisted helpdesk for **Software Productivity Strategists (SPS)** — IT, cloud, cybersecurity and operations teams.

Three first-class **intake channels** (📧 Email, 📋 Web Form, 💬 AI Chat) converge into **one unified ticket system**. Humans own resolution and approvals; AI assists with triage, answers, summaries and knowledge base grounding.

> **🔒 Human-first policy (permanent):** The AI never grants access, never approves requests, never resets privileged accounts. High-risk requests are blocked in **Waiting Approval** until a human security admin or manager decides.

---

## 🛠️ Tech Stack

| Layer | Tools |
|-------|-------|
| **Backend** | 🚀 FastAPI • 🐍 Python 3.11+ • 🗄️ SQLAlchemy ORM |
| **Frontend** | 🎨 Vanilla JS SPA (no build) • 📱 Responsive CSS • 🎭 SPS Brand Colors |
| **Database** | 💾 SQLite (dev) / 🐘 PostgreSQL (prod) |
| **AI** | 🧠 Groq (llama-3.3-70b) • OpenAI-compatible API |
| **Email** | 📧 SMTP + IMAP (Gmail, Office 365, etc.) • Branded HTML |
| **Auth** | 🔐 PBKDF2-SHA256 • HMAC JWT • OAuth2 (Microsoft SSO) • 6-role RBAC |
| **Hosting** | ☁️ Render (free tier) • 🔗 Neon PostgreSQL (free) • UptimeRobot (keep-alive) |

---

## ⚡ Quick Start

### Local development (2 minutes)

```bash
cd spsnet_project
pip install -r requirements.txt
python -m uvicorn app.main:app --port 8000
```

Open **http://localhost:8000** → API docs at **http://localhost:8000/docs**

### Demo accounts

| Role | Email | Password |
|------|-------|----------|
| 👨‍💼 Administrator | `admin@spsnet.com` | `Admin@123` |
| 🛠️ Support Agent | `agent@spsnet.com` | `Agent@123` |
| 🔐 Security Admin | `security@spsnet.com` | `Security@123` |
| 📊 Manager | `manager@spsnet.com` | `Manager@123` |
| 👥 Employee | `employee@spsnet.com` | `Employee@123` |
| 🎓 Intern | `intern@spsnet.com` | `Intern@123` |

Database (SQLite) is **auto-created** on first start with 6 demo users, 8 KB articles, and SLA policies.

---

## 🏗️ Architecture

### Intake pipeline (three channels → one service)

```
┌─────────────────────────────────────────────────────────────────┐
│                     CUSTOMER INTAKE                              │
└─────────────────────────────────────────────────────────────────┘

    📧 EMAIL                    📋 WEB FORM              💬 AI CHAT
  ┌──────────────┐          ┌────────────────┐      ┌──────────────┐
  │ IMAP Poller  │          │ POST /api/      │      │ POST /api/   │
  │ or Simulate  │          │ tickets         │      │ chat/message │
  │              │          │ + attachments   │      │              │
  │ [SPS-YYYY-   │          │                │      │ KB-grounded  │
  │  NNN] thread │          │ source=         │      │ AI answer    │
  │              │          │ portal_form     │      │              │
  └──────┬───────┘          └────────┬────────┘      └──────┬───────┘
         │                            │                      │
         │                            │                      │
         │                    escalation on high-risk        │
         │                            │                      │
         └────────────────────────────┼──────────────────────┘
                                      │
                                      v
         ┌─────────────────────────────────────────────────┐
         │    create_ticket_service()                      │
         │  (THE ONLY INTAKE FUNCTION — app/main.py)     │
         │                                                  │
         │  ✓ Generate ticket ID: SPS-YYYY-NNN            │
         │  ✓ Timeline event + audit log (channel-tagged) │
         │  ✓ SLA policy match (sla_due_at)               │
         │  ✓ Security scan (secrets, injection)          │
         │  ✓ AI classification (category, priority, risk)│
         │  ✓ Send ACK email to requester                 │
         └─────────────────────────────────────────────────┘
                              │
                              v
              ┌───────────────────────────────┐
              │   HIGH RISK DETECTED?         │
              │                               │
              │  ✓ Admin/prod access         │
              │  ✓ Phishing/security         │
              │  ✓ Custom approval rules     │
              └───────────────────────────────┘
                    YES │                NO
                        │                │
                        v                v
              ┌──────────────────┐  ┌──────────────┐
              │ status=waiting_   │  │ status=open  │
              │ approval          │  │              │
              │                   │  │ Ready for    │
              │ 🔒 AI CANNOT     │  │ agent queue  │
              │    DECIDE        │  │              │
              │                   │  └──────────────┘
              │ ✉️ Approver          │
              │    emailed        │
              └──────────────────┘
                    │
                    v
         ┌─────────────────────────┐
         │  HUMAN APPROVAL GATE    │
         │  (security admin only)  │
         │                         │
         │  Approve → open         │
         │  Reject → reason reqd   │
         │  (immutable decision)   │
         └─────────────────────────┘
                    │
                    v
         ┌──────────────────────────────────┐
         │  Agent Workspace                 │
         │  ┌────────────────────────────┐  │
         │  │ Queue (filtered by team)   │  │
         │  ├────────────────────────────┤  │
         │  │ Two-panel detail:          │  │
         │  │  • Full timeline           │  │
         │  │  • KB suggestions          │  │
         │  │  • Email/form/chat threads │  │
         │  ├────────────────────────────┤  │
         │  │ Actions:                   │  │
         │  │  • Reply (email/internal)  │  │
         │  │  • Reassign                │  │
         │  │  • Resolve (note required) │  │
         │  └────────────────────────────┘  │
         └──────────────────────────────────┘
                    │
                    v
         ┌──────────────────────────┐
         │ Resolution email sent    │
         │ to requester             │
         │                          │
         │ Email threads updated    │
         │ Audit log final entry    │
         └──────────────────────────┘
```

### Data flow: email threading

```
User email    →  IMAP poller  →  Check subject [SPS-2026-042]
              →  Match Message-ID in In-Reply-To
              →  Same ticket? YES → add event, update timeline
              →  New email?   NO → create ticket SPS-2026-043
```

### Dashboard workspace map

| Role | Landing Page | Key Actions |
|------|--------------|-------------|
| 👨‍💼 **Admin** | User mgmt + KB editor | Create staff, manage SLA, Email Center |
| 🛠️ **Agent** | Ticket queue (team filtered) | Assign, reply, resolve, escalate |
| 🔐 **Security** | Approvals + audit log | Review high-risk, export audit CSV |
| 📊 **Manager** | Reports (SLA, volume, agent perf) | Export analytics, trend analysis |
| 👥 **Employee** | Submit form + chat | Ask AI, track tickets, update profile |
| 🎓 **Intern** | Chat + form (read-only queue) | Escalate via chat, learn from KB |

---

## 📁 Project Files (11 source files, no build step)

```
spsnet_project/
├── app/
│   ├── main.py          🚀 FastAPI app (1700+ lines)
│   │                    - All REST routes (auth, tickets, chat, approvals, reports)
│   │                    - Unified create_ticket_service()
│   │                    - Approval workflow + audit
│   │                    - SLA monitor
│   │
│   ├── models.py        🗄️ SQLAlchemy models
│   │                    - Tickets, events, approvals, audit_log
│   │                    - Users, KB articles, SLA policies
│   │                    - Auto seed + schema migration
│   │
│   ├── security.py      🔐 Auth & RBAC
│   │                    - PBKDF2-SHA256 hashing (200k iterations)
│   │                    - HMAC-signed JWT tokens (8-hour session)
│   │                    - Scoped tokens (password reset)
│   │                    - 6-role RBAC dependencies
│   │                    - Secret/injection detection
│   │
│   ├── ai.py            🧠 Groq AI integration
│   │                    - KB-grounded chat (citations)
│   │                    - Ticket classification
│   │                    - Risk assessment
│   │                    - Fallback keyword detection
│   │
│   └── emailer.py       📧 SMTP/IMAP
│                        - Outbound branded HTML emails
│                        - IMAP inbound polling (2-min default)
│                        - [SPS-YYYY-NNN] threading
│                        - Dev outbox simulator
│
├── static/
│   ├── index.html       🎨 SPA entry point
│   ├── app.js           💬 2500+ lines vanilla JS
│   │                    - All 6 workspaces + routing
│   │                    - SPS two-swoosh logo (SVG)
│   │                    - Auth (signup, reset, SSO)
│   │                    - Profile editor
│   │
│   └── styles.css       🎭 SPS brand colors + typography
│
├── docs/
│   └── screenshots/     📸 UI screenshots (for README)
│
├── .env                 🔐 Secrets (not committed)
├── requirements.txt     📦 Dependencies (7 packages)
├── run.bat              🏃 Windows launcher
├── smoke_test.py        ✅ 32 end-to-end tests
├── auth_test.py         🔐 16 auth feature tests
└── README.md            📚 This file
```

---

## 🔐 Security

✅ **RBAC enforced** server-side on every endpoint (6 roles, FastAPI dependencies)  
✅ **PBKDF2-SHA256** password hashing (200k iterations); password policy on creation  
✅ **HMAC-signed** expiring session tokens; failed logins audit-logged  
✅ **Input sanitization** (script/event stripping) on all user content  
✅ **Secret detection** (AWS keys, API tokens, private keys) → audit event  
✅ **Injection detection** (SQLi/XSS/template) → audit event  
✅ **ORM-parameterized** queries only (no raw SQL)  
✅ **Immutable audit log** (write-once, ORM guard)  
✅ **Approval decisions** immutable; rejection reason mandatory  
✅ **Attachment limits** (10MB, extension allow-list, auth-only download)  
✅ **OAuth2 SSO** (Microsoft integration ready)  

---

## 📊 Features

### 1️⃣ Three intake channels (unified)
- **📧 Email** — IMAP polling, [SPS-YYYY-NNN] threading, branded HTML replies
- **📋 Web form** — categories, priority, attachments, confirmation email
- **💬 AI chat** — KB-grounded answers, escalation with pre-filled ticket

### 2️⃣ AI-assisted workflow
- **🧠 Classification** — category, priority, risk level assigned by AI (agent override)
- **📚 Knowledge base** — AI cites published articles in chat; agents read suggestions
- **📝 Summaries & drafts** — AI proposes reply text (agent edits/sends)
- **🤖 + 🔒 Human-only decisions** — AI NEVER approves, NEVER resets accounts

### 3️⃣ Approval workflow
- **High-risk auto-escalate** — admin/production access, phishing, custom rules
- **🔒 Approval gate** — blocked until security admin or manager approves
- **✉️ Approver emails** — decision links, reason required on rejection
- **📋 Immutable decisions** — no override once approved/rejected

### 4️⃣ Team & SLA management
- **👥 Team assignment** — categories → teams, round-robin if multiple
- **⏰ SLA policies** — response time, resolution time by category + priority
- **📊 SLA monitor** — background check, status updates on breach
- **✉️ Breached alerts** — email to manager when SLA at risk

### 5️⃣ Audit & compliance
- **📋 Immutable audit log** — every action (login, ticket change, approval, secret) timestamped
- **🔍 Audit filter** — by user, action, channel, date range
- **📥 CSV export** — full audit trail for compliance reviews
- **🚨 Secret detection** — AWS, xAI, GitHub keys, private keys, SQL injection patterns

### 6️⃣ Reports & analytics
- **📈 Volume trends** — tickets by channel, category, priority, time period
- **⏱️ SLA compliance** — % on time, breached, by category
- **👤 Agent performance** — resolved count, avg resolution time, top categories
- **🔴 High-risk** — escalations & approvals this period
- **📥 CSV export** — full reports for stakeholder reviews

### 7️⃣ User & access management
- **🔑 Sign up** — self-service (interns/employees only); staff created by admin
- **🔓 Password reset** — 1-hour HMAC token, no account enumeration
- **🪟 Microsoft SSO** — OAuth2 flow + Graph API (config-ready)
- **👤 User profile** — edit name, dept, phone; change password with verification
- **🚫 Role-based access** — 6 roles, scoped endpoints

---

## ⚙️ Configuration

All secrets live in **`.env`** (never committed — see `.env.example`).

| Variable | Purpose | Example |
|----------|---------|---------|
| `XAI_API_KEY` | Groq API key (or OpenRouter, xAI, etc.) | `gsk_FXcT...` |
| `XAI_BASE_URL` | AI provider base URL | `https://api.groq.com/openai/v1` |
| `XAI_MODEL` | AI model name | `llama-3.3-70b-versatile` |
| `JWT_SECRET_KEY` | Session token signing (change for prod!) | `(random 48-char string)` |
| `DATABASE_URL` | SQLite or PostgreSQL | `sqlite:///securedesk.db` |
| `HELPDESK_EMAIL` | Sender name in emails | `helpdesk@spsnet.com` |
| `APP_BASE_URL` | Public URL (for email links) | `http://localhost:8000` |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` | Gmail, Office 365, etc. | `smtp.gmail.com`, `587`, ... |
| `IMAP_HOST`, `IMAP_USER`, `IMAP_PASSWORD` | Email inbound polling | `imap.gmail.com`, ... |
| `EMAIL_POLL_SECONDS` | IMAP polling interval | `120` (2 minutes) |
| `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_TENANT_ID` | Microsoft SSO (optional) | (from Azure AD app) |

---

## 🚀 Deploy for free (all pieces have permanent free tiers)

### Prerequisites
- GitHub account (free)
- Neon.tech account (free PostgreSQL)
- Render.com account (free hosting)
- UptimeRobot account (free keep-alive, optional)

### Step 1: Database — Neon PostgreSQL (~3 min)

1. Go to **neon.tech** → Sign up (GitHub button fastest)
2. Copy your connection string (looks like `postgresql://user:pass@host/db...`)
3. Edit it: change `postgresql://` → `postgresql+psycopg2://` (keep everything else + `?sslmode=require`)

### Step 2: Code — GitHub (~5 min)

1. Go to **github.com** → New repository → name: `sps-securedesk` → Private
2. In your project folder, run:
   ```bash
   git remote add origin https://github.com/YOUR_USERNAME/sps-securedesk.git
   git push -u origin master
   ```
   (Your `.env` is excluded via `.gitignore` — never pushed!)

### Step 3: Hosting — Render.com (~10 min)

1. Go to **render.com** → Sign up with GitHub → New → Web Service → pick your repo
2. Fill the form:
   - **Name**: `sps-securedesk` (becomes your URL)
   - **Instance Type**: Free
   - **Build**: `pip install -r requirements.txt`
   - **Start**: `python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT`
3. Add **Environment Variables** (all from your `.env`):
   ```
   DATABASE_URL = postgresql+psycopg2://...  (your edited Neon string)
   JWT_SECRET_KEY = (generate new: python -c "import secrets; print(secrets.token_urlsafe(48))")
   XAI_API_KEY = gsk_FXcT...
   XAI_MODEL = llama-3.3-70b-versatile
   XAI_BASE_URL = https://api.groq.com/openai/v1
   HELPDESK_EMAIL = your-email@gmail.com
   SMTP_HOST = smtp.gmail.com
   SMTP_PORT = 587
   SMTP_USER = your-email@gmail.com
   SMTP_PASSWORD = (Gmail app password)
   IMAP_HOST = imap.gmail.com
   IMAP_USER = your-email@gmail.com
   IMAP_PASSWORD = (Gmail app password)
   EMAIL_POLL_SECONDS = 120
   APP_BASE_URL = https://sps-securedesk.onrender.com
   ```
4. **Deploy** → watch the log (~3–5 min). When it says "live", open **https://sps-securedesk.onrender.com**

### Step 4: Keep-alive (optional, recommended)

Render free tier **sleeps after ~15 min idle**. Add a pinger:

1. Go to **uptimerobot.com** → Free sign-up
2. **Add Monitor** → HTTP → URL: `https://sps-securedesk.onrender.com/api/health` → 5-min interval
3. Done — your app never sleeps, IMAP runs 24/7

---

## 📸 Screenshots

### Login screen
![Login page](docs/screenshots/login.png)

---

## ✅ Success checklist (for reviewers)

- [ ] **Email journey**: inbox simulation → ticket created → agent replies → resolution email
- [ ] **Form journey**: employee submits request → agent works queue → resolves
- [ ] **Chat journey**: intern gets KB answer, then escalates high-risk request
- [ ] **Approval**: security admin approves/rejects (decision immutable)
- [ ] **Audit**: secret detection, filter by channel, CSV export
- [ ] **Reports**: volume by channel/category, SLA compliance, agent perf

---

## 📚 API Documentation

Interactive Swagger docs at `/docs` and OpenAPI JSON at `/openapi.json`:

```
GET  /docs                          → FastAPI Swagger UI
POST /api/auth/login                → Session token
POST /api/auth/signup               → Self-register (intern/employee)
POST /api/auth/forgot-password      → Reset link (1-hour token)
POST /api/auth/reset-password       → New password
GET  /api/auth/sso                  → Microsoft OAuth2 start
GET  /api/auth/sso/callback         → OAuth2 callback handler
GET  /api/profile                   → My account
PATCH /api/profile                  → Update name/dept/phone
POST /api/profile/change-password   → Change password

POST /api/tickets                   → Create ticket (email/form)
GET  /api/tickets                   → List (filtered by role/team)
GET  /api/tickets/{id}              → Ticket detail + timeline
PATCH /api/tickets/{id}             → Assign, update, resolve
POST /api/tickets/{id}/events       → Agent reply (email/internal)

POST /api/chat/message              → AI chat (KB-grounded)
GET  /api/kb/articles               → Published knowledge base
POST /api/kb/articles               → Admin create article
PATCH /api/kb/articles/{id}         → Admin edit
DELETE /api/kb/articles/{id}        → Admin delete

GET  /api/approvals                 → List pending (security/manager)
POST /api/approvals/{id}/approve    → Approve ticket
POST /api/approvals/{id}/reject     → Reject (reason required)

GET  /api/audit                     → Audit log (filter by user/action/channel)
GET  /api/audit/csv                 → Export CSV

GET  /api/reports/volume            → Tickets by channel/category
GET  /api/reports/sla               → SLA compliance by category
GET  /api/reports/agent             → Agent performance (resolved, avg time)
GET  /api/reports/high-risk         → Escalations + approvals
GET  /api/reports/csv               → Export all reports

GET  /api/health                    → Liveness (for UptimeRobot)
```

---

## 🧪 Testing

### Smoke tests (32 end-to-end checks)

```bash
python smoke_test.py
```

Covers: email ingestion, form submission, AI chat, approvals, audit, reports, security detection.

### Auth tests (16 checks)

```bash
python auth_test.py
```

Covers: signup, password reset, profile, SSO readiness.

---

## 🐛 Troubleshooting

### AI API unreachable
The system gracefully degrades: chat serves KB articles directly with citations; ticket classification falls back to keyword-based risk detection. **No single point of failure.**

### Email not ingesting
Check `.env`: `IMAP_HOST`, `IMAP_USER`, `IMAP_PASSWORD` set? Otherwise, use Admin → **Email Center** → "Simulate inbound email" to test the workflow.

### App sleeping on Render (first request slow)
Add UptimeRobot pinger (free, ping every 5 min) → app stays awake 24/7.

### Database connection error on Render
Double-check `DATABASE_URL` includes `postgresql+psycopg2://` (not just `postgresql://`). Render logs show the error — check them!

---

## 📖 Documentation

- **This README** — features, architecture, deploy, API, troubleshooting
- **`/docs`** (when running) — interactive Swagger API docs
- **`app/main.py`** — inline docstrings for each endpoint
- **`smoke_test.py`** — integration test examples for each journey

---

## 📋 License & Attribution

**SPS Capstone Project** — Software Productivity Strategists. Built June 2026.

UI per **UXD-001** design system:
- SPS Navy: `#1A4B8C`
- SPS Blue: `#2E75B6`
- SPS Sky: `#D5E8F0`
- Typography: Inter

AI provider: **Groq** (llama-3.3-70b-versatile)

---

<div align="center">

**🎓 Ready for production** • **Free forever** • **Human-first by design**

[↑ Back to top](#-sps-securedesk-ai)

</div>
