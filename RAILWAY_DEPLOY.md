# 🚂 Deploy SPS SecureDesk on Railway.app

Railway is easier than Render — no card loops, faster deploys. Let's go!

---

## Step 1: Sign up on Railway

1. Go to **https://railway.app**
2. Click **GitHub icon** (Sign up with GitHub)
3. It opens a GitHub window → **Authorize railway-app**
4. You land in Railway dashboard
5. ✅ Done

---

## Step 2: Create a new project

1. Click **+ New Project** (top area)
2. Select **Deploy from GitHub repo**
3. A window pops up to select your GitHub repo

---

## Step 3: Connect your GitHub repo

1. In the repo selection, type: `sps-securedesk`
2. You should see: `ibada0410/sps-securedesk`
3. Click it to select
4. Click **Deploy now** button

**Wait ~1-2 minutes** — it's cloning your repo.

---

## Step 4: Add PostgreSQL database

Once the repo is deployed, you see a **Project canvas** (looks like a flow diagram).

1. Click **+ Add** (or **+** button in the canvas area)
2. Select **Database**
3. Select **PostgreSQL**
4. Railway creates a PostgreSQL instance automatically
5. ✅ You now have a free PostgreSQL database

---

## Step 5: Get the database connection string

1. On the project canvas, click the **PostgreSQL box** (should show "postgres")
2. Click **Variables** tab (or look for it)
3. You should see several auto-generated variables:
   - `DATABASE_URL` ← **Copy this entire value**
   - `DATABASE_PUBLIC_URL`
   - `POSTGRES_*` etc.

4. **Copy the `DATABASE_URL`** value (it looks like):
   ```
   postgresql://user:password@host:5432/database
   ```

**Save it — you'll paste it in the next step.**

---

## Step 6: Configure your app with env variables

1. On the project canvas, click the **`sps-securedesk` box** (your web app)
2. Go to **Variables** tab
3. Click **Add Variable** (or **+ New Variable**)

**Add these 17 variables** (one by one):

### **Variable 1: DATABASE_URL**
- **Key:** `DATABASE_URL`
- **Value:** *(paste the PostgreSQL URL from Step 5)*
  ```
  postgresql://user:password@host:5432/database
  ```
- Click **Add**

### **Variable 2: JWT_SECRET_KEY**
- **Key:** `JWT_SECRET_KEY`
- **Value:** *(from your local .env file, or generate a new one)*
- Click **Add**

### **Variable 3: XAI_API_KEY**
- **Key:** `XAI_API_KEY`
- **Value:** *(from your local .env file)*
- Click **Add**

### **Variable 4: XAI_BASE_URL**
- **Key:** `XAI_BASE_URL`
- **Value:** `https://api.groq.com/openai/v1`
- Click **Add**

### **Variable 5: XAI_MODEL**
- **Key:** `XAI_MODEL`
- **Value:** `llama-3.3-70b-versatile`
- Click **Add**

### **Variable 6: HELPDESK_EMAIL**
- **Key:** `HELPDESK_EMAIL`
- **Value:** *(from your local .env file)*
- Click **Add**

### **Variable 7: SMTP_HOST**
- **Key:** `SMTP_HOST`
- **Value:** `smtp.gmail.com`
- Click **Add**

### **Variable 8: SMTP_PORT**
- **Key:** `SMTP_PORT`
- **Value:** `587`
- Click **Add**

### **Variable 9: SMTP_USER**
- **Key:** `SMTP_USER`
- **Value:** *(from your local .env file)*
- Click **Add**

### **Variable 10: SMTP_PASSWORD**
- **Key:** `SMTP_PASSWORD`
- **Value:** *(from your local .env file)*
- Click **Add**

### **Variable 11: SMTP_TLS**
- **Key:** `SMTP_TLS`
- **Value:** `true`
- Click **Add**

### **Variable 12: IMAP_HOST**
- **Key:** `IMAP_HOST`
- **Value:** `imap.gmail.com`
- Click **Add**

### **Variable 13: IMAP_USER**
- **Key:** `IMAP_USER`
- **Value:** *(from your local .env file)*
- Click **Add**

### **Variable 14: IMAP_PASSWORD**
- **Key:** `IMAP_PASSWORD`
- **Value:** *(from your local .env file)*
- Click **Add**

### **Variable 15: EMAIL_POLL_SECONDS**
- **Key:** `EMAIL_POLL_SECONDS`
- **Value:**
  ```
  120
  ```
- Click **Add**

