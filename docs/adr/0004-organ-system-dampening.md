# ADR 0004: Organ-system dampening (gamma) is OFF

Status: accepted (P2).

Spec §7 keeps gamma only if it improves dev MRR without raising false referral. Result on the 120 tuning cases with the other tuned values fixed: gamma on MRR 0.283, gamma off MRR 0.332 (false referral 0.00 in both). So `gamma_on: false` in config/engine.yaml. The code and tests keep both modes (`gamma_on=True` is the spec default of the dataclass).

Why plausible: findings in one body system are often genuinely correlated in the annotated diseases, so damping the k-th finding in a system discards real evidence.
