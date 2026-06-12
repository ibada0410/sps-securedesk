/* SPS SecureDesk AI - single-page app (hash-routed, no build step).
   Workspaces: Requester portal (chat / form / my tickets), Agent queue+detail,
   Security approvals, Manager reports, Admin (users / KB / email center / audit / SLA). */
'use strict';

const $ = (sel, el = document) => el.querySelector(sel);
const app = $('#app');
let USER = null, TOKEN = null, META = null;

// ---------------- utilities ----------------
function esc(s) { return String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
function toast(msg, kind = '') {
  const t = document.createElement('div');
  t.className = 't ' + kind; t.textContent = msg;
  $('#toast').appendChild(t); setTimeout(() => t.remove(), 4200);
}
function fmtDate(iso) { return iso ? new Date(iso).toLocaleString() : '—'; }
let _logoN = 0;
/* SPS corporate mark: bold italic "sps" between two swooshes —
   dark arc sweeping over the top-left, bright blue arc sweeping under the bottom-right */
function logoSPS(h = 34, gradFrom = '#4A77B8', gradTo = '#1A4B8C', topArc = '#1C1C1E', botArc = '#29ABE2') {
  const id = 'spsg' + (++_logoN);
  return `<svg viewBox="0 0 110 100" height="${h}" style="vertical-align:middle;overflow:visible" aria-label="SPS logo">
    <defs><linearGradient id="${id}" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="${gradFrom}"/><stop offset="1" stop-color="${gradTo}"/></linearGradient></defs>
    <path d="M 4 38 A 70 30 0 0 1 100 10" fill="none" stroke="${topArc}" stroke-width="7" stroke-linecap="round"/>
    <path d="M 10 88 A 70 30 0 0 0 106 62" fill="none" stroke="${botArc}" stroke-width="7" stroke-linecap="round"/>
    <text x="8" y="70" font-family="Arial,Helvetica,sans-serif" font-style="italic" font-weight="bold"
      font-size="48" fill="url(#${id})">sps</text></svg>`;
}
function badge(v) { return v ? `<span class="badge b-${esc(v)}">${esc(String(v).replace(/_/g, ' '))}</span>` : ''; }
function srcBadge(s) {
  const ic = { email: '✉', portal_form: '📋', chat: '💬' }[s] || '';
  return `<span class="badge b-${esc(s)}">${ic} ${esc(s === 'portal_form' ? 'form' : s)}</span>`;
}

async function api(path, opts = {}) {
  opts.headers = Object.assign({}, opts.headers, TOKEN ? { Authorization: 'Bearer ' + TOKEN } : {});
  if (opts.body && !(opts.body instanceof FormData)) {
    opts.headers['Content-Type'] = 'application/json';
    opts.body = JSON.stringify(opts.body);
  }
  const res = await fetch('/api' + path, opts);
  if (res.status === 401 && TOKEN) { logout(); throw new Error('Session expired. Please sign in again.'); }
  if (!res.ok) {
    let detail = res.statusText;
    try { const j = await res.json(); detail = typeof j.detail === 'string' ? j.detail : JSON.stringify(j.detail); } catch {}
    throw new Error(detail);
  }
  const ct = res.headers.get('content-type') || '';
  return ct.includes('json') ? res.json() : res.text();
}

function modal(html) {
  const bg = document.createElement('div');
  bg.className = 'modal-bg';
  bg.innerHTML = `<div class="modal">${html}</div>`;
  bg.addEventListener('click', e => { if (e.target === bg) bg.remove(); });
  document.body.appendChild(bg);
  return bg;
}

function logout() {
  TOKEN = null; USER = null; sessionStorage.removeItem('sps_token'); sessionStorage.removeItem('sps_user');
  location.hash = '#/login'; render();
}

// ---------------- navigation ----------------
const NAV = {
  intern:        [['Portal', null], ['AI Chat', '#/chat'], ['Submit Request', '#/submit'], ['My Tickets', '#/tickets']],
  employee:      [['Portal', null], ['AI Chat', '#/chat'], ['Submit Request', '#/submit'], ['My Tickets', '#/tickets']],
  support_agent: [['Workspace', null], ['Dashboard', '#/agent'], ['Ticket Queue', '#/queue'],
                  ['Self-service', null], ['AI Chat', '#/chat'], ['Submit Request', '#/submit']],
  security_admin:[['Security', null], ['Approvals', '#/approvals'], ['High-Risk Queue', '#/queue?queue=high_risk'],
                  ['All Tickets', '#/queue'], ['Audit Log', '#/audit'], ['Email Center', '#/emailcenter']],
  manager:       [['Management', null], ['Reports', '#/reports'], ['Approvals', '#/approvals'], ['High-Risk Tickets', '#/queue?queue=high_risk']],
  administrator: [['Admin', null], ['Users', '#/users'], ['Knowledge Base', '#/kb'], ['Email Center', '#/emailcenter'],
                  ['Audit Log', '#/audit'], ['SLA Policies', '#/sla'], ['All Tickets', '#/queue'], ['Reports', '#/reports']],
};
Object.values(NAV).forEach(items => items.push(['Account', null], ['My Profile', '#/profile']));
const HOME = { intern:'#/tickets', employee:'#/tickets', support_agent:'#/agent',
               security_admin:'#/approvals', manager:'#/reports', administrator:'#/users' };

function shell(content) {
  const links = (NAV[USER.role] || []).map(([label, href]) => {
    if (!href) return `<div class="sec">${label}</div>`;
    const active = href.includes('?') ? location.hash === href
      : location.hash.split('?')[0] === href;
    return `<a class="nav ${active ? 'active' : ''}" href="${href}">${label}</a>`;
  }).join('');
  app.innerHTML = `
    <div class="topnav">
      <div class="logo">${logoSPS(40, '#FFFFFF', '#D5E8F0', '#9CC3E5', '#29ABE2')} SecureDesk <span style="font-weight:400;opacity:.7">AI Helpdesk</span></div>
      <div class="spacer"></div>
      <div class="userbox"><div>${esc(USER.name)}</div><div class="role">${esc(USER.role.replace('_',' '))}</div></div>
      <button class="ghost-w" onclick="logout()">Sign out</button>
    </div>
    <div class="sidebar">${links}</div>
    <div class="main" id="main">${content}</div>`;
}

// ---------------- login ----------------
function viewLogin() {
  app.innerHTML = `
  <div class="login-wrap"><div class="login-card">
    <div class="logo">${logoSPS(64)}</div>
    <div style="text-align:center;color:#3a3a3a;font-weight:600;font-size:15px;margin-bottom:6px">Software Productivity Strategists, Inc.</div>
    <h2 style="text-align:center;color:var(--navy)">Welcome to SecureDesk</h2>
    <p class="small" style="text-align:center">SPS IT Support Portal — email · web form · AI chat</p>
    <div id="login-err"></div>
    <label>Email <span class="req">*</span></label><input type="email" id="lg-email" placeholder="you@spsnet.com">
    <label>Password <span class="req">*</span></label><input type="password" id="lg-pass" placeholder="••••••••">
    <div style="margin-top:20px"><button class="btn-primary" style="width:100%;height:44px" id="lg-btn">Sign In</button></div>
    <div style="display:flex;justify-content:space-between;margin-top:12px">
      <a href="#/signup">Create an account</a>
      <a href="#/forgot">Forgot password?</a>
    </div>
    <div style="display:flex;align-items:center;gap:10px;margin:16px 0 0;color:var(--muted);font-size:12px">
      <hr style="flex:1;margin:0"> OR <hr style="flex:1;margin:0"></div>
    <div style="margin-top:14px"><button class="btn-secondary" style="width:100%;height:44px" id="lg-ms">
      <svg viewBox="0 0 21 21" width="16" height="16" style="vertical-align:-2px;margin-right:8px"><rect x="1" y="1" width="9" height="9" fill="#F25022"/><rect x="11" y="1" width="9" height="9" fill="#7FBA00"/><rect x="1" y="11" width="9" height="9" fill="#00A4EF"/><rect x="11" y="11" width="9" height="9" fill="#FFB900"/></svg>
      Sign in with Microsoft</button></div>
    <div class="demo-accounts"><b>Demo accounts</b> (click to fill — password pattern <code>Role@123</code>):<br>
      ${['intern','employee','agent','security','manager','admin'].map(r =>
        `<code data-u="${r}@spsnet.com">${r}@spsnet.com</code>`).join(' · ')}
    </div>
  </div></div>`;
  $('#lg-ms').onclick = async () => {
    const sso = await api('/auth/sso');
    if (sso.enabled) location.href = sso.auth_url;
    else toast(sso.message, 'err');
  };
  app.querySelectorAll('code[data-u]').forEach(c => c.onclick = () => {
    $('#lg-email').value = c.dataset.u;
    const name = c.dataset.u.split('@')[0];
    $('#lg-pass').value = name[0].toUpperCase() + name.slice(1) + '@123';
  });
  const submit = async () => {
    try {
      const out = await api('/auth/login', { method:'POST', body:{ email:$('#lg-email').value.trim(), password:$('#lg-pass').value } });
      TOKEN = out.token; USER = out.user;
      sessionStorage.setItem('sps_token', TOKEN); sessionStorage.setItem('sps_user', JSON.stringify(USER));
      META = await api('/meta');
      location.hash = HOME[USER.role]; render();
    } catch (e) { $('#login-err').innerHTML = `<div class="alert alert-error">${esc(e.message)}</div>`; }
  };
  $('#lg-btn').onclick = submit;
  $('#lg-pass').onkeydown = e => { if (e.key === 'Enter') submit(); };
}

// ---------------- signup / forgot / reset (public) ----------------
function authCard(inner) {
  app.innerHTML = `<div class="login-wrap"><div class="login-card">
    <div class="logo">${logoSPS(56)}</div>
    <div style="text-align:center;color:#3a3a3a;font-weight:600;font-size:14px;margin-bottom:4px">Software Productivity Strategists, Inc.</div>
    ${inner}
    <div style="text-align:center;margin-top:16px"><a href="#/login">← Back to sign in</a></div>
  </div></div>`;
}

function viewSignup() {
  authCard(`
    <h2 style="text-align:center;color:var(--navy)">Create your account</h2>
    <p class="small" style="text-align:center">Self sign-up for SPS employees and interns</p>
    <div id="su-err"></div>
    <label>Full name <span class="req">*</span></label><input type="text" id="su-name">
    <label>Email <span class="req">*</span></label><input type="email" id="su-email" placeholder="you@spsnet.com">
    <label>I am a</label><select id="su-role"><option value="employee">Employee</option><option value="intern">Intern</option></select>
    <label>Password <span class="req">*</span></label><input type="password" id="su-pass" placeholder="8+ chars, 1 uppercase, 1 number">
    <label>Confirm password <span class="req">*</span></label><input type="password" id="su-pass2">
    <div style="margin-top:20px"><button class="btn-primary" style="width:100%;height:44px" id="su-go">Create Account</button></div>`);
  $('#su-go').onclick = async () => {
    const err = m => { $('#su-err').innerHTML = `<div class="alert alert-error">${esc(m)}</div>`; };
    if (!$('#su-name').value.trim() || !$('#su-email').value.trim()) return err('Name and email are required.');
    if ($('#su-pass').value !== $('#su-pass2').value) return err('Passwords do not match.');
    try {
      await api('/auth/signup', { method:'POST', body:{ full_name: $('#su-name').value, email: $('#su-email').value,
        role: $('#su-role').value, password: $('#su-pass').value } });
      toast('Account created — please sign in', 'ok'); location.hash = '#/login';
    } catch (e) { err(e.message); }
  };
}

function viewForgot() {
  authCard(`
    <h2 style="text-align:center;color:var(--navy)">Forgot password</h2>
    <p class="small" style="text-align:center">Enter your email and we'll send a reset link (valid 1 hour).</p>
    <div id="fp-msg"></div>
    <label>Email <span class="req">*</span></label><input type="email" id="fp-email" placeholder="you@spsnet.com">
    <div style="margin-top:20px"><button class="btn-primary" style="width:100%;height:44px" id="fp-go">Send reset link</button></div>
    <p class="small" style="margin-top:12px">Already have a reset code? <a href="#/reset">Enter it here</a>.<br>
    Dev note: if SMTP isn't configured, the email lands in Admin → Email Center and the <code>outbox/</code> folder.</p>`);
  $('#fp-go').onclick = async () => {
    const out = await api('/auth/forgot-password', { method:'POST', body:{ email: $('#fp-email').value } });
    $('#fp-msg').innerHTML = `<div class="alert alert-success">${esc(out.message)}</div>`;
  };
}

function viewReset() {
  const params = new URLSearchParams(location.hash.split('?')[1] || '');
  authCard(`
    <h2 style="text-align:center;color:var(--navy)">Choose a new password</h2>
    <div id="rs-err"></div>
    <label>Reset code <span class="req">*</span></label><input type="text" id="rs-token" value="${esc(params.get('token') || '')}" placeholder="paste the code from your email">
    <label>New password <span class="req">*</span></label><input type="password" id="rs-pass" placeholder="8+ chars, 1 uppercase, 1 number">
    <label>Confirm new password <span class="req">*</span></label><input type="password" id="rs-pass2">
    <div style="margin-top:20px"><button class="btn-primary" style="width:100%;height:44px" id="rs-go">Reset Password</button></div>`);
  $('#rs-go').onclick = async () => {
    if ($('#rs-pass').value !== $('#rs-pass2').value) {
      $('#rs-err').innerHTML = '<div class="alert alert-error">Passwords do not match.</div>'; return; }
    try {
      const out = await api('/auth/reset-password', { method:'POST',
        body:{ token: $('#rs-token').value.trim(), new_password: $('#rs-pass').value } });
      toast(out.message, 'ok'); location.hash = '#/login';
    } catch (e) { $('#rs-err').innerHTML = `<div class="alert alert-error">${esc(e.message)}</div>`; }
  };
}

// ---------------- my profile (every role) ----------------
async function viewProfile() {
  shell(`<h1>My Profile</h1><div id="pf">Loading…</div>`);
  const p = await api('/profile');
  $('#pf').innerHTML = `
    <div class="grid g2" style="align-items:start">
      <div class="card titled"><div class="head">Account details</div><div class="body">
        <label>Email</label><input type="email" value="${esc(p.email)}" disabled>
        <label>Role</label><input type="text" value="${esc(p.role.replace('_',' '))}" disabled>
        <label>Full name</label><input type="text" id="pf-name" value="${esc(p.full_name)}">
        <label>Department</label><input type="text" id="pf-dept" value="${esc(p.department || '')}" placeholder="e.g. Cloud Services">
        <label>Phone</label><input type="text" id="pf-phone" value="${esc(p.phone || '')}" placeholder="+1 ...">
        <p class="small" style="margin-top:8px">Last sign-in: ${fmtDate(p.last_login_at)}</p>
        <div style="margin-top:14px"><button class="btn-primary" id="pf-save">Save Profile</button></div>
      </div></div>
      <div class="card titled"><div class="head">Change password</div><div class="body">
        <div id="pf-err"></div>
        <label>Current password</label><input type="password" id="pf-cur">
        <label>New password</label><input type="password" id="pf-new" placeholder="8+ chars, 1 uppercase, 1 number">
        <label>Confirm new password</label><input type="password" id="pf-new2">
        <div style="margin-top:14px"><button class="btn-secondary" id="pf-pass">Update Password</button></div>
      </div></div>
    </div>`;
  $('#pf-save').onclick = async () => {
    try {
      const out = await api('/profile', { method:'PATCH', body:{ full_name: $('#pf-name').value,
        department: $('#pf-dept').value, phone: $('#pf-phone').value } });
      USER = out.user; sessionStorage.setItem('sps_user', JSON.stringify(USER));
      toast('Profile saved', 'ok'); viewProfile();
    } catch (e) { toast(e.message, 'err'); }
  };
  $('#pf-pass').onclick = async () => {
    if ($('#pf-new').value !== $('#pf-new2').value) {
      $('#pf-err').innerHTML = '<div class="alert alert-error">New passwords do not match.</div>'; return; }
    try {
      await api('/profile', { method:'PATCH', body:{ current_password: $('#pf-cur').value, new_password: $('#pf-new').value } });
      $('#pf-err').innerHTML = ''; toast('Password updated', 'ok');
      ['#pf-cur','#pf-new','#pf-new2'].forEach(s => $(s).value = '');
    } catch (e) { $('#pf-err').innerHTML = `<div class="alert alert-error">${esc(e.message)}</div>`; }
  };
}

// ---------------- AI chat ----------------
let chatSession = null, chatBusy = false;
function viewChat() {
  shell(`
  <h1>AI Assistant</h1>
  <p class="small">Answers come from the approved SPS knowledge base only. The assistant can never grant access or approve requests — those need a human.</p>
  <div class="chat-box">
    <div class="chat-head">${logoSPS(30, '#FFFFFF', '#D5E8F0', '#9CC3E5', '#29ABE2')} <span class="dot"></span> SecureDesk AI Assistant <span id="chat-status" style="font-weight:400;font-size:12px;opacity:.8">Online</span></div>
    <div class="chat-msgs" id="chat-msgs">
      <div class="empty"><div class="big">👋</div><h3>How can I help you today?</h3>
        <div class="chips">
          ${['How do I connect to the VPN?','How do I report a phishing email?','Intern onboarding checklist','I need admin access to production']
            .map(q => `<button class="chip" data-q="${esc(q)}">${esc(q)}</button>`).join('')}
        </div></div>
    </div>
    <div class="chat-input">
      <textarea id="chat-in" placeholder="Type your question…" rows="1"></textarea>
      <button class="btn-primary" id="chat-send">Send</button>
    </div>
  </div>`);
  $('#main').querySelectorAll('.chip').forEach(c => c.onclick = () => { $('#chat-in').value = c.dataset.q; sendChat(); });
  $('#chat-send').onclick = sendChat;
  $('#chat-in').onkeydown = e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendChat(); } };
}
function addMsg(cls, html) {
  const empty = $('#chat-msgs .empty'); if (empty) empty.remove();
  const div = document.createElement('div'); div.className = 'msg ' + cls; div.innerHTML = html;
  $('#chat-msgs').appendChild(div); $('#chat-msgs').scrollTop = 1e9; return div;
}
async function sendChat() {
  const input = $('#chat-in'); const text = input.value.trim();
  if (!text || chatBusy) return;
  input.value = ''; chatBusy = true;
  addMsg('user', esc(text));
  const thinking = addMsg('bot', '<i>Thinking…</i>');
  $('#chat-status').textContent = 'Thinking…';
  try {
    const out = await api('/chat/message', { method:'POST', body:{ session_id: chatSession, message: text } });
    chatSession = out.session_id;
    thinking.innerHTML = esc(out.reply) +
      (out.citations.length ? '<br>' + out.citations.map(c => `<span class="cite">✦ Source: ${esc(c)}</span>`).join('') : '');
    if (out.escalate) {
      const card = document.createElement('div');
      card.className = 'escalate-card';
      card.innerHTML = `${out.high_risk ? '<b>⚠ This request needs security review.</b><br>' : ''}
        This looks like it needs an agent. Create a support ticket?
        <div style="margin-top:8px"><button class="btn-warning btn-sm" id="esc-btn">Yes, create ticket</button></div>`;
      $('#chat-msgs').appendChild(card); $('#chat-msgs').scrollTop = 1e9;
      $('#esc-btn').onclick = escalateChat;
    }
  } catch (e) { thinking.innerHTML = `<span style="color:var(--danger)">${esc(e.message)}</span>`; }
  chatBusy = false; $('#chat-status').textContent = 'Online';
}
async function escalateChat() {
  let pre = { subject: '', description: '' };
  try { pre = await api('/chat/escalate-prefill', { method:'POST', body:{ session_id: chatSession, message:'' } }); } catch {}
  const m = modal(`
    <h3>Create ticket from chat</h3>
    <p class="small">Review the AI-prefilled summary before submitting. Source will be tagged as <b>chat</b>.</p>
    <label>Subject <span class="req">*</span></label><input type="text" id="esc-sub" value="${esc(pre.subject)}">
    <label>Description <span class="req">*</span></label><textarea id="esc-desc">${esc(pre.description)}</textarea>
    <div style="margin-top:18px;display:flex;gap:10px">
      <button class="btn-primary" id="esc-go">Create Ticket</button>
      <button class="btn-ghost" onclick="this.closest('.modal-bg').remove()">Cancel</button></div>`);
  $('#esc-go', m).onclick = async () => {
    try {
      const t = await api('/tickets', { method:'POST', body:{ subject: $('#esc-sub', m).value, description: $('#esc-desc', m).value,
        source:'chat', chat_session_id: chatSession } });
      m.remove();
      addMsg('bot', `✅ Ticket <b class="mono">${esc(t.ticket_id)}</b> created! Track it in <a href="#/tickets">My Tickets</a>.` +
        (t.status === 'waiting_approval' ? '<br>⚠ It requires <b>human security approval</b> before any action is taken.' : ''));
      chatSession = null;
    } catch (e) { toast(e.message, 'err'); }
  };
}

