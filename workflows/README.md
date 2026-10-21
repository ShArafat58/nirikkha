# n8n workflows

Nirikkha uses [n8n](https://n8n.io) (self-hosted, free) for scheduling and alerts.
n8n runs locally in Docker. The workflows call the deployed Nirikkha API.

| File                        | Trigger                                   | What it does                                                                                                                                                                                                                             |
| --------------------------- | ----------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `radar-daily-telegram.json` | Every day 09:00 (Asia/Dhaka) + manual run | Runs the Regulatory Change Radar scan (two streams: curated SEC rule changes + new filings on SEC EDGAR), reads the prioritised alerts, and sends a Telegram summary listing high and medium alerts that still wait for a human decision |
| `render-warmup.json`        | Every 10 minutes                          | Pings `GET /health` on the Render backend so the free instance does not sleep during demos                                                                                                                                               |

## Human in the loop

n8n never approves or rejects anything. The Telegram message links to the Radar page,
where a signed-in person chooses **Approve** or **Reject**. Every decision is stored with
the reviewer and time in the Radar audit trail (`radar_decisions` table).

## Security

- `POST /api/radar/scan` requires the `x-radar-token` header. The value is the
  `RADAR_SCAN_TOKEN` secret, set in `backend/.env` and on Render. A wrong token returns 401.
- The Telegram bot token and the scan token are stored as n8n credentials, not in these files.
  The exported JSON only references the credential names.

## Run it

```powershell
docker volume create n8n_data
docker run -d --name n8n --restart unless-stopped -p 5678:5678 -e GENERIC_TIMEZONE=Asia/Dhaka -e TZ=Asia/Dhaka -v n8n_data:/home/node/.n8n docker.n8n.io/n8nio/n8n
```

1. Open http://localhost:5678 and create the local owner account.
2. Create a workflow, then `…` → Import → From file, and pick a JSON file from this folder.
3. In **Run Radar scan**, create a Header Auth credential: name `x-radar-token`, value = your `RADAR_SCAN_TOKEN`.
4. In **Send to Telegram**, create a Telegram credential with your bot token from @BotFather, and set your own Chat ID.
5. Execute once to test, then Publish.

## Limits

n8n runs on the developer's laptop, so schedules run only while Docker is running.
Retries: 5 tries, 5 seconds apart, to ride out a cold start on the free backend.
