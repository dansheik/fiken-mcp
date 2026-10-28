"""Synthetic accounting scenarios; no customer data or live requests."""
import pytest
import httpx
import server
import client
from auth import FikenError
from test_pilot import proposal, transport


def page(rows, has_more=False):
    return {'data': rows, 'pagination': {'has_more': has_more}}


def purchase(number='INV-1', amount=12500, date='2026-10-01'):
    return {'purchaseId': 42, 'identifier': number, 'date': date, 'currency': 'NOK',
            'supplier': {'contactId': 12}, 'lines': [{'netPrice': amount-2500, 'vat': 2500, 'account': '6800', 'vatType': 'HIGH'}]}


def test_balance_date_and_pagination_on_wire(monkeypatch):
    def handler(req):
        assert req.method == 'GET'
        assert req.url.params['date'] == '2026-09-30'
        assert req.url.params['page'] == '2'
        return httpx.Response(200, json=[{'code': '1920', 'balance': 12345}], headers={
            'Fiken-Api-Page': '2', 'Fiken-Api-Page-Count': '3', 'Fiken-Api-Result-Count': '201'})
    transport(monkeypatch, handler)
    result = server.fiken_list_account_balances('example', '2026-09-30', page=2)
    assert result['pagination']['result_count'] == 201
    assert result['pagination']['next_page'] is None


@pytest.mark.parametrize('value', ['2026-02-30', '20261001', '', '01-10-2026'])
def test_invalid_balance_date_before_network(value):
    with pytest.raises(FikenError): server.fiken_list_account_balances('example', value)


def test_missing_page_metadata_requires_empty_page(monkeypatch):
    calls = []
    def handler(req):
        calls.append(int(req.url.params['page']))
        return httpx.Response(200, json=[{'code': '6800'}] if len(calls) == 1 else [])
    transport(monkeypatch, handler)
    result = server._collect('example', 'accounts')
    assert calls == [0, 1]
    assert result['complete']


def test_mismatched_page_rejected():
    with pytest.raises(FikenError):
        client.page_result([], {'Fiken-Api-Page': '0'}, {'page': 1})


def test_page_limit_not_reported_complete(monkeypatch):
    monkeypatch.setattr(server, '_request', lambda *a, **k: page([{'code': '6800'}], True))
    result = server._collect('example', 'accounts', max_pages=1)
    assert not result['complete'] and result['next_page'] == 1


def test_live_validation_checks_accounts_on_later_page(monkeypatch):
    def request(path, params):
        assert path.endswith('/accounts')
        return page([{'code': '6800'}], True) if params['page'] == 0 else page([{'code': '2710'}, {'code': '2400'}])
    monkeypatch.setattr(server, '_request', request)
    data = proposal()
    for line in data['lines']: line['vat_code'] = '0'
    result = server.fiken_validate_posting_proposal(server.PostingProposal(**data))
    assert result['account_check']['status'] == 'verified'
    assert result['vat_check']['status'] == 'recognized_codes'
    assert not result['vat_check']['tax_treatment_validated']
    assert result['duplicate_check']['status'] == 'not_checked'
    assert not result['accounting_validated']


def test_unknown_account_and_vat_flagged(monkeypatch):
    monkeypatch.setattr(server, '_request', lambda *a, **k: page([{'code': '6800'}]))
    result = server.fiken_validate_posting_proposal(server.PostingProposal(**proposal()))
    assert result['account_check']['status'] == 'unknown_accounts'
    assert result['vat_check']['status'] == 'unresolved'
    assert result['arithmetic_valid']  # Balanced never means accounting-correct.


def test_partial_account_catalog_never_verified(monkeypatch):
    monkeypatch.setattr(server, '_request', lambda *a, **k: page([{'code': c} for c in ['6800', '2710', '2400']], True))
    result = server.fiken_validate_posting_proposal(server.PostingProposal(**proposal()), max_pages=1)
    assert result['account_check']['status'] == 'incomplete'


def test_duplicate_number_different_date_and_amount(monkeypatch):
    def request(path, params):
        assert params['contactId'] == 12
        assert not params.get('dateGe')
        return page([purchase(amount=30000, date='2026-01-01')])
    monkeypatch.setattr(server, '_request', request)
    result = server.fiken_find_duplicate_purchases('example', 12, ' inv-1 ', 12500, '2026-10-01')
    assert result['matches'][0]['reasons'] == ['same_supplier_and_invoice_number']


