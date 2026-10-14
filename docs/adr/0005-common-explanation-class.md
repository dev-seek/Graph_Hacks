# ADR 0005: Common-explanation class D0 (pi0, beta)

Status: accepted (P2).

Chosen: **pi0 = 0.7**, **beta = 0.45** (spec start 0.97 / 0.45). Rare priors are rescaled to sum to 1 - pi0 over diseases that have at least one phenotype annotation.

Why pi0 moved: on the dev positives (all rare-disease cases) a lower pi0 always raised MRR (pi0 0.3: 0.24, 0.7: 0.23, 0.97: 0.12 at the same other values), which would push it towards "everything is rare". To stop that, every candidate had to keep false referral <= 10% and false see-doctor <= 30% on the negatives at the default taus (0.05/0.30/0.70). pi0 = 0.7 was the lowest-risk point with a feasible result; 0.5 and 0.3 gave false see-doctor 0.47 and 0.75. rare_mass is therefore a ranking-quality signal for the gates, not a calibrated probability, and the parent UI never shows it.

Beta had little effect (0.45 vs 0.9 within 0.01 MRR); kept at the spec value.
