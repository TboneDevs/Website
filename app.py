import time
import json
import os
from flask import Flask, request, render_template, redirect, url_for, session

app = Flask(__name__)
# Secret key is required for session management
app.secret_key = 'your_secret_key_here' 

# File paths
TRACKER_FILE = 'tracker.json'
POOL_FILE = 'accounts_pool.json'
HOURS_24_IN_SECONDS = 24 * 3600

# [Functions load_json and save_json remain the same]
def load_json(filepath, default_data):
    if not os.path.exists(filepath):
        save_json(filepath, default_data)
        return default_data
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except:
        return default_data 

def save_json(filepath, data):
    try:
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=4)
    except:
        pass 

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handles authentication for users to edit game information."""
    if request.method == 'POST':
        # Your authentication logic goes here (e.g., verifying a password or token)
        # session['logged_in'] = True 
        # return redirect(url_for('dashboard'))
        pass 
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

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
    claims_left = 5 - len(user_data['claimed'])
    pool_empty = len(unclaimed_pool) == 0
    
    seconds_left = max(0, user_data['reset_time'] - current_time)
    hours = int(seconds_left // 3600)
    minutes = int((seconds_left % 3600) // 60)
    time_left_str = f"{hours}h {minutes}m"
    
    return render_template('premade_accounts.html', 
                           claimed_accounts=user_data['claimed'], 
                           claims_left=claims_left, 
                           pool_empty=pool_empty, 
                           time_left_str=time_left_str)

@app.route('/claim-account', methods=['POST'])
def claim_account():
    claim_tracker = load_json(TRACKER_FILE, {})
    unclaimed_pool = load_json(POOL_FILE, [])
    client_ip = request.remote_addr
    current_time = time.time()
    
    if client_ip not in claim_tracker:
        claim_tracker[client_ip] = {'claimed': [], 'reset_time': current_time + HOURS_24_IN_SECONDS}
        
    user_data = claim_tracker[client_ip]
    
    if len(user_data['claimed']) < 5 and len(unclaimed_pool) > 0:
        account = unclaimed_pool.pop(0) 
        account['status'] = 'Claimed'
        user_data['claimed'].append(account) 
        save_json(TRACKER_FILE, claim_tracker)
        save_json(POOL_FILE, unclaimed_pool)
        
    return redirect(url_for('premade_accounts'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
    
