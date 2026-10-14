# ADR 0005: Common-explanation class D0 (pi0, beta)

Status: accepted (P2).

Chosen: **pi0 = 0.7**, **beta = 0.45** (spec start 0.97 / 0.45). Rare priors are rescaled to sum to 1 - pi0 over diseases that have at least one phenotype annotation.

Why pi0 moved: on the dev positives (all rare-disease cases) a lower pi0 raises MRR. First stage, lambda 0.35, weights 0.6/0.7, gamma on, beta 0.45 (log `.build/logs/tune-grid2.out`):

| pi0 | eps 0.01: dev MRR | false see-doctor at spec taus |
|---|---|---|
| 0.3 | 0.238 | 0.75 (infeasible) |
| 0.5 | 0.224 | 0.35 (infeasible) |
| **0.7** | **0.225** | **0.12** |
| 0.85 | 0.211 | 0.05 |
| 0.97 | 0.199 | 0.00 |

Every candidate had to keep false referral <= 10% and false see-doctor <= 30% on the negatives at the default taus, otherwise pi0 would drift towards "everything is rare" just because the dev positives are all rare. pi0 = 0.7 had the best MRR among feasible values. rare_mass is a ranking-quality signal for the gates, not a calibrated probability; the parent UI never shows it.

Beta had little effect (0.45 vs 0.9 within 0.01 MRR); kept at the spec value.
