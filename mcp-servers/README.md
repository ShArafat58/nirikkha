# Nirikkha MCP servers

Five small MCP servers (official Python SDK, FastMCP) that expose Nirikkha's capabilities to any MCP client
(Claude Desktop, Google Antigravity, our own agents).

| Server | Tools | Port (`--http`) |
|---|---|---|
| nirikkha-filings | `list_companies`, `list_sec_filings` | 8101 |
| nirikkha-rules | `list_rules`, `evaluate_rules` | 8102 |
| nirikkha-graph | `get_relationship_graph`, `find_interlocks`, `person_connections` | 8103 |
| nirikkha-crashtest | `get_report_summary`, `start_crash_test`, `get_replay_result` | 8104 |
| nirikkha-regulation | `explain_sk_item`, `list_rule_changes`, `get_radar_alerts` | 8105 |

Transports: **stdio** (default) and **Streamable HTTP** (`python graph_server.py --http`, endpoint `/mcp`).

Permissions: every tool is read-only except `start_crash_test`, which queues one analysis under the demo
account (or the account in `NIRIKKHA_TOKEN`). No tool writes to the database or the graph directly.

## Run

```powershell
cd mcp-servers
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt -r ..\backend\requirements.txt   # rules_server reuses the backend engine
copy .env.example .env    # set NIRIKKHA_API_URL and SEC_USER_AGENT
python smoke_test.py      # an MCP client: lists tools and calls one per server
```

## Use from Claude Desktop or Antigravity (stdio)

Add to the client's MCP config (paths are examples):

```json
{
  "mcpServers": {
    "nirikkha-graph": { "command": "D:/AI_Buildfest/Nirikkha/mcp-servers/.venv/Scripts/python.exe",
                        "args": ["D:/AI_Buildfest/Nirikkha/mcp-servers/graph_server.py"] }
  }
}
```