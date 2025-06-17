# 🚀 Manual GitHub Deployment Instructions

## Your repository: https://github.com/rittes91/rifty50

### Step 1: Get Personal Access Token

1. **Go to:** https://github.com/settings/tokens
2. **Click:** "Generate new token (classic)"
3. **Name:** "Nifty50 Deployment"
4. **Expiration:** 90 days
5. **Scopes:** Select these checkboxes:
   - ✅ `repo` (Full control of private repositories)
   - ✅ `workflow` (Update GitHub Action workflows)
6. **Click:** "Generate token"
7. **COPY the token** (starts with `ghp_`)

### Step 2: Push Code

**Option A: Command Line (Copy and paste this command)**
```powershell
git push -u origin main
```
When prompted:
- **Username:** `rittes91`
- **Password:** `[PASTE YOUR TOKEN HERE]`

**Option B: Use Git Credential Manager**
```powershell
git config --global credential.helper manager-core
git push -u origin main
```

**Option C: Direct URL method**
Replace `YOUR_TOKEN_HERE` with your actual token:
```powershell
git remote set-url origin https://rittes91:YOUR_TOKEN_HERE@github.com/rittes91/rifty50.git
git push -u origin main
```

### Step 3: Verify Deployment

After successful push, check: https://github.com/rittes91/rifty50

You should see all your files including:
- ✅ README.md with project documentation
- ✅ app.py (Flask web application)
- ✅ telegram_bot.py (Telegram bot)
- ✅ requirements.txt (Dependencies)
- ✅ templates/ folder
- ✅ LICENSE file

### Step 4: Deploy to Cloud Platform

Choose one of these platforms:

#### **Render (Free - Recommended)**
1. Go to https://render.com
2. Connect your GitHub account
3. Select your `rifty50` repository
4. Configure:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python app.py`
   - **Environment Variables:**
     - `TELEGRAM_BOT_TOKEN` = Your bot token
     - `PORT` = 5000

#### **Railway (Free)**
1. Go to https://railway.app
2. Connect GitHub
3. Deploy from `rifty50` repository
4. Set environment variables

#### **Heroku (Paid)**
1. Install Heroku CLI
2. `heroku create nifty50-analysis`
3. `git push heroku main`
4. `heroku config:set TELEGRAM_BOT_TOKEN=your_token`

### Step 5: Set Environment Variables

After deployment, set these environment variables:

```
TELEGRAM_BOT_TOKEN=7705078747:AAG5mAf8YnyJ3wl7zIZIJ8dghajfv4kFDqE
TELEGRAM_CHAT_ID=your_chat_id (optional)
PORT=5000
```

### Your Project Features:

🎯 **What you've built:**
- ✅ Real-time Nifty 50 technical analysis
- ✅ Telegram bot (@rifty50_bot) with commands
- ✅ Web dashboard with live signals
- ✅ REST API for signal data
- ✅ Multiple technical indicators (RSI, MACD, Bollinger Bands)
- ✅ Automated analysis every 15 minutes
- ✅ SQLite database for signal storage

🚀 **Live URLs after deployment:**
- **Web Dashboard:** https://your-app.render.com
- **API Endpoint:** https://your-app.render.com/api/latest-signals
- **Telegram Bot:** t.me/rifty50_bot

🎉 **You're ready to go live!**

---

**If you encounter any issues:**
1. Verify your Personal Access Token has correct permissions
2. Make sure you're using the token as password (not your GitHub password)
3. Check that the repository exists: https://github.com/rittes91/rifty50
4. Try clearing browser cache and retrying authentication

