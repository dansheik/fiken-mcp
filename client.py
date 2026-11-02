"""Fiken API transport.

Reads use GET. The only writes allowed are on purchase and sale DRAFTS
(create, update, delete and attach documentation). Paths that would finalise
a draft into the ledger (``createPurchase`` / ``createSale``) or touch any
other resource are rejected before a request is sent. Redirects are never
followed.
"""
from __future__ import annotations
import json
import re
import secrets
import time
from urllib.parse import urlsplit
import httpx
from auth import FikenError, access_token, session_lock
API_ROOT = 'https://api.fiken.no/api/v2'
MAX_BYTES = 15 * 1024 * 1024

def get(path: str, params=None, *, binary=False):
    if binary:
        parsed = urlsplit(path)
        if (parsed.scheme != 'https' or parsed.hostname not in {'api.fiken.no', 'fiken.no'}
            or parsed.port not in (None, 443) or parsed.username or parsed.password or parsed.fragment):
            raise FikenError('Bilagslenken har ikke en tillatt Fiken-adresse.')
        url = path
    else:
        if not re.fullmatch(r'companies(?:/[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)*)?', path):
            raise FikenError('Ugyldig API-sti.')
        url = API_ROOT + '/' + path
    clean = {k: str(v).lower() if isinstance(v, bool) else v for k, v in (params or {}).items() if v is not None and v != ''}
    with session_lock():
        try:
            with httpx.Client(timeout=30, follow_redirects=False) as client:
                with client.stream('GET', url, params=clean, headers={
                    'Authorization': 'Bearer ' + access_token(),
                    'Accept': '*/*' if binary else 'application/json',
                    'User-Agent': 'fiken-mcp/0.4.0'}) as response:
                    if response.status_code != 200:
                        raise FikenError(f'Fiken svarte med HTTP {response.status_code}. Kontroller tilgang; ved 401, logg inn på nytt.')
                    chunks = bytearray()
                    for chunk in response.iter_bytes():
                        chunks.extend(chunk)
                        if len(chunks) > MAX_BYTES:
                            raise FikenError('Svaret er for stort (maks 15 MiB). Avgrens forespørselen.')
                    if binary:
                        return bytes(chunks), response.headers.get('content-type', '').split(';')[0]
                    data = json.loads(chunks)
                    if isinstance(data, list) and 'page' in clean:
                        return page_result(data, response.headers, clean)
                    return data
        except (httpx.HTTPError, ValueError):
            raise FikenError('Kunne ikke lese et gyldig svar fra Fiken.') from None
        finally:
            # Also spaces consecutive calls from separate Claude processes.
            time.sleep(0.30)


def page_result(data, headers, params):
    """Preserve pagination; absent metadata never implies a complete result set."""
    page = int(params['page'])
    size = int(params.get('pageSize', 100))
    def number(name):
        value = headers.get(name)
        if value is None:
            return None
        parsed = int(value)
        if parsed < 0:
            raise FikenError('Ugyldig sideinformasjon fra Fiken.')
        return parsed
    returned_page = number('Fiken-Api-Page')
    if returned_page is not None and returned_page != page:
        raise FikenError('Fiken returnerte feil side. Resultatet er ikke komplett.')
    count = number('Fiken-Api-Page-Count')
    total = number('Fiken-Api-Result-Count')
    has_more = page + 1 < count if count is not None else bool(data)
    return {'data': data, 'pagination': {
        'page': page, 'page_size': size, 'page_count': count,
        'result_count': total, 'has_more': has_more,
        'next_page': page + 1 if has_more else None,
        'metadata_available': count is not None}}


# Draft-only write allowlist. Anything else (including .../createPurchase and
# .../createSale, which would book the draft) is refused locally.
_SLUG = r'companies/[A-Za-z0-9_-]+/(?:purchases|sales)/drafts'
WRITE_RULES = {
    'POST': re.compile(_SLUG + r'(?:/[1-9][0-9]*/attachments)?'),
    'PUT': re.compile(_SLUG + r'/[1-9][0-9]*'),
    'DELETE': re.compile(_SLUG + r'/[1-9][0-9]*'),
}
_SAFE_FIELD = re.compile(r'[A-Za-z0-9_]+')


def _error_detail(response) -> str:
    """Only short, structured validation text from Fiken; never raw bodies."""
    if response.status_code not in (400, 409, 422):
        return ''
    try:
        body = json.loads(response.content)
    except ValueError:
        return ''
    if not isinstance(body, dict):
        return ''
    parts = [str(body[k]) for k in ('error_description', 'message', 'error') if isinstance(body.get(k), str)]
    return (' Fiken: ' + ' | '.join(parts)[:500]) if parts else ''


def multipart(fields: dict[str, str], file: tuple[str, bytes, str] | None = None):
    boundary = secrets.token_hex(16)
    out = bytearray()
    for name, value in fields.items():
        if not _SAFE_FIELD.fullmatch(name):
            raise FikenError('Ugyldig skjemafelt.')
        out += f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode()
    if file:
        filename, data, mime = file
        filename = re.sub(r'[^A-Za-z0-9._-]', '_', filename)[:100] or 'bilag'
        out += (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\n'
                f'Content-Type: {mime}\r\n\r\n').encode() + data + b'\r\n'
    out += f'--{boundary}--\r\n'.encode()
    return bytes(out), f'multipart/form-data; boundary={boundary}'


def send(method: str, path: str, *, json_body=None, params=None, form=None):
    """Write to a purchase/sale draft. Returns {'status', 'location', 'data'}."""
    rule = WRITE_RULES.get(method)
    if not rule or not rule.fullmatch(path):
        raise FikenError('Denne serveren kan bare opprette, endre og slette kjøps- og salgsutkast. Bokføring er sperret.')
    headers = {'Authorization': '', 'Accept': 'application/json', 'User-Agent': 'fiken-mcp/0.4.0'}
    content = None
    if json_body is not None:
        content = json.dumps(json_body).encode()
        headers['Content-Type'] = 'application/json'
    elif form is not None:
        content, headers['Content-Type'] = form
    clean = {k: str(v).lower() if isinstance(v, bool) else v for k, v in (params or {}).items() if v is not None and v != ''}
    with session_lock():
        try:
            headers['Authorization'] = 'Bearer ' + access_token()
            with httpx.Client(timeout=60, follow_redirects=False) as client:
                response = client.request(method, API_ROOT + '/' + path, params=clean, content=content, headers=headers)
                if response.status_code not in (200, 201, 204):
                    raise FikenError(f'Fiken svarte med HTTP {response.status_code}.{_error_detail(response)}')
                data = None
                if response.content and response.headers.get('content-type', '').startswith('application/json'):
                    data = json.loads(response.content)
                return {'status': response.status_code, 'location': response.headers.get('location'), 'data': data}
        except (httpx.HTTPError, ValueError):
            raise FikenError('Kunne ikke fullføre skrivingen til Fiken. Kontroller utkastlisten før du prøver igjen.') from None
        finally:
            time.sleep(0.30)
