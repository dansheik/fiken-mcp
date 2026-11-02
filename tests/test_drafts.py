"""Synthetic draft scenarios; no customer data or live requests."""
import json
import httpx
import pytest
import client
import server
from auth import FikenError
from test_pilot import transport


def draft(**overrides):
    data = dict(contact_id=12, invoice_issue_date='2026-08-31', due_date='2026-09-07', invoice_number='INV-1',
                expected_gross_ore=12750,
                lines=[dict(text='Råvarer', account='4030', vat_type='MEDIUM', net_ore=10000, gross_ore=11500),
                       dict(text='Emballasje', account='4000', vat_type='HIGH', net_ore=1000, gross_ore=1250)])
    data.update(overrides)
    return server.DraftInput(**data)


@pytest.mark.parametrize('method,path', [
    ('POST', 'companies/x/purchases/drafts/5/createPurchase'),
    ('POST', 'companies/x/sales/drafts/5/createSale'),
    ('POST', 'companies/x/purchases'),
    ('POST', 'companies/x/sales'),
    ('POST', 'companies/x/journalEntries'),
    ('PUT', 'companies/x/purchases/drafts'),
    ('DELETE', 'companies/x/purchases/5'),
    ('PATCH', 'companies/x/purchases/drafts/5'),
    ('GET', 'companies/x/purchases/drafts'),
    ('POST', 'companies/../purchases/drafts'),
    ('POST', 'companies/x/purchases/drafts/0/attachments'),
])
def test_write_transport_only_allows_draft_paths(monkeypatch, method, path):
    def handler(req):
        raise AssertionError('No request may be sent')
    transport(monkeypatch, handler)
    with pytest.raises(FikenError, match='Bokføring er sperret'):
        client.send(method, path, json_body={})


def fake_fiken(monkeypatch, *, existing_drafts=(), purchases=(), attach_status=201):
    calls = []
    def handler(req):
        path = req.url.path.removeprefix('/api/v2/')
        calls.append((req.method, path, req))
        assert 'createPurchase' not in path and 'createSale' not in path
        if req.method == 'GET' and path.endswith('/drafts'):
            rows = list(existing_drafts) if req.url.params['page'] == '0' else []
            return httpx.Response(200, json=rows)
        if req.method == 'GET' and path.endswith('/purchases'):
            return httpx.Response(200, json=list(purchases) if req.url.params['page'] == '0' else [])
        if req.method == 'POST' and path.endswith('/drafts'):
            return httpx.Response(201, headers={'Location': f'https://api.fiken.no/api/v2/{path}/77'})
        if req.method == 'POST' and path.endswith('/attachments'):
            return httpx.Response(attach_status, json={'error_description': 'not allowed'} if attach_status == 400 else None)
        if req.method == 'GET' and path.endswith('/drafts/77'):
            return httpx.Response(200, json={'draftId': 77, 'lines': []})
        if req.method == 'GET' and path.endswith('/inbox/5'):
            return httpx.Response(200, json={'documentId': 5, 'name': 'faktura', 'documentUrl': 'https://fiken.no/doc/5'})
        if req.method == 'GET' and req.url.host == 'fiken.no':
            return httpx.Response(200, content=b'%PDF-1.4 test', headers={'content-type': 'application/pdf'})
        raise AssertionError(f'Unexpected {req.method} {path}')
    transport(monkeypatch, handler)
    return calls


def test_create_purchase_draft_sends_fiken_fields_and_attaches(monkeypatch):
    calls = fake_fiken(monkeypatch)
    result = server.fiken_create_purchase_draft('example', draft(), inbox_document_id=5)
    assert result['status'] == 'draft_created' and result['draft_id'] == 77 and result['booked'] is False
    assert result['attachment']['method'] == 'inbox_document'
    post = next(req for method, path, req in calls if method == 'POST' and path.endswith('/drafts'))
    body = json.loads(post.content)
    assert body['contactId'] == 12 and body['cash'] is False and body['paid'] is False
    assert body['lines'][0] == {'text': 'Råvarer', 'vatType': 'MEDIUM', 'incomeAccount': '4030', 'net': 10000, 'gross': 11500}
    attach = next(req for method, path, req in calls if path.endswith('/attachments'))
    assert attach.url.params['inboxDocumentId'] == '5'
    assert attach.headers['content-type'].startswith('multipart/form-data')
    assert [m for m, *_ in calls].count('POST') == 2


