---
phase: P1
title: Knowledge graph, OMIM bridge, splits
model: sonnet
advisor: opus
effort: high
max_budget_usd: 15
needs_reviewed_files: []
---
## Goal
`kb_<release>` and `kb_<release>_lpo` built in FalkorDB from pinned public data, with indexes, our `cx_*` labels, term resolution that works on parent words, and frozen evaluation splits.

## Read (only when needed)
§5 `04-data.md` · §8.2 `06-planner-gates-safety.md` · §11.1 `09-graph-model.md` · §13 Q0, Q1, Q5 `11-cypher.md` · §14 data/splits/leakage `12-eval.md` · §10.2, §10.7 `08-llm.md` · cheat sheet §2–4, §7–8.

## Tasks
1. `data/manifest.yaml` + `make data`: hp.json + phenotype.hpoa (latest release — record version), Orphanet en_product9_prev.xml and en_product1.json.tar.gz, Phenopacket Store 0.1.27 all_phenopackets.zip; SHA-256 verified; never committed.
2. Synthetic fixture ontology in `data/fixtures/` (fake IDs) for unit tests.
3. Parsers, tests first (use `test-engineer`): hp.json; phenotype.hpoa (frequency formats → §5 table; NOT → LACKS_PHENOTYPE; aspects; OMIM+IEA filter); prevalence → priors; en_product1 → EQUIVALENT_TO with relation (derive field names and relation codes from the file itself, log in VERIFIED.md); phenopackets → eval cases (diagnosis, present/excluded, onset, age, PMID).
4. Embedding adapter behind `EmbeddingPort` (local, bge-small-en-v1.5, CPU).
5. `make kb`: batched UNWIND writes; depth, ic, bg, cx_system; range + full-text + vector indexes (dimension from the adapter); KbInfo. Integration test for each index and Q0/Q1/Q5.
6. Term resolution service (§10.9 last paragraph) with `backend/tests/kb/lay_phrases.yaml` (50 lay phrases from HPO layperson synonyms → expected IDs).
7. `cx_*` labels (§8.2): rules first; then offline `label_terms` through the Message Batches API (§10.5) if `make llm-key-check` prints `set` (start the batch early, continue other tasks while it runs); otherwise rules-only, marking terms `cx_label_source=rules`; cache to `data/derived/term_labels.v1.jsonl`; write `data/derived/spotcheck_100.csv`.
8. Eval splits by PMID (fixed seed, 30/70) via script; print and record SHA-256 of `eval/splits/test_ids.txt`.
9. Build `kb_<release>_lpo` (drop HPOA rows whose reference cites any test PMID); record the count.
10. `/api/version` reports kb, HPO, Orphanet, Phenopacket Store, embedding model.

## Gate
- ≥ 90% of Phenopacket Store diagnoses resolve to a scored disease node (direct or exact EQUIVALENT_TO). If lower: record the number and the main cause in STATE + ADR, then continue (do not block).
- Lay-phrase top-3 ≥ 80%.
- `make kb` < 5 min; counts per label/type recorded; versions recorded.
- Test split SHA-256 committed; `_lpo` row count recorded.
- Every cheat-sheet item used so far marked verified in docs/VERIFIED.md.

## Handoff note
Coverage %, lay-phrase accuracy, label source mix (LLM vs rules), anything surprising in the data files.
