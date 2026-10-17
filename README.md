# Constellation

> Skeleton (P0). Sections are filled as phases complete. Outline follows spec §18.

**Not a diagnosis tool.** Constellation helps families gather evidence and reach the right specialist sooner.

## 1. Why
TODO(P6)

## 2. What it does
TODO(P6) — demo GIF

## 3. Try it

You need Docker, [uv](https://docs.astral.sh/uv/), Node 22 with pnpm, and `make`. No API key is needed:
the demos run in replay mode and every language step has a deterministic fallback.

```bash
make setup         # Python and web dependencies
make data up       # download the pinned public data (checksummed), start FalkorDB + API + web
make seed          # build the knowledge graphs and the synthetic clinic (a few minutes)
```

Open <http://localhost:8080>. Stop with `make down`.

Optional: to let Claude read the stories, put your key in a local `.env` file as `ANTHROPIC_API_KEY`
and set `LLM_MODE=live`; `make llm-key-check` reports whether it is set (never the value).

TODO(P6) — 5-minute tour with the example families; link to docs/USER_GUIDE.md

## 4. How it works
TODO(P6) — agents, gates, safety

## 5. FalkorDB inside
TODO(P6) — graphs, model (Mermaid), Cypher queries and algorithms (table with file links), checkpointer, MCP

## 6. Evaluation
TODO(P5/P6) — headline numbers with CIs and the honest framing

## 7. Data and credits
Frozen test split (`eval/splits/test_ids.txt`, 7,496 cases): SHA-256 `223e60764140a0c696b991e828e742e7fe9c43293f30444494e0c3ef9791b6d5`.

See [docs/DATA_LICENSES.md](docs/DATA_LICENSES.md).

## 8. Limits and what's next
TODO(P6)

## 9. Tracks
TODO(P6)

## 10. Built with AI assistants
See [docs/AI_USAGE.md](docs/AI_USAGE.md). Safety rules, demo stories and doctor letters are drafted by Claude and reviewed by a human; each file's first line states its status.

## 11. Licence
MIT — see [LICENSE](LICENSE).