// ---------------- submit request form ----------------
function viewSubmit() {
  shell(`
  <h1>Submit a Request</h1>
  <p class="small">Prefer email? Write to <b>helpdesk@spsnet.com</b> — it creates the same kind of ticket.</p>
  <div class="card" style="max-width:680px">
    <div id="form-err"></div>
    <label>Subject / title <span class="req">*</span></label><input type="text" id="f-sub" maxlength="200">
    <label>Category</label>
    <select id="f-cat"><option value="">— let AI suggest —</option>
      ${(META?.categories || []).map(c => `<option value="${c}">${c.replace(/_/g, ' ')}</option>`).join('')}</select>
    <label>Description <span class="req">*</span></label><textarea id="f-desc" placeholder="What happened? What do you need?"></textarea>
    <label>Priority hint (optional — agents and AI may adjust)</label>
    <select id="f-pri"><option value="">— default —</option>${(META?.priorities || []).map(p => `<option>${p}</option>`).join('')}</select>
    <label>Contact email <span class="req">*</span></label><input type="email" id="f-email" value="${esc(USER.email)}">
    <label>Attachment (screenshots, logs — max 10MB)</label><input type="file" id="f-file">
    <div style="margin-top:22px"><button class="btn-primary" id="f-go">Submit Request</button></div>
  </div>`);
  $('#f-go').onclick = async () => {
    const sub = $('#f-sub').value.trim(), desc = $('#f-desc').value.trim();
    if (!sub || !desc) { $('#form-err').innerHTML = '<div class="alert alert-error">Subject and description are required.</div>'; return; }
    $('#f-go').disabled = true;
    try {
      const t = await api('/tickets', { method:'POST', body:{ subject: sub, description: desc,
        category: $('#f-cat').value || null, priority: $('#f-pri').value || null,
        contact_email: $('#f-email').value, source:'portal_form' } });
      const file = $('#f-file').files[0];
      if (file) { const fd = new FormData(); fd.append('file', file);
        try { await api(`/tickets/${t.ticket_id}/attachments`, { method:'POST', body: fd }); } catch (e) { toast('Attachment: ' + e.message, 'err'); } }
      shell(`
        <div class="card" style="max-width:640px;margin:48px auto;text-align:center">
          <div style="font-size:48px">✅</div>
          <h2 style="color:var(--success)">Request submitted</h2>
          <p>Your ticket number is</p><div class="bigid">${esc(t.ticket_id)}</div>
          <p class="small">A confirmation email was sent to ${esc($('#f-email')?.value || USER.email)}. AI triage is running — an agent will review shortly.</p>
          <div style="margin-top:20px;display:flex;gap:10px;justify-content:center">
            <a class="btn btn-primary" href="#/ticket/${t.ticket_id}">View Ticket</a>
            <a class="btn btn-secondary" href="#/submit" onclick="setTimeout(render)">Submit Another</a></div>
        </div>`);
    } catch (e) { $('#form-err').innerHTML = `<div class="alert alert-error">${esc(e.message)}</div>`; $('#f-go').disabled = false; }
  };
}

