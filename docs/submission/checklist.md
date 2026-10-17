# Submission checklist (spec §18) with evidence

Legend: [x] done and evidenced, [ ] human-only or blocked on something only the human has.

## Done
- [x] Public GitHub repo, MIT licence: `LICENSE`; repo `github.com/dev-seek/Graph_Hacks`. **Check it is set to public before submitting** (human).
- [x] No secrets: gitleaks v8.28.0 over the full history, 92 commits, "no leaks found" (2026-10-17); `.env` git-ignored, `.env.example` lists names only; CI job `secrets` runs gitleaks on every push.
- [x] README sections 1-11 per §18: `README.md` (problem, 3-command setup, architecture and graph Mermaid diagrams, Cypher + algorithms table with file links, evaluation with CIs and honest framing, safety design, attributions, limits, tracks, AI disclosure). Link check: `backend/tests/test_readme_links.py`.
- [x] Three-command local setup works from a fresh clone: see "Fresh-clone test" below.
- [x] All three tracks named: README top, sections 5 and 9.
- [x] Rules 11-13: `docs/AI_USAGE.md` (who drafted, decided and reviewed each part; pending-review rows are marked as such).
- [x] Every module explainable: `docs/explain/P0.md` to `P6.md`.
- [x] Live inspector (never-cut): `/j/<id>/inspector` shows the queries FalkorDB runs for an example-story family (ADR-0016, e2e `web/e2e/inspector.spec.ts`); `/demo/*` replays recorded queries and says so; the centre dashboard has its own live log.
- [x] Dependency audit: `make audit` (pip-audit and pnpm audit, "No known vulnerabilities found"); gating in CI.
- [x] Retention and abuse limits: 7-day purge job (integration test), per-route rate limits, upload size caps (5 MB PDF, 8 MB edge), daily token budget for live mode (unit tests).
- [x] Deployment files verified locally: `docker-compose.prod.yml`, `Caddyfile`, `web/Dockerfile`, `docs/submission/deploy.md`; 29 browser tests pass through Caddy (docs/VERIFIED.md).
- [x] Demo GIF in the README: screenshot slideshow (`scripts/make_gif.py`).
- [x] Drafts for the human: `video_script.md`, `blog_outline.md`, `deploy.md`.

## Human-only (not done)
- [ ] **Live deployment link.** Provide `DEPLOY_HOST` and `DEPLOY_DOMAIN`, follow `docs/submission/deploy.md`, run the browser suite against the URL, put the URL in the README table.
- [ ] **Demo video (at most 3 minutes), voiced by you:** `docs/submission/video_script.md`. Add the link to the README.
- [ ] **Blog post** (side prize), written or edited by you: `docs/submission/blog_outline.md`.
- [ ] Optional: replace the README slideshow GIF (`docs/media/demo.gif`, stitched from screenshots; no screen recorder or ffmpeg was available) with a real screen recording.
- [ ] **Team and tagline** in the README and the video.
- [ ] Review the rows marked "pending (human)" in `docs/AI_USAGE.md`, or leave them as "pending" (do not claim a review that did not happen).
- [ ] Review ADR-0012 (441 disease names that equal sign labels are allowed in parent text).
- [ ] Optional: set `ANTHROPIC_API_KEY`, run `make llm-contract`, re-record demos with `LLM_MODE=record`, then update the "not measured" statements (README sections 3 and 8, ADR-0009).
- [ ] Optional: official HPO logo for the footer and About page (HPO requests it); fill `data/derived/spotcheck_100.csv`.
- [ ] File the FalkorDB `UNWIND` performance issue upstream (repro in `docs/VERIFIED.md`).
- [ ] Ask on Discord whether one project can win several tracks (R5); submit the form naming all three tracks.

## Fresh-clone test
Run on 2026-10-17 from `git clone` of the pushed repo, a separate compose project (`cxfresh`, own volumes), only the README commands:

| Step | Time |
|---|---|
| `make setup` | 2 s (uv and pnpm caches were warm) |
| `make data up` | 24 s (images and raw data cached); 100 s when the data download was cold |
| `make seed` | 171 s (kb 114 s, previous kb, centre) |
| **Total** | **about 3.3 min** (4 min on the first, partly cold run). The limit is 15 min. |

Then, in the clone: the app answers on <http://localhost:8080>, `/api/demo/kabir/steps` returns the recording, a new family accepted a story, `make demo-replay`
reproduced all three journeys (three runs in a row), `make check` was green and `make test-int` passed (77). Caveats: warm caches; a truly cold machine adds
the Python, Node and Docker image downloads. Snags found and fixed on the way: the API image lacked `review/` (safety rules) and the demo recordings; the
dev compose still had a stub web service; `make seed` did not exist. One unexplained one-off: in the first, discarded clone run `make demo-replay`
reported `kabir: DIFFERS` (the mounts of that run were broken, so it is not a clean data point); three later runs in a clean clone all reproduced.
The temporary clone was created under `$HOME/Documents/cx-fresh-clone` (Colima shares only `$HOME` with the VM) and can be deleted.
