# 🎯 SPS SecureDesk AI — Complete Walkthrough

This guide walks you through **all three intake channels** (Email, Form, Chat) showing how tickets are created, processed, approved, and resolved.

**Prerequisites:** App running at `http://localhost:8000` (or your deployed URL)

---

## 🚀 Quick Setup

```bash
python -m uvicorn app.main:app --port 8000
```

Open **http://localhost:8000** in your browser.

---

## 1️⃣ EMAIL JOURNEY

### Scenario
A support agent receives an inbound email from a customer about a VPN connection issue. The email is automatically ingested, a ticket is created, the agent replies, and the customer sees the response.

### Step-by-step

#### **Step 1a: Log in as Admin (prepare email)**
- Go to **http://localhost:8000**
- Click **Sign In**
- Email: `admin@spsnet.com` | Password: `Admin@123`
- You land in the **Admin Dashboard**

#### **Step 1b: Simulate inbound email (no IMAP needed for this demo)**
- Click **Email Center** (left sidebar)
- Scroll to **"Simulate inbound email"** section
- Fill the form:
  - **From:** `customer@acme.com`
  - **Subject:** `VPN connection timeout on macOS`
  - **Body:**
    ```
    Hi SPS Helpdesk,
    
    I've been unable to connect to the corporate VPN for the past 2 hours.
    When I try to authenticate, I get "timeout" error.
    
    Our team is blocked and needs this resolved ASAP.
    
    Thanks,
    John
    ```
  - Leave **attachments** blank for now
- Click **Simulate email** (orange button)
- ✅ **Expected result:** Message says "Email ingested. New ticket created."

#### **Step 1c: Check the ticket was created**
- You see a confirmation with **ticket ID** (e.g., `SPS-2026-042`)
- Click the ticket ID or go to **Tickets** (sidebar)
- Open the ticket → you see:
  - Full email from customer in the timeline
  - ✉️ **Email badge** (orange)
  - Automatic **ACK email** sent to `customer@acme.com` (check **Outbox**)
  - AI classification: category (likely **Network**), priority, team assignment
  - Status: **Open** (ready for agent)

#### **Step 1d: Log in as Support Agent (in a new browser tab)**
- Open a **new tab** or **private window**
- Go to **http://localhost:8000**
- Email: `agent@spsnet.com` | Password: `Agent@123`
- You land in the **Agent Dashboard** (ticket queue)

#### **Step 1e: Agent picks up the ticket**
- You see the ticket queue filtered by your assigned team
- Find the ticket with the VPN issue (most recent, ✉️ email badge)
- Click to open the **ticket detail**
- Two-panel view:
  - **Left:** timeline (customer email, AI suggestions)
  - **Right:** agent actions (reply, reassign, resolve)

#### **Step 1f: Agent sends an email reply**
- In the **Email** section of the right panel, click **"Send Email Reply"**
- Type a response:
  ```
  Hi John,
  
  Thanks for reaching out. Let's troubleshoot this:
  
  1. Are you using the latest VPN client? (v2.5+)
  2. Try clearing your local cache: ~/.vpn/cache
  3. If still failing, let me know and we'll reset your VPN account
  
  — SPS Helpdesk
  ```
- Click **Send**
- ✅ **Expected result:** Reply appears in timeline, email sent to customer

#### **Step 1g: Back as Admin — verify email in Outbox**
- Switch back to Admin tab
- Click **Email Center** → **Outbox**
- You see:
  - **ACK email** (timestamp when customer emailed)
  - **Agent reply** (just now)
  - Both are branded with SPS colors, footer with helpdesk email

#### **Step 1h: Simulate customer reply (closes the loop)**
- Back in **Email Center** → **Simulate inbound email**
- From: `customer@acme.com`
- Subject: `RE: VPN connection timeout on macOS` (NOTE: uses RE: to trigger threading)
- Body:
  ```
  Perfect! Clearing the cache worked. We're back online.
  
  Thanks for the fast support!
  ```
- Click **Simulate email**
- ✅ **Expected result:** **Same ticket** (SPS-2026-042) gets a new event — email threading works!

#### **Step 1i: Agent resolves the ticket**
- Back as Agent, refresh the ticket
- New customer reply is in the timeline
- Click **Resolve** button
- Enter resolution note: `Customer cleared VPN cache per our suggestion. Issue resolved.`
- Click **Confirm**
- Status changes to **Resolved** ✅
- **Resolution email** sent to customer with full ticket details

