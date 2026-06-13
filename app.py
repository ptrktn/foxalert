import os
import io
import base64
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
import pyotp
import qrcode
import json
import time
from flask import Response, stream_with_context, jsonify

try:
    from pywebpush import webpush, WebPushException
except Exception:
    webpush = None
    WebPushException = Exception

# Simple in-memory subscribers list for Server-Sent Events (SSE)
SSE_SUBSCRIBERS = []

# VAPID keys loaded from environment
VAPID_PUBLIC_KEY = os.environ.get('VAPID_PUBLIC_KEY')
VAPID_PRIVATE_KEY = os.environ.get('VAPID_PRIVATE_KEY')

app = Flask(__name__)
app.secret_key = os.urandom(24)

xcfg = {
    "passkey_login_enabled": True, # Toggle to enable/disable passkey registration/login flows in the UI
    "password_login_enabled": False, # Toggle to enable/disable password-based login flows in the UI
}

@app.context_processor
def inject_context():
    return {
        "xcfg": xcfg,
        "current_user": session.get('user_id')
    }

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


# --- Simple Server-Sent Events (SSE) for server->client notifications ---
def event_stream(queue):
    try:
        while True:
            msg = queue.pop(0) if queue else None
            if msg:
                data = json.dumps(msg)
                yield f"data: {data}\n\n"
            else:
                # heartbeat to keep connection alive
                yield 'data: {"type":"ping"}\n\n'
            time.sleep(1)
    except GeneratorExit:
        return


@app.route('/notifications/stream')
def notifications_stream():
    # Each client gets its own queue
    q = []
    SSE_SUBSCRIBERS.append(q)

    @stream_with_context
    def generator():
        try:
            for chunk in event_stream(q):
                yield chunk
        finally:
            # cleanup on disconnect
            try:
                SSE_SUBSCRIBERS.remove(q)
            except ValueError:
                pass

    return Response(generator(), mimetype='text/event-stream')


@app.route('/notifications/send', methods=['POST'])
def notifications_send():
    """POST JSON {"title":"...","body":"...","data":{...}} to broadcast to connected clients."""
    payload = request.get_json() or {}
    if not payload.get('title') and not payload.get('body'):
        return {"error": "missing title/body"}, 400

    # Broadcast to all subscriber queues
    for q in list(SSE_SUBSCRIBERS):
        q.append({
            "type": "notification",
            "title": payload.get('title'),
            "body": payload.get('body'),
            "data": payload.get('data', {})
        })

    return {"status": "ok", "sent_to": len(SSE_SUBSCRIBERS)}


@app.route('/vapid_public_key')
def vapid_public_key():
    """Return the VAPID public key for PushManager subscription (base64 URL-safe)."""
    if not VAPID_PUBLIC_KEY:
        return {"error": "VAPID public key not configured. Set VAPID_PUBLIC_KEY env var."}, 500
    return {"publicKey": VAPID_PUBLIC_KEY}


@app.route('/push/subscribe', methods=['POST'])
def push_subscribe():
    """Store subscription info for the logged-in user."""
    if 'user_id' not in session:
        app.logger.warning('Push subscribe denied: no authenticated user in session')
        return {"error": "not authenticated"}, 401
    sub = request.get_json() or {}
    if not sub.get('endpoint'):
        app.logger.warning('Push subscribe denied: invalid subscription payload %s', sub)
        return {"error": "invalid subscription"}, 400

    username = session['user_id']
    DB_USERS.setdefault(username, {}).update({'push_subscription': sub})
    app.logger.info('Stored push subscription for user %s', username)
    return {"status": "ok"}


@app.route('/push/send', methods=['POST'])
def push_send():
    """Send Web Push to a user's stored subscription. POST {"username":"user1","title":"...","body":"..."}
       Requires VAPID_PUBLIC_KEY and VAPID_PRIVATE_KEY env vars to be set."""
    if webpush is None:
        return {"error": "pywebpush not installed"}, 500
    data = request.get_json() or {}
    target = data.get('username')
    title = data.get('title')
    body = data.get('body')
    if not target or not title:
        return {"error": "missing username or title"}, 400

    user = DB_USERS.get(target)
    if not user:
        return {"error": "unknown user"}, 404
    sub = user.get('push_subscription')
    if not sub:
        return {"error": "user has no subscription"}, 404

    if not VAPID_PRIVATE_KEY or not VAPID_PUBLIC_KEY:
        app.logger.error('VAPID keys not configured for push send')
        return {"error": "VAPID keys not configured"}, 500

    payload = json.dumps({"title": title, "body": body, "data": data.get('data', {})})

    try:
        resp = webpush(
            subscription_info=sub,
            data=payload,
            vapid_private_key=VAPID_PRIVATE_KEY,
            vapid_claims={"sub": "mailto:admin@example.com"}
        )
        app.logger.info('Web push sent to user %s, status %s', target, getattr(resp, 'status_code', 'unknown'))
        return {"status": "ok", "response": str(resp)}
    except WebPushException as ex:
        app.logger.exception('Web push failed for user %s', target)
        return {"error": "webpush failed", "details": str(ex)}, 500


@app.route('/service-worker.js')
def service_worker():
    return send_file(os.path.join(app.static_folder, 'service-worker.js'), mimetype='application/javascript')

if __name__ == '__main__':
    app.run(host="0.0.0.0",port=5000, debug=True)