// ---------------- ticket lists ----------------
function ticketRows(tickets) {
  if (!tickets.length) return `<tr><td colspan="7"><div class="empty"><div class="big">🗂</div><h3>No tickets match</h3><p class="small">All caught up, or try clearing filters.</p></div></td></tr>`;
  return tickets.map(t => `
    <tr class="click" onclick="location.hash='#/ticket/${t.ticket_id}'">
      <td class="mono">${esc(t.ticket_id)}</td>
      <td>${esc(t.subject)}${t.sla_breached ? ' <span class="badge b-critical">SLA</span>' : ''}</td>
      <td>${srcBadge(t.source)}</td><td>${badge(t.status)}</td><td>${badge(t.priority)}</td>
      <td>${['high','critical'].includes(t.risk_level) ? badge(t.risk_level) : '<span class="small">'+esc(t.risk_level)+'</span>'}</td>
      <td class="small">${fmtDate(t.created_at)}</td></tr>`).join('');
}

async function viewMyTickets() {
  shell(`<h1>My Tickets</h1><p class="small">All your requests — from email, web form and chat — in one place.</p><div class="card titled"><div class="head">Tickets</div><div class="body" id="list">Loading…</div></div>`);
  const out = await api('/tickets');
  $('#list').innerHTML = out.tickets.length
    ? `<table><tr><th>ID</th><th>Subject</th><th>Source</th><th>Status</th><th>Priority</th><th>Risk</th><th>Created</th></tr>${ticketRows(out.tickets)}</table>`
    : `<div class="empty"><div class="big">📭</div><h3>No tickets yet — we haven't heard from you!</h3><a class="btn btn-primary" href="#/submit">Submit a Request</a></div>`;
}

