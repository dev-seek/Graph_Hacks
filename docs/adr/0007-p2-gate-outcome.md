# ADR-0007: P2 gate outcome

Status: accepted (2026-10-15, human decision: option (a))

## Gate as worded
"Ours beats B0, B1 and B2 on the dev split with a controlled false-alarm rate."

## Held-out result (400 dev cases, disjoint from the 120 tuning cases; 3 rounds; bootstrap 95% CIs)
| method | top-1 % | top-3 % | top-10 % | MRR |
|---|---|---|---|---|
| B0 story only | 17.0 [13.5, 20.5] | 31.0 [26.5, 35.5] | 56.2 [51.0, 61.3] | 0.286 |
| B1 random x3 | 19.8 [16.0, 23.8] | 35.0 [30.5, 39.5] | 58.5 [53.5, 63.2] | 0.314 |
| B2 frequent x3 | 25.0 [20.8, 29.2] | 41.8 [36.5, 46.8] | 60.5 [55.8, 65.8] | 0.368 |
| Ours x3 | 25.2 [21.2, 29.5] | 42.2 [37.2, 47.0] | 60.2 [55.2, 65.2] | 0.369 |

Paired top-10 gain of Ours, 95% CI: vs B0 +1.0 to +7.3 pts; vs B1 -1.5 to +4.7; vs B2 -3.3 to +2.7.

## Outcome
The gate **as worded is not met**: Ours beats B0 but is statistically level with B1 and B2 (intervals include zero). We do not reword the gate.
Human decision (Manoj): accept and report honestly (option a). Consequences:
- No re-tuning toward B2 and no planner change. The tuned values in ADRs 0003-0006 stand.
- Thresholds tau0/tau1/tau2 = 0.30/0.40/0.50 stay.
- Negatives (40 reviewed vignettes, after the 6 accepted phrase-map corrections, no re-tuning): false referral 0%, false see-doctor 20.0% (was 22.5%), safety floor 0/40. Referral sensitivity on dev positives is about 21%; 25% of dev positives end at "mention at routine visit" (ADR-0006).

## Reporting
- README and the submission text state the result as "level with the strongest simple baseline on dev (MRR 0.369 vs 0.368), clearly above story-only", with the table above. The product case rests on the safety rules, the graph-first rounds, the gates and the false-alarm control, not on a ranking win.
- P5 runs the frozen test split on `kb_20260901_lpo` once and reports whatever it shows, including against B0-B2, with no tuning.
