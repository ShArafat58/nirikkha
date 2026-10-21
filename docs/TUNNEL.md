# Publishing local services to the internet

Some Nirikkha parts run on the developer's laptop: n8n (scheduling and alerts), the MCP servers
over Streamable HTTP, and Ollama (Private mode). To show them from outside, we use a
**Cloudflare quick tunnel** (`cloudflared`). It needs no account, no open router port and no card.
Each run gets a new temporary `https://<words>.trycloudflare.com` address.

## What we publish, and what we do not

| Service                            | Local address               | Published  | Why                                                                                                                        |
| ---------------------------------- | --------------------------- | ---------- | -------------------------------------------------------------------------------------------------------------------------- |
| n8n                                | `http://localhost:5678`     | Yes        | Show the Radar workflows; protected by the n8n owner login                                                                 |
| MCP graph server (Streamable HTTP) | `http://localhost:8103/mcp` | Yes        | Let a remote MCP client call `find_interlocks` and the other graph tools (read-only, public data)                          |
| Ollama                             | `http://localhost:11434`    | **No**     | Ollama has no authentication; publishing it would let anyone use the machine. Private mode is meant to stay on the machine |
| Backend, frontend                  | —                           | Not needed | Already deployed on Render and Vercel                                                                                      |

## Commands

```powershell
winget install --id Cloudflare.cloudflared -e

# n8n
cloudflared tunnel --url http://localhost:5678

# MCP server (start it first: python graph_server.py --http)
cloudflared tunnel --url http://localhost:8103 --http-host-header localhost:8103
```

`--http-host-header localhost:8103` is needed because the MCP SDK's DNS-rebinding protection
rejects unknown Host headers with `421 Misdirected Request`. Rewriting the Host header at the
tunnel keeps that protection switched on in the server.

## Evidence (21 Oct 2026, Cloudflare edge `dac12`, Dhaka)

| Check                                                                                             | Result                                                                                                                                   |
| ------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| `GET https://<n8n-tunnel>.trycloudflare.com/healthz`                                              | `{"status":"ok"}`                                                                                                                        |
| `python mcp-servers/http_check.py https://<mcp-tunnel>.trycloudflare.com/mcp` before the Host fix | `421 Misdirected Request` (blocked by the MCP SDK, as designed)                                                                          |
| Same check with `--http-host-header localhost:8103`                                               | `tools=['get_relationship_graph', 'find_interlocks', 'person_connections']`, `find_interlocks -> Bank of America`, `Streamable HTTP: OK` |

## Limits

- Quick-tunnel addresses change on every run and have no uptime guarantee. They are for demos, not production.
  Production would use a named Cloudflare tunnel with access rules.
- Some browsers flag `trycloudflare.com` addresses as unsafe, because the shared domain is often abused.
  The tunnels were verified from the command line instead.
- Tunnels are stopped after each demo (Ctrl + C), so nothing stays exposed.
