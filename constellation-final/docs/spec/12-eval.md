<!-- Constellation spec v2 (locked). Section numbers are global; see 00-index.md. -->

## 14. Evaluation (`eval/`)

**Data.** Phenopacket Store 0.1.27. Keep cases with a diagnosis that resolves to a `kb` disease node (directly or via an exact `EQUIVALENT_TO`) and ≥ 5 present phenotypic features. Report coverage: share of all store diagnoses that resolve (target ≥ 90%; if lower, report and investigate before tuning). Split **by source publication (PMID)** with a fixed seed: **dev 30% / test 70%**. Write `eval/splits/dev_ids.txt` and `eval/splits/test_ids.txt` from the split script; README carries the SHA-256 of the test list. The test split is frozen from Phase 1.

**Leakage guard.** Test runs use `kb_<release>_lpo` (HPOA rows citing any test-case PMID removed). Report both `lpo` and standard results; headline = `lpo`.

**Hit rule.** A prediction is a hit if it equals the target ID or an exact (`relation = 'E'`) equivalent. Broader/narrower mapping hits are reported in a separate column, never in the headline.

**Synthetic negatives.** `review/negatives.yaml` (drafted by Claude, reviewed by the human): 40 common-explanation vignettes as finding lists, **fixed before any tuning**, labelled synthetic (isolated speech delay, simple febrile seizure, constitutional growth delay, benign joint hypermobility, viral gastroenteritis, familial short stature, mild motor delay that resolved, …).

**Simulated parent** (no LLM):
1. Story = 2–3 present `home` features, earliest onset first.
2. Asked term q: `yes` if q or a descendant is present (5% flipped to `unsure`); `no` if q or an ancestor is explicitly excluded; otherwise **`unsure` 90% / `no` 10%** (primary), with a sensitivity table at 0% / 10% / 30% `no`.
3. When G1 fires, the doctor visit reveals present `exam` terms listed in the doctor pack's checks, plus up to 3 suggested `test` terms.
4. Age gating applies: the simulated child's age is taken from the phenopacket when available, else 60 months.

**Baselines:** B0 story only; B1 4 rounds of random home questions; B2 most-frequent unasked sign among the top 10; **Ours**. B3 (LLM interviewer) is **cut**. Published figures (GPT-4 19.2% top-1 / 32.5% top-10; Exomiser phenotype-only 35.5% top-1; DeepRare 57.18% Recall@1) appear in the README as context only — different datasets and settings.

**Metrics per round 0–4 and after the doctor visit:** top-1/3/10, MRR, median rank, questions asked, rounds to G1, referral sensitivity (positives), false referral and false see-doctor on the 40 negatives, per-round latency; bootstrap 95% CIs. Output `eval/reports/<date>.md` + JSON + PNG charts.

**Smoke:** 30 dev cases, 3 rounds, < 2 min, in CI.

**Honest framing:** "On real published cases with simulated answers…"; not a clinical validation; never "saves 4.7 years".
