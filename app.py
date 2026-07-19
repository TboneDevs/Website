import asyncio
from flask import Flask, request, render_template, redirect, url_for, session, flash
from cpm_nuker import CPMNuker

app = Flask(__name__)
app.secret_key = 'your_super_secret_key_here' # Change this to a random string

nuker = CPMNuker()

# --- ROUTES ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email')
    password = request.form.get('password')
    
    # Perform login
    result = asyncio.run(nuker.account_login(email, password))
    
    if result.get("ok"):
        session['logged_in'] = True
        session['cpm_email'] = email
        # Store the UID (localId) from the login response for future requests
        session['cpm_uid'] = int(result.get('localId')) 
        
        # Save token for persistence
        nuker.save_token(session['cpm_uid'], result['auth'], email, password, result.get('refresh_token'))
        return redirect(url_for('dashboard'))
    else:
        return f"Login Failed: {result.get('message')}"

@app.route('/dashboard')
def dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('index'))
    return render_template('dashboard.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# --- MODIFICATION ROUTES ---

@app.route('/modify-money', methods=['POST'])
def modify_money():
    if not session.get('logged_in'): return redirect(url_for('login'))
    uid = session.get('cpm_uid')
    amount = int(request.form.get('amount'))
    asyncio.run(nuker.set_money(uid, amount))
    return redirect(url_for('dashboard'))

@app.route('/modify-coins', methods=['POST'])
def modify_coins():
    if not session.get('logged_in'): return redirect(url_for('login'))
    uid = session.get('cpm_uid')
    amount = int(request.form.get('amount'))
    asyncio.run(nuker.set_coin(uid, amount))
    return redirect(url_for('dashboard'))

@app.route('/modify-achievements', methods=['POST'])
def modify_achievements():
    if not session.get('logged_in'): return redirect(url_for('login'))
    uid = session.get('cpm_uid')
    asyncio.run(nuker.unlock_achievements(uid))
    return redirect(url_for('dashboard'))

@app.route('/modify-levels', methods=['POST'])
def modify_levels():
    if not session.get('logged_in'): return redirect(url_for('login'))
    uid = session.get('cpm_uid')
    asyncio.run(nuker.complete_all_levels(uid))
    return redirect(url_for('dashboard'))

@app.route('/modify-animations', methods=['POST'])
def modify_animations():
    if not session.get('logged_in'): return redirect(url_for('login'))
    uid = session.get('cpm_uid')
    asyncio.run(nuker.unlock_animations(uid))
    return redirect(url_for('dashboard'))

@app.route('/modify-wheels', methods=['POST'])
def modify_wheels():
    if not session.get('logged_in'): return redirect(url_for('login'))
    uid = session.get('cpm_uid')
    asyncio.run(nuker.unlock_wheels(uid))
    return redirect(url_for('dashboard'))

@app.route('/modify-houses', methods=['POST'])
def modify_houses():
    if not session.get('logged_in'): return redirect(url_for('login'))
    uid = session.get('cpm_uid')
    asyncio.run(nuker.unlock_houses(uid))
    return redirect(url_for('dashboard'))

@app.route('/modify-smoke', methods=['POST'])
def modify_smoke():
    if not session.get('logged_in'): return redirect(url_for('login'))
    uid = session.get('cpm_uid')
    asyncio.run(nuker.unlock_smoke(uid))
    return redirect(url_for('dashboard'))

@app.route('/modify-name', methods=['POST'])
def modify_name():
    if not session.get('logged_in'): return redirect(url_for('login'))
    uid = session.get('cpm_uid')
    name = request.form.get('name')
    asyncio.run(nuker.set_player_name(uid, name))
    return redirect(url_for('dashboard'))

@app.route('/modify-id', methods=['POST'])
def modify_id():
    if not session.get('logged_in'): return redirect(url_for('login'))
    uid = session.get('cpm_uid')
    pid = request.form.get('pid')
    asyncio.run(nuker.set_player_id(uid, pid))
    return redirect(url_for('dashboard'))

@app.route('/modify-rank', methods=['POST'])
def modify_rank():
    if not session.get('logged_in'): return redirect(url_for('login'))
    uid = session.get('cpm_uid')
    asyncio.run(nuker.set_rank(uid))
    return redirect(url_for('dashboard'))

@app.route('/fix-data', methods=['POST'])
def fix_data():
    if not session.get('logged_in'): return redirect(url_for('login'))
    uid = session.get('cpm_uid')
    asyncio.run(nuker.fix_account_data(uid))
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)
    
