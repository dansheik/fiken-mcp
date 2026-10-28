"""The accounting API transport exposes GET only and never follows redirects."""
from __future__ import annotations
import re
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
                    'User-Agent': 'fiken-mcp/0.3.0'}) as response:
                    if response.status_code != 200:
                        raise FikenError(f'Fiken svarte med HTTP {response.status_code}. Kontroller tilgang; ved 401, logg inn på nytt.')
                    chunks = bytearray()
                    for chunk in response.iter_bytes():
                        chunks.extend(chunk)
                        if len(chunks) > MAX_BYTES:
                            raise FikenError('Svaret er for stort (maks 15 MiB). Avgrens forespørselen.')
                    if binary:
                        return bytes(chunks), response.headers.get('content-type', '').split(';')[0]
                    import json
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