def test_attachment_falls_back_to_uploading_copy(monkeypatch):
    calls = fake_fiken(monkeypatch, attach_status=400)
    # First direct link is rejected, then the copy upload also hits 400 in this fake.
    result = server.fiken_create_purchase_draft('example', draft(), inbox_document_id=5)
    assert result['status'] == 'draft_created'
    assert result['attachment']['status'] == 'not_attached'
    uploads = [req for method, path, req in calls if path.endswith('/attachments')]
    assert len(uploads) == 2 and b'%PDF-1.4 test' in uploads[1].content


def test_total_mismatch_writes_nothing(monkeypatch):
    calls = fake_fiken(monkeypatch)
    with pytest.raises(FikenError, match='avviker'):
        server.fiken_create_purchase_draft('example', draft(expected_gross_ore=12751))
    assert calls == []


def test_zero_vat_line_must_have_gross_equal_net(monkeypatch):
    calls = fake_fiken(monkeypatch)
    bad = draft(expected_gross_ore=200, lines=[dict(text='Pant', account='4340', vat_type='NONE', net_ore=176, gross_ore=200)])
    with pytest.raises(FikenError, match='ikke mva'):
        server.fiken_create_purchase_draft('example', bad)
    assert calls == []


def test_paid_requires_matching_payment():
    with pytest.raises(FikenError, match='paid=true'):
        server.fiken_create_purchase_draft('example', draft(paid=True))


def test_existing_draft_blocks_duplicate(monkeypatch):
    calls = fake_fiken(monkeypatch, existing_drafts=[{'draftId': 9, 'invoiceNumber': ' inv-1 ', 'contact': {'contactId': 12}}])
    with pytest.raises(FikenError, match='duplikat'):
        server.fiken_create_purchase_draft('example', draft())
    assert not any(method == 'POST' for method, *_ in calls)


def test_booked_purchase_blocks_duplicate(monkeypatch):
    booked = {'purchaseId': 42, 'identifier': 'INV-1', 'date': '2026-08-31', 'currency': 'NOK', 'lines': []}
    calls = fake_fiken(monkeypatch, purchases=[booked])
    with pytest.raises(FikenError, match='purchase:42'):
        server.fiken_create_purchase_draft('example', draft())
    assert not any(method == 'POST' for method, *_ in calls)


def test_allow_duplicate_skips_checks(monkeypatch):
    calls = fake_fiken(monkeypatch, existing_drafts=[{'draftId': 9, 'invoiceNumber': 'INV-1', 'contact': {'contactId': 12}}])
    assert server.fiken_create_purchase_draft('example', draft(), allow_duplicate=True)['draft_id'] == 77
    assert not any(path.endswith('/drafts') and method == 'GET' for method, path, _ in calls)


def test_sale_draft_with_negative_fee_line(monkeypatch):
    calls = fake_fiken(monkeypatch)
    sale = draft(contact_id=30, invoice_number=None, due_date=None, expected_gross_ore=868000, lines=[
        dict(text='Salg 15 %', account='3017', vat_type='MEDIUM', net_ore=760870, gross_ore=875000),
        dict(text='Gebyr', account='7300', vat_type='NONE', net_ore=-7000, gross_ore=-7000)])
    result = server.fiken_create_sale_draft('example', sale)
    assert result['draft_type'] == 'sale' and result['draft_id'] == 77
    post = next(req for method, path, req in calls if method == 'POST')
    assert post.url.path.endswith('/sales/drafts')


def test_supplier_purchase_requires_contact():
    with pytest.raises(FikenError, match='contact_id'):
        server.fiken_create_purchase_draft('example', draft(contact_id=None))


def test_validation_error_text_is_returned(monkeypatch):
    def handler(req):
        return httpx.Response(400, json={'error_description': 'Konto 9999 finnes ikke'})
    transport(monkeypatch, handler)
    with pytest.raises(FikenError, match='Konto 9999 finnes ikke'):
        client.send('POST', 'companies/x/purchases/drafts', json_body={})


def test_delete_only_targets_drafts(monkeypatch):
    seen = []
    def handler(req):
        seen.append((req.method, req.url.path))
        return httpx.Response(204)
    transport(monkeypatch, handler)
    assert server.fiken_delete_sale_draft('example', 3)['status'] == 'draft_deleted'
    assert seen == [('DELETE', '/api/v2/companies/example/sales/drafts/3')]