async function viewQueue() {
  const params = new URLSearchParams(location.hash.split('?')[1] || '');
  const queue = params.get('queue') || '';
  shell(`
  <h1>${queue === 'high_risk' ? 'High-Risk Queue' : 'Ticket Queue'}</h1>
  <div class="tabs" id="qtabs">
    ${[['','All'],['mine','My Queue'],['unassigned','Unassigned'],['high_risk','High-Risk']].map(([k, l]) =>
      `<button data-q="${k}" class="${queue === k ? 'on' : ''}">${l}</button>`).join('')}
  </div>
  <div class="filters">
    <select id="q-status"><option value="">All statuses</option>${META.statuses.map(s => `<option>${s}</option>`).join('')}</select>
    <select id="q-source"><option value="">All sources</option>${META.sources.map(s => `<option>${s}</option>`).join('')}</select>
    <select id="q-cat"><option value="">All categories</option>${META.categories.map(c => `<option>${c}</option>`).join('')}</select>
    <input type="text" id="q-q" placeholder="Search subject or ID…">
    <button class="btn-secondary btn-sm" id="q-apply">Filter</button>
  </div>
  <div class="card titled"><div class="head">Tickets <span id="q-count" class="small"></span></div><div class="body" id="list">Loading…</div></div>`);
  $('#qtabs').querySelectorAll('button').forEach(b => b.onclick = () => { location.hash = '#/queue' + (b.dataset.q ? '?queue=' + b.dataset.q : ''); });
  const load = async () => {
    const qs = new URLSearchParams({ queue, status: $('#q-status').value, source: $('#q-source').value,
      category: $('#q-cat').value, q: $('#q-q').value });
    const out = await api('/tickets?' + qs);
    $('#q-count').textContent = `(${out.total})`;
    $('#list').innerHTML = `<table><tr><th>ID</th><th>Subject</th><th>Source</th><th>Status</th><th>Priority</th><th>Risk</th><th>Created</th></tr>${ticketRows(out.tickets)}</table>`;
  };
  $('#q-apply').onclick = load; load();
}

async function viewAgentDash() {
  shell(`<h1>Agent Dashboard</h1><div id="dash">Loading…</div>`);
  const [all, mine, unassigned] = await Promise.all([
    api('/tickets'), api('/tickets?queue=mine'), api('/tickets?queue=unassigned')]);
  const open = all.tickets.filter(t => !['resolved','closed','rejected'].includes(t.status));
  const breach = open.filter(t => t.sla_breached);
  const waiting = all.tickets.filter(t => t.status === 'waiting_approval');
  $('#dash').innerHTML = `
    <div class="grid g4">
      <div class="stat"><div class="num">${open.length}</div><div class="lbl">Open tickets</div></div>
      <div class="stat"><div class="num">${mine.total}</div><div class="lbl">Assigned to me</div></div>
      <div class="stat"><div class="num">${unassigned.total}</div><div class="lbl">Unassigned</div></div>
      <div class="stat"><div class="num" style="color:${breach.length ? 'var(--danger)' : 'var(--success)'}">${breach.length}</div><div class="lbl">SLA breached</div></div>
    </div>
    ${waiting.length ? `<div class="alert alert-warn" style="margin-top:24px">⚠ ${waiting.length} ticket(s) are <b>Waiting Approval</b> — blocked until a security admin or manager decides.</div>` : ''}
    <div class="card titled" style="margin-top:24px"><div class="head">Latest open tickets</div><div class="body">
      <table><tr><th>ID</th><th>Subject</th><th>Source</th><th>Status</th><th>Priority</th><th>Risk</th><th>Created</th></tr>
      ${ticketRows(open.slice(0, 10))}</table>
      <div style="margin-top:12px"><a class="btn btn-secondary" href="#/queue">Open full queue →</a></div></div></div>`;
}

// ---------------- ticket detail ----------------
function slaCard(t) {
  if (!t.sla_due_at) return '<p class="small">No SLA policy matched.</p>';
  const due = new Date(t.sla_due_at), now = new Date();
  const total = due - new Date(t.created_at), left = due - now;
  const pct = Math.max(0, Math.min(100, 100 * (1 - left / total)));
  const cls = t.sla_breached || left < 0 ? 'bad' : (left < 2 * 3600e3 ? 'warn' : '');
  return `<div class="sla-bar"><i class="${cls}" style="width:${t.sla_breached ? 100 : pct}%"></i></div>
    <div class="small">${t.sla_breached || left < 0 ? '<b style="color:var(--danger)">BREACHED</b> — was due ' : 'Due '} ${due.toLocaleString()}</div>`;
}

