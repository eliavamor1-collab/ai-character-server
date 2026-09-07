# AI Character — Perchance Proxy

Lightweight proxy for the AI Character app.

- **camoufox** solves the Cloudflare managed challenge briefly and captures a
  `cf_clearance` cookie + `userKey`.
- **hrequests** (light) handles all `/generate` calls using that cookie.

## Endpoints

- `GET /health` — keep-alive
- `POST /generate` — body `{ "prompt": "...", "stopSequences": [...] }` → `{ "text": "..." }`

## Deploy (Render, Docker)

1. New Web Service → connect this repo.
2. Runtime: **Docker**.
3. Instance: Free.
4. No env vars required (`RENDER_EXTERNAL_URL` is provided automatically and
   used for keep-alive self-ping).