---

## 2️⃣ FORM JOURNEY

### Scenario
An employee submits a request form to request a new cloud VM. The form creates a ticket, an agent picks it up, and resolves it.

### Step-by-step

#### **Step 2a: Log in as Employee**
- Open a **new tab**
- Go to **http://localhost:8000**
- Email: `employee@spsnet.com` | Password: `Employee@123`
- You land in the **Employee Portal**

#### **Step 2b: Submit a request form**
- Click **Submit Request** (or **📋 Submit** in sidebar)
- Fill the form:
  - **Title:** `Request: New Ubuntu 22.04 VM for ML pipeline`
  - **Category:** Cloud (dropdown)
  - **Priority:** High
  - **Description:**
    ```
    We need a new Ubuntu VM for our ML data pipeline:
    - 4 vCPU
    - 16GB RAM
    - 200GB SSD
    - Access to S3 buckets (prod and dev)
    
    Timeline: needed by end of week
    ```
  - **Attachment** (optional): pick any file (`.txt`, `.pdf`, or image)
- Click **Submit**
- ✅ **Expected result:** Confirmation page with:
  - **Big ticket ID** (e.g., `SPS-2026-043`)
  - Confirmation message: "Your request has been received"
  - Confirmation email sent to your inbox (check **Email Center → Outbox**)

#### **Step 2c: See the ticket in the queue (as Agent)**
- Switch to Agent tab (or log in again in new tab as `agent@spsnet.com`)
- Agent Dashboard shows the new ticket
- 📋 **Form badge** (blue) indicates it came from the form
- Click to open
- You see:
  - Original form data in timeline
  - If you uploaded an attachment, it's in the **Attachments** section
  - AI suggestions for category, priority, team

#### **Step 2d: Agent reviews and replies**
- Click **Send Email Reply** or **Internal Note** (if just for team)
- Example reply:
  ```
  Hi there,
  
  We can provision this VM. Quick questions:
  1. Which AWS region? (us-east-1 is default)
  2. Do you need auto-scaling enabled?
  
  ETA: 2 business days once we confirm above.
  ```
- Click **Send** → email goes to the requester

#### **Step 2e: Agent resolves the ticket**
- After the customer replies (simulate another email or just proceed), click **Resolve**
- Resolution note:
  ```
  VM provisioned in AWS us-east-1:
  - IP: 10.0.1.42
  - Hostname: ml-pipeline-prod-01
  - Access details: see email
  
  Completed and tested.
  ```
- Click **Confirm**
- Status: **Resolved** ✅
- Employee gets a final email with the resolution

---

## 3️⃣ CHAT JOURNEY (with escalation)

### Scenario
An intern asks the AI helpdesk about VPN setup. The AI provides a KB-grounded answer. Then the intern asks for admin access, which triggers an escalation to a security review.

### Step-by-step

#### **Step 3a: Log in as Intern**
- Open a new tab
- Go to **http://localhost:8000**
- Email: `intern@spsnet.com` | Password: `Intern@123`
- You land in the **Intern Portal**

#### **Step 3b: Start AI Chat (knowledge-based question)**
- Click **AI Chat** (or 💬 Chat in sidebar)
- Type a question:
  ```
  How do I connect to the corporate VPN on macOS?
  ```
- Press **Send**
- ✅ **Expected result:** AI responds with:
  - A helpful answer (KB-grounded from the published articles)
  - **✦ Source** link(s) showing which KB articles were cited
  - **No ticket created** (this is just a Q&A)

#### **Step 3c: Ask a high-risk question (escalation)**
- In the same chat, ask:
  ```
  I need temporary admin access to production servers for debugging
  ```
- Press **Send**
- ✅ **Expected result:** AI detects this is **high-risk** (admin/production access) and shows:
  - **Escalation message:** "This request requires security review. Please submit a formal ticket."
  - **"Escalate to Ticket"** button
  - A pre-filled form with your AI summary