### **Variable 16: APP_BASE_URL**
- **Key:** `APP_BASE_URL`
- **Value:** *(you'll get this from Railway after deploy, for now)*
  ```
  https://sps-securedesk.railway.app
  ```
- Click **Add**

### **Variable 17: PYTHONUNBUFFERED** (for logs)
- **Key:** `PYTHONUNBUFFERED`
- **Value:**
  ```
  1
  ```
- Click **Add**

✅ **All 17 variables added**

---

## Step 7: Check build & start commands

1. Still in the `sps-securedesk` box, look for **Settings** tab
2. Scroll down to find **Build Command** and **Start Command**

**Build Command should be:**
```
pip install -r requirements.txt
```

**Start Command should be:**
```
python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

*(If these are missing or blank, Railway might auto-detect them. Check the Deployments tab to see what it's using.)*

---

## Step 8: Deploy

Railway should auto-deploy after you add the variables.

1. Look for the **Deployments** tab in the `sps-securedesk` box
2. You should see a deployment in progress (spinning icon)
3. **Wait for it to finish** (~3-5 minutes)
4. Status should change to **✅ Success** (green check)

---

## Step 9: Get your live URL

Once deployment succeeds:

1. On the `sps-securedesk` box, click **Settings** (or look for URL)
2. You should see a **Domain** section with a generated URL like:
   ```
   https://sps-securedesk-production.up.railway.app
   ```
   *(or similar)*
3. **Copy this URL**
4. Click the URL → your app opens in a new tab

---

## Step 10: First time? Tables auto-create

When you first visit the app:
- Database tables are created automatically
- Demo users are seeded
- KB articles are added
- **Wait 10-15 seconds** if you see a blank page

---

## Step 11: Login and test

1. Open your Railway URL
2. Click **Sign In**
3. Login with:
   - Email: `admin@spsnet.com`
   - Password: `Admin@123`

✅ You should see the **Admin Dashboard**

---

## Step 12: Test the three channels

**📧 Email Center**
- Click **Email Center** (left sidebar)
- Scroll to "Simulate inbound email"
- Send a test email → ticket created

**📋 Form submission**
- Log in as `employee@spsnet.com` / `Employee@123`
- Click **Submit Request**
- Submit a form → ticket created

**💬 AI Chat**
- Log in as `intern@spsnet.com` / `Intern@123`
- Click **AI Chat**
- Ask: "How do I connect to the VPN?" → KB answer

✅ All three channels working!

---

## 🎉 You're live!

Your app is now deployed at Railway with:
- ✅ PostgreSQL database (Railway-hosted)
- ✅ All 17 environment variables configured
- ✅ Email (IMAP/SMTP) active
- ✅ AI (Groq) responding
- ✅ Free tier (no card charges ever)

---

## 📝 What to do next

### **Update APP_BASE_URL (optional but recommended)**

If you want email links in your app to work correctly:

1. Get your Railway domain (from Step 9)
2. Go back to **Variables** on the `sps-securedesk` box
3. Edit **APP_BASE_URL**
4. Change it to your actual Railway URL:
   ```
   https://sps-securedesk-production.up.railway.app
   ```
5. Save → auto-redeploy

This makes email links (password resets, ticket links) point to the correct domain.

---

## 🔧 Useful Railway features

**View logs:**
- Click `sps-securedesk` box → **Logs** tab
- See real-time app output

**Restart the app:**
- Click `sps-securedesk` box → **Settings** → **Restart**

**Check database:**
- Click PostgreSQL box → **Data** tab
- Browse tables and data

---

## 🚨 Troubleshooting

| Problem | Solution |
|---------|----------|
| Deployment stuck | Check **Deployments** tab → click to see error logs |
| Login fails | Wait 15-20 seconds, page might still be initializing |
| Blank page | Check browser console (F12) for errors |
| Email not working | Check variables are spelled correctly (case-sensitive!) |
| AI not responding | Verify XAI_API_KEY is valid |
| Database error | Ensure DATABASE_URL was copied completely (no truncation) |

---

## 💡 Pro tips

1. **Share your Railway URL** with reviewers — it's publicly accessible
2. **Monitor logs** if something breaks — Deployments tab shows error messages
3. **UptimeRobot** (optional) — add to keep the app active (though Railway doesn't sleep like Render)
4. **Scale up** — if you need more resources, Railway charges only for what you use (but free tier is plenty for a capstone)

---

## ✅ Success checklist

- [ ] GitHub connected to Railway
- [ ] PostgreSQL database created
- [ ] All 17 env variables set
- [ ] Deployment succeeded (green checkmark)
- [ ] Can access live URL
- [ ] Can login with `admin@spsnet.com` / `Admin@123`
- [ ] Email Center, Form, and Chat work
- [ ] Database auto-created with demo data

---

**Ready? Go to https://railway.app and start with Step 1!**

**Paste your live URL back here when it's ready.** 🚀
