# ADR 0003: Tunable scoring values (eps, lambda, source weights) and other defaults

Status: accepted (P2). Tuned on the DEV split (120 sampled cases, seed 20260901) plus the 40 reviewed synthetic negatives. Nothing here touched the frozen test split or `_lpo`.

## Chosen values (config/engine.yaml)
| Value | Spec start | Chosen | Note |
|---|---|---|---|
| eps (no-link noise LR) | 0.05 | **0.02** | grid 0.01 / 0.02 / 0.05 |
| lambda (broader-match decay) | 0.35 | **1.0** | upper edge of grid {0.35, 0.6, 1.0}: stronger decay was better; not explored further |
| w parent_story / parent_answer | 0.6 / 0.7 | **0.8 / 0.9** | grid (0.6,0.7) (0.8,0.9) (1.0,1.0); doctor_exam and lab_or_test stay 1.0 |

Method: coordinate descent (pi0 x eps, lambda x beta, weights, gamma, refine). Objective: dev MRR after 3 simulated rounds. Feasibility at each step: false referral <= 10% and false see-doctor <= 30% on the negatives at the spec default taus (a refinement added before tuning the taus, see ADR-0005). Logs: `.build/logs/tune-grid2.out`.

## Other values (unchanged)
- Missing HPOA frequency 0.5 (spec §5): not tuned (needs a kb rebuild).
- `bg` floor 1e-4; `cx_system` rule per ADR-0002.
- Doctor pack lists up to 8 exam checks plus 3 suggested tests in the simulator (a simulation setting, not tuned; 5 checks gave a lower referral sensitivity ceiling).

## Caveats
Dev MRR rose from about 0.12 (spec defaults) to 0.34 on the 120 tuning cases; those cases were used for tuning, so the headline number comes from the frozen test run in P5. lambda sits at the grid edge.

## Rule
Nothing here may be tuned on the frozen test split. The `lpo_test_*` numbers in `coverage_P1.json` are an eligibility check only.