#### **Step 3d: Review and submit escalation**
- Click **"Escalate to Ticket"**
- A form pops up with:
  - Auto-filled title (from your question)
  - Auto-filled description (summary of the chat)
  - Category: **Security** (auto-filled)
  - Priority: **High** (auto-filled because it's high-risk)
  - **Chat transcript linked** (agents can read the full conversation)
- Review the text, make any edits, click **Submit Ticket**
- ✅ **Expected result:** Ticket created with:
  - 📋 **Chat badge** (magenta)
  - Status: **Waiting Approval** 🔒 (auto-escalated because it's high-risk)
  - Approval request email sent to security admin

---

## 4️⃣ APPROVAL WORKFLOW (high-risk)

### Scenario
The high-risk escalation from Step 3d now goes to the security admin for approval.

### Step-by-step

#### **Step 4a: Security Admin sees approval request**
- Log in as `security@spsnet.com` | Password: `Security@123`
- You land in the **Security Admin Portal**
- Click **Approvals** (sidebar)
- You see a list of pending approvals (our prod access request is here)

#### **Step 4b: Review the request**
- Click on the approval record
- You see:
  - Full ticket details and chat transcript
  - Requester info (intern)
  - Risk assessment (AI flagged as high-risk: "production access")
  - Reason for escalation
  - **Approve** and **Reject** buttons

#### **Step 4c: Approve the request**
- Read the chat context
- Click **Approve**
- A modal asks: "Confirm approval?"
- Click **Confirm**
- ✅ **Expected result:**
  - Status changes to **Open** (now agents can work it)
  - Approval email sent to the intern: "Your admin access request has been approved..."
  - Security team gets an audit entry

#### **Step 4d: Agent now can work the ticket**
- Log in as Agent
- The ticket is now in the queue (status: **Open**)
- Agent reviews and sends: "We've granted you sudo access on prod-web-1 and prod-db-1. Please see SSH key in email."
- Agent resolves the ticket

#### **Alternate: Reject the request**
- If security admin clicks **Reject** instead:
  - Modal asks for **rejection reason** (mandatory)
  - Enter: "Please use the sandbox environment instead. Production access requires manager approval."
  - **Confirm Reject**
  - Status: **Rejected** ❌
  - Intern gets email: rejection reason included
  - Agents are **blocked** from working it
  - **Immutable** — can't change the decision

---

## 5️⃣ AUDIT & COMPLIANCE

### Scenario
A security admin reviews the audit log to verify all actions and exports a compliance report.

### Step-by-step

#### **Step 5a: Log in as Security Admin**
- Email: `security@spsnet.com` | Password: `Security@123`
- Click **Audit Log** (sidebar)
- You see **all actions** (logins, ticket changes, approvals, secret detections, etc.)

#### **Step 5b: Filter and search**
- Filter by **Channel**: select `email` → see only email-sourced tickets
- Filter by **User**: select `agent@spsnet.com` → see agent's actions
- Filter by **Action**: select `ticket_created` → see creation events only
- Date range: keep as default (all)
- Results update in real-time

#### **Step 5c: Test secret detection**
- Create a **new ticket** (form or email) with this text:
  ```
  AKIA1234567890ABCDEF
  ```
  (fake AWS key format)
- ✅ **Expected result:**
  - Ticket is created
  - In the Audit Log, you see a `secret_detected` event for that ticket
  - Categorized as `aws_access_key`

#### **Step 5d: Export audit log as CSV**
- On the **Audit Log** page, click **Export CSV**
- Your browser downloads `audit_log_YYYY-MM-DD.csv`
- Open in Excel → all audit entries in table format (for compliance reviews)

---

## 6️⃣ REPORTS & ANALYTICS

### Scenario
A manager reviews ticket volume and SLA compliance.

### Step-by-step

#### **Step 6a: Log in as Manager**
- Email: `manager@spsnet.com` | Password: `Manager@123`
- Click **Reports** (sidebar)
- You land in the **Reports Dashboard**

#### **Step 6b: View volume metrics**
- **Tickets by Channel** chart: see how many came from email, form, chat
- **Tickets by Category** chart: cloud, network, security, etc.
- **Tickets by Priority** chart: high, medium, low

#### **Step 6c: Check SLA compliance**
- Scroll to **SLA Compliance** section
- Table shows:
  - Category | Response time due | % On time | % Breached
  - E.g., "Network | 4 hours | 85% | 15%"
- (SLA times are configured in the code)

#### **Step 6d: Agent performance**
- **Agent Performance** table:
  - Agent name | # Resolved | Avg resolution time | Top categories
  - E.g., "agent@spsnet.com | 12 | 2.5 hours | Network, Cloud"

#### **Step 6e: Export reports**
- Click **Export CSV**
- Download `reports_YYYY-MM-DD.csv` with all analytics
- Share with stakeholders

---

## 7️⃣ PROFILE & ACCOUNT MANAGEMENT

### Scenario
A user updates their profile and password.

### Step-by-step

#### **Step 7a: Log in as any user**
- E.g., `employee@spsnet.com` | `Employee@123`

#### **Step 7b: Click "My Profile" (top-right avatar menu)**
- Profile page opens
- You see your current info:
  - Name: "Employee User"
  - Department: "Engineering"
  - Email: "employee@spsnet.com"
  - Phone: (blank)

#### **Step 7c: Edit your profile**
- Click **Edit** button
- Change:
  - Name: `Jane Smith`
  - Department: `Cloud Operations`
  - Phone: `+1-555-1234`
- Click **Save**
- ✅ **Expected result:**
  - Profile updated
  - Audit log entry: `profile_updated`

#### **Step 7d: Change password**
- On the same profile page, scroll to **Change Password**
- Enter:
  - Current password: `Employee@123`
  - New password: `NewPass@123!`
  - Confirm: `NewPass@123!`
- Click **Change Password**
- ✅ **Expected result:**
  - Password changed
  - Audit log entry: `password_changed`
  - You're logged out (for security)
  - Next login uses the new password

---

## 🔐 SECURITY & SECRET DETECTION

### Scenario
The system detects and blocks secrets in tickets.

### Step-by-step

#### **Step 8a: Submit a ticket with a secret**
- Log in as Employee
- Click **Submit Request**
- In the description, paste:
  ```
  I accidentally committed my AWS key to GitHub:
  AKIA2B3D4E5F6G7H8I9J
  
  Please revoke it ASAP.
  ```
- Submit the ticket
- ✅ **Expected result:**
  - Ticket created successfully
  - But in **Audit Log** (as Admin/Security), you see:
    - Event: `secret_detected`
    - Details: `aws_access_key` in description
    - This alerts security to review immediately

#### **Step 8b: Injection pattern detection**
- Try to submit a ticket with:
  ```
  '; DROP TABLE users; --
  ```
- ✅ **Expected result:**
  - Ticket is created, but an `injection_attempt` event is logged
  - Security team is alerted

---

## 📋 VERIFICATION CHECKLIST

After walking through all journeys, verify:

- [ ] **Email journey**: ticket created from simulated email → agent replied → customer reply auto-threaded
- [ ] **Form journey**: form submission created ticket → agent worked it → resolved email sent
- [ ] **Chat journey**: knowledge-based Q&A worked → escalation triggered on high-risk question → ticket created
- [ ] **Approval workflow**: high-risk ticket blocked in "Waiting Approval" → security admin approved/rejected → immutable decision
- [ ] **Audit log**: all actions visible, filterable by channel/user/action, CSV export works
- [ ] **Reports**: volume by channel, SLA compliance metrics, agent performance visible
- [ ] **Security**: secret detected in tickets → audit entries created
- [ ] **Profile**: user can edit profile and change password
- [ ] **SPS branding**: all pages use navy/blue colors, logo in header, branded emails

---

## 🚀 API QUICK TEST

If you prefer testing via API (Postman, curl, etc.):

**Interactive docs:** `http://localhost:8000/docs` (Swagger UI)

### Example: Create ticket via API
```bash
curl -X POST "http://localhost:8000/api/tickets" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "title": "Test via API",
    "category": "Cloud",
    "priority": "High",
    "description": "Testing API ticket creation",
    "source": "portal_form"
  }'
```

**Response:**
```json
{
  "ticket_id": "SPS-2026-099",
  "status": "open",
  "created_at": "2026-06-12T...",
  ...
}
```

---

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| Login fails | Check email/password in demo table above |
| Ticket not appearing | Refresh page (F5) or check correct role |
| Email not ingesting | Ensure IMAP_HOST in `.env` is configured, or use "Simulate email" |
| AI not responding | Check XAI_API_KEY in `.env`; if unreachable, fallback KB search triggers |
| Approval not showing | Must be high-risk category (admin/production access) or custom escalation rule |
| Can't resolve ticket | If status is "Waiting Approval", only humans with approval role can unblock |

---

## 📞 Support

Need help? Check:
- **API docs**: `http://localhost:8000/docs`
- **GitHub**: https://github.com/ibada0410/sps-securedesk
- **README**: Full architecture and config reference
- **Code comments**: `app/main.py`, `app/ai.py`, `static/app.js`

---

<div align="center">

**🎓 You've walked through all three intake channels, approvals, audit, and reports.**

**Your SPS SecureDesk AI is production-ready.**

</div>
