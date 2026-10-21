"""Check one Nirikkha MCP server over the Streamable HTTP transport.

Start the server first in another terminal:
    python graph_server.py --http
Then run:
    python http_check.py            (default: http://127.0.0.1:8103/mcp)
    python http_check.py http://127.0.0.1:8104/mcp
"""
import asyncio
import json
import sys

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8103/mcp"


async def main() -> None:
    async with streamablehttp_client(URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            names = [t.name for t in tools.tools]
            print(f"{URL}: tools={names}")

            if "find_interlocks" in names:
                result = await session.call_tool(
                    "find_interlocks",
                    {"cik": "719739", "accession": "0001193125-22-064940"},
                )
                text = result.content[0].text if result.content else ""
                try:
                    data = json.loads(text)
                    first = data[0] if isinstance(data, list) else data
                    print("find_interlocks ->", first.get("organization", first))
                except (ValueError, AttributeError, IndexError):
                    print("find_interlocks ->", text[:200])
            print("Streamable HTTP: OK")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except BaseException as exc:
        inner = exc
        while getattr(inner, "exceptions", None):
            inner = inner.exceptions[0]
        print(f"Streamable HTTP: FAILED {type(inner).__name__}: {inner}")
        sys.exit(1)