async function viewTicket(id) {
  shell(`<div id="tk">Loading ticket…</div>`);
  let t;
  try { t = await api('/tickets/' + id); }
  catch (e) { $('#tk').innerHTML = `<div class="empty"><div class="big">🔍</div><h3>Ticket not found</h3><p>${esc(e.message)}</p><a class="btn btn-secondary" href="${HOME[USER.role]}">Back</a></div>`; return; }
  const isAgent = ['support_agent','security_admin','administrator'].includes(USER.role);
  const isRequester = t.requester_email === USER.email;
  const timeline = t.events.map(e => `
    <li class="${e.is_internal ? 'internal' : ''}">
      <span class="who">${esc(e.actor_email || 'system')}</span>
      <span class="badge b-${esc(e.channel || 'portal')}" style="margin-left:6px">${esc(e.channel || '')}</span>
      ${e.is_internal ? '<span class="badge b-pending">internal</span>' : ''}
      <span class="badge b-low">${esc(e.event_type.replace(/_/g, ' '))}</span>
      <div class="when">${fmtDate(e.created_at)}</div>
      <div class="body">${esc(e.content || '')}</div></li>`).join('');
  const atts = t.attachments.map(a =>
    `<div>📎 <a href="javascript:void(0)" onclick="downloadAtt('${a.attachment_id}','${esc(a.file_name)}')">${esc(a.file_name)}</a> <span class="small">(${Math.round(a.size_bytes/1024)} KB · ${esc(a.uploader_email)})</span></div>`).join('') || '<span class="small">None</span>';

  const sidebar = isAgent ? `
    <div class="card titled"><div class="head">Ticket Properties</div><div class="body">
      <label>Status</label><select id="p-status">${META.statuses.map(s => `<option ${s===t.status?'selected':''}>${s}</option>`).join('')}</select>
      <label>Priority</label><select id="p-pri">${META.priorities.map(p => `<option ${p===t.priority?'selected':''}>${p}</option>`).join('')}</select>
      <label>Category</label><select id="p-cat"><option value="">—</option>${META.categories.map(c => `<option ${c===t.category?'selected':''}>${c}</option>`).join('')}</select>
      <label>Risk level</label><select id="p-risk">${META.priorities.map(r => `<option ${r===t.risk_level?'selected':''}>${r}</option>`).join('')}</select>
      <label>Assignee</label><select id="p-asg"><option value="">— unassigned —</option>
        ${META.agents.map(a => `<option value="${a.id}" ${t.assignee && t.assignee.id===a.id?'selected':''}>${esc(a.name)}</option>`).join('')}</select>
      <label>Resolution note (required to resolve/close)</label><textarea id="p-note" style="min-height:60px">${esc(t.resolution_note || '')}</textarea>
      <div style="margin-top:14px"><button class="btn-primary btn-sm" id="p-save">Save changes</button></div>
    </div></div>
    <div class="card titled"><div class="head" style="background:#EDE4FF;color:var(--risk)">✦ AI Summary <span class="small">(suggestion — agent owns final)</span></div><div class="body">
      <div id="ai-sum">${t.ai_summary ? esc(t.ai_summary) : '<span class="small">No summary yet.</span>'}</div>
      <div style="margin-top:10px;display:flex;gap:8px">
        <button class="btn-secondary btn-sm" id="ai-sum-btn">✦ Generate summary</button>
        <button class="btn-secondary btn-sm" id="ai-cls-btn">✦ Re-classify</button></div>
    </div></div>` : '';

  const composer = (isAgent || isRequester) ? `
    <div class="card titled"><div class="head">${isAgent ? 'Reply Composer' : 'Add a comment'}</div><div class="body">
      ${isAgent ? `<div class="tabs" id="r-tabs">
        <button class="on" data-m="public">Public Reply</button>
        <button data-m="internal">Internal Note</button>
        <button data-m="email">Email Reply</button></div>` : ''}
      <textarea id="r-body" placeholder="${isAgent ? 'Write your reply…' : 'Add information for the support team…'}"></textarea>
      <div style="margin-top:12px;display:flex;gap:10px;flex-wrap:wrap">
        <button class="btn-primary" id="r-send">Send</button>
        ${isAgent ? '<button class="btn-secondary" id="r-draft">✦ Draft with AI</button>' : ''}
        <label style="margin:0;display:inline-flex;align-items:center;gap:6px;text-transform:none;font-weight:400">
          <input type="file" id="r-file" style="width:auto"></label>
        <button class="btn-secondary" id="r-upload">Upload file</button>
      </div></div></div>` : '';

  $('#tk').innerHTML = `
    <div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:10px;align-items:center">
      <h1><span class="mono">${esc(t.ticket_id)}</span> — ${esc(t.subject)}</h1>
      <div>${srcBadge(t.source)} ${badge(t.status)} ${badge(t.priority)} ${['high','critical'].includes(t.risk_level) ? badge(t.risk_level) : ''}</div>
    </div>
    <p class="small">Requester: <b>${esc(t.requester_email)}</b> · Team: ${esc(t.team || '—')} · Created ${fmtDate(t.created_at)}</p>
    ${t.status === 'waiting_approval' ? `<div class="confirm-banner">⏳ Waiting for human approval — no action can be taken until a security admin or manager decides.${t.approval ? '' : ''}</div>` : ''}
    ${t.approval && t.approval.status !== 'pending' ? `<div class="alert ${t.approval.status === 'approved' ? 'alert-success' : 'alert-error'}">Access request <b>${t.approval.status.toUpperCase()}</b>${t.approval.reason ? ' — Reason: ' + esc(t.approval.reason) : ''} (${fmtDate(t.approval.decided_at)})</div>` : ''}
    <div class="two-col">
      <div>
        <div class="card titled"><div class="head">Timeline — one record across email, portal and chat</div><div class="body">
          ${t.description ? `<div class="alert alert-info"><b>Description:</b><br>${esc(t.description)}</div>` : ''}
          <ul class="timeline">${timeline}</ul>
          <hr><b class="small">ATTACHMENTS</b>${atts}
        </div></div>
        ${composer}
      </div>
      <div>
        ${sidebar}
        <div class="card titled"><div class="head">SLA</div><div class="body">${slaCard(t)}</div></div>
        ${t.chat_transcript ? `<div class="card titled"><div class="head">💬 Linked chat transcript</div><div class="body" style="max-height:260px;overflow:auto">${t.chat_transcript.map(m => `<p class="small"><b>${esc(m.role)}:</b> ${esc(m.content)}</p>`).join('')}</div></div>` : ''}
      </div>
    </div>`;

  let replyMode = 'public';
  if (isAgent) {
    $('#r-tabs')?.querySelectorAll('button').forEach(b => b.onclick = () => {
      $('#r-tabs').querySelectorAll('button').forEach(x => x.classList.remove('on'));
      b.classList.add('on'); replyMode = b.dataset.m;
    });
    $('#p-save').onclick = async () => {
      try {
        await api('/tickets/' + id, { method:'PATCH', body:{
          status: $('#p-status').value, priority: $('#p-pri').value, category: $('#p-cat').value || null,
          risk_level: $('#p-risk').value, assignee_id: $('#p-asg').value, resolution_note: $('#p-note').value || null } });
        toast('Ticket updated', 'ok'); viewTicket(id);
      } catch (e) { toast(e.message, 'err'); }
    };
    $('#ai-sum-btn').onclick = async () => {
      $('#ai-sum').innerHTML = '<i>✦ Summarizing…</i>';
      try { const o = await api(`/tickets/${id}/summary`); $('#ai-sum').textContent = o.summary; }
      catch (e) { toast(e.message, 'err'); }
    };
    $('#ai-cls-btn').onclick = async () => {
      await api(`/tickets/${id}/classify`, { method:'POST' });
      toast('AI classification running — refresh in a few seconds', 'ok');
      setTimeout(() => viewTicket(id), 4000);
    };
    $('#r-draft')?.addEventListener('click', async () => {
      $('#r-body').value = '✦ drafting…';
      try { const o = await api(`/tickets/${id}/draft-reply`, { method:'POST' }); $('#r-body').value = o.draft; toast('AI draft inserted — edit before sending', 'ok'); }
      catch (e) { $('#r-body').value = ''; toast(e.message, 'err'); }
    });
  }
  $('#r-send')?.addEventListener('click', async () => {
    const content = $('#r-body').value.trim(); if (!content) return;
    try {
      await api(`/tickets/${id}/reply`, { method:'POST', body:{ content,
        is_internal: replyMode === 'internal', send_email: replyMode === 'email' } });
      toast(replyMode === 'email' ? 'Reply sent and emailed to requester' : 'Reply added to timeline', 'ok');
      viewTicket(id);
    } catch (e) { toast(e.message, 'err'); }
  });
  $('#r-upload')?.addEventListener('click', async () => {
    const file = $('#r-file').files[0]; if (!file) { toast('Choose a file first', 'err'); return; }
    const fd = new FormData(); fd.append('file', file);
    try { await api(`/tickets/${id}/attachments`, { method:'POST', body: fd }); toast('File uploaded', 'ok'); viewTicket(id); }
    catch (e) { toast(e.message, 'err'); }
  });
}
async function downloadAtt(attId, name) {
  const res = await fetch('/api/attachments/' + attId, { headers:{ Authorization: 'Bearer ' + TOKEN } });
  const blob = await res.blob(); const a = document.createElement('a');
  a.href = URL.createObjectURL(blob); a.download = name; a.click();
}

