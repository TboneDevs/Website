#!/usr/bin/env python3
"""
CPM Web Tool - Railway Ready
Public website version: Anyone can use the core modification features.
No Telegram bot, no admin system, no tokens stored long-term beyond session.
"""

import asyncio
import os
import uuid
from datetime import datetime

from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, session, jsonify
)
from cpm_nuker import CPMNuker

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "change-this-to-a-secure-random-string-in-production")
app.config['SESSION_TYPE'] = 'filesystem'  # Simple, works on Railway without extra deps

nuker = CPMNuker()

# In-memory mapping: web_session_id -> nuker user_id (for this process)
# For production with multiple workers, better to store web_uid in session and always use it
WEB_SESSIONS = {}


def get_web_uid() -> int:
    """Get or create a stable user id for this browser session."""
    if 'web_uid' not in session:
        web_uid = str(uuid.uuid4().int)[:12]  # short numeric id
        session['web_uid'] = int(web_uid)
        session['email'] = None
    return session['web_uid']


def get_email() -> str:
    return session.get('email', 'Not logged in')


@app.route('/')
def index():
    """Landing page with big warning + login form."""
    return render_template('index.html', email=get_email())


@app.route('/login', methods=['POST'])
async def login():
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '').strip()

    if not email or not password:
        flash("Email and password are required.", "error")
        return redirect(url_for('index'))

    web_uid = get_web_uid()

    # Login to CPM
    result = await nuker.account_login(email, password)
    if not result.get("ok"):
        msg = result.get("message", "LOGIN_FAILED")
        flash(f"Login failed: {msg}", "error")
        return redirect(url_for('index'))

    # Save token + load real account data
    nuker.save_token(web_uid, result["auth"], email, password, result.get("refresh_token", ""))
    loaded = await nuker.load_account(web_uid, force=True)

    if loaded:
        session['email'] = email
        session['logged_in'] = True
        flash(f"✅ Successfully logged in as {email}", "success")
        return redirect(url_for('dashboard'))
    else:
        flash("Login succeeded but could not load account data. Try again.", "error")
        return redirect(url_for('index'))


@app.route('/dashboard')
def dashboard():
    if not session.get('logged_in'):
        flash("Please log in first.", "error")
        return redirect(url_for('index'))

    web_uid = get_web_uid()
    email = session.get('email', 'Unknown')

    # Try to get cached data
    try:
        data = nuker.get_user_template(web_uid, email)
    except:
        data = {}

    money = data.get('money', 0)
    coin = data.get('coin', 0)
    name = data.get('Name', 'Unknown')
    pid = data.get('localID', 'N/A')

    return render_template(
        'dashboard.html',
        email=email,
        name=name,
        pid=pid,
        money=money,
        coin=coin,
        web_uid=web_uid
    )


def run_async(coro):
    """Helper to run async nuker methods from Flask routes."""
    try:
        return asyncio.run(coro)
    except Exception as e:
        print(f"Async error: {e}")
        return {"ok": False, "message": str(e)}


