# ADR-0011: Which questions a parent may be asked (P3)

Status: accepted (2026-10-16)

## Context
P1 labels are rules-only: any HPO term not matched by the test/exam word lists defaults to `cx_obs = home`, so the planner could ask a parent "Have you noticed Mental-retardation in your child?" or about hip formation, philtrum or bladder function. The P1 review (#7) asked for a wording check and an askable filter in P3.

## Decision
`Reasoner.plan_input` (shared by the API and the evaluation) now drops an askable term unless `parent_askable` holds:
- its `cx_question` and `cx_plain_label` pass `app.llm.lexicon.violations` (no disease-flavoured suffixes, eponyms, percentages, stigmatising words such as "retardation", clinical filler such as "abnormality", "hypoplasia", "morphology"); and
- for `home` questions, the term has a real lay synonym (`cx_lay_text` contains ` | `). Of 15 214 home terms at depth >= 3, 2 059 qualify.
The same lexicon checks every LLM rephrase; answer-derived findings are labelled with `cx_plain_label`, not the question sentence.

## Consequence
- Evaluation inputs changed. `make eval-smoke` (30 dev cases, 3 rounds) before: Ours top-10 63.3%, MRR 0.341; after: top-10 70.0%, MRR 0.459. n = 30, so this is noise-level evidence that nothing broke, not an improvement claim. The 400-case held-out result in ADR-0007 was **not** re-run; it describes the unfiltered planner.
- Question copy is still rules-only (`Have you noticed {label} in your child?`); wording quality will improve when `label_terms` is run with an LLM (not measured: no key).
- Demo recordings were re-made with this filter (Kabir still reaches REFERRAL_READY, Arjun ends in "watching").
