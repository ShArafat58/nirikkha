"""An MCP client: starts each Nirikkha server over stdio, lists its tools and calls one. Run: python smoke_test.py"""
import asyncio
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

HERE = Path(__file__).resolve().parent
CHECKS = [
    ("filings_server.py", "list_sec_filings", {"cik": "320193", "limit": 3}),
    ("rules_server.py", "list_rules", {}),
    ("graph_server.py", "find_interlocks", {"cik": "719739", "accession": "0001193125-22-064940"}),
    ("crashtest_server.py", "get_replay_result", {}),
    ("regulation_server.py", "explain_sk_item", {"item": "407"}),
]


async def check(script: str, tool: str, args: dict) -> None:
    params = StdioServerParameters(command=sys.executable, args=[str(HERE / script)], cwd=str(HERE))
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = [t.name for t in (await session.list_tools()).tools]
            result = await session.call_tool(tool, args)
            text = " ".join(getattr(c, "text", "") for c in result.content)
            print(f"\n{script}: tools={tools}\n  {tool}{args} -> {text[:220]}{'…' if len(text) > 220 else ''}")


async def main() -> None:
    for c in CHECKS:
        try:
            await check(*c)
        except BaseException as exc:
            inner = exc
            while getattr(inner, "exceptions", None):
                inner = inner.exceptions[0]
            print(f"\n{c[0]}: FAILED {type(inner).__name__}: {inner}")


asyncio.run(main())