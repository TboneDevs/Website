# Project entrypoint for Car Parking Multiplayer account modifier
# Structure:
# - app.py (this file) sits at the project root and expects a sibling `templates/` folder.
# - templates/ contains Jinja2 templates: base.html, index.html, dashboard.html
# - cpm_nuker.py contains the async CPM-related calls; app.py calls them synchronously via asyncio.run()
# Note: For production, set a secure FLASK secret key via environment variables instead of the hard-coded default below.

from flask import Flask, render_template, request, redirect, url_for, flash, session
import asyncio
import os
import cpm_nuker

app = Flask(__name__)
# Change this in production (use environment variable)
app.secret_key = os.environ.get('FLASK_SECRET', 'change-me')

# Helper to run async CPM calls synchronously in Flask routes
def run_async(coro):
    return asyncio.run(coro)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    if not username or not password:
        flash('Username and password are required')
        return redirect(url_for('index'))

    result = run_async(cpm_nuker.login(username, password))
    if result.get('success'):
        session['user'] = username
        flash('Login successful')
        return redirect(url_for('dashboard'))

    flash(result.get('error', 'Login failed'))
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('index'))
    return render_template('dashboard.html', user=session.get('user'))

@app.route('/do_action', methods=['POST'])
def do_action():
    if 'user' not in session:
        flash('Please login first')
        return redirect(url_for('index'))

    action = request.form.get('action')

    if action == 'add_money':
        try:
            amount = int(request.form.get('amount', 0))
        except ValueError:
            amount = 0
        res = run_async(cpm_nuker.add_money(session.get('user'), amount))
        flash(res.get('message', 'Money updated'))

    elif action == 'add_coins':
        try:
            amount = int(request.form.get('amount', 0))
        except ValueError:
            amount = 0
        res = run_async(cpm_nuker.add_coins(session.get('user'), amount))
        flash(res.get('message', 'Coins updated'))

    elif action == 'unlock_all':
        res = run_async(cpm_nuker.unlock_all(session.get('user')))
        flash(res.get('message', 'Unlock complete'))

    elif action == 'preset':
        name = request.form.get('preset_name')
        res = run_async(cpm_nuker.apply_preset(session.get('user'), name))
        flash(res.get('message', 'Preset applied'))

    else:
        flash('Unknown action')

    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    # Use 0.0.0.0 so Railway and other hosts can bind
    app.run(host='0.0.0.0', port=port)
