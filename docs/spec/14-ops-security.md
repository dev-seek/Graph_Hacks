<!-- Constellation spec v2 (locked). Section numbers are global; see 00-index.md. -->

## 17. Security, privacy, performance, deployment

- **Privacy by design:** no accounts, no names, no dates of birth (age in months), no location. Family token in the URL fragment for the first visit, then stored in `localStorage` (wrapped in try/catch) — show "save this link to come back" with a copy button. Public demo deployment deletes families after 7 days (scheduled job). Centre only receives families that opt in, de-identified to term sets and age band.
- **Security:** parameterised Cypher only; per-route rate limits; upload size/type checks, PDF text-only extraction; CORS locked to the web origin; security headers (CSP, HSTS via Caddy); secrets only via env; dependency audit (`pip-audit`, `pnpm audit`) in CI; structured logs without free text.
- **Performance budgets:** Q1+Q2 < 300 ms; score < 100 ms; question batch < 500 ms; API p95 < 2 s excluding LLM; page LCP < 2.5 s on mid-range mobile; kb build < 5 min.
- **Deployment:** Docker Compose (falkordb **pinned tag, never `latest`**, api, web, caddy) on one 2 vCPU / 4 GB VPS, FalkorDB on the internal network only, Caddy for automatic HTTPS. Public deployment defaults to replay mode for demos; live mode on with strict rate limit and daily LLM budget. Document a zero-cost local path: `make setup data kb up` with `LLM_MODE=replay` (no API key needed for demos).

### 17.1 Seams for later (build the interface and the hackathon implementation only)
| Port | Hackathon implementation | Later (not now — see the separate production roadmap, not in this repo) |
|---|---|---|
| `LLMPort`, `EmbeddingPort` (§10) | Claude adapter (profiles in config), fake, replay; local embeddings | per-region model routing, data-class policies |
| `AuthPort` | family capability tokens + clinician codes | accounts, OIDC, roles |
| `NotifierPort` | in-app banner + watcher log | messaging channels |
| `ConsentPort` | single checkbox "share de-identified with the centre" stored in the family graph | consent ledger, withdrawal workflows |
| `ExportPort` | GA4GH Phenopacket v2 JSON download | lab/EHR integrations |
Keep each port a small Protocol in `backend/app/ports/` with one implementation; no unused abstractions beyond these five.

