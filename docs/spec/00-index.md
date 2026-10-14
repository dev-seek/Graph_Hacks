# Spec index (v2, locked) — open only the file you need

Section numbers (§) are global and stable; other files refer to them. Values marked *tuned* are the only things that change during the build (via ADRs, dev split + synthetic negatives only).

| § | File | Read when | Lines |
|---|---|---|---|
| 1–3 | `01-product.md` | purpose, users, non-goals, journey states and rules | 72 |
| 4 | `02-ux.md` | routes, parent/clinician screens, demo journeys, live inspector, guided tour + help (§4.7) | 50 |
| 6 | `03-design-copy.md` | colour tokens, type, voice, exact copy, mandatory texts | 50 |
| 5 | `04-data.md` | data files, licences, HPOA parsing, frequency/prior tables, OMIM bridge, leakage guard | 42 |
| 7 | `05-scoring.md` | graph-first rule, LR table, weights, D₀, invariants, budgets | 41 |
| 8 | `06-planner-gates-safety.md` | planner, `cx_*` labels, gates + thresholds, safety rules engine | 37 |
| 9 | `07-agents.md` | LangGraph state, nodes, checkpointer, centre agent, watcher | 26 |
| 10 | `08-llm.md` | Claude LLM layer: port, task profiles + fallbacks, structured output, advisor, batches, replay, contract suite, embeddings | 110 |
| 11 | `09-graph-model.md` | node/edge schemas for kb, family, centre graphs | 64 |
| 12 | `10-api-mcp.md` | API routes, auth, MCP tools | 30 |
| 13 | `11-cypher.md` | every core Cypher query (Q0–Q8) + guardrails | 131 |
| 14 | `12-eval.md` | splits, simulator, baselines, metrics, leakage guard | 25 |
| 15 | `13-testing.md` | test layers, CI, coverage | 15 |
| 17 | `14-ops-security.md` | privacy, security, budgets, deployment, seams (§17.1) | 19 |
| 18–20 | `15-submission.md` | submission checklist, README outline, limitations, references | 42 |

Other references: `docs/DECISIONS.md` (locked decisions), `docs/FALKORDB_CHEATSHEET.md` (syntax + guardrails), `review/` (inputs drafted by Claude, reviewed by the human).
