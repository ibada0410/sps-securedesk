# SPS SecureDesk AI

AI-assisted enterprise helpdesk for **Software Productivity Strategists (SPS)** — IT, cloud,
cybersecurity and operations. Replaces the legacy osTicket deployment with three first-class
intake channels (**email**, **web form**, **AI chat**) that all converge into **one unified
ticket system**. Humans own resolution and approvals; AI assists with answers, triage,
summaries and drafts.

> **Human-first policy (permanent):** the AI never grants access, never approves requests,
> never resets privileged accounts, never answers outside the approved knowledge base, and
> never closes security incidents. High-risk requests are blocked in **Waiting Approval**
> until a human security admin or manager decides.

---

## Quick start (Windows / any OS)

```bash
cd spsnet_project
pip install -r requirements.txt
python -m uvicorn app.main:app --port 8000
```

Open **http://localhost:8000** — interactive API docs at **http://localhost:8000/docs**.

The database (SQLite by default) is created and seeded automatically on first start:
6 demo users (one per role), 6 teams, SLA policies and 8 published KB articles.

| Role | Login | Password |
|---|---|---|
| Administrator | admin@spsnet.com | Admin@123 |
| Support Agent | agent@spsnet.com | Agent@123 |
| Security Admin | security@spsnet.com | Security@123 |
| Manager | manager@spsnet.com | Manager@123 |
| Employee | employee@spsnet.com | Employee@123 |
| Intern | intern@spsnet.com | Intern@123 |

AI features use **Groq** (`llama-3.3-70b-versatile`) — the key is already configured in
`.env`. Any OpenAI-compatible provider works by changing `XAI_BASE_URL` + `XAI_MODEL`
(e.g. OpenRouter `sk-or-...`, native xAI `xai-...`). If the AI API is ever unreachable
(network, credits, rate limits), deterministic fallbacks keep every flow working: keyword
triage still classifies and flags high-risk tickets, and chat serves the best-matching KB
article directly with a citation.

---

## Architecture — three intake pipelines, one ticket service

```
  EMAIL                      WEB FORM                   AI CHAT
  IMAP poller / simulator    POST /api/tickets          POST /api/chat/message
  (app/emailer.py)           source=portal_form         KB-grounded AI answer
  [SPS-YYYY-NNN] threading        |                     escalation -> ticket source=chat
        |                         |                          |
        +------------+------------+--------------------------+
                     v
        create_ticket_service()  (app/main.py — the ONLY intake pipeline)
          - ticket id SPS-YYYY-NNN     - SLA policy match (sla_due_at)
          - timeline event + audit log (channel-tagged)
          - ACK email to requester     - security input scan (secrets/injection)
          - async AI classification (category/priority/risk/team — agent overrides)
                     |
                     v
          high risk? -> status=waiting_approval + approval record
                        + approver emails  (AI can NEVER decide)
                     |
                     v
          Agent workspace: queue -> two-panel detail -> public/internal/email replies
          -> resolve (resolution note required, requester emailed)
```

**Email inbound:** if `IMAP_HOST` is set, a background thread polls the mailbox every
`EMAIL_POLL_SECONDS`. Without IMAP, **Admin → Email Center → "Simulate inbound email"**
feeds the *exact same* ingestion function (`ingest_inbound_email`). Threading: a
`[SPS-2026-042]` tag in the subject (or the In-Reply-To Message-ID) updates the existing
ticket; anything else creates a new one.

**Email outbound:** if `SMTP_HOST` is set, real SMTP is used. Either way, every message
(ACK, agent reply, status change, approval request/decision) is recorded in `email_threads`
(visible in Email Center → Outbox) and written as a branded `.eml` file to `/outbox`.

**AI chat:** answers come *only* from published KB articles injected into the Grok prompt
with citations; high-risk requests (admin/production access, phishing) trigger the
escalation CTA. Escalation pre-fills a ticket from an AI chat summary which the user
reviews before submitting; the chat transcript is linked to the ticket for agents.

## Project layout (11 source files, no build step)

```
app/main.py      FastAPI app: all REST routes, ticket service, approvals, audit, SLA monitor
app/models.py    SQLAlchemy models (tickets, events, approvals, audit_log, KB, ...) + seed
app/security.py  PBKDF2 passwords, HMAC JWT, RBAC dependencies, secret/injection scanning
app/ai.py        xAI Grok: classification, KB chat, summaries, draft replies (+ fallbacks)
app/emailer.py   SMTP outbound + dev outbox, IMAP poller, [SPS-ID] threading
static/          index.html + app.js + styles.css — SPS-branded single-page frontend
```

Runtime folders created automatically: `uploads/` (attachments, 10MB cap, extension
allow-list), `outbox/` (.eml copies), `securedesk.db` (SQLite).

## Configuration

All secrets live in `.env` (never committed — see `.env.example`). Key variables:

| Var | Purpose |
|---|---|
| `XAI_API_KEY`, `XAI_MODEL` | Grok AI (default `grok-3-mini`) |
| `JWT_SECRET_KEY` | session token signing — change for production |
| `DATABASE_URL` | `sqlite:///securedesk.db` or a PostgreSQL URL |
| `SMTP_*` / `IMAP_*` | real mail; blank = dev outbox + inbound simulator |
| `HELPDESK_EMAIL`, `APP_BASE_URL` | branding in outbound mail |

**Production:** point `DATABASE_URL` at PostgreSQL, set real SMTP/IMAP credentials and a
strong `JWT_SECRET_KEY`, then run behind a TLS reverse proxy (nginx/Caddy):
`python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2`.
A container is one `python:3.11-slim` image: `pip install -r requirements.txt` + the same command.

