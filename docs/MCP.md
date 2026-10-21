# MCP in Nirikkha

Model Context Protocol (MCP) lets an AI agent call tools through one standard interface.
Nirikkha uses MCP in two ways:

1. **Built:** five MCP servers of our own that expose Nirikkha's real functions (filings, rule engine, relationship graph, Crash-Test, regulations).
2. **Used:** five community MCP servers we used while building and checking the project.

All servers run on the developer's laptop. No server needs a paid service.

---

## 1. MCP servers we built (5 servers, 13 tools)

Folder: `mcp-servers/` · SDK: official MCP Python SDK (`mcp` 1.x, `FastMCP`) · Shared helper: `common.py`

| Server              | File                   | Tools                                                             | What it exposes                                                                                                    |
| ------------------- | ---------------------- | ----------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| nirikkha-filings    | `filings_server.py`    | `list_companies`, `list_sec_filings`                              | Companies in Nirikkha; live SEC EDGAR filing list (User-Agent header, rate-limited)                                |
| nirikkha-rules      | `rules_server.py`      | `list_rules`, `evaluate_rules`                                    | The Governance Rule Engine (Reg S-K Items 401, 402, 404, 407; Pass / Potential Gap / Fail / Insufficient Evidence) |
| nirikkha-graph      | `graph_server.py`      | `get_relationship_graph`, `find_interlocks`, `person_connections` | Neo4j relationship graph of directors, executives, committees and outside organisations                            |
| nirikkha-crashtest  | `crashtest_server.py`  | `get_report_summary`, `start_crash_test`, `get_replay_result`     | Crash-Test reports, starting a new Crash-Test, the SVB First Warning Sign Replay result                            |
| nirikkha-regulation | `regulation_server.py` | `explain_sk_item`, `list_rule_changes`, `get_radar_alerts`        | Regulation S-K explanations, curated rule changes, Regulatory Change Radar alerts                                  |

The servers do not touch the database directly. They call the documented Nirikkha REST API (`NIRIKKHA_API_URL`: the deployed API or a local one), so they reuse the same auth, caching and guardrails as the web app.

### Transports (both verified)

- **stdio** (default): `python graph_server.py` — used by Antigravity and by `smoke_test.py`.
- **Streamable HTTP**: `python graph_server.py --http` serves `http://127.0.0.1:8103/mcp` (ports 8101–8105, one per server). Checked with `http_check.py`.

### Clients / hosts

| Client / host                               | How                                                                 | Verified                  |
| ------------------------------------------- | ------------------------------------------------------------------- | ------------------------- |
| Google Antigravity (agent)                  | `antigravity.mcp_config.example.json` (stdio)                       | Yes — tests 1 and 3 below |
| `smoke_test.py` (our own Python MCP client) | starts each server over stdio, lists tools, calls one tool          | Yes — all 5 servers pass  |
| `http_check.py` (our own Python MCP client) | connects over Streamable HTTP, lists tools, calls `find_interlocks` | Yes — test 9 below        |
| Claude Desktop                              | config example in `mcp-servers/README.md`                           | Config provided           |

---

## 2. Community MCP servers we used (5)

| Server              | Package                                            | Runs with              | What we used it for                                                     |
| ------------------- | -------------------------------------------------- | ---------------------- | ----------------------------------------------------------------------- |
| Filesystem          | `@modelcontextprotocol/server-filesystem`          | `npx`                  | Listed and read the SVB Replay case file to check its numbers           |
| Git                 | `mcp-server-git`                                   | Python (`.venv-ext`)   | Read the commit log for progress notes                                  |
| Fetch               | `mcp-server-fetch`                                 | Python (`.venv-ext`)   | Fetched the Federal Reserve's SVB review to check the Replay's evidence |
| Neo4j Cypher        | `mcp-neo4j-cypher`                                 | Python (`.venv-neo4j`) | Ran read-only Cypher to count nodes in our relationship graph           |
| Sequential Thinking | `@modelcontextprotocol/server-sequential-thinking` | `npx`                  | Planned the timing of the 181-second demo video                         |

