# FoxAlert — Flask MFA Demo

This small demo app shows password login with a second factor (TOTP) using an authenticator app.

## Requirements

- Python 3.8+
- Virtual environment (recommended)
- Dependencies listed in `requirements.txt` (install with pip)

## Quick start

Create and activate a virtual environment, install deps, then run the app:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 app.py
```

The app will listen on port `5000` by default (http://127.0.0.1:5000).

## Default test account

- Username: `user1`
- Password: `password123`

Flow:
- Visit `/login` and sign in with the test account.
- If the account has not finished MFA setup you will be redirected to the setup flow.
- Scan the QR code shown (or copy the secret) into Google Authenticator / Authy and enter the 6-digit TOTP to confirm.
- After successful verification you are logged in and taken to the dashboard.

## Important routes

- `/` — Dashboard (requires logged-in session)
- `/login` — Password entry
- `/mfa/setup` — MFA onboarding and verification
- `/mfa/verify` — MFA challenge for returning logins
- `/qrcode` — PNG QR code for the provisioning URI (served while in setup)
- `/logout` — Clears session and returns to `/login`

## Templates

I replaced inline HTML with proper templates under the `templates/` folder:

- `templates/base.html` — shared layout and styles
- `templates/login.html` — password login form
- `templates/mfa_setup.html` — QR code + setup form
- `templates/mfa_verify.html` — TOTP verification form
- `templates/index.html` — simple dashboard

## Notes

- This app uses an in-memory mock user store in `app.py` and is intended for demo/learning only. Do not use it as-is in production.
- Secrets are generated via `pyotp.random_base32()` at runtime; restarting the app resets those values for the demo user.
