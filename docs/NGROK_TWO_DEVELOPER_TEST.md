# Exposing the Neo Local Server with ngrok

Use this when developers on other machines need to hit your local Neo
coordination server (`POST /api/log-activity`, etc.) during a multi-developer test.
Your laptop runs the server; ngrok gives it a public https URL.

## Security

The server has no accounts. With `--ngrok` it generates (or uses) an **API token**
that every request must send as `Authorization: Bearer <token>`. Without the token
requests get `401`. Anyone with the URL *and* token can write to the activity log
and can clear it (`/api/reset-log`), so share the token only with the test group.

## One-time setup (host machine)

1. Install ngrok from https://ngrok.com/download
2. Add your authtoken once: `ngrok config add-authtoken <your-token>`

## Host: start the server with a tunnel

```bash
cd ~/Neo
.venv/bin/python3 -m cli.neo_server --clear --ngrok
```

Output includes the public URL and the token to share:

```
🌐 Public URL (ngrok): https://abc123.ngrok-free.app
🔑 API token required on every request: <token>
```

To pick your own token instead of a generated one:

```bash
NEO_API_TOKEN=my-test-token .venv/bin/python3 -m cli.neo_server --clear --ngrok
```

Stopping the server (Ctrl+C) also stops the ngrok tunnel.

## Developers: send updates to the server

Set the URL and token once, then use the client as usual:

```bash
export NEO_API_TOKEN=<token-from-host>
.venv/bin/python3 -m cli.neo_client --server https://abc123.ngrok-free.app declare alice src/auth.py "Add OAuth2"
.venv/bin/python3 -m cli.neo_client --server https://abc123.ngrok-free.app check bob src/auth.py "Add JWT"
.venv/bin/python3 -m cli.neo_client --server https://abc123.ngrok-free.app log
```

Or with curl:

```bash
curl -X POST https://abc123.ngrok-free.app/api/log-activity \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"agent_id": "alice", "file_path": "src/auth.py", "intent": "Add OAuth2", "intent_category": "feature"}'
```

## Notes

- Free ngrok URLs change each time the tunnel restarts; share the new URL.
- The local server still writes to `.devsync/activity-log.json` on the host.
- Without `--ngrok`, the server stays on `localhost` and needs no token unless
  `--token` or `NEO_API_TOKEN` is set.
- ngrok's local inspection API (port 4040) must be free. If another ngrok agent is
  already running, stop it first.
