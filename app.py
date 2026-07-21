#!/usr/bin/env python3
"""TNNR CPM1 Webtool - Original working logic + full unlocks"""

import asyncio
import os
import uuid
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from cpm_nuker import CPMNuker

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "change-this-to-a-secure-random-string-in-production")
nuker = CPMNuker()


def get_web_uid() -> int:
    if "web_uid" not in session:
        session["web_uid"] = int(str(uuid.uuid4().int)[:12])
        session["email"] = None
    return session["web_uid"]


def run_async(coro):
    try:
        return asyncio.run(coro)
    except Exception as e:
        print(f"[ERROR] {e}")
        return {"ok": False, "message": str(e)}


@app.route("/")
def index():
    return render_template("index.html", email=session.get("email", "Not logged in"))


@app.route("/login", methods=["POST"])
def login():
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "").strip()
    if not email or not password:
        flash("Email and password are required.", "error")
        return redirect(url_for("index"))

    web_uid = get_web_uid()
    result = run_async(nuker.account_login(email, password))
    if not result.get("ok"):
        flash(f"Login failed: {result.get('message', 'LOGIN_FAILED')}", "error")
        return redirect(url_for("index"))

    nuker.save_token(web_uid, result["auth"], email, password, result.get("refresh_token", ""))
    loaded = run_async(nuker.load_account(web_uid, force=True))
    session["email"] = email
    session["logged_in"] = True

    if loaded:
        flash(f"✅ Successfully logged in as {email}", "success")
    flash(
        "ℹ️ Important: Logout of the game first, then run unlocks here. "
        "Once the site shows successful, log back into the game.",
        "info",
    )
    return redirect(url_for("dashboard"))


@app.route("/dashboard")
def dashboard():
    if not session.get("logged_in"):
        flash("Please log in first.", "error")
        return redirect(url_for("index"))

    web_uid = get_web_uid()
    email = session.get("email", "Unknown")
    try:
        data = nuker.get_user_template(web_uid, email)
    except Exception:
        data = {}

    return render_template(
        "dashboard.html",
        email=email,
        name=data.get("Name", "Unknown"),
        pid=data.get("localID", "N/A"),
        money=data.get("money", 0),
        coin=data.get("coin", 0),
    )


@app.route("/action/<action>", methods=["POST"])
def action(action):
    if not session.get("logged_in"):
        return jsonify({"ok": False, "message": "Not logged in"}), 401

    web_uid = get_web_uid()
    result = {"ok": False, "message": "Unknown action"}

    try:
        if action == "set_money":
            amount = int(request.form.get("amount", 0) or 0)
            result = run_async(nuker.set_money(web_uid, amount))

        elif action == "set_coin":
            amount = int(request.form.get("amount", 0) or 0)
            result = run_async(nuker.set_coin(web_uid, amount))

        elif action == "set_race_wins":
            amount = int(request.form.get("amount", 0) or 0)
            result = run_async(nuker.set_race_wins(web_uid, amount))

        elif action == "set_rank":
            result = run_async(nuker.set_rank(web_uid))

        elif action == "complete_levels":
            result = run_async(nuker.complete_all_levels(web_uid))

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

        elif action == "unlock_equipments_male":
            result = run_async(nuker.unlock_equipments_male(web_uid))

        elif action == "unlock_equipments_female":
            result = run_async(nuker.unlock_equipments_female(web_uid))

        elif action == "preset_50m_30k":
            r1 = run_async(nuker.set_money(web_uid, 50_000_000))
            r2 = run_async(nuker.set_coin(web_uid, 30_000))
            result = {"ok": r1.get("ok") and r2.get("ok")}

        elif action == "preset_50m_50k":
            r1 = run_async(nuker.set_money(web_uid, 50_000_000))
            r2 = run_async(nuker.set_coin(web_uid, 50_000))
            result = {"ok": r1.get("ok") and r2.get("ok")}

        elif action == "preset_50m_100k":
            r1 = run_async(nuker.set_money(web_uid, 50_000_000))
            r2 = run_async(nuker.set_coin(web_uid, 100_000))
            result = {"ok": r1.get("ok") and r2.get("ok")}

        elif action == "preset_50m_500k":
            r1 = run_async(nuker.set_money(web_uid, 50_000_000))
            r2 = run_async(nuker.set_coin(web_uid, 500_000))
            result = {"ok": r1.get("ok") and r2.get("ok")}

        elif action == "full_unlock":
            results = [
                run_async(nuker.set_money(web_uid, 50_000_000)),
                run_async(nuker.set_coin(web_uid, 30_000)),
                run_async(nuker.set_race_wins(web_uid, 670000)),
                run_async(nuker.set_rank(web_uid)),
                run_async(nuker.complete_all_levels(web_uid)),
                run_async(nuker.unlock_w16(web_uid)),
                run_async(nuker.unlock_horns(web_uid)),
                run_async(nuker.disable_damage(web_uid)),
                run_async(nuker.unlimited_fuel(web_uid)),
                run_async(nuker.unlock_smoke(web_uid)),
                run_async(nuker.unlock_animations(web_uid)),
                run_async(nuker.unlock_wheels(web_uid)),
                run_async(nuker.unlock_houses(web_uid)),
                run_async(nuker.unlock_equipments_male(web_uid)),
                run_async(nuker.unlock_equipments_female(web_uid)),
            ]
            result = {"ok": all(r.get("ok") for r in results)}

    except Exception as e:
        result = {"ok": False, "message": str(e)}

    if result.get("ok"):
        # Force refresh cached account data for dashboard display
        try:
            run_async(nuker.load_account(web_uid, force=True))
        except Exception:
            pass
        flash(f"✅ {action.replace('_', ' ').title()} completed successfully!", "success")
    else:
        flash(f"❌ Failed: {result.get('message', 'Unknown error')}", "error")
    return redirect(url_for("dashboard"))


@app.route("/logout")
def logout():
    web_uid = session.get("web_uid")
    if web_uid:
        try:
            nuker.delete_token(web_uid)
        except Exception:
            pass
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))


@app.route("/health")
def health():
    return "✅ TNNR CPM1 Webtool is running", 200


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    print(f"🚀 Starting TNNR CPM1 Webtool on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
