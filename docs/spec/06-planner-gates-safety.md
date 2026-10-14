<!-- Constellation spec v2 (locked). Section numbers are global; see 00-index.md. -->

## 8. Question planner, gates and safety

### 8.1 Planner (`engine/planner.py`)
- Candidate diseases: top 50 by posterior + class D₀. Annotations come from Cypher Q3 each round.
- Candidate questions: terms with `F(D,t)` defined for any candidate, mapped up to an **askable** level (term has `cx_question` text and observability allowed for this round), excluding terms already answered or implied (present ancestors / absent descendants), excluding ancestors/descendants of each other within a batch.
- `P(yes | q) = Σ_D post(D) × p_D(q)` with `p_D(q) = F(D,q)` if defined, else `ε × bg(q)`; for D₀ use `bg(q)`.
- **Age gate:** skip q if `child_age_months < cx_min_age_months`. **Branch memory:** skip q if q or any ancestor/descendant was already asked (family graph).
- Information gain `IG(q) = H(post) − [P(yes) H(post|yes) + P(no) H(post|no)]` (treat "not sure" as no update). Optionally weight by observability cost (home 1.0, exam 0.5, test 0.3).
- Batch of 3–5 by greedy IG with diversity: at most 2 questions per `cx_system`; stop early if the next IG < 0.02 bits.
- Round types: `home` → only `home` terms; `post_doctor` → `home` + `exam` (phrased "Ask your doctor whether…" when exam). `test` terms only appear as **suggested checks** in the doctor pack / clinician view.

### 8.2 Observability and question text (`data/derived/`, our own labels; HPO itself untouched)
- For every HPO phenotype term that appears in any annotation (and its askable ancestors), assign `cx_obs ∈ {home, exam, test}`, `cx_min_age_months` (e.g. reading/school questions ≥ 60, puberty ≥ 108), `cx_system` (top-level branch under HP:0000118, computed from the tree, not the LLM), and generate `cx_question`, `cx_why`, `cx_how_to_check`, `cx_plain_label`, plus `cx_lay_text` for search.
- Method: rules first (e.g., terms under "Abnormality of blood and blood-forming tissues", terms containing "level", "concentration", "on MRI", "EEG", "biopsy" → `test`; measured growth/head circumference → `exam`), then an offline batch LLM pass (task `label_terms` via the Message Batches API, §10.5; rules-only fallback) for the rest with structured output; cached in `data/derived/term_labels.v1.jsonl` with prompt version, input hash and model id.
- Write `data/derived/spotcheck_100.csv` (100 random labels, empty `human_label` column). The human fills it when convenient — **non-blocking**; `make review-check` reports agreement once filled (target ≥ 90%) and logs it in `docs/VERIFIED.md`.
- Stored in the kb graph as separate `cx_*` properties so HPO content stays unaltered.

### 8.3 Gates (`engine/gates.py`, deterministic)
| Gate | Fires when | Result |
|---|---|---|
| G0 Emergency | any EMERGENCY safety rule | URGENT state, stop |
| G0b Urgent soon | any URGENT_SOON rule | banner + move to SEE_DOCTOR |
| G1 See doctor | after ≥ 1 home round and (`rare_mass ≥ τ1` **or** best home IG < 0.05 bits while best exam/test IG ≥ 0.1 **or** 4 home rounds done) | SEE_DOCTOR, doctor pack |
| G2 Referral | after ≥ 1 doctor/test finding, `rare_mass ≥ τ2`, ≥ 2 findings from doctor/test, and top-10 share of rare mass ≥ 0.6 | REFERRAL_READY, referral letter + Phenopacket v2 JSON |
| G3 No escalation | after ≥ 2 home rounds, `rare_mass < τ0` and no flags | "mention at routine visit" + WATCH |

Defaults `τ0 = 0.05, τ1 = 0.30, τ2 = 0.70`. Tune on the dev split: maximise referral sensitivity on positives subject to false referral ≤ 10% and false see-doctor ≤ 30% on synthetic negatives. Record chosen values and the trade-off curve in ADR-0006. Each gate decision stores its inputs (numbers + rule) in the family graph for the judge panel and audit.

### 8.4 Safety (`backend/app/safety/`)
- **Ownership (Rule 13 + safety):** the rules live in `review/safety_rules.yaml`, drafted by Claude from public guidance and reviewed by the human before use. The agent also writes the loader, schema validator (`make review-check`) and tests.
- `review/safety_rules.yaml`: each rule has `id`, `level (EMERGENCY|URGENT_SOON)`, `patterns` (regex on lower-cased text, with negation guard e.g. "no seizures"), `hpo_ids` (if a confirmed present finding matches or descends), `plain` text for the message, `source` (reference to public guidance, e.g., NHS / WHO pages) **[VERIFY each rule's wording against a public source]**.
- Starter set (EMERGENCY): seizure lasting > 5 minutes or repeated without recovery; difficulty breathing, blue/grey lips; unresponsive or very hard to wake; suspected poisoning; severe head injury; non-blanching rash with fever; fever in a baby under 3 months; signs of severe dehydration in an infant; **teen rules:** statements of self-harm, suicidal thoughts or a plan → urgent message with local crisis lines (India Tele-MANAS 14416; US 988) plus emergency numbers **[VERIFY numbers]**.
- Starter set (URGENT_SOON): loss of skills already gained (developmental regression, HP:0002376); new weakness or unsteadiness; head growing much faster than before; repeated vomiting in the morning with headache; new unexplained bruising/bleeding.
- Runs on: story, each answer batch, each uploaded document. Deterministic first; then an LLM "additional concerns" check may **add** a URGENT_SOON flag with a quoted span (never removes, never sets EMERGENCY alone — it proposes, rules decide; if the LLM proposes EMERGENCY, show URGENT_SOON plus "if you are worried, call emergency services").
- Every rule has positive and negative unit tests; a regression corpus of 60 short synthetic messages (30 should flag, 30 should not) in `backend/tests/safety/corpus.yaml`.
