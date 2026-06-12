# 🚨 Render Deployment Troubleshooting

## Issue: Card entry loops / stuck at payment screen

### **Quick fixes (try in order)**

#### **Fix 1: Clear browser cache**
1. Open Render.com in **Incognito/Private window** (Ctrl+Shift+N)
2. Sign in again
3. Try adding card again

#### **Fix 2: Use a different browser**
- Try Chrome, Edge, or Firefox instead
- Cache/cookies might be blocking

#### **Fix 3: Verify your Render account first**
1. Go to Render dashboard → **Account Settings** (gear icon, top-right)
2. Look for **"Billing"** or **"Payment method"** section
3. Add card there first (before creating Web Service)
4. Verify email if needed
5. Then try Web Service creation

#### **Fix 4: Try a different card**
- Card might be flagged as suspicious
- Try Visa instead of Mastercard, or vice versa
- Try a card from a different bank

---

## ⚠️ If Render still doesn't work: **Alternative FREE deployment**

### **Option A: Railway.app (RECOMMENDED — easiest)**

Railway is almost identical to Render but often has fewer card issues.

**Step 1: Go to Railway**
1. Open **https://railway.app**
2. Click **Sign up with GitHub**
3. Authorize GitHub

**Step 2: Create new project**
1. Click **New Project**
2. Select **Deploy from GitHub repo**
3. Find and select `sps-securedesk`

**Step 3: Add PostgreSQL database**
1. Click **+ New** (in the Project canvas)
2. Select **Database** → **PostgreSQL**
3. It auto-generates a `DATABASE_URL`

**Step 4: Add environment variables**
1. Click on your web service (the repo box)
2. Go to **Variables** tab
3. Add all 16 env vars (same as Render list above)
4. For **DATABASE_URL**: use the one Railway generated (starts with `postgresql://`)

**Step 5: Deploy**
1. Click **Deploy** button
2. Watch logs (usually done in 2-3 min)
3. You get a public `.railway.app` URL

**Railway is free tier:** 5GB storage, 512MB RAM — perfectly fine for SPS SecureDesk.

---

### **Option B: Heroku alternative (Koyeb or Cyclic)**

If Railway doesn't work either:

- **Koyeb** (https://koyeb.com) — free tier, similar to Render
- **Cyclic** (https://cyclic.sh) — free tier, Node-based but has Python support

Both follow similar steps to Render.

---

### **Option C: Run locally + share with Cloudflare tunnel (instant)**

If you want to demo it RIGHT NOW without waiting for Render:

```bash
python -m uvicorn app.main:app --port 8000
```

Then in another PowerShell window:

```bash
cloudflared tunnel --url http://localhost:8000
```

You get a public `*.trycloudflare.com` URL instantly. Share it with reviewers.

---

## ✅ Recommended: **Railway.app (try this first)**

1. Go to https://railway.app
2. Sign up with GitHub
3. New Project → Deploy from GitHub → select `sps-securedesk`
4. Add PostgreSQL → copy the `DATABASE_URL`
5. Add all 16 env vars (use Neon string OR Railway's PostgreSQL)
6. Deploy → get live URL in 2-3 min

Railway has fewer card issues than Render. Try it.

---

## 📱 If you want to stick with Render:

**Contact Render support:**
1. Go to Render dashboard
2. Click **Help** (bottom-left)
3. Chat with support → explain "card entry loops"
4. They can manually verify your account

---

## For now: Share locally

While you sort out deployment, you can demo the app locally and share with a tunnel:

```bash
# Terminal 1: Start app
python -m uvicorn app.main:app --port 8000

# Terminal 2: Create public tunnel
cloudflared tunnel --url http://localhost:8000
```

You get a URL like: `https://xyz123.trycloudflare.com`

Share this with reviewers — it works for hours.

---

**Let me know which option you pick and I'll walk you through it!**
