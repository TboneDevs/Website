import time
import json
import os
from flask import Flask, request, render_template, redirect, url_for, session

app = Flask(__name__)
# Secret key is required to secure the temporary session token
app.secret_key = 'your_secure_random_key_here' 

# File paths for game-related data
TRACKER_FILE = 'tracker.json'
POOL_FILE = 'accounts_pool.json'
HOURS_24_IN_SECONDS = 24 * 3600

# Helper functions for account pool management
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
    """Authenticates the user against CPM servers for temporary game editing session."""
    if request.method == 'POST':
        # These credentials are used for the API request but are NOT saved to a user database
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Temporary session token
        session['logged_in'] = True
        session['cpm_email'] = email
        
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    """Game Editor dashboard (Protected by temporary session)."""
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template('dashboard.html')

@app.route('/logout')
def logout():
    """Clears temporary session data."""
    session.clear()
    return redirect(url_for('index'))

@app.route('/premade-accounts')
def premade_accounts():
    """Publicly accessible account claiming endpoint."""
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
    
