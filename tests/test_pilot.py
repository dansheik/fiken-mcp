import base64
import hashlib
import json
from contextlib import nullcontext
import httpx
import pytest
import auth
import client
import server
from pydantic import ValidationError


def test_pkce():
    verifier, challenge = auth.pkce()
    assert 43 <= len(verifier) <= 128
    assert challenge == base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
    assert auth.pkce() != (verifier, challenge)


@pytest.mark.parametrize('slug', ['../other', 'a?x=y', 'a#x', 'a/b', 'a%2fb', ''])
def test_company_path_rejects_injection(slug):
    with pytest.raises(auth.FikenError):
        server.fiken_get_company(slug)


@pytest.mark.parametrize('url', ['http://fiken.no/x', 'https://evil.test/x', 'https://fiken.no.evil.test/x', 'https://x@fiken.no/x', 'https://fiken.no:444/x'])
def test_download_rejects_untrusted_origins(url):
    with pytest.raises(auth.FikenError):
        client.get(url, binary=True)


def transport(monkeypatch, handler):
    real = httpx.Client
    monkeypatch.setattr(client, 'session_lock', nullcontext)
    monkeypatch.setattr(client, 'access_token', lambda: 'test-token')
    monkeypatch.setattr(client.time, 'sleep', lambda _: None)
    monkeypatch.setattr(client.httpx, 'Client', lambda **kw: real(transport=httpx.MockTransport(handler), **kw))


def test_get_only_and_no_redirect(monkeypatch):
    requests = []
    def handler(req):
        requests.append(req)
        return httpx.Response(302, headers={'location': 'https://evil.test/'})
    transport(monkeypatch, handler)
    with pytest.raises(auth.FikenError):
        client.get('companies')
    assert len(requests) == 1
    assert requests[0].method == 'GET'


def test_json_filters_and_safe_errors(monkeypatch):
    def handler(req):
        assert req.url.params['settled'] == 'false'
        return httpx.Response(403, text='secret body')
    transport(monkeypatch, handler)
    with pytest.raises(auth.FikenError, match='403') as exc:
        client.get('companies/test/invoices', {'settled': False})
    assert 'secret body' not in str(exc.value)


def test_rotated_refresh_persisted(monkeypatch):
    events = []
    old = {'access_token': 'old-access', 'refresh_token': 'old-refresh', 'expires_at': 0}
    class Store:
        def get_password(self, *args): return json.dumps(old)
        def set_password(self, service, user, value): events.append(json.loads(value))
    monkeypatch.setenv('FIKEN_CLIENT_ID', 'public-id')
    monkeypatch.setattr(auth, 'keychain', Store)
    def exchange(data):
        assert data == {'grant_type': 'refresh_token', 'refresh_token': 'old-refresh'}
        return {'access_token': 'new-access', 'refresh_token': 'new-refresh', 'expires_at': 99999999999}
    monkeypatch.setattr(auth, 'exchange', exchange)
    assert auth.access_token() == 'new-access'
    assert events[0]['refresh_token'] == 'new-refresh'


def proposal():
    return dict(company_slug='example', document_id='inbox:1', document_date='2026-10-01', supplier='Example AS', invoice_number='1', due_date=None, currency='NOK', gross_ore=12500,
                lines=[dict(account='6800', description='Kontor', debit_ore=10000, credit_ore=0, vat_code='uavklart', source='inbox:1 side 1'),
                       dict(account='2710', description='Mva', debit_ore=2500, credit_ore=0, vat_code='uavklart', source='inbox:1 side 1'),
                       dict(account='2400', description='Gjeld', debit_ore=0, credit_ore=12500, vat_code='ingen', source='inbox:1 side 1')],
                rationale='Test', uncertainties=['Fradragsrett må kontrolleres'], checks=['Duplikatsøk'])


def test_balanced_proposal_remains_draft():
    result = server.fiken_validate_posting_proposal(server.PostingProposal(**proposal()), check_fiken=False)
    assert result['arithmetic_valid']
    assert not result['accounting_validated'] and not result['written_to_fiken']


def test_unbalanced_proposal():
    data = proposal(); data['lines'][0]['debit_ore'] = 9999
    assert not server.fiken_validate_posting_proposal(server.PostingProposal(**data), check_fiken=False)['arithmetic_valid']


def test_fractional_money_rejected():
    data = proposal(); data['lines'][0]['debit_ore'] = 1.5
    with pytest.raises(ValidationError): server.PostingProposal(**data)


def test_scanned_pdf_and_page_bounds(monkeypatch):
    from pypdf import PdfWriter
    import io
    writer = PdfWriter(); writer.add_blank_page(width=200, height=200)
    out = io.BytesIO(); writer.write(out)
    monkeypatch.setattr(server, 'fiken_get_inbox_document', lambda *a: {'documentUrl': 'https://fiken.no/test'})
    monkeypatch.setattr(server, '_request', lambda *a, **k: (out.getvalue(), 'application/pdf'))
    assert server.fiken_read_document('test', 1)['pages'] == 1
    assert isinstance(server.fiken_read_document('test', 1, as_image=True), server.Image)
    with pytest.raises(auth.FikenError): server.fiken_read_document('test', 1, page=2)


def test_oauth_uses_public_client_body(monkeypatch):
    real = httpx.Client
    monkeypatch.setenv('FIKEN_CLIENT_ID', 'public-id')
    def handler(req):
        assert 'authorization' not in req.headers
        assert b'client_id=public-id' in req.content
        assert b'code_verifier=verifier' in req.content
        assert b'client_secret' not in req.content
        return httpx.Response(200, json={'access_token':'a', 'refresh_token':'r', 'expires_in':3600})
    monkeypatch.setattr(auth.httpx, 'Client', lambda **kw: real(transport=httpx.MockTransport(handler), **kw))
    assert auth.exchange({'grant_type':'authorization_code', 'code':'code', 'code_verifier':'verifier'})['refresh_token'] == 'r'


def test_login_checks_state_before_exchange(monkeypatch):
    import threading
    from urllib.parse import urlsplit, parse_qs
    monkeypatch.setenv('FIKEN_CLIENT_ID', 'public-id')
    monkeypatch.setattr(auth, 'session_lock', nullcontext)
    saved = []
    monkeypatch.setattr(auth, 'save', saved.append)
    calls = []
    def exchange(data):
        calls.append(data)
        return {'access_token': 'test', 'refresh_token': 'test'}
    monkeypatch.setattr(auth, 'exchange', exchange)
    responses = []
    threads = []
    def browser(url):
        query = parse_qs(urlsplit(url).query)
        assert query['code_challenge_method'] == ['S256']
        assert 'code_verifier' not in query
        def callback():
            with httpx.Client(trust_env=False) as c:
                responses.append(c.get(auth.REDIRECT, params={'state': 'wrong', 'code': 'bad'}).status_code)
                responses.append(c.get(auth.REDIRECT, params={'state': query['state'][0], 'code': 'good'}).status_code)
        thread = threading.Thread(target=callback); thread.start(); threads.append(thread)
        return True
    monkeypatch.setattr(auth.webbrowser, 'open', browser)
    auth.login()
    for thread in threads: thread.join(timeout=5)
    assert responses == [400, 200]
    assert len(calls) == 1 and calls[0]['code'] == 'good'
    assert len(saved) == 1