// ---------------- approvals (security/manager) ----------------
async function viewApprovals() {
  shell(`<h1>Access Approvals</h1>
    <div class="alert alert-warn"><b>Human-only decisions.</b> AI flags high-risk requests but can never approve them. Every decision is recorded in the immutable audit log.</div>
    <div class="tabs" id="ap-tabs"><button class="on" data-s="pending">Pending</button><button data-s="approved">Approved</button><button data-s="rejected">Rejected</button></div>
    <div id="ap-list">Loading…</div>`);
  let status = 'pending';
  const load = async () => {
    const rows = await api('/approvals?status=' + status);
    $('#ap-list').innerHTML = rows.length ? rows.map(a => `
      <div class="card" style="border-left:4px solid var(--risk)">
        <div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px">
          <div><b class="mono">${esc(a.ticket_id)}</b> — ${esc(a.subject)}<br>
            <span class="small">${esc(a.requester_email)} · ${srcBadge(a.source)} ${badge(a.risk_level)} ${badge(a.status)} · requested ${fmtDate(a.requested_at)}</span>
            ${a.risk_factors ? `<div class="ai-pill">✦ AI risk note: ${esc(a.risk_factors)}</div>` : ''}
            ${a.reason ? `<div class="small" style="margin-top:6px"><b>Reason:</b> ${esc(a.reason)}</div>` : ''}
          </div>
          <div style="display:flex;gap:8px;align-items:flex-start">
            <a class="btn btn-secondary btn-sm" href="#/ticket/${a.ticket_id}">Review ticket</a>
            ${a.status === 'pending' && ['security_admin','manager'].includes(USER.role) ? `
              <button class="btn-approve btn-sm" onclick="decide('${a.approval_id}','approved','${esc(a.ticket_id)}')">Approve</button>
              <button class="btn-danger btn-sm" onclick="decide('${a.approval_id}','rejected','${esc(a.ticket_id)}')">Reject</button>` : ''}
          </div></div></div>`).join('')
      : `<div class="empty"><div class="big">✅</div><h3>No ${status} approvals</h3></div>`;
  };
  $('#ap-tabs').querySelectorAll('button').forEach(b => b.onclick = () => {
    $('#ap-tabs').querySelectorAll('button').forEach(x => x.classList.remove('on'));
    b.classList.add('on'); status = b.dataset.s; load();
  });
  load();
}
function decide(approvalId, decision, ticketId) {
  const approving = decision === 'approved';
  const m = modal(`
    <div class="confirm-banner">${approving ? 'CONFIRM APPROVAL' : 'CONFIRM REJECTION'}</div>
    <p>You are about to <b>${decision === 'approved' ? 'APPROVE' : 'REJECT'}</b> high-risk request <b class="mono">${ticketId}</b>.
       This decision is <b>immutable</b> and will be written to the audit log with your identity, IP and timestamp.</p>
    <label>Reason ${approving ? '(optional)' : '<span class="req">* required</span>'}</label>
    <textarea id="d-reason"></textarea>
    <div style="margin-top:18px;display:flex;gap:10px">
      <button class="${approving ? 'btn-approve' : 'btn-danger'}" id="d-go">${approving ? 'Approve Access Request' : 'Confirm Rejection'}</button>
      <button class="btn-ghost" onclick="this.closest('.modal-bg').remove()">Cancel</button></div>`);
  $('#d-go', m).onclick = async () => {
    try {
      await api('/approvals/' + approvalId, { method:'PATCH', body:{ decision, reason: $('#d-reason', m).value } });
      m.remove(); toast('Decision recorded and requester notified', 'ok'); viewApprovals();
    } catch (e) { toast(e.message, 'err'); }
  };
}

// ---------------- manager reports ----------------
function bars(obj, total) {
  return Object.entries(obj).map(([k, v]) => `
    <div class="bar-row"><span class="lab">${esc(k.replace(/_/g, ' '))}</span>
      <span class="bar"><i style="width:${total ? Math.round(100 * v / total) : 0}%"></i></span><b>${v}</b></div>`).join('') || '<p class="small">No data.</p>';
}
async function viewReports() {
  shell(`<h1>Management Reports</h1>
    <div class="filters"><label style="margin:0">Period</label>
      <select id="rp-days"><option value="7">Last 7 days</option><option value="30" selected>Last 30 days</option><option value="90">Last 90 days</option></select>
      <button class="btn-secondary btn-sm" id="rp-export">Export CSV</button></div>
    <div id="rp">Loading…</div>`);
  const load = async () => {
    const r = await api('/reports/summary?days=' + $('#rp-days').value);
    $('#rp').innerHTML = `
      <div class="grid g4">
        <div class="stat"><div class="num">${r.total_tickets}</div><div class="lbl">Tickets created</div></div>
        <div class="stat"><div class="num">${r.resolved_count}</div><div class="lbl">Resolved</div></div>
        <div class="stat"><div class="num" style="color:${r.sla_compliance_pct >= 90 ? 'var(--success)' : 'var(--warning)'}">${r.sla_compliance_pct}%</div><div class="lbl">SLA compliance</div></div>
        <div class="stat"><div class="num" style="color:var(--risk)">${r.high_risk_count}</div><div class="lbl">High-risk requests</div></div>
      </div>
      <div class="grid g2" style="margin-top:24px">
        <div class="card titled"><div class="head">Tickets by channel</div><div class="body">${bars(r.by_source, r.total_tickets)}</div></div>
        <div class="card titled"><div class="head">Tickets by category</div><div class="body">${bars(r.by_category, r.total_tickets)}</div></div>
        <div class="card titled"><div class="head">Tickets by status</div><div class="body">${bars(r.by_status, r.total_tickets)}</div></div>
        <div class="card titled"><div class="head">Approvals (${r.approvals.total})</div><div class="body">${bars({approved:r.approvals.approved, rejected:r.approvals.rejected, pending:r.approvals.pending}, r.approvals.total)}</div></div>
      </div>
      <div class="card titled"><div class="head">High-risk access requests this period</div><div class="body">
        ${r.high_risk_tickets.length ? `<table><tr><th>ID</th><th>Subject</th><th>Source</th><th>Status</th><th>Risk</th></tr>
          ${r.high_risk_tickets.map(t => `<tr class="click" onclick="location.hash='#/ticket/${t.ticket_id}'"><td class="mono">${esc(t.ticket_id)}</td><td>${esc(t.subject)}</td><td>${srcBadge(t.source)}</td><td>${badge(t.status)}</td><td>${badge(t.risk_level)}</td></tr>`).join('')}</table>`
        : '<p class="small">None this period.</p>'}</div></div>
      <div class="card titled"><div class="head">Agent performance (resolved)</div><div class="body">${bars(r.agent_resolved, r.resolved_count)}</div></div>`;
  };
  $('#rp-days').onchange = load;
  $('#rp-export').onclick = async () => {
    const res = await fetch(`/api/reports/summary?days=${$('#rp-days').value}&export=true`, { headers:{ Authorization:'Bearer ' + TOKEN } });
    const blob = await res.blob(); const a = document.createElement('a');
    a.href = URL.createObjectURL(blob); a.download = 'sps_report.csv'; a.click(); toast('Report downloaded', 'ok');
  };
  load();
}

