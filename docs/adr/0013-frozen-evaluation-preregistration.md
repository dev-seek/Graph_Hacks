# ADR 0013: Frozen-split evaluation, pre-registered before the first test run

Status: accepted (P5). Written and committed **before** any run on `eval/splits/test_ids.txt`.

## Rules (fixed now; nothing below changes after the first test result is seen)
1. **Split.** `eval/splits/test_ids.txt`, SHA-256 `223e60764140a0c696b991e828e742e7fe9c43293f30444494e0c3ef9791b6d5`. The runner refuses to start if the file hash differs, and the report prints the hash.
2. **One case list for both knowledge bases.** Built once on the **standard** kb (`kb_20260901`): a case is kept if its diagnosis (or an exact `EQUIVALENT_TO` of it) is a scored disease on the standard kb and it has ≥ 5 present features. Present/excluded HPO ids are first mapped to live ids through the HPO alt-id/replaced-by table (the Phenopacket Store predates our HPO release; ids with no live term are dropped before counting features). The same list is used for the `lpo` run. We do **not** re-filter on `lpo`: a case whose target lost all its annotations under leave-publication-out is a **miss** (rank = none), because that is what a clinician-facing system would do. Dropping those cases would inflate the headline (P1 measured 68.7% of test cases still resolve on `lpo`).
3. **Headline = `lpo`, all cases in the list.** Secondary columns: `lpo`, cases whose target is still annotated ("annotated only"); the standard kb (leaky, shown for context only). Hits are exact mappings only (AGENTS.md rule 9).
4. **Strategies and rounds.** B0 story only, B1 four rounds of random home questions, B2 four rounds of most-frequent unasked sign among the top 10, Ours (4 home rounds + one simulated doctor visit). Simulated parent exactly as spec §14, `no` rate 10% primary. Sensitivity table: `no` rate 0% and 30% for Ours on `lpo` only (cost limit). B1/B2 run on both kbs.
5. **Parameters.** Scoring values and taus are those in `config/engine.yaml` at the time of this ADR (taus 0.30 / 0.40 / 0.50); the report records the file's SHA-256. No tuning, no threshold change after seeing any test number. The tau sweep on the test split is **report-only**.
6. **Failures.** A query timeout or error is retried 3 times, then recorded as an error and counted in the report; a case is never silently dropped. A bug found after the run is fixed, noted in STATE.md and the report, and the run repeated in full with the same rules.
7. **No per-case output.** Raw traces go to a git-ignored checkpoint that nobody opens; only aggregates are printed or committed.
8. **Negatives.** The 40 reviewed negatives are re-run on each kb at the fixed taus for false-referral and false-see-doctor rates (they are not part of the frozen split).
9. **Metrics.** top-1/3/10, MRR, median rank at rounds 0..4 and after the doctor visit; questions asked; rounds to see-doctor; referral sensitivity; per-round latency; paired bootstrap 95% CIs (1000 resamples, seed 20260901).

## Why
The leave-publication-out kb removes the annotations that were published from the same papers as the test cases; keeping the case list fixed stops the headline from improving by quietly shrinking the denominator.
