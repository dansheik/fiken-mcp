"""Public-client OAuth with S256 PKCE. Credentials live only in macOS Keychain."""
from __future__ import annotations
import base64
import hashlib
import json
import os
import secrets
import sys
import time
import webbrowser
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit
import fcntl
import httpx
from keyring.backends.macOS import Keyring

REDIRECT = 'http://127.0.0.1:8765/callback'
SERVICE = 'no.fiken.mcp.oauth'

class FikenError(RuntimeError):
    """Safe error that may be shown to the user."""

def client_id():
    value = os.environ.get('FIKEN_CLIENT_ID', '').strip()
    if not value:
        raise FikenError('Sett FIKEN_CLIENT_ID til ID-en fra en offentlig Fiken-app med PKCE.')
    return value

def keychain():
    if sys.platform != 'darwin':
        raise FikenError('Denne piloten krever macOS og Apple Nøkkelring.')
    return Keyring()

@contextmanager
def session_lock():
    """Serialize API calls and rotating refresh tokens across local processes."""
    root = Path.home() / 'Library' / 'Application Support' / 'fiken-mcp'
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(root / 'session.lock', os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)

def pkce():
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
    return verifier, challenge

def exchange(data):
    try:
        with httpx.Client(timeout=30, follow_redirects=False) as client:
            response = client.post('https://fiken.no/oauth/token', data={'client_id': client_id(), **data})
        if response.status_code != 200:
            raise FikenError('Fiken avviste innlogging/fornyelse. Kjør fiken-mcp login på nytt.')
        token = response.json()
        if not token.get('access_token') or not token.get('refresh_token'):
            raise FikenError('Ufullstendig OAuth-svar fra Fiken. Logg inn på nytt.')
        token['expires_at'] = time.time() + int(token['expires_in'])
        return token
    except (httpx.HTTPError, ValueError, KeyError):
        raise FikenError('Kunne ikke fullføre OAuth. Prøv innlogging på nytt.') from None

def save(token):
    try:
        keychain().set_password(SERVICE, client_id(), json.dumps(token))
    except Exception:
        raise FikenError('Kunne ikke lagre i Nøkkelring. Lås opp Nøkkelring og logg inn på nytt.') from None

def access_token():
    """Caller must hold session_lock for the complete API operation."""
    try:
        raw = keychain().get_password(SERVICE, client_id())
        token = json.loads(raw) if raw else None
    except Exception:
        raise FikenError('Kunne ikke lese Nøkkelring. Kjør fiken-mcp login.') from None
    if not token:
        raise FikenError('Ikke innlogget. Kjør fiken-mcp login i Terminal først.')
    if token['expires_at'] <= time.time() + 120:
        token = exchange({'grant_type': 'refresh_token', 'refresh_token': token['refresh_token']})
        # Persist the rotated token before making another request.
        save(token)
    return token['access_token']

def login():
    cid = client_id()
    verifier, challenge = pkce()
    state = secrets.token_urlsafe(32)
    result = {}
    class Callback(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass
        def do_GET(self):
            parsed = urlsplit(self.path)
            query = parse_qs(parsed.query)
            valid = (parsed.path == '/callback' and len(query.get('state', [])) == 1
                     and secrets.compare_digest(query['state'][0], state))
            if not valid:
                self.send_error(400, 'Invalid OAuth callback')
                return
            if len(query.get('code', [])) == 1 and 'error' not in query:
                result['code'] = query['code'][0]
            else:
                result['error'] = True
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(b'Du kan lukke dette vinduet og gaa tilbake til Terminal.')
    url = 'https://fiken.no/oauth/authorize?' + urlencode({
        'response_type': 'code', 'client_id': cid, 'redirect_uri': REDIRECT,
        'state': state, 'code_challenge': challenge, 'code_challenge_method': 'S256'})
    try:
        with HTTPServer(('127.0.0.1', 8765), Callback) as server:
            server.timeout = 1
            print('Åpner Fiken i nettleseren. Fullfør innlogging innen 3 minutter.', file=sys.stderr)
            if not webbrowser.open(url):
                print(url, file=sys.stderr)
            deadline = time.monotonic() + 180
            while not result and time.monotonic() < deadline:
                server.handle_request()
    except OSError:
        raise FikenError('Port 8765 er opptatt. Avslutt annen innlogging og prøv igjen.') from None
    if not result.get('code'):
        raise FikenError('Innlogging avbrutt eller tidsavbrudd.')
    with session_lock():
        save(exchange({'grant_type': 'authorization_code', 'code': result['code'],
                       'code_verifier': verifier, 'redirect_uri': REDIRECT, 'state': state}))
    print('Innlogget. Tilgangen er lagret i macOS Nøkkelring.', file=sys.stderr)

def logout():
    with session_lock():
        store = keychain()
        if store.get_password(SERVICE, client_id()):
            store.delete_password(SERVICE, client_id())
    print('Lokal tilgang slettet. Tilbakekall også appen under Sikkerhet i Fiken.', file=sys.stderr)
