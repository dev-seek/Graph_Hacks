# ADR 0006: Gate thresholds tau0 / tau1 / tau2

Status: accepted (P2).

Rule (pre-declared): maximise referral sensitivity on dev positives subject to false referral <= 10% and false see-doctor <= 30% on the 40 negatives; ties -> more conservative (higher tau2, then tau1).

Chosen: **tau0 = 0.30, tau1 = 0.40, tau2 = 0.50** (spec defaults 0.05 / 0.30 / 0.70).

| | referral sensitivity (dev, n=120) | false referral | false see-doctor |
|---|---|---|---|
| chosen | 20.8% | 0% | 22.5% |
| spec defaults | 22.5% | 0% | 85% |

The defaults fail the false see-doctor limit because a negative that never reaches G3 is sent to a doctor after 4 home rounds. Safety rules alone send 0% of the negatives to a doctor (safety floor 0/40).
Trade-off chart: `0006-tau-tradeoff.png` (each dot is one tau triple with false referral <= 10%; the best feasible dot is red).

## Honest reading
- Referral sensitivity is low (about 21%) because the simulated doctor visit reveals at least two exam/test findings in only about a fifth of the cases; G2 needs two. It is a property of the simulator and the gate, not a clinical claim.
- tau2 = 0.5 is lower than the spec start; the 40 negatives contain no false referral at any tau2 >= 0.5 with these scoring values, but 40 vignettes is a small sample. Revisit in P5 on the frozen test run (report only, no re-tuning).
- tau0 and tau2 sit on the edges of the sweep grid (tau0 grid 0.01-0.3, tau2 grid 0.5-0.99); wider grids were not explored.
- At the chosen taus 30 of 120 dev positives (25%) end in WATCH ("mention at routine visit"): this is the false-reassurance side of raising tau0 from 0.05. 25 reach REFERRAL_READY, 65 SEE_DOCTOR. Among negatives 31/40 WATCH, 9/40 SEE_DOCTOR, 0 referral.
- tau0 = 0.30 means "routine visit" is advised when rare_mass is below 30% after two rounds with no flags; the safety rules still override.
