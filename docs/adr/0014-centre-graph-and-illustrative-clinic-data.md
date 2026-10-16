# ADR 0014: Centre graph, illustrative clinic data and assignment rules

Status: accepted (P5).

## Seed (`make centre`, idempotent, fixed seed 20260901)
- Source: **dev split only** (AGENTS.md rule 6), cases re-read through `app.eval.frozen.case_list("dev")` (HPO ids mapped to live ids). 250 `resolved` cases (at most 6 per diagnosis) and 50 open cases (38 `open`, 12 `referred`); 40 of the 50 have a solved look-alike with the same diagnosis, 10 do not. Case ids are pseudonyms `C-001…C-300`; every Case, Clinician, Protocol and Decision carries `synthetic: true` and the UI says "illustrative clinic data".
- The **diagnosis of an open case is never written to the graph** (tested).
- Terms = signs of all cases plus their ancestors (minus the two root terms); `HAS_ANC` is the ancestor closure of the present signs; `PRESENTED_WITH` carries the signs. `SIMILAR_TO` = IC-weighted Jaccard of the two ancestor sets, computed in Python from the in-memory ancestor cache (the one allowed structure), top 5 per case, written back. `CLOSE_TO` = the SIMILAR_TO edges with score ≥ 0.30 (466 of 1,500).
- Cases are stamped `kb_version = kb_20250901`: the clinic "opened" them when the previous HPO/HPOA release was current (`make kb-prev`, same Orphanet files). That makes the what-if real data: rescore on `kb_20260901`.

## Assignment rules (all in `backend/app/centre/rules.py`, unit-tested)
- **Clinician** (7 role pseudonyms, "Clinician A — neurogenetics" …): the clinician whose specialty owns the most frequent top-level HPO body system among the case's signs (table `SYSTEM_TO_CLINICIAN`); ties → smallest id; unknown → clinical genetics. Uses signs only, so open and resolved cases are routed alike.
- **Protocol** (7): by diagnosis-name keywords, first match wins — mitochondrial → mtDNA + panel; repeat-expansion diseases → repeat testing; imprinting disorders → methylation; deletion/duplication/trisomy/… → chromosomal microarray; enzyme/storage/-uria/-emia → metabolic screen; else targeted panel for skeletal/cardiac/sensory specialties, otherwise trio exome.
- **Turnaround** = protocol base days ± 30% (seeded). Dates are seeded within the last three years.
These are illustrations of the shape of clinic memory, not evidence about real clinics.

## Deviations from the spec text (all recorded)
- **Q7 uses `WHERE t.id IN $terms`** instead of `UNWIND … MATCH`: same rows, 13 ms vs 420 ms on the pinned image. Every look-alike must have a `MANAGED` edge (Q7 joins it non-optionally); the seed gives every case one and a test pins it.
- **Betweenness** follows stored edge direction only (docs/VERIFIED.md), so the seed also writes `(:Term)-[:PRESENTED_IN]->(:Case)` and Q8a lists both types.
- **WCC** on `SIMILAR_TO` is one component of 300 cases, so Q8b runs on `CLOSE_TO` (score ≥ 0.30); label propagation (Q8c) runs on `SIMILAR_TO`. Clusters of size 1 are not shown.
- The what-if writes its `KbUpdate`/`AFFECTED` records and the new `rare_mass` values into `centre_whatif` (the `GRAPH.COPY`), never into the live `centre`. "Crosses τ2" = rare-disease mass rises from below to at least τ2 (or falls the other way) when the open case is rescored on the newer kb.
- `centre_lookalikes.cypher` (a P3 placeholder that ignored ancestors) is replaced by Q7.
- Ask-the-centre: the model (task `centre_template_pick`) may only return one of six whitelisted template ids with exactly their params (case id must look like `C-123`); otherwise the keyword picker answers. Answers are templated text over registry-query rows; no free Cypher anywhere.
