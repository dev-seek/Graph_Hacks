<!-- Constellation spec v2 (locked). Section numbers are global; see 00-index.md. -->

## 9. Agents (LangGraph, `backend/app/agents/`)

LangGraph `StateGraph` with typed state (Pydantic or TypedDict) and **FalkorDBSaver** checkpointer (`from langchain_falkordb.checkpoint import FalkorDBSaver`; `FalkorDBSaver(host=..., port=...)`; `graph.compile(checkpointer=saver)`; config `{"configurable": {"thread_id": f"family_{family_id}"}}`). Human input uses `interrupt()` and resumes with `Command(resume=…)` **[VERIFY on pinned langgraph 1.2.15]**. Pinned and tested combo: langgraph 1.2.15, langgraph-checkpoint 4.3.0, langchain-falkordb 0.2.0. Use only put / `get_state` / `list(limit=…)`.

**State:** `family_id, kb_version, child_age_months, sex?, phase, round_no, round_kind, pending_questions, last_answers, pending_extraction, flags, gate, gate_inputs, artifacts`. Findings themselves live in the family graph (source of truth), not in state.

**Nodes:**
| Node | Does | LLM task (default profile) — §10.2 |
|---|---|---|
| `safety` | run rules on new text; set flags; route to `urgent` on EMERGENCY | rules; `safety_extra` (fast), add-only |
| `intake` | extract findings from story (LLM) → resolve to HPO via FalkorDB full-text + vector index → produce confirm list → `interrupt` for parent confirmation → write Findings + Evidence to family graph | `extract_story` (fast) |
| `reasoner` | load active findings from the family graph → run Q1 (prune) and Q2a–d (retrieve) on `kb` → `engine.score` over the returned rows → write Snapshot (top candidates, rare_mass) | no |
| `gatekeeper` | `engine.gates` → next phase; write Gate node | no |
| `planner` | `engine.plan` → questions with pre-generated text; optional LLM rephrase for child's age (validated against banned-word lexicon, else fall back) → `interrupt` for answers → write Round/Question/Answer + Findings | `phrase_question` (fast), optional |
| `doctor_pack` | build pack data (timeline, present/absent/unknown, suggested checks, questions to ask, clinician code) | no (templated) |
| `doc_reader` | parse uploaded doctor letter (text or PDF via pypdf) → LLM extracts findings with spans, negation, dates, source → resolve to HPO → `interrupt` confirm → write | `read_document` (`fast_advised`) |
| `referral` | draft referral letter (clinician-facing) from findings + candidates + explanation paths | `draft_referral` (`smart`), template-constrained |
| `exporter` | build a GA4GH Phenopacket v2 JSON (subject age/sex, present + excluded HPO features with onset, metaData with HPO version); validate against the schema | no |
| `watcher` | on schedule or "6 months later" demo button: advance age, re-score against latest `kb_version`, plan age-unlocked questions; if a gate newly fires, notify | no |
| `urgent` | terminal for the episode; record; show urgent copy | no |

**Centre agent** (separate graph, read-only on centre graph): answers centre questions by choosing one of the predefined, parameterised Cypher templates (§13) and filling parameters — it never writes free-form Cypher. Task `centre_template_pick` (fast); deterministic fallback by keyword.

**Watcher and knowledge updates:** keep two real KB versions as separate FalkorDB graphs (`kb_<prev_release>`, `kb_<current_release>`) from two real HPO/HPOA releases about a year apart. A family created against the older version can be re-scored against the newer one; the watcher lists which new/changed annotations moved the picture. This is real data, not invented knowledge. (Cut to single KB if time is short.)