// ---------------- audit log ----------------
async function viewAudit() {
  shell(`<h1>Audit Log</h1><p class="small">Write-once compliance log. Every event is tagged with its source channel (email / portal / chat / system / admin).</p>
    <div class="filters">
      <select id="au-ch"><option value="">All channels</option>${['email','portal','chat','system','admin'].map(c => `<option>${c}</option>`).join('')}</select>
      <input type="text" id="au-et" placeholder="event type e.g. approval_approved">
      <button class="btn-secondary btn-sm" id="au-apply">Filter</button>
      <button class="btn-secondary btn-sm" id="au-export">Export CSV</button></div>
    <div class="card titled"><div class="head">Events <span class="small" id="au-count"></span></div><div class="body" id="au-list">Loading…</div></div>`);
  const load = async () => {
    const out = await api(`/audit?channel=${$('#au-ch').value}&event_type=${encodeURIComponent($('#au-et').value)}`);
    $('#au-count').textContent = `(${out.total})`;
    $('#au-list').innerHTML = `<table><tr><th>Time</th><th>Event</th><th>Actor</th><th>Ticket</th><th>Channel</th><th>IP</th><th>Payload</th></tr>
      ${out.rows.map(r => `<tr><td class="small">${fmtDate(r.created_at)}</td>
        <td><span class="badge ${r.event_type.includes('secret') || r.event_type.includes('injection') ? 'b-critical' : 'b-low'}">${esc(r.event_type)}</span></td>
        <td class="small">${esc(r.actor_email || 'system')}${r.actor_role ? '<br>' + esc(r.actor_role) : ''}</td>
        <td class="mono">${r.ticket_id ? `<a href="#/ticket/${r.ticket_id}">${esc(r.ticket_id)}</a>` : '—'}</td>
        <td>${r.channel ? badge(r.channel) : '—'}</td><td class="small">${esc(r.ip_address || '—')}</td>
        <td class="mono small" style="max-width:280px;word-break:break-all">${esc(JSON.stringify(r.payload))}</td></tr>`).join('')
      || '<tr><td colspan="7"><div class="empty">No events match your filters.</div></td></tr>'}</table>`;
  };
  $('#au-apply').onclick = load;
  $('#au-export').onclick = async () => {
    const res = await fetch(`/api/audit?export=true&channel=${$('#au-ch').value}`, { headers:{ Authorization:'Bearer ' + TOKEN } });
    const blob = await res.blob(); const a = document.createElement('a');
    a.href = URL.createObjectURL(blob); a.download = 'audit_log.csv'; a.click();
  };
  load();
}

// ---------------- admin: users ----------------
async function viewUsers() {
  shell(`<h1>User Management</h1>
    <div style="margin-bottom:16px"><button class="btn-primary" id="u-new">+ New User</button></div>
    <div class="card titled"><div class="head">Users</div><div class="body" id="u-list">Loading…</div></div>`);
  const load = async () => {
    const rows = await api('/users');
    $('#u-list').innerHTML = `<table><tr><th>Name</th><th>Email</th><th>Role</th><th>Active</th><th>Last login</th><th></th></tr>
      ${rows.map(u => `<tr><td>${esc(u.name)}</td><td>${esc(u.email)}</td><td>${badge(u.role === 'administrator' ? 'critical' : 'open')} <span class="small">${esc(u.role.replace('_',' '))}</span></td>
        <td>${u.is_active ? '✅' : '⛔'}</td><td class="small">${fmtDate(u.last_login_at)}</td>
        <td>${USER.role === 'administrator' && u.id !== USER.id ? `<button class="btn-ghost btn-sm" onclick="toggleUser('${u.id}', ${!u.is_active})">${u.is_active ? 'Deactivate' : 'Activate'}</button>` : ''}</td></tr>`).join('')}</table>`;
  };
  window.toggleUser = async (uid, active) => {
    try { await api('/users/' + uid, { method:'PATCH', body:{ is_active: active } }); toast('User updated', 'ok'); load(); }
    catch (e) { toast(e.message, 'err'); }
  };
  $('#u-new').onclick = () => {
    const m = modal(`<h3>Invite user</h3>
      <label>Full name</label><input type="text" id="nu-name">
      <label>Email</label><input type="email" id="nu-email">
      <label>Role</label><select id="nu-role">${META.roles.map(r => `<option>${r}</option>`).join('')}</select>
      <label>Temporary password (8+ chars, 1 uppercase, 1 number)</label><input type="text" id="nu-pass" value="Welcome@123">
      <div style="margin-top:18px;display:flex;gap:10px"><button class="btn-primary" id="nu-go">Create</button>
      <button class="btn-ghost" onclick="this.closest('.modal-bg').remove()">Cancel</button></div>`);
    $('#nu-go', m).onclick = async () => {
      try {
        await api('/users', { method:'POST', body:{ full_name: $('#nu-name', m).value, email: $('#nu-email', m).value,
          role: $('#nu-role', m).value, password: $('#nu-pass', m).value } });
        m.remove(); toast('User created', 'ok'); load();
      } catch (e) { toast(e.message, 'err'); }
    };
  };
  load();
}