Two virtual environments are needed because `mcp-server-git` and `mcp-server-fetch` require `mcp` 2.x, while `mcp-neo4j-cypher` requires `mcp` 1.x.

---

## 3. Permissions and safety

| Server              | Access                 | Limit                                                                                                                                                            |
| ------------------- | ---------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| nirikkha-\*         | Nirikkha REST API only | Read-only, except `start_crash_test`, which starts one analysis under the demo account (or `NIRIKKHA_TOKEN`) and goes through the same guardrails as the web app |
| Filesystem          | Files                  | Only `docs/` and `backend/data/`. No other folder is reachable                                                                                                   |
| Git                 | One repository         | Only this repo. Used for reading the log                                                                                                                         |
| Fetch               | Public web             | Respects `robots.txt`: SEC.gov returned 403 and the server stopped, we did not bypass it                                                                         |
| Neo4j Cypher        | Graph database         | `write_neo4j_cypher` switched off in the host; only read queries                                                                                                 |
| Sequential Thinking | None                   | No file, network or database access                                                                                                                              |

The HTTP transport listens on `127.0.0.1` only, so it is not reachable from other machines.
Secrets (Neo4j password, SEC contact) live only in the host's own config file outside the repository. The committed example uses placeholders. `.venv`, `.venv-ext`, `.venv-neo4j` and `.env` are git-ignored.

---

## 4. Evidence (run on 21 Oct 2026, host: Antigravity unless noted)

| #   | Server · tool                                      | Request                                   | Result                                                                                                                                                        |
| --- | -------------------------------------------------- | ----------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 0   | all 5 Nirikkha servers · `smoke_test.py` (stdio)   | list tools + call one each                | 5 / 5 pass                                                                                                                                                    |
| 1   | nirikkha-graph · `find_interlocks`                 | SVB, DEF 14A 2022                         | Bank of America (Kate Mitchell p.15, Laura Izurieta p.30); Charles Schwab & Co. (Michelle Draper p.29, Christopher Edmonds-Waters p.29)                       |
| 2   | neo4j · `read_neo4j_cypher`                        | count nodes by label                      | Organization 115, Person 39, Committee 21, Party 4, Filing 3, Company 2                                                                                       |
| 3   | nirikkha-crashtest · `get_replay_result`           | SVB Replay                                | VALID; detected 2, questioned 3, missed 0, not knowable 1                                                                                                     |
| 4   | git · `git_log`                                    | last 5 commits                            | Latest commits listed correctly                                                                                                                               |
| 5   | filesystem · `list_directory`, `read_text_file`    | SVB Replay case                           | 12 timeline events, 6 warning signs, freeze date 2023-03-07                                                                                                   |
| 6   | fetch · `fetch`                                    | SEC press release                         | Blocked by SEC `robots.txt` (403); server refused, as designed                                                                                                |
| 7   | fetch · `fetch`                                    | Federal Reserve SVB review                | Published 28 Apr 2023; found board and management failed to manage risks and supervisors did not act quickly enough. Matches Replay sign `ws_board_oversight` |
| 8   | sequential-thinking · `sequentialthinking`         | 181-second video plan                     | Five parts, total 181 s                                                                                                                                       |
| 9   | nirikkha-graph · `http_check.py` (Streamable HTTP) | initialize, list tools, `find_interlocks` | 3 tools listed; first interlock Bank of America; session opened and closed cleanly                                                                            |

---

## 5. Run it yourself

```powershell
cd mcp-servers
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt -r ..\backend\requirements.txt
Copy-Item .env.example .env   # set NIRIKKHA_API_URL and SEC_USER_AGENT
python smoke_test.py          # stdio check, all 5 servers

# Streamable HTTP check (two terminals)
python graph_server.py --http
python http_check.py
```

To use the servers in Antigravity, copy `antigravity.mcp_config.example.json` into the host's MCP config, replace the placeholders, and refresh.
