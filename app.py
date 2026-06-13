import os
import io
import base64
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
import pyotp
import qrcode

app = Flask(__name__)
app.secret_key = os.urandom(24)

xcfg = {
    "passkey_login_enabled": True, # Toggle to enable/disable passkey registration/login flows in the UI
    "password_login_enabled": False, # Toggle to enable/disable password-based login flows in the UI
}

@app.context_processor
def inject_xcfg():
    return {"xcfg": xcfg}

# Mock Database (In-Memory)
# Format: "username": {"password": "password123", "totp_secret": "BASE32SECRET...", "mfa_enabled": False}
DB_USERS = {
    "user1": {
        "password": "password123",
        "totp_secret": pyotp.random_base32(), # Pre-generate a unique secret for this user
        "mfa_enabled": False,
        "passkeys": []
    }
}


def _b64url_encode(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode('utf-8')


def _b64url_decode(s: str) -> bytes:
    padding = '=' * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + padding)


# --- Simple WebAuthn / Passkey demo endpoints (minimal, not production-safe) ---
@app.route('/register/begin', methods=['POST'])
def register_begin():
    data = request.get_json() or {}
    username = data.get('username')
    if not username:
        return {"error": "missing username"}, 400

    if not xcfg['passkey_login_enabled']:
        return {"error": "passkey registration is disabled"}, 400

    # Ensure user record exists
    if username not in DB_USERS:
        DB_USERS[username] = {
            "password": "",
            "totp_secret": pyotp.random_base32(),
            "mfa_enabled": False,
            "passkeys": []
        }

    challenge = os.urandom(32)
    session['webauthn_challenge'] = _b64url_encode(challenge)
    session['webauthn_user'] = username

    user_id = username.encode('utf-8')
    options = {
        "challenge": session['webauthn_challenge'],
        "rp": {"name": "FoxAlert"},
        "user": {"id": _b64url_encode(user_id), "name": username, "displayName": username},
        "pubKeyCredParams": [{"type": "public-key", "alg": -7}],
        "timeout": 60000,
        "attestation": "direct",
        "excludeCredentials": []
    }

    for cred in DB_USERS[username].get('passkeys', []):
        options['excludeCredentials'].append({"type": "public-key", "id": cred['id']})

    return options


@app.route('/register/complete', methods=['POST'])
def register_complete():
    payload = request.get_json() or {}
    username = session.get('webauthn_user')
    if not username:
        return {"error": "no user in session"}, 400

    # NOTE: Proper attestation verification is omitted for brevity
    cred_id = payload.get('rawId') or payload.get('id')
    if not cred_id:
        return {"error": "missing credential id"}, 400

    DB_USERS[username].setdefault('passkeys', []).append({"id": cred_id})
    return {"status": "ok"}


@app.route('/login/begin', methods=['POST'])
def login_begin():
    data = request.get_json() or {}
    username = data.get('username')
    if not username or username not in DB_USERS:
        return {"error": "unknown user"}, 400

    creds = DB_USERS[username].get('passkeys', [])
    challenge = os.urandom(32)
    session['webauthn_challenge'] = _b64url_encode(challenge)
    session['webauthn_user'] = username

    options = {
        "challenge": session['webauthn_challenge'],
        "timeout": 60000,
        "allowCredentials": [{"type": "public-key", "id": c['id']} for c in creds],
        "userVerification": "preferred"
    }
    return options


@app.route('/login/complete', methods=['POST'])
def login_complete():
    payload = request.get_json() or {}
    username = session.get('webauthn_user')
    if not username:
        return {"error": "no user in session"}, 400

    # NOTE: Proper assertion signature verification is omitted for brevity
    session['user_id'] = username
    session.pop('webauthn_challenge', None)
    session.pop('webauthn_user', None)
    return {"status": "ok"}


# --- ROUTES ---

@app.route('/')
def index():
    if 'user_id' in session:
        return render_template('index.html', username=session['user_id'])
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if not xcfg['password_login_enabled']:
            return {"error": "password login is disabled"}, 400

        username = request.form.get('username')
        password = request.form.get('password')
        
        user = DB_USERS.get(username)
        if user and user['password'] == password:
            # First factor approved! Stash the pending user ID in the session
            session['pending_user_id'] = username
            
            # Check if this user completed their mobile MFA registration onboarding before
            if user['mfa_enabled']:
                return redirect(url_for('mfa_verify'))
            else:
                return redirect(url_for('mfa_setup'))
                
        flash('Invalid username or password credentials.')
    return render_template('login.html')

@app.route('/mfa/setup', methods=['GET', 'POST'])
def mfa_setup():
    username = session.get('pending_user_id')
    if not username:
        return redirect(url_for('login'))
        
    user = DB_USERS[username]
    
    if request.method == 'POST':
        token = request.form.get('totp_token')
        totp = pyotp.TOTP(user['totp_secret'])
        
        # Validate the user's setup token to confirm sync
        if totp.verify(token):
            user['mfa_enabled'] = True # Secure user record flag
            session['user_id'] = username # Fully elevate session to logged in
            session.pop('pending_user_id', None)
            return redirect(url_for('index'))
            
        flash('Invalid verification token. Please try scanning again.')

    return render_template('mfa_setup.html', secret=user['totp_secret'])

@app.route('/qrcode')
def qrcode_image():
    username = session.get('pending_user_id')
    if not username:
        return "Unauthorized", 401
        
    user = DB_USERS[username]
    
    # Generate the standard TOTP URI layout that authenticator apps parse
    totp_uri = pyotp.totp.TOTP(user['totp_secret']).provisioning_uri(
        name=username, 
        issuer_name="Flask-MFA"
    )
    
    # Render the text string URI map into a real visual QR matrix block stream
    img = qrcode.make(totp_uri)
    buf = io.BytesIO()
    img.save(buf, 'PNG')
    buf.seek(0)
    
    return send_file(buf, mimetype='image/png')

@app.route('/mfa/verify', methods=['GET', 'POST'])
def mfa_verify():
    username = session.get('pending_user_id')
    if not username:
        return redirect(url_for('login'))
        
    user = DB_USERS[username]
    
    if request.method == 'POST':
        token = request.form.get('totp_token')
        totp = pyotp.TOTP(user['totp_secret'])
        
        # Validates rolling timed tokens (handles subtle clock drifts cleanly)
        if totp.verify(token):
            session['user_id'] = username # Fully elevate session to logged in
            session.pop('pending_user_id', None)
            return redirect(url_for('index'))
            
        flash('Invalid or expired MFA code.')
        
    return render_template('mfa_verify.html', username=username)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host="0.0.0.0",port=5000, debug=True)