// ---------------- admin: knowledge base ----------------
async function viewKB() {
  shell(`<h1>Knowledge Base</h1>
    <p class="small">Published articles are the ONLY source the AI chat assistant answers from.</p>
    ${USER.role === 'administrator' ? '<div style="margin-bottom:16px"><button class="btn-primary" id="kb-new">+ New Article</button></div>' : ''}
    <div id="kb-list">Loading…</div>`);
  const load = async () => {
    const rows = await api('/kb');
    $('#kb-list').innerHTML = rows.length ? rows.map(a => `
      <div class="card titled"><div class="head" style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px">
        <span>${esc(a.title)}</span>
        <span>${badge(a.status === 'published' ? 'resolved' : a.status === 'draft' ? 'pending' : 'closed')}
          <span class="small">v${a.version} · ${esc(a.category)} · cited ${a.citation_count}×</span></span></div>
        <div class="body"><div style="white-space:pre-wrap">${esc(a.content)}</div>
        ${USER.role === 'administrator' ? `<div style="margin-top:12px;display:flex;gap:8px">
          <button class="btn-secondary btn-sm" onclick='editKB(${JSON.stringify(a).replace(/'/g, "&#39;")})'>Edit</button>
          ${a.status !== 'published' ? `<button class="btn-approve btn-sm" onclick='setKBStatus(${JSON.stringify(a).replace(/'/g, "&#39;")}, "published")'>Publish</button>` :
            `<button class="btn-warning btn-sm" onclick='setKBStatus(${JSON.stringify(a).replace(/'/g, "&#39;")}, "archived")'>Archive</button>`}</div>` : ''}
        </div></div>`).join('')
      : '<div class="empty"><div class="big">📚</div><h3>No articles yet</h3></div>';
  };
  window.setKBStatus = async (a, status) => {
    try { await api('/kb/' + a.article_id, { method:'PUT', body:{ title: a.title, content: a.content, category: a.category, status } });
      toast(status === 'published' ? 'Article published — now available to the AI assistant' : 'Article ' + status, 'ok'); load(); }
    catch (e) { toast(e.message, 'err'); }
  };
  window.editKB = (a) => kbEditor(a, load);
  $('#kb-new')?.addEventListener('click', () => kbEditor(null, load));
  load();
}
function kbEditor(a, reload) {
  const m = modal(`<h3>${a ? 'Edit' : 'New'} article</h3>
    <label>Title</label><input type="text" id="kb-title" value="${esc(a?.title || '')}">
    <label>Category</label><select id="kb-cat">${META.categories.map(c => `<option ${a?.category === c ? 'selected' : ''}>${c}</option>`).join('')}</select>
    <label>Content</label><textarea id="kb-content" style="min-height:200px">${esc(a?.content || '')}</textarea>
    <label>Status</label><select id="kb-status">${['draft','published','archived'].map(s => `<option ${a?.status === s ? 'selected' : ''}>${s}</option>`).join('')}</select>
    <div style="margin-top:18px;display:flex;gap:10px"><button class="btn-primary" id="kb-save">Save</button>
    <button class="btn-ghost" onclick="this.closest('.modal-bg').remove()">Cancel</button></div>`);
  $('#kb-save', m).onclick = async () => {
    const body = { title: $('#kb-title', m).value, content: $('#kb-content', m).value,
      category: $('#kb-cat', m).value, status: $('#kb-status', m).value };
    try {
      if (a) await api('/kb/' + a.article_id, { method:'PUT', body });
      else await api('/kb', { method:'POST', body });
      m.remove(); toast('Article saved', 'ok'); reload();
    } catch (e) { toast(e.message, 'err'); }
  };
}

// ---------------- admin: email center ----------------
async function viewEmailCenter() {
  shell(`<h1>Email Center</h1>
    <p class="small">Mode: outbound <b>${META.smtp_mode === 'smtp' ? 'real SMTP' : 'dev outbox'}</b> · inbound <b>${META.imap_mode === 'imap' ? 'IMAP polling' : 'simulator'}</b> (configure SMTP/IMAP in .env for production).</p>
    <div class="grid g2">
      <div class="card titled"><div class="head">📥 Simulate inbound email → helpdesk@spsnet.com</div><div class="body">
        <p class="small">Feeds the exact same pipeline as the IMAP poller. Include <span class="mono">[SPS-2026-001]</span> in the subject to thread into an existing ticket.</p>
        <label>From</label><input type="email" id="ie-from" value="employee@spsnet.com">
        <label>Subject</label><input type="text" id="ie-sub" value="My laptop will not turn on">
        <label>Body</label><textarea id="ie-body">Hi helpdesk, my laptop stopped booting this morning. I have a client demo at 3pm — please help. Asset tag SPS-LT-0421.</textarea>
        <div style="margin-top:14px"><button class="btn-primary" id="ie-go">Deliver email</button></div>
        <div id="ie-out" style="margin-top:10px"></div>
      </div></div>
      <div class="card titled"><div class="head">📤 Outbox / message log</div>
        <div class="body" id="ob-list" style="max-height:540px;overflow:auto">Loading…</div></div>
    </div>`);
  const loadOutbox = async () => {
    const rows = await api('/email/outbox');
    $('#ob-list').innerHTML = rows.length ? rows.map(r => `
      <div style="border-bottom:1px solid var(--frost);padding:10px 0">
        <span class="badge ${r.direction === 'outbound' ? 'b-in_progress' : 'b-chat'}">${r.direction}</span>
        <b>${esc(r.subject)}</b><br>
        <span class="small">${esc(r.from)} → ${esc(r.to)} · ${fmtDate(r.sent_at)} · ${r.ticket_id ? `<a href="#/ticket/${r.ticket_id}">${esc(r.ticket_id)}</a>` : ''}</span>
        <div class="small" style="white-space:pre-wrap;max-height:90px;overflow:hidden;color:var(--text)">${esc((r.body || '').slice(0, 400))}</div></div>`).join('')
      : '<div class="empty">No emails yet.</div>';
  };
  $('#ie-go').onclick = async () => {
    try {
      const out = await api('/email/inbound', { method:'POST', body:{ from_email: $('#ie-from').value,
        subject: $('#ie-sub').value, body: $('#ie-body').value } });
      $('#ie-out').innerHTML = `<div class="alert alert-success">${esc(out.note)} — <a href="#/ticket/${out.ticket_id}"><b class="mono">${esc(out.ticket_id)}</b></a></div>`;
      loadOutbox();
    } catch (e) { toast(e.message, 'err'); }
  };
  loadOutbox();
}

// ---------------- admin: SLA ----------------
async function viewSLA() {
  shell(`<h1>SLA Policies</h1><div class="card titled"><div class="head">Policies (matched at ticket creation by category + priority)</div><div class="body" id="sla">Loading…</div></div>`);
  const rows = await api('/sla-policies');
  $('#sla').innerHTML = `<table><tr><th>Category</th><th>Priority</th><th>First response</th><th>Resolution</th><th>Warning window</th></tr>
    ${rows.map(p => `<tr><td>${esc(p.category)}</td><td>${badge(p.priority)}</td><td>${p.response_minutes} min</td><td>${(p.resolution_minutes/60).toFixed(1)} h</td><td>${p.warning_minutes} min</td></tr>`).join('')}</table>`;
}

// ---------------- router ----------------
const ROUTES = {
  '#/login': viewLogin, '#/chat': viewChat, '#/submit': viewSubmit, '#/tickets': viewMyTickets,
  '#/queue': viewQueue, '#/agent': viewAgentDash, '#/approvals': viewApprovals,
  '#/reports': viewReports, '#/audit': viewAudit, '#/users': viewUsers, '#/kb': viewKB,
  '#/emailcenter': viewEmailCenter, '#/sla': viewSLA, '#/profile': viewProfile,
};
const PUBLIC_ROUTES = { '#/login': viewLogin, '#/signup': viewSignup, '#/forgot': viewForgot, '#/reset': viewReset };
async function render() {
  const base = (location.hash || '').split('?')[0];
  if (base === '#/sso') {           // Microsoft SSO callback hands us a session token
    const token = new URLSearchParams(location.hash.split('?')[1] || '').get('token');
    if (token) {
      TOKEN = token;
      try {
        USER = await api('/me');
        sessionStorage.setItem('sps_token', TOKEN); sessionStorage.setItem('sps_user', JSON.stringify(USER));
        location.hash = HOME[USER.role]; return;
      } catch { TOKEN = null; }
    }
    location.hash = '#/login'; return;
  }
  if (!TOKEN) { (PUBLIC_ROUTES[base] || viewLogin)(); return; }
  if (!META) { try { META = await api('/meta'); } catch { logout(); return; } }
  const hash = location.hash || HOME[USER.role];
  if (hash.startsWith('#/ticket/')) { viewTicket(hash.split('/')[2].split('?')[0]); return; }
  const view = ROUTES[hash.split('?')[0]];
  if (view) { try { await view(); } catch (e) { toast(e.message, 'err'); } }
  else { location.hash = HOME[USER.role]; }
}
window.addEventListener('hashchange', render);
window.logout = logout; window.decide = decide; window.downloadAtt = downloadAtt;

(function boot() {
  TOKEN = sessionStorage.getItem('sps_token');
  const u = sessionStorage.getItem('sps_user');
  if (TOKEN && u) USER = JSON.parse(u);
  else TOKEN = null;
  render();
})();
