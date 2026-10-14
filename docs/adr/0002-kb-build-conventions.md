# ADR 0002: Knowledge-base build conventions (P1)

Status: accepted (2026-10-15). Values marked *default* may be tuned on the dev split in P2 (ADR-0003).

## Context
Spec §5/§11 fix the shape of `kb_<release>` but leave edge cases to the build. Source structure was
derived from the pinned files (docs/VERIFIED.md), not assumed.

## Decisions
- **Identifiers.** One normaliser (`app/kb/ids.py`): `HP:0001250`, `ORPHA:123`, `OMIM:123456`.
  Product 1 relation stored as the bare code (`E`, `BTNT`, `NTBT`, `ND`) so Q5 filters `= 'E'`.
- **Frequencies.** HPO frequency terms and `n/m`, `x%` as in spec §5. `HP:0040285`, `0/n` and `0%`
  are *excluded* annotations → `LACKS_PHENOTYPE`. `n/0` and unparseable → missing. Missing → 0.5
  (*default*). One edge per HPOA row (Q2a takes `max`), so duplicates are harmless.
- **Rows kept.** Aspect `P` only becomes edges; `I` → `Disease.inheritance` (term names), `C` is
  read for onset terms but not stored in P1. OMIM+IEA rows dropped (27,851) unless
  `KB_INCLUDE_OMIM_IEA=true`; ORPHA and DECIPHER rows are never dropped.
- **Terms.** Obsolete HPO terms are not written (588 skipped); alt ids and `replaced_by` are
  resolved when parsing annotations. All live terms are stored; `depth` = shortest IS_A distance
  below `HP:0000118` (−1 outside the phenotype subtree); `cx_system` = the top-level branch
  (smallest id when several); only phenotype-subtree terms get `cx_*` labels and embeddings.
- **bg / ic.** Annotation frequencies are propagated to all ancestors, keeping the max per disease:
  `F(D,t)`. `bg(t) = Σ_D F(D,t) / N` over diseases that have ≥ 1 positive annotation (N = 12,062),
  floored at 1e-4. `ic(t) = −ln(n_D(t) / N)` where `n_D` = diseases with `F > 0` (floor of 1).
  `_lpo` recomputes both from its own (filtered) rows.
- **Priors.** ORPHA: point prevalence class (prefer Validated, Worldwide/Europe; else any); OMIM:
  the highest prior among its *exact* ORPHA equivalents; else Unknown (1e-6). Rescaling to
  `1 − π0` happens in the engine (P2).
- **`cx_obs` default.** Terms matching no rule are `home`. This over-labels bone/organ findings as
  askable at home (e.g. "Fractured calcaneus"); the planner (P2) must also gate on `cx_min_age_months`,
  term depth and information gain, and the spot-check sheet measures the label quality.
- **Embeddings.** `name; up to 10 layperson synonyms`, bge-small-en-v1.5, 384-d, cosine; vectors
  cached on disk by (model, text). Queries use the bge retrieval instruction prefix.
- **Split.** By PMID, `sha256(seed:pmid) / 2^64 < 0.30` → dev (seed 20260901). Order-independent,
  independent of the kb; all 10,377 cases are listed (eligibility is applied at evaluation time).
  Result: dev 2,881 cases / test 7,496 cases (1,197 PMIDs). `test_ids.txt` SHA-256
  `223e60764140a0c696b991e828e742e7fe9c43293f30444494e0c3ef9791b6d5`. The script refuses to overwrite.
- **Leave-publication-out.** `_lpo` is built by the same builder from filtered rows (not by
  deleting edges from a copy): rows whose `;`-separated references include any test PMID are
  dropped (18,096 rows). ORPHA rows cite `ORPHA:<id>`, so only OMIM-sourced rows are affected.

## Consequences
- Coverage of Phenopacket Store diagnoses by the standard kb is 99.7%, but under `_lpo` only 68.7%
  of test-split cases still have a scored disease (the publication that described a disease is often
  its only annotation source). P5 must report both denominators and treat unresolved cases as
  unreachable by construction, not as engine misses.
- Sentence-level term resolution is weaker than synonym lookup (45% vs 100% top-3 on our sets); the
  LLM `extract_story` task and the parent's confirmation step carry the sentence → term step.
