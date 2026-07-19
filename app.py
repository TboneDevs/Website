from flask import Flask, request, render_template, redirect, url_for, session
import json
import os
import time
import cpm_nuker # Your original tool logic[span_1](start_span)[span_1](end_span)

app = Flask(__name__)
app.secret_key = 'your_secure_random_key_here' 

# File paths
TRACKER_FILE = 'tracker.json'
POOL_FILE = 'accounts_pool.json'
HOURS_24_IN_SECONDS = 24 * 3600

def load_json(filepath, default_data):
    if not os.path.exists(filepath): return default_data
    with open(filepath, 'r') as f: return json.load(f)

def save_json(filepath, data):
    with open(filepath, 'w') as f: json.dump(data, f, indent=4)

# --- PUBLIC ROUTES ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/premade-accounts')
def premade_accounts():
    claim_tracker = load_json(TRACKER_FILE, {})
    unclaimed_pool = load_json(POOL_FILE, [])
    client_ip = request.remote_addr
    current_time = time.time()
    
    if client_ip not in claim_tracker:
        claim_tracker[client_ip] = {'claimed': [], 'reset_time': current_time + HOURS_24_IN_SECONDS}
    if current_time >= claim_tracker[client_ip]['reset_time']:
        claim_tracker[client_ip] = {'claimed': [], 'reset_time': current_time + HOURS_24_IN_SECONDS}
    
    save_json(TRACKER_FILE, claim_tracker)
    user_data = claim_tracker[client_ip]
    return render_template('premade_accounts.html', claimed_accounts=user_data['claimed'], claims_left=5 - len(user_data['claimed']), pool_empty=len(unclaimed_pool) == 0)

@app.route('/claim-account', methods=['POST'])
def claim_account():
    claim_tracker = load_json(TRACKER_FILE, {})
    unclaimed_pool = load_json(POOL_FILE, [])
    client_ip = request.remote_addr
    if client_ip in claim_tracker and len(claim_tracker[client_ip]['claimed']) < 5 and len(unclaimed_pool) > 0:
        account = unclaimed_pool.pop(0)
        claim_tracker[client_ip]['claimed'].append(account)
        save_json(TRACKER_FILE, claim_tracker)
        save_json(POOL_FILE, unclaimed_pool)
    return redirect(url_for('premade_accounts'))

# --- PROTECTED TOOLS ROUTES ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        session['logged_in'] = True
        session['cpm_email'] = request.form.get('email')
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if not session.get('logged_in'): return redirect(url_for('login'))
    return render_template('dashboard.html')

@app.route('/modify-money', methods=['POST'])
def modify_money():
    if not session.get('logged_in'): return redirect(url_for('login'))
    cpm_nuker.modify_money(session.get('cpm_email'), request.form.get('amount'))
    return redirect(url_for('dashboard'))

@app.route('/modify-coins', methods=['POST'])
def modify_coins():
    if not session.get('logged_in'): return redirect(url_for('login'))
    cpm_nuker.modify_coins(session.get('cpm_email'), request.form.get('amount'))
    return redirect(url_for('dashboard'))

@app.route('/modify-levels', methods=['POST'])
def modify_levels():
    if not session.get('logged_in'): return redirect(url_for('login'))
    cpm_nuker.modify_levels(session.get('cpm_email'), request.form.get('level'))
    return redirect(url_for('dashboard'))

@app.route('/modify-achievements', methods=['POST'])
def modify_achievements():
    if not session.get('logged_in'): return redirect(url_for('login'))
    cpm_nuker.unlock_achievements(session.get('cpm_email'))
    return redirect(url_for('dashboard'))

@app.route('/modify-presents', methods=['POST'])
def modify_presents():
    if not session.get('logged_in'): return redirect(url_for('login'))
    cpm_nuker.inject_presents(session.get('cpm_email'))
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
    
