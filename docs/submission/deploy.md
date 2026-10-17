# Deploying the public demo

`DEPLOY_HOST` and `DEPLOY_DOMAIN` were not provided during the build, so nothing is deployed yet. Everything below was **verified locally on the
same compose file** (see "What was verified" and `docs/VERIFIED.md`); the DNS and certificate steps are not verified.

Target: one 2 vCPU / 4 GB VPS with Docker, a DNS A record for your domain, ports 80 and 443 open.

## Steps
```bash
git clone https://github.com/dev-seek/Graph_Hacks.git && cd Graph_Hacks
export SITE_ADDRESS=constellation.example.org        # your DNS name; Caddy gets a certificate automatically
docker compose -f docker-compose.prod.yml up -d --build falkordb
docker compose -f docker-compose.prod.yml --profile seed run --rm seed      # data + knowledge graphs + synthetic centre (about a minute with data cached; downloads add time)
docker compose -f docker-compose.prod.yml up -d --build --wait
curl -s https://$SITE_ADDRESS/api/health                                     # {"status":"ok"}
```
Optional live mode (rate limited, daily token budget in `config/llm.yaml`): put `ANTHROPIC_API_KEY=...` in a local `.env` next to the compose file and
start with `LLM_MODE=live`. The default is `replay` (no key needed). The daily budget (`budget.daily_tokens`) is counted in memory and resets when the API restarts, so also set a spend limit in the Anthropic console.

## What the stack does
- Only Caddy publishes ports (80, 443). FalkorDB, the API and the web app are on the internal network; no MCP port is exposed.
- Caddy sets CSP, HSTS, `nosniff`, `X-Frame-Options`, caps request bodies at 8 MB, and sends `/api/*` straight to the API.
- The API trusts the forwarded client address only from Caddy (`FORWARDED_ALLOW_IPS=*` is safe because only Caddy can reach it), so the
  per-visitor limit of 10 new families per hour is per visitor, not global (`CREATE_LIMIT_PER_HOUR`).
- Families are erased after 7 days (`PURGE_AFTER_DAYS=7`, hourly sweep); the daily watcher runs every 24 h.

## After a reboot or a FalkorDB restart
`restart: unless-stopped` brings the containers back and FalkorDB reloads its snapshot. We observed (docs/VERIFIED.md) that after a restart of a seeded
volume free-text term search can rank differently, even after re-running the seed in place, and that graphs created since the last snapshot are lost.
A fresh volume is deterministic. For a demo that must behave exactly like the recordings (this erases families, which the public demo deletes after 7 days anyway):
```bash
docker compose -f docker-compose.prod.yml down
docker volume rm constellation-prod_falkordb_data
docker compose -f docker-compose.prod.yml up -d --build falkordb
docker compose -f docker-compose.prod.yml --profile seed run --rm seed
docker compose -f docker-compose.prod.yml up -d --build --wait
```

## What was verified (local, 2026-10-17)
Fresh volume → seed (42 s with data cached) → stack healthy → all headers present → 29 Playwright tests pass through Caddy → the 11th family
create returns 429 → a spoofed `X-Forwarded-For` is ignored. **Not verified:** a real domain with automatic HTTPS, a 2 vCPU / 4 GB VPS, behaviour under load.
After deploying, run the browser suite against the live URL: `E2E_BASE_URL=https://your.domain pnpm --dir web e2e` (set `CREATE_LIMIT_PER_HOUR=1000` for the run).
