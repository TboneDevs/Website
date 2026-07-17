#!/usr/bin/env python3
"""
CPM Web Tool - Fixed Version (Synchronous login)
"""

import asyncio
import os
import uuid
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from cpm_nuker import CPMNuker

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "change-this-to-a-secure-random-string-in-production")

nuker = CPMNuker()


def get_web_uid() -> int:
    if 'web_uid' not in session:
        web_uid = str(uuid.uuid4().int)[:12]
        session['web_uid'] = int(web_uid)
        session['email'] = None
    return session['web_uid']


def get_email():
    return session.get('email', 'Not logged in')


def run_async(coro):
    try:
        return asyncio.run(coro)
    except Exception as e:
        print(f"[ERROR] {e}")
        return {"ok": False, "message": str(e)}


@app.route('/')
def index():
    return render_template('index.html', email=get_email())


@app.route('/login', methods=['POST'])
def login():                    # ← Must NOT be async
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '').strip()

    if not email or not password:
        flash("Email and password are required.", "error")
        return redirect(url_for('index'))

    web_uid = get_web_uid()

    result = run_async(nuker.account_login(email, password))
    if not result.get("ok"):
        msg = result.get("message", "LOGIN_FAILED")
        flash(f"Login failed: {msg}", "error")
        return redirect(url_for('index'))

    nuker.save_token(web_uid, result["auth"], email, password, result.get("refresh_token", ""))
    loaded = run_async(nuker.load_account(web_uid, force=True))

    if loaded:
        session['email'] = email
        session['logged_in'] = True
        flash(f"✅ Successfully logged in as {email}", "success")
        return redirect(url_for('dashboard'))
    else:
        flash("Login succeeded but failed to load account data.", "error")
        return redirect(url_for('index'))


@app.route('/dashboard')
def dashboard():
    if not session.get('logged_in'):
        flash("Please log in first.", "error")
        return redirect(url_for('index'))

    web_uid = get_web_uid()
    email = session.get('email', 'Unknown')

    try:
        data = nuker.get_user_template(web_uid, email)
    except:
        data = {}

    return render_template(
        'dashboard.html',
        email=email,
        name=data.get('Name', 'Unknown'),
        pid=data.get('localID', 'N/A'),
        money=data.get('money', 0),
        coin=data.get('coin', 0)
    )


@app.route('/action/<action>', methods=['POST'])
def action(action):
    if not session.get('logged_in'):
        return jsonify({"ok": False, "message": "Not logged in"}), 401

    web_uid = get_web_uid()
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
    elif action == "unlock_equipments_male":
        result = run_async(nuker.unlock_equipments_male(web_uid))
    elif action == "unlock_equipments_female":
        result = run_async(nuker.unlock_equipments_female(web_uid))
    elif action == "set_rank":
        result = run_async(nuker.set_rank(web_uid))
    elif action == "fix_account":
        result = run_async(nuker.fix_account_data(web_uid))

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
    app.run(host="0.0.0.0", port=port, debug=False)
