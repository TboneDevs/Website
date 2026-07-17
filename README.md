# 🚗 CPM Web Tool - Railway Edition

A clean web interface for modifying your **Car Parking Multiplayer** account directly from the browser. No Telegram bot required.

## ✨ Features

- Login with your CPM email & password
- View current money, coins, name, and player ID
- Set money (up to $50M) and coins (up to 500K)
- One-click feature unlocks: W16, Horns, No Damage, Unlimited Fuel, Smoke, Animations, Wheels, Houses, All Levels, Male/Female outfits, Max Rank
- Quick presets: **Starter**, **Pro**, and **Max**
- "Unlock Everything" button
- Fix account bugs
- Change player name and ID
- Clean, modern, mobile-friendly UI (Tailwind)

## 🚀 Deploy on Railway (Recommended)

1. Push this folder to a GitHub repository.

2. On [Railway.app](https://railway.app):
   - New Project → Deploy from GitHub
   - Select this repo

3. (Optional but recommended) Add a **Volume** for persistent token storage (`cpm_tokens.db`).

4. Deploy. Railway will automatically use `Procfile`, `runtime.txt`, and `requirements.txt`.

The app will be live at your Railway URL and anyone can use it (no login required to access the tool).

## 🛠 Local Development

```bash
git clone <your-repo>
cd cpm-web-app

python -m venv venv
source venv/bin/activate

pip install -r requirements.txt

# Optional: set a secret key
export FLASK_SECRET_KEY="super-secret-key-here"

python app.py
```

Open http://localhost:8080

## ⚠️ Important Security & Legal Notes

- This tool **logs into your CPM account** using your real email and password.
- Passwords are processed in memory only and **never stored** after the request.
- You are fully responsible for any account modifications or bans.
- This is for **personal / educational use only**.
- Do **not** use this on accounts with real money or sentimental value.
- The developers are not affiliated with Car Parking Multiplayer.

## Project Structure

```
cpm-web-app/
├── app.py                 # Flask web application
├── cpm_nuker.py           # Core CPM game interaction logic (async)
├── requirements.txt
├── Procfile
├── runtime.txt
├── README.md
├── templates/
│   ├── base.html
│   ├── index.html         # Login + warning page
│   └── dashboard.html     # Main control panel
└── cpm_tokens.db          # Created automatically (SQLite)
```

## How It Works

1. User enters CPM email + password on the landing page.
2. The server logs into the official CPM servers using the same protocol as the game.
3. Real account data is fetched and cached.
4. Any modification (money, unlocks, etc.) is sent back to the CPM servers.
5. The dashboard always shows the latest state after each action.

---

Built with ❤️ for the CPM community. Use responsibly.