def test_duplicate_amount_date_without_number(monkeypatch):
    monkeypatch.setattr(server, '_request', lambda *a, **k: page([purchase()]))
    result = server.fiken_find_duplicate_purchases('example', 12, '', 12500, '2026-10-01')
    assert result['matches'][0]['reasons'] == ['same_supplier_date_and_amount']


def test_deleted_purchase_excluded(monkeypatch):
    monkeypatch.setattr(server, '_request', lambda *a, **k: page([{**purchase(), 'deleted': True}]))
    result = server.fiken_find_duplicate_purchases('example', 12, 'INV-1', 12500, '2026-10-01')
    assert result['status'] == 'no_matches_in_scope'


def test_missing_amount_not_silently_zero(monkeypatch):
    row = purchase(); del row['lines'][0]['vat']
    monkeypatch.setattr(server, '_request', lambda *a, **k: page([row]))
    result = server.fiken_find_duplicate_purchases('example', 12, '', 12500, '2026-10-01')
    assert result['status'] == 'incomplete'
    assert result['amounts_not_comparable'] == 1


def test_duplicate_on_later_page_reached(monkeypatch):
    monkeypatch.setattr(server, '_request', lambda path, params: page([], True) if params['page'] == 0 else page([purchase()]))
    result = server.fiken_find_duplicate_purchases('example', 12, 'INV-1', 12500, '2026-10-01')
    assert result['status'] == 'possible_duplicates'
    assert result['pages_read'] == 2


def test_attachment_must_belong_to_purchase(monkeypatch):
    monkeypatch.setattr(server, 'fiken_list_purchase_attachments', lambda *a: [{'uuid': 'real', 'downloadUrl': 'https://fiken.no/test'}])
    with pytest.raises(FikenError):
        server.fiken_read_purchase_attachment('example', 1, 'other')


def test_attachment_source_preserved(monkeypatch):
    monkeypatch.setattr(server, 'fiken_list_purchase_attachments', lambda *a: [{'uuid': 'real', 'downloadUrl': 'https://fiken.no/test'}])
    monkeypatch.setattr(server, '_read_document_url', lambda url, source, page, as_image: {'source': source, 'page': page})
    assert server.fiken_read_purchase_attachment('example', 1, 'real', page=2) == {'source': 'purchase:1/attachment:real', 'page': 2}


def test_complete_review_runs_duplicate_search(monkeypatch):
    def request(path, params):
        if path.endswith('/accounts'):
            return page([{'code': c} for c in ['6800', '2710', '2400']])
        assert path.endswith('/purchases') and params['contactId'] == 12
        return page([purchase(number='1')])
    monkeypatch.setattr(server, '_request', request)
    data = proposal(); data['supplier_id'] = 12
    result = server.fiken_validate_posting_proposal(server.PostingProposal(**data))
    assert result['duplicate_check']['status'] == 'possible_duplicates'
    assert result['status'] == 'draft_requires_human_review'


def test_config_contains_no_tokens(monkeypatch, tmp_path):
    import setup_cli
    executable = tmp_path / 'fiken-mcp'; executable.touch()
    monkeypatch.setattr(setup_cli.sys, 'executable', str(tmp_path / 'python'))
    monkeypatch.setenv('FIKEN_CLIENT_ID', 'public-client')
    result = setup_cli.claude_config()['mcpServers']['fiken']
    assert result['command'] == str(executable)
    assert result['env'] == {'FIKEN_CLIENT_ID': 'public-client'}


def test_doctor_never_returns_company_data(monkeypatch):
    import setup_cli
    monkeypatch.setenv('FIKEN_CLIENT_ID', 'public-client')
    monkeypatch.setattr(setup_cli.sys, 'platform', 'darwin')
    monkeypatch.setattr(client, 'get', lambda *a: {'data': [{'name': 'Private AS'}], 'pagination': {'result_count': 1}})
    result = setup_cli.doctor()
    assert result['accessible_company_count'] == 1
    assert 'Private AS' not in str(result)
