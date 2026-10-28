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
                assert len(tools) >= 18
                assert all(t.annotations.readOnlyHint for t in tools)
                assert 'fiken_read_document' in {t.name for t in tools}
                prompts = await session.list_prompts()
                assert 'foresla_kontering' in {p.name for p in prompts.prompts}
                result = await session.call_tool('fiken_get_company', {'company_slug': '../evil'})
                assert result.isError
    asyncio.run(run())