## Deploying for free ($0 total)

Recommended stack — every piece has a permanent free tier:

| Piece | Free service |
|---|---|
| App hosting | Render.com free Web Service (HTTPS included) |
| Database | Neon.tech free PostgreSQL (data persists forever) |
| Helpdesk mailbox | A Gmail account + App Password (IMAP + SMTP) |
| AI | Groq free tier (already configured) |

Steps:

1. **Database** — sign up at neon.tech, create a project, copy the connection string.
2. **Code** — push this folder to a GitHub repo (`.env` stays out via `.gitignore`).
   Uncomment `psycopg2-binary` in `requirements.txt`.
3. **Render** — New → Web Service → connect the repo.
   - Build command: `pip install -r requirements.txt`
   - Start command: `python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - Environment variables: everything from your `.env`, but set
     `DATABASE_URL=postgresql+psycopg2://...` (Neon string, add the `+psycopg2`),
     `APP_BASE_URL=https://<your-app>.onrender.com`, a fresh `JWT_SECRET_KEY`,
     and the Gmail IMAP/SMTP credentials.
4. Open `https://<your-app>.onrender.com` — tables are created and seeded automatically.

Free-tier caveats (fine for a capstone demo):
- Render free instances **sleep after ~15 min idle** (first request takes ~40s to wake;
  the IMAP poller pauses while asleep, so email tickets appear after the next visit
  wakes the app). Keep-alive pingers like UptimeRobot (also free) avoid this.
- The container disk is ephemeral: `uploads/` and `outbox/` reset on redeploy. Ticket
  data is safe in Neon. Use real SMTP so emails actually send instead of the dev outbox.
- Quick zero-setup alternative for a live demo from your own PC: run locally and expose
  it with a free tunnel — `cloudflared tunnel --url http://localhost:8000` (or ngrok) —
  then share the URL it prints. Set `APP_BASE_URL` to that URL so email links work.
- An always-on free option with persistent disk (SQLite works as-is): an Oracle Cloud
  "Always Free" VM — more setup (Linux server + nginx), but no sleeping and no DB service needed.

## Accounts & sign-in

- **Self sign-up** (`#/signup`): interns and employees can register themselves; staff roles
  are created by an administrator. Password policy enforced; welcome email sent.
- **Forgot / reset password** (`#/forgot`): emailed 1-hour HMAC reset link (no account
  enumeration — the response is identical whether or not the email exists). In dev mode the
  email is written to `outbox/`.
- **Sign in with Microsoft**: full OAuth2 + Microsoft Graph flow at
  `/api/auth/sso/callback`; enabled by setting `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`,
  `AZURE_TENANT_ID` in `.env` (per TRD, V1 ships local-auth-first; the button explains
  what's missing if SSO is not configured). First SSO sign-in auto-creates an employee account.
- **My Profile** (every role): edit name, department, phone; change password with current
  password verification. All changes audit-logged.

## Security

- RBAC enforced server-side on every endpoint (6 roles, FastAPI dependencies)
- PBKDF2-SHA256 password hashing (200k iterations); password policy on user creation
- HMAC-signed expiring session tokens; failed logins audited
- Input sanitization (script/event-handler stripping) on all user content
- Secret detection (AWS/xAI/GitHub keys, private keys, plaintext passwords) and injection
  pattern detection (SQLi/XSS/template) → `secret_detected` / `injection_attempt` audit events
- ORM-parameterized queries only; immutable `audit_log` and `ticket_events` (ORM guard)
- Approval decisions immutable once made; rejection reason mandatory
- Attachment limits: 10MB, extension allow-list, served only via authenticated endpoint

## Reviewer walkthrough (success criteria)

1. **Email journey** — login as `admin`, open **Email Center**, deliver the sample inbound
   email → note the ticket ID and the branded ACK in the Outbox. Login as `agent`
   (new browser tab/profile), open the ticket from the queue (✉ email badge), send an
   **Email Reply** → it appears in the Outbox. Back as admin, simulate a user reply with
   `[SPS-2026-XXX]` in the subject → same ticket, same timeline. Agent resolves with a note
   → resolution email sent.
2. **Form journey** — login as `employee`, **Submit Request** ("VM down", category cloud,
   attach a file) → confirmation page with big ticket ID + confirmation email. Agent works
   it from the queue (📋 form badge), AI suggestions visible, replies, resolves.
3. **Chat journey** — login as `intern`, **AI Chat**: ask *"How do I connect to the VPN?"*
   → KB-grounded answer with `✦ Source` citation, no ticket. Then ask *"I need admin access
   to production"* → escalation CTA → review the AI-prefilled ticket → submit. Ticket is
   **high risk / Waiting Approval**; agents are blocked from resolving it (try it — 409).
4. **Approval** — login as `security`, **Approvals** → review, Approve or Reject (reason
   required on reject) in the confirm modal → requester emailed, decision immutable.
5. **Audit** — as `security` or `admin`, **Audit Log**: filter by channel = email / chat /
   portal; export CSV. Secret test: submit a ticket containing `AKIA1234567890ABCDEF` →
   a `secret_detected` event appears.
6. **Reports** — login as `manager`, **Reports**: volume by channel/category, SLA
   compliance, high-risk requests this period, agent performance; export CSV.

---
*SPS Capstone Project — Software Productivity Strategists. UI per UXD-001 design system
(SPS Navy #1A4B8C, SPS Blue #2E75B6, Inter typography).*