@app.route('/action/<action>', methods=['POST'])
def action(action):
    if not session.get('logged_in'):
        return jsonify({"ok": False, "message": "Not logged in"}), 401

    web_uid = get_web_uid()
    email = session.get('email')

    result = {"ok": False, "message": "Unknown action"}

    if action == "set_money":
        amount = int(request.form.get('amount', 0))
        result = run_async(nuker.set_money(web_uid, amount))

    elif action == "set_coin":
        amount = int(request.form.get('amount', 0))
        result = run_async(nuker.set_coin(web_uid, amount))

    elif action == "set_name":
        new_name = request.form.get('name', '').strip()
        result = run_async(nuker.set_player_name(web_uid, new_name))

    elif action == "set_pid":
        new_pid = request.form.get('pid', '').strip().upper()
        result = run_async(nuker.set_player_id(web_uid, new_pid))

    elif action == "set_wins":
        amount = int(request.form.get('amount', 0))
        result = run_async(nuker.set_race_wins(web_uid, amount))

    elif action == "set_loses":
        amount = int(request.form.get('amount', 0))
        result = run_async(nuker.set_race_loses(web_uid, amount))

    elif action == "unlock_w16":
        result = run_async(nuker.unlock_w16(web_uid))

    elif action == "unlock_horns":
        result = run_async(nuker.unlock_horns(web_uid))

    elif action == "disable_damage":
        result = run_async(nuker.disable_damage(web_uid))

    elif action == "unlimited_fuel":
        result = run_async(nuker.unlimited_fuel(web_uid))

    elif action == "unlock_smoke":
        result = run_async(nuker.unlock_smoke(web_uid))

    elif action == "unlock_animations":
        result = run_async(nuker.unlock_animations(web_uid))

    elif action == "unlock_wheels":
        result = run_async(nuker.unlock_wheels(web_uid))

    elif action == "unlock_houses":
        result = run_async(nuker.unlock_houses(web_uid))

    elif action == "complete_levels":
        result = run_async(nuker.complete_all_levels(web_uid))

    elif action == "unlock_male":
        result = run_async(nuker.unlock_equipments_male(web_uid))

    elif action == "unlock_female":
        result = run_async(nuker.unlock_equipments_female(web_uid))

    elif action == "set_rank":
        result = run_async(nuker.set_rank(web_uid))

    elif action == "fix_account":
        result = run_async(nuker.fix_account_data(web_uid))

    elif action == "preset_starter":
        r1 = run_async(nuker.set_money(web_uid, 1_000_000))
        r2 = run_async(nuker.set_coin(web_uid, 100_000))
        result = {"ok": r1.get("ok") and r2.get("ok")}

    elif action == "preset_pro":
        r1 = run_async(nuker.set_money(web_uid, 25_000_000))
        r2 = run_async(nuker.set_coin(web_uid, 250_000))
        r3 = run_async(nuker.set_rank(web_uid))
        result = {"ok": r1.get("ok") and r2.get("ok") and r3.get("ok")}

    elif action == "preset_max":
        r1 = run_async(nuker.set_money(web_uid, 50_000_000))
        r2 = run_async(nuker.set_coin(web_uid, 500_000))
        r3 = run_async(nuker.set_rank(web_uid))
        r4 = run_async(nuker.unlock_w16(web_uid))
        r5 = run_async(nuker.disable_damage(web_uid))
        result = {"ok": all([r1.get("ok"), r2.get("ok"), r3.get("ok"), r4.get("ok"), r5.get("ok")])}

    elif action == "unlock_all":
        # This one is heavier - we can run it
        feats = [
            nuker.unlock_w16(web_uid),
            nuker.unlock_horns(web_uid),
            nuker.disable_damage(web_uid),
            nuker.unlimited_fuel(web_uid),
            nuker.unlock_smoke(web_uid),
            nuker.unlock_animations(web_uid),
            nuker.unlock_wheels(web_uid),
            nuker.unlock_houses(web_uid),
            nuker.complete_all_levels(web_uid),
            nuker.unlock_equipments_male(web_uid),
            nuker.unlock_equipments_female(web_uid),
            nuker.set_rank(web_uid),
        ]
        results = [run_async(f) for f in feats]
        result = {"ok": all(r.get("ok", False) for r in results)}

    else:
        result = {"ok": False, "message": "Invalid action"}

    if result.get("ok"):
        flash(f"✅ {action.replace('_', ' ').title()} completed successfully!", "success")
    else:
        flash(f"❌ Failed: {result.get('message', 'Unknown error')}", "error")

    return redirect(url_for('dashboard'))


@app.route('/logout')
def logout():
    web_uid = session.get('web_uid')
    if web_uid:
        try:
            nuker.delete_token(web_uid)
        except:
            pass
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for('index'))


@app.route('/health')
def health():
    return "✅ CPM Web Tool is running", 200


if __name__ == '__main__':
    port = int(os.getenv("PORT", 8080))
    print(f"🚀 Starting CPM Web Tool on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
