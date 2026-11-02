import asyncio
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def test_real_stdio_handshake():
    async def run():
        async with stdio_client(StdioServerParameters(command=sys.executable, args=['-m', 'server'])) as (reader, writer):
            async with ClientSession(reader, writer) as session:
                await session.initialize()
                tools = (await session.list_tools()).tools
                assert len(tools) == 38
                writers = {t.name for t in tools if not t.annotations.readOnlyHint}
                assert writers == {'fiken_create_purchase_draft', 'fiken_create_sale_draft',
                                   'fiken_update_purchase_draft', 'fiken_update_sale_draft',
                                   'fiken_attach_inbox_document_to_draft',
                                   'fiken_delete_purchase_draft', 'fiken_delete_sale_draft'}
                assert not any('createPurchase' in t.name or 'from_draft' in t.name for t in tools)
                assert 'fiken_read_document' in {t.name for t in tools}
                assert 'fiken_find_duplicate_purchases' in {t.name for t in tools}
                from test_pilot import proposal
                validation = await session.call_tool('fiken_validate_posting_proposal', {'proposal': proposal(), 'check_fiken': False})
                assert not validation.isError
                prompts = await session.list_prompts()
                assert 'foresla_kontering' in {p.name for p in prompts.prompts}
                result = await session.call_tool('fiken_get_company', {'company_slug': '../evil'})
                assert result.isError
    asyncio.run(run())


def test_read_only_mode_hides_draft_tools(monkeypatch):
    monkeypatch.setenv('FIKEN_READ_ONLY', '1')
    async def run():
        import os
        params = StdioServerParameters(command=sys.executable, args=['-m', 'server'], env=dict(os.environ))
        async with stdio_client(params) as (reader, writer):
            async with ClientSession(reader, writer) as session:
                await session.initialize()
                tools = (await session.list_tools()).tools
                assert len(tools) == 31
                assert all(t.annotations.readOnlyHint for t in tools)
    asyncio.run(run())
