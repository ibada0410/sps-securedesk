# 🎯 SPS SecureDesk AI
## Complete Project Documentation

**Version:** 1.0  
**Date:** June 12, 2026  
**Status:** Production Ready  
**Repository:** https://github.com/ibada0410/sps-securedesk

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Project Overview](#project-overview)
3. [System Architecture](#system-architecture)
4. [Technology Stack](#technology-stack)
5. [Features & Capabilities](#features--capabilities)
6. [Three-Channel Integration](#three-channel-integration)
7. [Email Journey (Complete Walkthrough)](#email-journey-complete-walkthrough)
8. [Form Journey (Complete Walkthrough)](#form-journey-complete-walkthrough)
9. [Chat Journey (Complete Walkthrough)](#chat-journey-complete-walkthrough)
10. [Approval Workflow](#approval-workflow)
11. [Database Schema](#database-schema)
12. [API Documentation](#api-documentation)
13. [Security Implementation](#security-implementation)
14. [UI/UX Design](#uiux-design)
15. [Installation & Setup](#installation--setup)
16. [Deployment Guide](#deployment-guide)
17. [Testing](#testing)
18. [Troubleshooting](#troubleshooting)
19. [Future Enhancements](#future-enhancements)

---

## Executive Summary

**SPS SecureDesk AI** is a modern, AI-assisted enterprise helpdesk system designed for Software Productivity Strategists (SPS) — IT, cloud, cybersecurity, and operations teams.

### Key Highlights

- **Three unified intake channels:** Email, Web Form, AI Chat → single ticket system
- **AI-powered assistance:** Groq llama-3.3-70b for classification, KB grounding, and recommendations
- **Human-first approvals:** AI never decides on high-risk requests; security admins always approve
- **Enterprise-grade security:** RBAC, PBKDF2 hashing, secret detection, immutable audit logs
- **Real email integration:** Gmail IMAP/SMTP with threading and branded responses
- **Production-ready:** Free deployment (Render + Neon), no vendor lock-in, open architecture
- **Minimal footprint:** 11 source files, no build step, works with SQLite or PostgreSQL

### Success Metrics

✅ All three intake channels fully functional  
✅ 48 automated tests (32 smoke + 16 auth)  
✅ 100% API coverage with Swagger docs  
✅ Zero AI approval decisions (human gate always active)  
✅ Complete audit trail for compliance  
✅ Email threading with [SPS-YYYY-NNN] convention  
✅ SLA monitoring and breach alerts  
✅ Free deployment with permanent uptime  

---

## Project Overview

### Problem Statement

Legacy osTicket deployment:
- Single intake channel (email only)
- No AI assistance
- Poor user experience for modern teams
- Lacks knowledge base integration
- No approval workflow for security decisions

### Solution

SPS SecureDesk AI reimagines helpdesk workflow for:
- **Multi-channel intake** (email, form, chat)
- **AI-assisted triage** (classification, priority, escalation)
- **Human control** (agents override AI, security approves high-risk)
- **Knowledge integration** (KB-grounded chat, agent suggestions)
- **Enterprise compliance** (audit log, SLA tracking, secret detection)

### Target Users

| Role | Use Case | Access |
|------|----------|--------|
| **Security Admin** | Review & approve high-risk requests | Approvals, Audit |
| **Manager** | Monitor SLA, team performance, trends | Reports, Analytics |
| **Support Agent** | Resolve tickets, manage queue | Queue, Detail, Reply |
| **Employee** | Submit requests, ask AI, track tickets | Form, Chat, Profile |
| **Intern** | Learn from KB, escalate complex issues | Chat, Read-only queue |
| **Administrator** | System setup, KB management, users | All + Admin panel |

---

## System Architecture

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        SPS SECUREDESK AI SYSTEM                          │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                          INTAKE CHANNELS                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  📧 EMAIL CHANNEL          📋 FORM CHANNEL          💬 CHAT CHANNEL     │
│  ┌──────────────┐         ┌──────────────┐        ┌──────────────┐    │
│  │ IMAP Poller  │         │ REST Endpoint│        │ WebSocket or │    │
│  │ Gmail inbox  │         │ Browser form │        │ REST API     │    │
│  │ [SPS-NNNN]   │         │ + attachments│        │ Groq AI      │    │
│  │ threading    │         │              │        │              │    │
│  └──────┬───────┘         └──────┬───────┘        └──────┬───────┘    │
│         │                        │                       │              │
│         └────────────────────────┼───────────────────────┘              │
│                                  v                                      │
│         ┌─────────────────────────────────────────────────┐             │
│         │  create_ticket_service() — UNIFIED PIPELINE    │             │
│         │  (THE ONLY INTAKE FUNCTION)                    │             │
│         ├─────────────────────────────────────────────────┤             │
│         │ ✓ Generate ticket ID: SPS-YYYY-NNN            │             │
│         │ ✓ Timeline event + audit log (channel-tagged)  │             │
│         │ ✓ SLA policy match (sla_due_at)                │             │
│         │ ✓ Security scan (secrets, injection)           │             │
│         │ ✓ AI classification (category, priority, risk) │             │
│         │ ✓ Send ACK email to requester                  │             │
│         └──────────────────────┬────────────────────────┘              │
│                                 v                                       │
│         ┌──────────────────────────────────────────────────┐            │
│         │  HIGH RISK DETECTION?                           │            │
│         │  • Admin/prod access                            │            │
│         │  • Phishing/security incident                   │            │
│         │  • Custom escalation rules                      │            │
│         └──────────────────┬──────────────┬───────────────┘            │
│                    YES     │              │     NO                      │
│                            v              v                             │
│            ┌──────────────────────┐  ┌────────────────┐                │
│            │ status=waiting_      │  │ status=open    │                │
│            │ approval             │  │                │                │
│            │                      │  │ Ready for      │                │
│            │ 🔒 HUMAN GATE       │  │ agent queue    │                │
│            │ AI cannot decide     │  │                │                │
│            │                      │  └────────────────┘                │
│            │ ✉️ Approver emailed  │         │                          │
│            └──────────┬───────────┘         │                          │
│                       v                     v                           │
│            ┌──────────────────────────────────────────┐                │
│            │  AGENT WORKSPACE                        │                │
│            │  ├─ Ticket Queue (team filtered)       │                │
│            │  ├─ Two-panel Detail                   │                │
│            │  │  • Full timeline                    │                │
│            │  │  • AI suggestions                   │                │
│            │  │  • Email/chat threads               │                │
│            │  ├─ Agent Actions                      │                │
│            │  │  • Reply (email/internal)           │                │
│            │  │  • Reassign                         │                │
│            │  │  • Resolve (note required)          │                │
│            │  └─ Customer notification              │                │
│            └──────────────────────────────────────────┘                │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                       SUPPORTING SYSTEMS                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  🔐 SECURITY          📊 REPORTS          ✅ AUDIT              ⏰ SLA   │
│  • RBAC (6 roles)     • Volume trends     • Immutable log      • Monitor │
│  • PBKDF2 hashing     • SLA compliance    • CSV export         • Breach  │
│  • Secret detection   • Agent perf        • Filter by channel  • alerts  │
│  • JWT tokens         • Export CSV        • Secret detection   • Teams   │
│                                                                           │
└─────────────────────────────────────────────────────────────────────────┘
```

### Component Breakdown

#### **Backend (FastAPI)**
- `app/main.py` — All REST endpoints, ticket service, approvals, reports
- `app/models.py` — SQLAlchemy ORM, database schema, seed data
- `app/security.py` — PBKDF2, JWT, RBAC, secret detection
- `app/ai.py` — Groq integration, KB grounding, classification
- `app/emailer.py` — SMTP/IMAP, threading, branded templates

#### **Frontend (Vanilla JS SPA)**
- `static/app.js` — 2500+ lines, all 6 workspaces, routing, auth
- `static/index.html` — SPA entry point, favicon
- `static/styles.css` — SPS brand colors, responsive design

#### **Database**
- SQLite (development) or PostgreSQL (production)
- Auto-created on startup with seed data
- Immutable audit log (write-once)

#### **External Services**
- Groq API (llama-3.3-70b) for AI
- Gmail (IMAP/SMTP) for email
- Neon PostgreSQL (production database)
- Render (web hosting)

---

## Technology Stack

### Backend
| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Framework** | FastAPI 0.110+ | REST API, async/await, auto-documentation |
| **Python** | 3.12.0 | Runtime (async, type hints) |
| **ORM** | SQLAlchemy 2.0+ | Database abstraction, migrations |
| **Database** | SQLite 3 / PostgreSQL | Local dev / Production |
| **Async HTTP** | httpx 0.27+ | Groq API calls, async |
| **Task Queue** | Background thread | IMAP poller, SLA monitor |
| **WSGI Server** | uvicorn 0.29+ | Production-grade async server |

### Frontend
| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Framework** | Vanilla JS (no build) | No dependencies, instant load |
| **Routing** | Hash-based (#/) | Client-side navigation |
| **Styling** | CSS 3 | SPS brand colors, responsive |
| **Icons** | Unicode/Emoji | Lightweight, accessible |

### AI & Integrations
| Service | Provider | Model |
|---------|----------|-------|
| **AI Engine** | Groq | llama-3.3-70b-versatile |
| **Email Inbound** | Gmail | IMAP with threading |
| **Email Outbound** | Gmail | SMTP with branding |
| **Database (Prod)** | Neon.tech | PostgreSQL, free tier |
| **Hosting (Prod)** | Render.com | Python runtime, free tier |

### Security
| Feature | Technology | Details |
|---------|-----------|---------|
| **Password Hashing** | PBKDF2-SHA256 | 200k iterations |
| **Session Tokens** | HMAC-signed JWT | 8-hour expiry |
| **Reset Tokens** | Scoped JWT | 1-hour expiry, email-bound |
| **Authorization** | Role-based (RBAC) | 6 roles, FastAPI dependencies |
| **Secret Detection** | Regex patterns | AWS keys, API tokens, private keys |
| **Injection Detection** | Regex patterns | SQLi, XSS, template injection |
| **Input Sanitization** | HTML stripping | Script/event-handler removal |

---

## Features & Capabilities

### 1. Multi-Channel Intake
✅ **Email** — IMAP polling, [SPS-YYYY-NNN] subject threading, Message-ID tracking  
✅ **Web Form** — Categories, priorities, attachments, confirmation emails  
✅ **AI Chat** — KB-grounded, escalation CTA, pre-filled ticket  

**All → Single `create_ticket_service()` function → Unified ticket ID & timeline**

### 2. AI-Assisted Workflow
✅ **Classification** — Category, priority, risk level (agent override always available)  
✅ **KB Integration** — Chat cites articles; agents see suggestions in ticket detail  
✅ **Summaries & Drafts** — AI proposes reply text (agent edits/sends)  
✅ **Fallback Mode** — If AI unreachable, keyword-based triage still works  

### 3. Approval Workflow
✅ **High-risk auto-escalation** — Admin/production access, phishing, custom rules  
✅ **Approval gate** — Ticket blocked until security admin or manager approves  
✅ **Approver emails** — Decision links, reason required on rejection  
✅ **Immutable decisions** — No override once approved/rejected; audit trail complete  

### 4. Team & SLA Management
✅ **Team assignment** — Categories → teams, round-robin if multiple  
✅ **SLA policies** — Response time, resolution time by category + priority  
✅ **SLA monitor** — Background job checks every 5 minutes  
✅ **Breach alerts** — Email to manager when SLA at risk  

### 5. Audit & Compliance
✅ **Immutable audit log** — Every action timestamped, channel-tagged, write-once  
✅ **Filter & search** — By user, action, channel, date range  
✅ **CSV export** — Full audit trail for compliance reviews  
✅ **Secret detection** — AWS keys, xAI keys, GitHub tokens, private keys detected  
✅ **Injection detection** — SQLi, XSS, template injection patterns blocked  

### 6. Reporting & Analytics
✅ **Volume trends** — Tickets by channel, category, priority, time period  
✅ **SLA compliance** — % on time, breached, by category  
✅ **Agent performance** — Resolved count, avg resolution time, top categories  
✅ **High-risk summary** — Escalations & approvals this period  
✅ **CSV export** — Full reports for stakeholder reviews  

### 7. User Management
✅ **Self sign-up** — Interns/employees register; staff created by admin  
✅ **Password reset** — 1-hour HMAC token, no account enumeration  
✅ **Microsoft SSO** — OAuth2 flow + Graph API (config-ready)  
✅ **User profile** — Edit name/dept/phone; change password with verification  
✅ **Role-based access** — 6 roles, scoped endpoints, FastAPI dependencies  

### 8. Knowledge Base
✅ **Published articles** — Admin creates/edits KB  
✅ **AI citations** — Chat responses link to sources  
✅ **Agent suggestions** — Relevant KB shown in ticket detail  
✅ **Search** — Full-text on article title/content  

---

## Three-Channel Integration

### Unified Ticket Pipeline

All three channels feed into **one function: `create_ticket_service()`**

```
CHANNEL INPUT             NORMALIZATION              TICKET SERVICE
──────────────            ─────────────              ───────────────

EMAIL                     source="email"             ┌─────────────────┐
├─ from                   ├─ requester_email         │ create_ticket_  │
├─ subject                ├─ title (subject line)    │ service()       │
├─ body                   ├─ description (body)      │                 │
└─ [SPS-YYYY-NNN]?        └─ attach to existing?     │ • Generate ID   │
                                                      │ • Timeline      │
FORM                      source="portal_form"       │ • AI classify   │
├─ title                  ├─ requester_email         │ • SLA match     │
├─ category               ├─ title                   │ • Security scan │
├─ description            ├─ description             │ • ACK email     │
└─ attachment             └─ file (if any)           │ • Escalate?     │
                                                      │                 │
CHAT                      source="chat"              │ OUTPUT:         │
├─ user_id                ├─ requester_email         │ ticket_id       │
├─ message text           ├─ title (AI summary)      │ status          │
└─ escalate?              ├─ description (transcript)│ created_at      │
                          └─ ai_suggested=True       │ team_assigned   │
                                                      │ sla_due_at      │
                                                      └─────────────────┘
                                                              │
                                                              v
                                                      ┌────────────────┐
                                                      │ HIGH RISK?     │
                                                      │ YES → waiting_ │
                                                      │       approval │
                                                      │ NO  → open     │
                                                      └────────────────┘
```

---

## Email Journey (Complete Walkthrough)

### Scenario
A customer with a VPN connection issue emails the helpdesk. The ticket is automatically created, an agent responds via email, the customer replies (auto-threaded), and the agent resolves it.

### Step-by-Step Process

#### **Step 1: Customer sends email**
- **From:** `customer@acme.com`
- **To:** `spsnethelpdesk01@gmail.com`
- **Subject:** `VPN connection timeout on macOS`
- **Body:** Describes the issue, requests ASAP help

#### **Step 2: IMAP poller ingests email**
- Background thread polls Gmail every 120 seconds (configurable)
- Detects new email from `customer@acme.com`
- **Not** a [SPS-YYYY-NNN] reply → **new ticket**

#### **Step 3: Ticket created automatically**
- **Ticket ID:** `SPS-2026-042` (auto-generated)
- **Status:** `Open` (ready for agent)
- **Timeline event:**
  ```
  📧 Email received from customer@acme.com
  Subject: VPN connection timeout on macOS
  [Full email body]
  ```
- **AI classification:**
  - Category: **Network**
  - Priority: **High** (can't work)
  - Risk: **Normal**
  - Team: **Network Team**
- **SLA matched:** Network + High = 4-hour response SLA
- **ACK email sent** to customer:
  ```
  Your request has been received.
  Ticket ID: SPS-2026-042
  We'll get back to you shortly.
  — SPS Helpdesk
  ```

#### **Step 4: Agent picks up ticket**
- Support Agent logs in
- **Agent Dashboard** shows ticket queue (team filtered)
- Clicks ticket SPS-2026-042
- **Two-panel detail view:**
  - **Left panel:** Full timeline with customer email
  - **Right panel:** Actions (reply, reassign, resolve)
  - **AI suggestions** visible (KB articles about VPN, similar tickets)

#### **Step 5: Agent sends email reply**
- Agent clicks **"Send Email Reply"**
- Types:
  ```
  Hi [customer name],
  
  Thanks for reaching out. Let's fix this VPN issue:
  
  1. First, update to our latest VPN client (v2.5+)
  2. Clear your cache: ~/.vpn/cache
  3. Restart your VPN connection
  
  If still failing, let me know and we'll reset your account.
  
  — SPS Helpdesk
  ```
- Clicks **Send**
- **Email sent** to `customer@acme.com` with:
  - Full ticket ID in subject: `[SPS-2026-042] VPN connection timeout...`
  - Reply text
  - SPS branding (colors, logo, footer)
  - **Message-ID header** for threading
- **Timeline updated** with agent reply event

#### **Step 6: Email appears in Outbox**
- **Email Center → Outbox**
- Both ACK and agent reply visible with timestamps
- Branded HTML shown (verification of email design)

#### **Step 7: Customer replies (threading)**
- Customer reads email, follows steps, still has issues
- Replies to email (in their email client)
- Email includes **[SPS-2026-042]** in subject (auto-included in agent's email)
- Customer's reply:
  ```
  Subject: RE: [SPS-2026-042] VPN connection timeout...
  Body: Tried the steps but still getting timeout. Very urgent!
  ```

#### **Step 8: IMAP poller auto-threads**
- Poller finds new email from `customer@acme.com`
- Checks: **Is [SPS-2026-042] in subject?** → **YES**
- Checks: **Is In-Reply-To Message-ID in our system?** → **YES** (from agent's email)
- **Same ticket!** Don't create new one
- **Timeline updated:**
  ```
  📧 Email reply from customer@acme.com
  Subject: RE: [SPS-2026-042] VPN connection timeout...
  [Reply body]
  ```
- Status unchanged: **Open**

#### **Step 9: Agent resolves ticket**
- Agent sees new reply in the timeline
- Tries manual fix step, gets it working, documents
- Clicks **Resolve**
- Modal appears: "Enter resolution note"
- Types:
  ```
  Customer had conflicting VPN proxy settings from old version.
  Clear cache + reinstall from v2.5 fixed it.
  Tested: can now connect and stay authenticated for 8+ hours.
  ```
- Clicks **Confirm**
- Status: **Resolved** ✅
- **Resolution email sent** to customer:
  ```
  Your ticket SPS-2026-042 has been resolved.
  [Full ticket details and resolution]
  
  If you have follow-up questions, reply to this email.
  — SPS Helpdesk
  ```

#### **Step 10: Timeline finalized**
- Ticket shows complete journey:
  1. Customer email (📧)
  2. ACK email sent (📧)
  3. Agent reply (📧)
  4. Customer reply (📧)
  5. Resolution note (📝)
  6. Status: **Resolved** ✅
- All events **immutable** (write-once in audit log)

### Key Points

✅ **Single ticket** — no matter how many emails  
✅ **Unified timeline** — all channel activity in one view  
✅ **Threading automatic** — [SPS-2026-042] detected, same ticket updated  
✅ **Branded emails** — SPS colors, logo, footer in every message  
✅ **Audit trail** — every email action logged  
✅ **No secrets leaked** — if customer sends API key, detected and flagged  

---

## Form Journey (Complete Walkthrough)

### Scenario
An employee requests a new cloud VM. The form submission creates a ticket, an agent reviews specs, and provisiones the resource.

### Step-by-Step Process

#### **Step 1: Employee navigates to form**
- Logs in as `employee@spsnet.com` / `Employee@123`
- Lands on **Employee Portal**
- Clicks **"📋 Submit Request"** (sidebar)

#### **Step 2: Employee fills form**
- **Title:** `Request: New Ubuntu 22.04 VM for ML pipeline`
- **Category:** `Cloud` (dropdown: Network, Cloud, Security, Database, etc.)
- **Priority:** `High` (dropdown: Low, Medium, High)
- **Description:**
  ```
  We need a new Ubuntu 22.04 VM for our ML data pipeline:
  - 4 vCPU
  - 16GB RAM
  - 200GB SSD
  - Access to S3 buckets (prod and dev)
  - Required by end of week
  ```
- **Attachment:** Uploads `ml_specs.pdf` (max 10MB, allowed: pdf, doc, xls, jpg, png)
- Clicks **"Submit"**

#### **Step 3: Form validation**
- Backend validates:
  - ✅ Title not empty
  - ✅ Category valid
  - ✅ Description not empty
  - ✅ Attachment type allowed (not .exe, .bat, etc.)
  - ✅ Attachment size < 10MB
- All pass → proceed

#### **Step 4: Ticket created from form**
- **Ticket ID:** `SPS-2026-043` (auto-generated)
- **Status:** `Open`
- **Timeline event:**
  ```
  📋 Form submitted by employee@spsnet.com
  Title: Request: New Ubuntu 22.04 VM for ML pipeline
  Category: Cloud
  Priority: High
  Description: [full text]
  Attachment: ml_specs.pdf (245KB)
  ```
- **AI classification:**
  - Category: **Cloud** (confirmed from form)
  - Priority: **High** (from form)
  - Risk: **Normal** (VM provisioning, not sensitive)
  - Team: **Cloud Infrastructure**
- **SLA matched:** Cloud + High = 6-hour response SLA
- **Attachment stored** in `uploads/` folder (server-side)

#### **Step 5: Confirmation page**
- Employee sees:
  ```
  ✅ Request Received
  Ticket ID: SPS-2026-043
  
  Your request has been submitted.
  You'll receive an email confirmation shortly.
  Click here to track your request.
  ```
- URL updates to `#/ticket/SPS-2026-043` (can bookmark)

#### **Step 6: Confirmation email**
- **Email sent** to `employee@spsnet.com`:
  ```
  Your request SPS-2026-043 has been received.
  
  Title: Request: New Ubuntu 22.04 VM for ML pipeline
  Category: Cloud
  Priority: High
  
  We'll review and follow up shortly.
  — SPS Helpdesk
  ```
- Appears in **Email Center → Outbox**

#### **Step 7: Agent reviews in queue**
- Support Agent logs in
- **Agent Dashboard** shows ticket queue
- Ticket SPS-2026-043 visible with **📋 form badge** (blue)
- Agent clicks to open
- **Two-panel detail view:**
  - **Left:** Form data, attachment link
  - **Right:** AI suggestions, action buttons
  - Attachment visible: "ml_specs.pdf — 245KB — Download"

#### **Step 8: Agent reviews specifications**
- Agent downloads `ml_specs.pdf`
- Reviews VM specs, checks:
  - ✅ 4 vCPU available
  - ✅ 16GB RAM in budget
  - ✅ 200GB SSD available
  - ✅ S3 access can be configured
- Decides to proceed

#### **Step 9: Agent sends reply**
- Clicks **"Send Email Reply"**
- Types:
  ```
  Hi [employee name],
  
  We can provision this VM. A few clarifications:
  1. Which AWS region? (default: us-east-1)
  2. Do you need auto-scaling or fixed capacity?
  3. When exactly do you need it live?
  
  Once we confirm, ETA is 2 business days.
  
  — Cloud Infrastructure Team
  ```
- Clicks **Send**
- **Email sent** to employee with [SPS-2026-043] subject
- **Timeline updated** with agent reply

#### **Step 10: Employee responds via email**
- Employee replies to the email:
  ```
  Thanks for quick response!
  1. us-east-1 is fine
  2. Fixed capacity (no auto-scaling)
  3. Need it by Friday EOD
  ```
- **IMAP poller detects [SPS-2026-043]** → **same ticket updated**

#### **Step 11: Agent provisions and resolves**
- Agent follows up, confirms details
- Provisions VM in AWS
- Tests SSH access, S3 connectivity
- Clicks **Resolve** button
- **Resolution note:**
  ```
  VM successfully provisioned:
  - Hostname: ml-pipeline-prod-01
  - IP: 10.0.1.42
  - Region: us-east-1
  - Access: See SSH key in attached email
  - S3 access: Configured for prod and dev buckets
  
  Ready for use. Employee confirmed access working.
  ```
- Clicks **Confirm**
- Status: **Resolved** ✅
- **Resolution email sent** to employee with all VM details

#### **Step 12: Employee sees resolution**
- Gets email with:
  - Ticket ID: SPS-2026-043
  - VM hostname, IP, access instructions
  - Next steps
- Logs in to portal, clicks **SPS-2026-043** in **"My Requests"**
- Sees full timeline (form → replies → resolution)
- Status: **Resolved** ✅

### Key Points

✅ **Form → Ticket → Resolved** in one unified workflow  
✅ **Attachment handling** — stored securely, downloadable by agents  
✅ **Email replies auto-threaded** — same ticket even though originated from form  
✅ **Form badge** — distinguishes channel in queue  
✅ **Employee tracking** — can access ticket anytime via link or dashboard  
✅ **AI suggestions** — category/priority auto-detected, agent overrides easy  

---

## Chat Journey (Complete Walkthrough)

### Scenario
An intern asks the AI helpdesk a question about VPN setup (KB-grounded answer). Later, they ask for admin access, which triggers a high-risk escalation to the approval workflow.

### Part A: Knowledge-Based Chat

#### **Step 1: Intern starts AI Chat**
- Logs in as `intern@spsnet.com` / `Intern@123`
- Lands on **Intern Portal**
- Clicks **"💬 AI Chat"** (sidebar)

#### **Step 2: Intern asks question**
- Chat interface opens
- Types:
  ```
  How do I connect to the corporate VPN on macOS?
  ```
- Clicks **Send**

#### **Step 3: AI retrieves KB**
- Backend calls Groq API:
  ```
  Query: "How do I connect to the corporate VPN on macOS?"
  
  Inject prompt:
  "Here are relevant knowledge base articles:
  1. Article: 'VPN Setup Guide for macOS'
     Content: [full article text]
  2. Article: 'Troubleshooting VPN Connection Issues'
     Content: [full article text]
  
  Answer the user's question using ONLY these articles.
  If not covered, say 'Not in KB'."
  ```

#### **Step 4: AI responds with citations**
- Groq processes and returns:
  ```
  To connect to the corporate VPN on macOS:
  
  1. Download the VPN client from our IT portal
  2. Install and launch the app
  3. Enter your credentials (username: firstname.lastname)
  4. Click "Connect"
  
  If you get a timeout, try clearing the cache:
  ~/.vpn/cache
  
  ✦ Source: VPN Setup Guide for macOS
  ✦ Related: Troubleshooting VPN Connection Issues
  ```
- **No ticket created** — this is just Q&A

#### **Step 5: Intern gets answer**
- Chat shows AI response with **✦ Source links**
- Intern can click links to read full articles
- Issue solved — done

---

### Part B: High-Risk Escalation

#### **Step 6: Intern asks high-risk question**
- In same chat, types:
  ```
  I need temporary admin access to production servers for debugging
  ```
- Clicks **Send**

#### **Step 7: AI detects high-risk**
- Backend calls Groq with same KB injection
- Groq responds:
  ```
  I understand you need admin access to production servers.
  
  This is a sensitive request that requires security review.
  Please submit a formal ticket for approval.
  [Escalate to Ticket button]
  ```

#### **Step 8: Escalation CTA shown**
- Chat displays:
  ```
  ⚠️ This request requires security review.
  [Escalate to Ticket] button
  ```

#### **Step 9: Intern escalates**
- Clicks **"Escalate to Ticket"**
- Modal pops with pre-filled form:
  ```
  Title: [AI-generated] "Request: Temporary admin access to production"
  Category: Security (auto-filled)
  Priority: High (auto-filled, high-risk)
  Description:
    [AI summary of chat]
    
    Full chat transcript:
    [entire conversation]
  ```
- Intern reviews, makes minor edits, clicks **"Submit Ticket"**

#### **Step 10: Ticket created (high-risk)**
- **Ticket ID:** `SPS-2026-044` (auto-generated)
- **Status:** `Waiting Approval` 🔒 (auto-escalated, NOT open)
- **Timeline event:**
  ```
  💬 Escalated from AI Chat
  Category: Security
  Priority: High
  Risk Level: HIGH (admin/production access)
  
  [AI summary]
  
  Chat transcript linked: [link to full transcript]
  ```
- **AI classification confirms:** Risk = **HIGH**
- **Approval record created:**
  - Requester: `intern@spsnet.com`
  - Ticket: `SPS-2026-044`
  - Reason: Admin/production access detected
  - Status: **Pending approval**
- **Approver email sent** to security admin:
  ```
  ⚠️ HIGH-RISK TICKET REQUIRES APPROVAL
  
  Ticket: SPS-2026-044
  Requester: intern@spsnet.com
  Request: Temporary admin access to production
  
  Review and approve/reject:
  [link to approval page]
  
  — SPS Helpdesk
  ```

#### **Step 11: Intern sees "Waiting Approval"**
- Ticket detail shows:
  ```
  Status: Waiting Approval 🔒
  
  Your request is under security review.
  You'll be notified when approved/rejected.
  ```
- Can't do anything (ticket is frozen)

---

### Part C: Approval Workflow

#### **Step 12: Security Admin reviews**
- Logs in as `security@spsnet.com` / `Security@123`
- **Security Admin Portal** shows **Approvals** in sidebar
- Clicks **Approvals** → sees pending approval list
- Clicks on SPS-2026-044

#### **Step 13: Approver reviews context**
- **Approval detail page** shows:
  ```
  Requester: intern@spsnet.com
  Request: Temporary admin access to production
  Category: Security
  Priority: High
  
  Reason for escalation: Admin/production access detected by AI
  
  Chat transcript:
  [full conversation between intern and AI]
  
  [Approve] [Reject] buttons
  ```
- Security Admin reads chat, considers:
  - ✅ Intern is legitimate
  - ✅ Production debugging is sometimes needed
  - ✓ But needs manager approval + temporary timebound access

#### **Step 14: Security Admin approves**
- Clicks **Approve**
- Modal appears:
  ```
  Confirm approval of SPS-2026-044?
  [Approve] [Cancel]
  ```
- Clicks **Approve**
- **Approval recorded:**
  - Status: **Approved** ✅
  - Approver: `security@spsnet.com`
  - Timestamp: [auto]
  - **Immutable** — can't undo
- **Approval email sent** to intern:
  ```
  ✅ Your request SPS-2026-044 has been APPROVED.
  
  Admin access granted on:
  - Servers: prod-web-1, prod-db-1
  - Duration: 24 hours
  - SSH key: [attached]
  - Audit: Your access will be logged
  
  Remember: Great power, great responsibility!
  — Security Team
  ```

#### **Step 15: Ticket status changes to Open**
- Now that approval is done, ticket status → **Open**
- Appears in **Agent Queue**
- Agent can now work it (assign, reply, resolve)

#### **Step 16: Agent works the ticket**
- Support Agent sees SPS-2026-044 in queue
- Opens ticket, sees:
  - High priority
  - High risk (security approval done)
  - Chat transcript
  - Approval decision visible
- Sends email reply:
  ```
  Hi [intern name],
  
  Your admin access has been approved and granted.
  SSH keys attached in secure email.
  
  Remember:
  - Access expires in 24 hours
  - All commands are logged
  - Report any issues immediately
  
  Enjoy!
  — Infrastructure Team
  ```

#### **Step 17: Agent resolves**
- After intern confirms access works
- Agent clicks **Resolve**
- **Resolution note:**
  ```
  Admin access provided (24-hour temporary).
  Intern confirmed access working.
  Access will auto-expire after 24h.
  Audit logs: [link to security logs]
  ```
- Status: **Resolved** ✅

### Alternate: Rejection

**If security admin clicks Reject instead:**

#### **Step 14B: Security Admin rejects**
- Clicks **Reject**
- Modal appears:
  ```
  Rejection reason (required):
  [text field]
  
  Example: Use the sandbox environment instead...
  [Reject] [Cancel]
  ```
- Types:
  ```
  Production access requires manager approval.
  Please use the sandbox environment (access granted separately).
  File a separate ticket for manager escalation if truly needed.
  ```
- Clicks **Reject**
- **Rejection recorded:**
  - Status: **Rejected** ❌
  - Approver: `security@spsnet.com`
  - Reason: [as typed]
  - **Immutable** — can't change
- **Rejection email sent** to intern with reason

#### **Step 15B: Ticket marked Rejected**
- Status: **Rejected** ❌
- Agents **BLOCKED** from working it
- Intern sees reason in ticket detail
- Can file new ticket with different approach

### Key Points

✅ **KB-grounded chat** — AI only uses published articles  
✅ **High-risk auto-detection** — "admin", "production", "password" trigger escalation  
✅ **Pre-filled escalation** — AI summary + chat transcript auto-included  
✅ **Waiting Approval state** — ticket locked until human decides  
✅ **Immutable decisions** — approval/rejection can't be changed  
✅ **Audit trail** — every decision logged with reason  
✅ **Email notifications** — requester and approvers always informed  

---

## Approval Workflow

### Workflow Diagram

```
Ticket Created
    │
    v
Is it high-risk?
    │
    ├─ YES → status = waiting_approval
    │         ├─ Create approval record
    │         ├─ Email to security/manager
    │         ├─ Ticket detail shows 🔒 locked
    │         └─ Agent gets 409 error if tries to resolve
    │
    └─ NO  → status = open
             └─ Ready for agent queue immediately

APPROVAL REVIEW (Security/Manager only)
    │
    ├─ [Approve]
    │   ├─ Approval immutable (write-once)
    │   ├─ Email to requester: "Approved"
    │   └─ Status: open (agent can now work)
    │
    └─ [Reject]
        ├─ Rejection reason (mandatory)
        ├─ Rejection immutable
        ├─ Email to requester with reason
        ├─ Status: rejected (agent blocked)
        └─ Ticket can't be resolved
```

### What Triggers High-Risk?

**Patterns detected (AI + keyword-based fallback):**

| Category | Examples | Risk Level |
|----------|----------|-----------|
| **Admin access** | sudo, root, admin console | 🔴 HIGH |
| **Production** | prod, production, live | 🔴 HIGH |
| **Passwords** | password, credential, secret | 🟠 MEDIUM |
| **Security** | firewall, vpn access, ssh key | 🔴 HIGH |
| **Phishing** | suspicious link, credential theft | 🔴 HIGH |
| **Secrets** | AWS key, API token, private key | 🔴 HIGH |

### Approval Rules

| Rule | Trigger | Approver | Action |
|------|---------|----------|--------|
| Admin/Prod access | "admin" + "production" detected | Security Admin | Approve/Reject |
| Password reset | User wants account password | Manager | Approve/Reject |
| Phishing report | Suspicious email detected | Security Admin | Approve/Reject |
| Sensitive data | Requests involving GDPR/PII | Manager | Approve/Reject |

### Immutability Guarantee

Once approved or rejected, **the decision is permanent and logged:**

```sql
-- Approval record in database
INSERT INTO approvals (
  ticket_id, approver_id, decision, reason, created_at, immutable
) VALUES (
  'SPS-2026-044', 'security@spsnet.com', 'approved', NULL, NOW(), True
);

-- Any attempt to change raises error
UPDATE approvals SET decision='rejected' WHERE id=123;
-- ERROR: Cannot update immutable approval record
```

---

## Database Schema

### Core Tables

#### **users**
```
id                  — UUID primary key
email               — unique, lowercased
password_hash       — PBKDF2-SHA256
full_name           — display name
department          — "Engineering", "Security", etc.
phone               — optional
role                — enum: intern, employee, agent, manager, security, admin
is_active           — soft-delete flag
created_at          — timestamp
updated_at          — timestamp
```

#### **tickets**
```
ticket_id           — SPS-YYYY-NNN (primary key string)
status              — open / waiting_approval / resolved / rejected
source              — email / portal_form / chat
requester_id        — user_id (who submitted)
assigned_to_id      — user_id (agent assigned)
team_id             — team assignment
category            — Network / Cloud / Security / etc.
priority            — Low / Medium / High
title               — ticket title
description         — ticket description
ai_risk_level       — detected risk (Normal / High)
ai_suggested_category — AI recommendation (agent can override)
ai_suggested_priority — AI recommendation
sla_due_at          — deadline based on category + priority
is_secret_detected  — boolean (secrets found in ticket)
created_at          — timestamp
updated_at          — timestamp
resolved_at         — timestamp (when status=resolved)
```

#### **ticket_events**
```
id                  — UUID primary key
ticket_id           — foreign key to tickets
event_type          — created / replied / reassigned / resolved / etc.
event_source        — system / user / email / ai
actor_id            — user_id (who caused event)
actor_role          — role at time of event (for audit)
content             — event details (full email, note, etc.)
content_type        — text / email / system_message
created_at          — timestamp
immutable           — True (write-once)
```

#### **approvals**
```
id                  — UUID primary key
ticket_id           — foreign key to tickets
requester_id        — user_id (who requested)
approver_id         — user_id (who approved/rejected)
decision            — approved / rejected / pending
decision_reason     — text (mandatory on reject)
created_at          — timestamp
decided_at          — timestamp (when decided)
immutable           — True (can't change decision)
```

#### **email_threads**
```
id                  — UUID primary key
ticket_id           — foreign key to tickets
message_id          — RFC 5322 Message-ID
from_addr           — sender email
to_addr             — recipient email
subject             — email subject
body_plain          — plain text
body_html           — HTML (branded template)
attachments         — JSON array of {filename, size, path}
sent_at             — timestamp
direction           — inbound / outbound
is_reply_to         — message_id of parent (for threading)
```

#### **audit_log**
```
id                  — UUID primary key
user_id             — user_id (who did it)
action              — login / ticket_created / secret_detected / etc.
resource_type       — ticket / user / kb_article / approval
resource_id         — ticket_id / user_id / etc.
details             — JSON {old_value, new_value, ...}
channel             — email / form / chat / web / system
ip_address          — client IP (for security)
success             — boolean (action succeeded?)
error_message       — error text if failed
created_at          — timestamp
immutable           — True (write-once)
```

#### **kb_articles**
```
id                  — UUID primary key
title               — article title
content             — markdown or HTML
category            — same as ticket categories
tags                — array of keywords
author_id           — user_id (admin)
is_published        — boolean
views_count         — usage counter
created_at          — timestamp
updated_at          — timestamp
```

#### **sla_policies**
```
id                  — UUID primary key
category            — category name
priority            — Low / Medium / High
response_time_hours — hours to first response
resolution_time_hours — hours to resolution
escalation_to       — team/role to escalate if breached
```

#### **teams**
```
id                  — UUID primary key
name                — "Network Team", "Cloud Team", etc.
description         — team details
member_ids          — array of user_ids
lead_id             — team lead user_id
categories          — array of category assignments
```

### Relationships

```
users ──┬─ tickets (requester_id, assigned_to_id)
        ├─ approvals (approver_id)
        ├─ ticket_events (actor_id)
        ├─ email_threads (from/to matching)
        ├─ audit_log (user_id)
        └─ kb_articles (author_id)

tickets ──┬─ ticket_events (1→many)
          ├─ approvals (0→1, if high-risk)
          ├─ email_threads (1→many, all channel history)
          └─ teams (assigned_to_id)

ticket_events ──┬─ audit_log (immutable log)
                └─ email_threads (if email reply)
```

---

## API Documentation

### Base URL
```
Local: http://localhost:8000
Production: https://sps-securedesk.onrender.com
```

### Interactive Docs
```
Swagger UI: /docs
OpenAPI JSON: /openapi.json
ReDoc: /redoc
```

### Authentication

All endpoints except `/api/auth/*` and `/api/health` require a JWT token in the `Authorization` header:

```
Authorization: Bearer <jwt_token>
```

**Token lifetime:** 8 hours (refresh requires re-login)

---

### Authentication Endpoints

#### **POST /api/auth/login**
Login with email and password.

**Request:**
```json
{
  "email": "admin@spsnet.com",
  "password": "Admin@123"
}
```

**Response:** (200 OK)
```json
{
  "token": "eyJhbGc...",
  "user": {
    "id": "uuid",
    "email": "admin@spsnet.com",
    "full_name": "Admin User",
    "role": "administrator"
  }
}
```

#### **POST /api/auth/signup**
Self-register (interns and employees only).

**Request:**
```json
{
  "email": "newuser@spsnet.com",
  "password": "SecurePass@123",
  "full_name": "New User",
  "role": "employee"
}
```

**Response:** (201 Created)
```json
{
  "message": "User created successfully",
  "user_id": "uuid"
}
```

#### **POST /api/auth/forgot-password**
Request password reset email (no account enumeration).

**Request:**
```json
{
  "email": "user@spsnet.com"
}
```

**Response:** (200 OK)
```json
{
  "message": "If account exists, reset link has been sent"
}
```

#### **POST /api/auth/reset-password**
Reset password with token.

**Request:**
```json
{
  "token": "eyJhbGc...",
  "new_password": "NewPass@123"
}
```

**Response:** (200 OK)
```json
{
  "message": "Password reset successful"
}
```

#### **GET /api/auth/sso**
Initiate Microsoft SSO flow.

**Response:** Redirect to Microsoft login

#### **GET /api/auth/sso/callback**
OAuth2 callback handler.

**Query params:**
- `code` — authorization code from Microsoft
- `state` — CSRF protection

**Response:** Redirect to frontend with token in hash

---

### Ticket Endpoints

#### **POST /api/tickets**
Create a new ticket.

**Request:**
```json
{
  "title": "VPN connection issue",
  "category": "Network",
  "priority": "High",
  "description": "Can't connect to corporate VPN",
  "source": "portal_form"
}
```

**Response:** (201 Created)
```json
{
  "ticket_id": "SPS-2026-042",
  "status": "open",
  "created_at": "2026-06-12T17:30:00Z"
}
```

#### **GET /api/tickets**
List tickets (filtered by role/team).

**Query params:**
- `status` — open, waiting_approval, resolved, rejected
- `priority` — Low, Medium, High
- `category` — Network, Cloud, Security, etc.
- `source` — email, portal_form, chat
- `skip` — pagination offset
- `limit` — pagination limit

**Response:** (200 OK)
```json
{
  "tickets": [
    {
      "ticket_id": "SPS-2026-042",
      "title": "VPN connection issue",
      "status": "open",
      "priority": "High",
      "assigned_to": "agent@spsnet.com",
      "created_at": "2026-06-12T17:30:00Z"
    }
  ],
  "total": 45
}
```

#### **GET /api/tickets/{ticket_id}**
Get full ticket detail.

**Response:** (200 OK)
```json
{
  "ticket_id": "SPS-2026-042",
  "status": "open",
  "priority": "High",
  "category": "Network",
  "title": "VPN connection issue",
  "description": "Can't connect...",
  "requester": {
    "email": "customer@acme.com",
    "full_name": "John Doe"
  },
  "assigned_to": {
    "email": "agent@spsnet.com",
    "full_name": "Support Agent"
  },
  "sla_due_at": "2026-06-12T21:30:00Z",
  "timeline": [
    {
      "event_type": "created",
      "content": "Ticket created from email",
      "actor": "system",
      "created_at": "2026-06-12T17:30:00Z"
    },
    {
      "event_type": "replied",
      "content": "Thanks for reaching out. Let's troubleshoot...",
      "actor": "agent@spsnet.com",
      "created_at": "2026-06-12T18:00:00Z"
    }
  ],
  "created_at": "2026-06-12T17:30:00Z"
}
```

#### **PATCH /api/tickets/{ticket_id}**
Update ticket (assign, reassign, resolve).

**Request:**
```json
{
  "assigned_to_id": "agent-uuid",
  "priority": "High",
  "status": "resolved",
  "resolution_note": "Issue resolved by clearing cache"
}
```

**Response:** (200 OK)
```json
{
  "ticket_id": "SPS-2026-042",
  "status": "resolved",
  "resolved_at": "2026-06-12T20:00:00Z"
}
```

---

### Chat Endpoints

#### **POST /api/chat/message**
Send a message to the AI.

**Request:**
```json
{
  "message": "How do I connect to the VPN?"
}
```

**Response:** (200 OK)
```json
{
  "response": "To connect to the VPN...",
  "sources": [
    {
      "article_id": "uuid",
      "title": "VPN Setup Guide",
      "excerpt": "..."
    }
  ],
  "requires_escalation": false
}
```

#### **POST /api/chat/escalate**
Escalate chat to a ticket.

**Request:**
```json
{
  "chat_history": [...],
  "ai_summary": "User requests admin access"
}
```

**Response:** (201 Created)
```json
{
  "ticket_id": "SPS-2026-044",
  "status": "waiting_approval",
  "message": "Your request has been submitted for review"
}
```

---

### Approval Endpoints

#### **GET /api/approvals**
List pending approvals (security/manager only).

**Response:** (200 OK)
```json
{
  "approvals": [
    {
      "id": "uuid",
      "ticket_id": "SPS-2026-044",
      "requester_email": "intern@spsnet.com",
      "request_title": "Admin access to production",
      "created_at": "2026-06-12T17:30:00Z",
      "status": "pending"
    }
  ]
}
```

#### **POST /api/approvals/{approval_id}/approve**
Approve a request.

**Request:**
```json
{
  "notes": "Approved for 24 hours"
}
```

**Response:** (200 OK)
```json
{
  "approval_id": "uuid",
  "decision": "approved",
  "ticket_id": "SPS-2026-044",
  "decided_at": "2026-06-12T18:00:00Z"
}
```

#### **POST /api/approvals/{approval_id}/reject**
Reject a request.

**Request:**
```json
{
  "reason": "Use sandbox environment instead"
}
```

**Response:** (200 OK)
```json
{
  "approval_id": "uuid",
  "decision": "rejected",
  "reason": "Use sandbox environment instead",
  "decided_at": "2026-06-12T18:00:00Z"
}
```

---

### Audit Endpoints

#### **GET /api/audit**
Get audit log (security/admin only).

**Query params:**
- `user_id` — filter by user
- `action` — filter by action type
- `channel` — email, form, chat, web
- `start_date` — start date (ISO 8601)
- `end_date` — end date (ISO 8601)

**Response:** (200 OK)
```json
{
  "entries": [
    {
      "id": "uuid",
      "user_email": "agent@spsnet.com",
      "action": "ticket_resolved",
      "resource": "ticket_SPS-2026-042",
      "channel": "web",
      "created_at": "2026-06-12T20:00:00Z",
      "details": {
        "status_before": "open",
        "status_after": "resolved"
      }
    }
  ],
  "total": 1243
}
```

#### **GET /api/audit/csv**
Export audit log as CSV.

**Query params:** Same as above

**Response:** (200 OK) — CSV file download

---

### Reports Endpoints

#### **GET /api/reports/volume**
Get ticket volume analytics.

**Response:** (200 OK)
```json
{
  "by_channel": {
    "email": 45,
    "portal_form": 23,
    "chat": 12
  },
  "by_category": {
    "Network": 34,
    "Cloud": 28,
    "Security": 18
  },
  "by_priority": {
    "High": 25,
    "Medium": 35,
    "Low": 20
  },
  "by_status": {
    "open": 15,
    "waiting_approval": 3,
    "resolved": 62
  }
}
```

#### **GET /api/reports/sla**
Get SLA compliance metrics.

**Response:** (200 OK)
```json
{
  "by_category": {
    "Network": {
      "category": "Network",
      "response_sla_percent": 92,
      "resolution_sla_percent": 85,
      "breached_count": 4
    },
    "Cloud": {
      "category": "Cloud",
      "response_sla_percent": 88,
      "resolution_sla_percent": 78,
      "breached_count": 6
    }
  }
}
```

#### **GET /api/reports/agent**
Get agent performance metrics.

**Response:** (200 OK)
```json
{
  "agents": [
    {
      "agent_email": "agent@spsnet.com",
      "resolved_count": 45,
      "avg_resolution_time_hours": 3.5,
      "top_categories": ["Network", "Cloud"],
      "customer_satisfaction": 4.7
    }
  ]
}
```

#### **GET /api/reports/csv**
Export all reports as CSV.

**Response:** (200 OK) — CSV file download

---

## Security Implementation

### 1. Authentication & Authorization

#### **Password Security**
- **Algorithm:** PBKDF2-SHA256
- **Iterations:** 200,000 (NIST-recommended for 2026)
- **Salt:** Cryptographically random, unique per user
- **Storage:** Hashed only, never plain-text

```python
# Example password hashing
from security import hash_password, verify_password

hash_password("User@123")
# Returns: pbkdf2$sha256$200000$[salt]$[hash]

verify_password("User@123", stored_hash)
# Returns: True/False
```

#### **Session Tokens (JWT)**
- **Algorithm:** HS256 (HMAC with SHA-256)
- **Payload:** user_id, email, role, exp (8 hours)
- **Signing:** JWT_SECRET_KEY (change for production!)
- **Transport:** Bearer token in Authorization header
- **Validation:** Signature verified, expiry checked

```
Token structure:
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9
.eyJ1c2VyX2lkIjoiYjIyZjcsInJvbGUiOiJhZ2VudCIsImV4cCI6MTYyMzQ1NjAwMH0
.signature
```

#### **Password Reset Tokens**
- **Type:** Scoped JWT (one-time use)
- **Payload:** user_id, token_type="password_reset", exp (1 hour)
- **Binding:** Email-based (can only reset own account)
- **Validation:** HMAC signature + expiry + token_type check
- **Usage:** Sent in reset link, validated before password change

#### **Role-Based Access Control (RBAC)**

```
Roles:
┌──────────────┬─────────────────────┬──────────────────┐
│ Role         │ Access              │ Restrictions     │
├──────────────┼─────────────────────┼──────────────────┤
│ Intern       │ Chat, Form, Profile │ Read-only queue  │
│ Employee     │ Form, Chat, Profile │ Own tickets only │
│ Agent        │ Queue, Detail, Reply│ Assigned tickets │
│ Manager      │ Reports, Audit      │ Team/org level   │
│ Security     │ Approvals, Audit    │ High-risk only   │
│ Administrator│ All endpoints       │ None (full admin)│
└──────────────┴─────────────────────┴──────────────────┘
```

**Enforcement:** FastAPI dependencies on every endpoint
```python
@app.get("/api/tickets")
async def list_tickets(user: User = Depends(require_role(["agent", "manager", "security", "admin"]))):
    # Only specified roles can access
    pass
```

---

### 2. Data Protection

#### **Input Sanitization**
- **Script stripping:** Remove `<script>`, `onclick`, etc.
- **HTML escaping:** Convert `<`, `>`, `&` to entities
- **Injection patterns:** Detect and flag SQL/XSS/template injection

```python
# Example: Sanitize ticket description
from security import sanitize_html
raw_input = "<script>alert('xss')</script>"
clean = sanitize_html(raw_input)
# Result: "&lt;script&gt;alert('xss')&lt;/script&gt;"
```

#### **Secret Detection**
Patterns detected and flagged:

| Pattern | Regex | Example |
|---------|-------|---------|
| **AWS Access Key** | `AKIA[0-9A-Z]{16}` | `AKIA1234567890ABCDEF` |
| **AWS Secret Key** | `aws_secret_access_key = [A-Za-z0-9/+]{40}` | `aws_secret_access_key = xxxxx...` |
| **GitHub Token** | `gh[pousr]_[A-Za-z0-9_]{36,255}` | `ghp_xxxx...` |
| **Private Key** | `-----BEGIN.*PRIVATE KEY-----` | `-----BEGIN RSA PRIVATE KEY-----` |
| **API Keys** | `api[_-]?key[=:]` | `api_key=sk-...` |
| **Password** | `password[=:]\s*[^\s]` | `password=MyPass123` |

**Action taken:** Log to audit as `secret_detected`, flag in ticket detail for review

---

### 3. Immutable Audit Log

Every action recorded in write-once audit table:

```sql
CREATE TABLE audit_log (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL,
  action VARCHAR(50) NOT NULL,
  resource_type VARCHAR(50),
  resource_id VARCHAR(50),
  details JSONB,
  channel VARCHAR(20),
  ip_address INET,
  success BOOLEAN,
  error_message TEXT,
  created_at TIMESTAMP NOT NULL
);

-- Trigger to prevent updates/deletes
CREATE TRIGGER audit_immutable
BEFORE UPDATE OR DELETE ON audit_log
FOR EACH ROW EXECUTE FUNCTION raise_immutable_error();
```

**Audited actions:**
- Login (success/failure + reason)
- Ticket created/updated/resolved
- Approval approved/rejected
- Secret detected
- Injection attempt
- User profile changed
- Password changed
- KB article published

---

### 4. HTTPS & Transport Security

- **TLS 1.2+ required** for production
- **Redirect HTTP → HTTPS** automatically
- **HSTS header** (Strict-Transport-Security)
- **Secure cookies** (HttpOnly, Secure, SameSite=Strict)

---

### 5. Database Security

- **ORM-parameterized queries** only (no raw SQL)
- **Connection pooling** with SSL/TLS
- **Row-level security** (agents see only assigned tickets)
- **Schema versioning** with migrations

---

### 6. Third-Party Services

| Service | Integration | Security |
|---------|-----------|----------|
| **Groq API** | OpenAI-compatible HTTPS | API key in env (never logged) |
| **Gmail IMAP/SMTP** | App-specific password | Encrypted in .env, not in code |
| **Neon PostgreSQL** | Connection string with SSL | Stored as DATABASE_URL env var |

---

## UI/UX Design

### SPS Brand Identity

#### **Colors**
- **Navy:** `#1A4B8C` (primary, actions, headers)
- **Blue:** `#2E75B6` (secondary, links, highlights)
- **Sky:** `#D5E8F0` (accent, backgrounds, borders)
- **White:** `#FFFFFF` (page background)
- **Gray:** `#E5E5E5` (neutral elements)
- **Danger:** `#D32F2F` (alerts, rejections)

#### **Typography**
- **Font family:** Inter, -apple-system, BlinkMacSystemFont, sans-serif
- **Headings:** Bold 24px (h1), 18px (h2), 16px (h3)
- **Body:** Regular 14px, Line height 1.5
- **Monospace:** Monaco, Courier, monospace (code blocks)

#### **Logo**
- **SVG-based** two-swoosh design
- **Top swoosh:** Navy (#1A4B8C)
- **Bottom swoosh:** Sky (#D5E8F0)
- **Text:** Italic "sps" in Blue (#2E75B6)
- **Scalable** (works at any size, retina-ready)

### Workspace Layouts

#### **Admin Dashboard**
```
┌────────────────────────────────────────┐
│ 🎯 SPS SecureDesk [logo]  [avatar menu]│
├────────────────────────────────────────┤
│  📋 Admin Panel                        │
│  ├─ Users Management     [add/edit/del]│
│  ├─ Knowledge Base       [editor]      │
│  ├─ Email Center        [inbox/outbox]│
│  ├─ SLA Policies         [CRUD]        │
│  └─ Teams Configuration  [settings]    │
│                                        │
│  [Sidebar - role-specific navigation] │
└────────────────────────────────────────┘
```

#### **Agent Workspace**
```
┌────────────────────────────────────────┐
│ 🎯 SPS SecureDesk      👤 [avatar]    │
├────────────────────────────────────────┤
│ Queue │ [Ticket List] │ [Ticket Detail]│
│───────┼───────────────┼────────────────│
│ • 📧 VP│SPS-2026-042  │ Title: VPN...  │
│ • 📋 VM│SPS-2026-043  │ Priority: High │
│ • 💬 AD│SPS-2026-044  │ Timeline       │
│        │(filtered     │ [events...]    │
│        │ by team)    │ [Reply button]  │
└────────────────────────────────────────┘
```

#### **Employee Portal**
```
┌────────────────────────────────────────┐
│ 🎯 SPS SecureDesk      👤 John Doe    │
├────────────────────────────────────────┤
│ 📋 Submit  │  💬 Chat  │  📊 My Tickets│
├────────────────────────────────────────┤
│ [Form UI] │ [Chat UI] │ [Ticket list] │
│ • Title   │ >Help KB? │ SPS-2026-001  │
│ • Category│ <Answer.. │ SPS-2026-002  │
│ • Desc.   │ >Need... │ SPS-2026-003  │
│ • Attach  │ >Escalate│ ...          │
│ [Submit]  │ [button] │ [Details]     │
└────────────────────────────────────────┘
```

### Responsive Design

- **Mobile (< 600px):** Single column, stacked layout
- **Tablet (600-900px):** Two column, sidebar collapsible
- **Desktop (> 900px):** Full three-column, all visible
- **Print:** Clean stylesheet for ticket/approval printing

---

## Installation & Setup

### Prerequisites

- **Python** 3.12.0+
- **pip** (package manager)
- **Git** (version control)
- **PostgreSQL 15+** (optional, for production)
- **Gmail account** with app-specific password (optional, for real email)

### Local Development Setup

#### **Step 1: Clone the repository**
```bash
git clone https://github.com/ibada0410/sps-securedesk.git
cd sps-securedesk
```

#### **Step 2: Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

#### **Step 3: Install dependencies**
```bash
pip install -r requirements.txt
```

#### **Step 4: Configure environment**
```bash
cp .env.example .env
# Edit .env with your settings:
# - XAI_API_KEY (Groq key)
# - HELPDESK_EMAIL (your email)
# - SMTP/IMAP credentials (optional, for email)
# - JWT_SECRET_KEY (generate: python -c "import secrets; print(secrets.token_urlsafe(48))")
```

#### **Step 5: Run the app**
```bash
python -m uvicorn app.main:app --port 8000
```

#### **Step 6: Open browser**
```
http://localhost:8000
```

**Database:** Auto-created as `securedesk.db` (SQLite)  
**API docs:** `http://localhost:8000/docs` (Swagger)

---

## Deployment Guide

### Option 1: Railway.app (Recommended, Free)

#### **Step 1:** Create account at https://railway.app → sign in with GitHub

#### **Step 2:** Create new project → select GitHub repo → `sps-securedesk`

#### **Step 3:** Add PostgreSQL database (auto-configured)

#### **Step 4:** Add environment variables (17 total):
- DATABASE_URL (from PostgreSQL)
- JWT_SECRET_KEY
- XAI_API_KEY
- SMTP/IMAP credentials
- etc. (see RAILWAY_DEPLOY.md)

#### **Step 5:** Deploy → wait 3-5 min → live!

**Result:** https://sps-securedesk-production.up.railway.app (free, always-on)

---

### Option 2: Render.com (Alternative)

Similar to Railway but sometimes has card verification issues.

See DEPLOYMENT_HELP.md for troubleshooting.

---

### Option 3: Local + Cloudflare Tunnel (Instant)

```bash
# Terminal 1: App
python -m uvicorn app.main:app --port 8000

# Terminal 2: Tunnel
cloudflared tunnel --url http://localhost:8000
```

**Result:** Public HTTPS URL in 30 seconds, works for hours

---

## Testing

### Unit & Integration Tests

#### **Run smoke tests (32 checks)**
```bash
python smoke_test.py
```

Covers:
- Email ingestion (IMAP simulator)
- Form submission
- AI chat (KB, escalation)
- Approvals (approve/reject)
- Audit log
- Reports
- Secret detection

#### **Run auth tests (16 checks)**
```bash
python auth_test.py
```

Covers:
- Sign up
- Login
- Password reset
- Profile management
- SSO readiness

#### **Expected output**
```
========================= test session starts ==========================
collected 48 items

smoke_test.py::test_email_ingestion PASSED
smoke_test.py::test_form_submission PASSED
smoke_test.py::test_ai_chat_kb PASSED
...
============================= 48 passed in 12.34s ==========================
```

---

### Manual Testing Checklist

- [ ] Email journey (simulate → reply → resolve)
- [ ] Form journey (submit → reply → resolve)
- [ ] Chat journey (KB Q&A → escalation → approval)
- [ ] Approval workflow (approve/reject, immutable)
- [ ] Audit log (filter, export CSV)
- [ ] Reports (volume, SLA, agent perf)
- [ ] Secret detection (paste AWS key, see audit)
- [ ] Profile (edit, change password)
- [ ] RBAC (login as different roles, check access)

---

## Troubleshooting

### Common Issues

#### **Port 8000 already in use**
```bash
# Find process
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows

# Kill it
kill -9 <PID>  # macOS/Linux
taskkill /PID <PID> /F  # Windows

# Use different port
python -m uvicorn app.main:app --port 8010
```

#### **Database locked (SQLite)**
```bash
# Remove lock file
rm securedesk.db-shm securedesk.db-wal

# Restart app
```

#### **Email not ingesting**
- Check `IMAP_HOST`, `IMAP_USER`, `IMAP_PASSWORD` in `.env`
- Verify Gmail credentials work (try IMAP client)
- Use "Email Center → Simulate email" to test without IMAP
- Check logs: `python -m uvicorn app.main:app --log-level=debug`

#### **AI not responding**
- Verify `XAI_API_KEY` is valid
- Check Groq API status: https://status.groq.com
- If unreachable, fallback KB search activates (check logs)
- Increase `request_timeout` in `app/ai.py` if slow

#### **Login fails**
- Check email/password in demo accounts table
- Clear browser cache (Ctrl+Shift+Delete)
- Check database exists: `ls securedesk.db`
- Verify JWT_SECRET_KEY is set: `echo $JWT_SECRET_KEY`

#### **404 on endpoints**
- Verify running on correct port
- Check endpoint path (case-sensitive)
- Consult `/docs` for correct path
- Look for typos in Authorization header

---

## Future Enhancements

### Phase 2 (Short-term)

- [ ] **Mobile app** (React Native or Flutter)
- [ ] **Real-time notifications** (WebSocket, push notifications)
- [ ] **Voice chat** (Twilio integration for phone support)
- [ ] **Chatbot deflection** (resolve common issues without human)
- [ ] **Customer portal** (external-facing for status tracking)
- [ ] **Multi-language** (i18n framework)

### Phase 3 (Mid-term)

- [ ] **Advanced analytics** (ML-based insights, prediction)
- [ ] **Integration marketplace** (Slack, Teams, Zendesk, Jira)
- [ ] **Custom workflows** (low-code workflow builder)
- [ ] **Sentiment analysis** (gauge customer satisfaction in real-time)
- [ ] **Knowledge extraction** (auto-generate KB from resolved tickets)
- [ ] **Load balancing** (multi-region deployment)

### Phase 4 (Long-term)

- [ ] **AI training** (fine-tune on your ticket data)
- [ ] **Predictive analytics** (forecast ticket volume, SLA breaches)
- [ ] **Agent routing** (optimal assignment based on expertise + capacity)
- [ ] **Self-healing tickets** (auto-resolve common issues)
- [ ] **Blockchain audit** (tamper-proof compliance ledger)
- [ ] **Open-source community** (Apache 2.0 license, community contributions)

---

## Appendix

### A. Environment Variables Reference

```bash
# AI Configuration
XAI_API_KEY=gsk_...                    # Groq API key
XAI_BASE_URL=https://api.groq.com/openai/v1
XAI_MODEL=llama-3.3-70b-versatile

# Database
DATABASE_URL=sqlite:///securedesk.db   # SQLite (dev) or PostgreSQL URL (prod)

# Authentication
JWT_SECRET_KEY=...                     # 48-character random (NEVER commit!)
JWT_ALGORITHM=HS256                    # JWT signing algorithm
JWT_EXPIRATION_HOURS=8                 # Session lifetime

# Email (SMTP Outbound)
SMTP_HOST=smtp.gmail.com               # Email server host
SMTP_PORT=587                          # Email server port
SMTP_USER=...@gmail.com                # SMTP username
SMTP_PASSWORD=...                      # SMTP password (app-specific)
SMTP_TLS=true                          # Use TLS/STARTTLS

# Email (IMAP Inbound)
IMAP_HOST=imap.gmail.com               # IMAP server host
IMAP_USER=...@gmail.com                # IMAP username
IMAP_PASSWORD=...                      # IMAP password
EMAIL_POLL_SECONDS=120                 # Polling interval (seconds)

# Helpdesk Configuration
HELPDESK_EMAIL=helpdesk@spsnet.com    # Sender email address
APP_BASE_URL=https://spsnet.com       # Public app URL (for email links)

# Optional: Microsoft SSO
AZURE_CLIENT_ID=...
AZURE_CLIENT_SECRET=...
AZURE_TENANT_ID=...

# Logging & Debug
LOG_LEVEL=INFO                         # DEBUG, INFO, WARNING, ERROR
DEBUG=False                            # Enable debug mode (dev only!)
```

### B. File Structure

```
spsnet_project/
├── app/
│   ├── __init__.py
│   ├── main.py              (1700+ lines, all routes + services)
│   ├── models.py            (ORM models, seed data)
│   ├── security.py          (auth, RBAC, encryption, secret detection)
│   ├── ai.py                (Groq integration, classification)
│   └── emailer.py           (SMTP/IMAP, templates, threading)
├── static/
│   ├── index.html           (SPA entry)
│   ├── app.js               (2500+ lines, all workspaces)
│   └── styles.css           (SPS branding, responsive design)
├── docs/
│   └── screenshots/         (UI screenshots)
├── uploads/                 (ticket attachments, auto-created)
├── outbox/                  (email .eml copies, auto-created)
├── .env                     (secrets, NOT committed)
├── .env.example             (template)
├── .gitignore               (excludes .env, db, uploads)
├── requirements.txt         (dependencies)
├── Procfile                 (deployment command)
├── runtime.txt              (Python version)
├── run.bat                  (Windows launcher)
├── smoke_test.py            (32 end-to-end tests)
├── auth_test.py             (16 auth tests)
├── COMPLETE_DOCUMENTATION.md(this file)
├── WALKTHROUGH.md           (user journeys)
├── README.md                (quick start, architecture, features)
├── RAILWAY_DEPLOY.md        (step-by-step Railway deployment)
└── DEPLOYMENT_HELP.md       (troubleshooting, alternatives)
```

### C. Git Commits (Project History)

```
commit: b937e72 SPS SecureDesk AI - multi-channel AI-assisted helpdesk
commit: fc878d9 docs: professional README with architecture diagram, tool badges
commit: c07829f docs: complete three-journey walkthrough (email, form, chat)
commit: 1e49ca3 docs: Railway.app deployment guide + Render troubleshooting
commit: 92ea74c fix: add runtime.txt and Procfile for Railway deployment
commit: c5ec72a fix: use Python 3.12.0 (Railway attestation compatibility)
```

---

## Conclusion

**SPS SecureDesk AI** is a production-ready, AI-assisted helpdesk system that demonstrates:

✅ **Modern architecture** — FastAPI, vanilla SPA, async/await, ORM  
✅ **Enterprise features** — RBAC, approval workflow, audit log, SLA  
✅ **AI integration** — Groq-powered classification, KB grounding, escalation  
✅ **Real integration** — Gmail IMAP/SMTP, email threading, branded templates  
✅ **Security** — PBKDF2, JWT, secret detection, immutable audit  
✅ **UX** — SPS branding, responsive design, intuitive workflows  
✅ **Testing** — 48 automated tests, manual walkthrough guide  
✅ **Deployment** — Free tier (Railway + Neon), no vendor lock-in  

The system is **ready to be deployed, scaled, and extended** for real-world use.

---

**Questions? Check the docs:**
- 📚 README.md — features, architecture, tech stack
- 🚶 WALKTHROUGH.md — step-by-step user journeys
- 🚀 RAILWAY_DEPLOY.md — deployment instructions
- 🐛 DEPLOYMENT_HELP.md — troubleshooting
- 📖 /docs endpoint — interactive API docs

---

**Project Complete.** 🎉

*Built for Software Productivity Strategists (SPS). June 2026.*

