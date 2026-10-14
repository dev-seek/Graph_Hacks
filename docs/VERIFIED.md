# Verified facts

Each entry: what was checked, how, when. Nothing is used before it is listed here.

## FalkorDB Docker image tag (P0, 2026-10-15)
- Pinned tag: `falkordb/falkordb:6.0.2` (Docker Hub; same digest as `latest` at the time: `sha256:107455e8…59ba6`; amd64 + arm64). Server reports module `graph` ver `60002`, Redis 8.10.2.
- Never use `latest`. Compose and CI use this exact tag.

## FalkorDB query timeouts (P0, 2026-10-15)
- Mechanism: env var `FALKORDB_ARGS="TIMEOUT_MAX 10000 TIMEOUT_DEFAULT 3000"` on the image; confirmed with `GRAPH.CONFIG GET TIMEOUT_MAX` → 10000 and `TIMEOUT_DEFAULT` → 3000.
- Behaviour: a runaway `GRAPH.RO_QUERY` returned "Query timed out" after 3.0 s (default); with `TIMEOUT 200` appended it timed out after 0.23 s. Per-query timeouts therefore work and are capped by TIMEOUT_MAX.

## Local container runtime (P0)
- macOS dev machine uses colima (`colima start --cpu 2 --memory 4`) with docker-compose plugin 5.x.
