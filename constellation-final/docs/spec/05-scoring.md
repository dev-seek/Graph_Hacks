<!-- Constellation spec v2 (locked). Section numbers are global; see 00-index.md. -->

## 7. Scoring engine (graph-first retrieval + `backend/app/engine/` maths)

**Rule (hackathon R3):** FalkorDB retrieves and connects; Python only does arithmetic on what the graph returns. Every round runs the Cypher queries in §13 (prune → retrieve → planner annotations). The only in-memory structure is an HPO ancestor-set cache (loaded from FalkorDB at startup, keyed by `kb_version`) used by the planner for speed. Background frequency `bg`, information content `ic`, organ system `cx_system` are precomputed at kb build and stored on `(:Term)` nodes. If FalkorDB is down, the API returns 503 — there is no fallback path that works without the graph.

The method below is **locked**. Values marked *tuned* are chosen on the **dev split + synthetic negatives only** and recorded in ADRs 0003–0006 at the end of Phase 2.

**Definitions.** `anc(t)` = t plus ancestors; `desc(t)` = t plus descendants; `f(D,a)` annotation frequency (table §5); `F(D,t) = max{ f(D,a) : a ∈ desc(t) }` (propagated, exact or more specific); `bg(t)` = mean over all diseases of `F(D,t)` (0 if none), floored at 1e-4; depth/hops from `IS_A`.

**Step 1 — Prune (Cypher Q1).** Present findings: drop any term that is an ancestor of another present term. Absent findings: drop any term that is a descendant of another absent term. Unsure answers are not findings.

**Step 2 — Per-finding LR for disease D** (rows come from Cypher Q2a/Q2b):
| Finding | Case | LR |
|---|---|---|
| present f | `F(D,f)` defined (exact or more specific annotation) | `F(D,f) / bg(f)` |
| present f | only a broader annotation `a ∈ anc(f)`, `1 ≤ d(f,a) ≤ 4` hops, `a` at depth ≥ 3 below HP:0000118; choose the `a` maximising the LR | `f(D,a) · exp(−λ·d) / bg(a)`, `λ = 0.35` *tuned* |
| present f | D has `neg=true` (NOT) annotation covering f | `0.001` |
| present f | no link within 4 hops | `ε = 0.05` *tuned* |
| absent f | `F(D,f)` defined | `(1 − min(F, 0.999)) / (1 − bg(f))` |
| absent f | D has NOT annotation for f or an ancestor | `1.5` |
| absent f | otherwise | `1` |

**Step 3 — Weights and combination.**
```
log score(D) = log prior(D) + Σ_f  w(source_f) · γ_k(f,D) · clip(log LR(f,D), −ln 100, +ln 100)
```
- `w`: parent_story 0.6, parent_answer 0.7, doctor_exam 1.0, lab_or_test 1.0 (*tuned*).
- Organ-system dampening `γ`: for each disease D, group present findings by `cx_system` (top-level HPO branch under HP:0000118); sort each group by `|log LR(f,D)|` descending; k-th in group gets `γ = 1.0, 0.6, 0.35 (k ≥ 3)`. Absent findings get `γ = 1`. **Kept only if it improves dev MRR without raising false referral** (*tuned on/off*, ADR-0004).

**Step 4 — Common-explanation class D₀.** Prior mass `π₀ = 0.97` (*tuned*), LR = 1 for every finding, and multi-system decay: with `M` = number of distinct `cx_system` values among present findings,
```
log score(D₀) = log π₀ − β · max(0, M − 2),   β = 0.45 (tuned)
```
Rare priors are scaled so `Σ prior(D) = 1 − π₀`. Normalise all scores (log-sum-exp) over retrieved candidates ∪ {D₀}. Diseases not retrieved by Q2 have no linked present finding, so every present finding gives them the same noise LR `ε`. Their combined mass is one exact term computed once per round: `(Σ_unlinked prior(D)) · exp(Σ_f w_f · γ_f · log ε)` (γ by system grouping of the findings). It goes into the normaliser but is never shown as a candidate. This keeps normalisation correct without scoring 8–12k diseases.

Outputs: `rare_mass = 1 − P(D₀)`; ranked diseases with posteriors (clinician view only); per-disease top supporting / opposing findings with their LR and the graph path id.

**Invariants (property tests, Hypothesis):** scores finite; finding order irrelevant; adding a present f with `F(D,f) > bg(f)` never lowers D relative to a disease with no link; an absent obligate sign pushes D down by ≥ ×500; `w = 0` ≡ finding removed; a broader-match LR never exceeds the exact-match LR for the same frequency; pruning is idempotent; `γ` off ≡ all γ = 1.

**Performance budget:** Q1+Q2 < 300 ms, scoring < 100 ms, planner < 500 ms per round on the full kb (benchmark test in Phase 2).
