# ADR 0003: Tunable scoring defaults

Status: open (created in P1; finalised at the end of P2, tuned on the dev split + synthetic negatives only).

## Values recorded so far
- Missing HPOA frequency → 0.5 (spec §5). Not yet tuned.
- `bg` floor 1e-4 (spec §7). `cx_system` = smallest top-level id among reachable branches (deterministic tie-break, ADR-0002).
- Other §7 values (λ, ε, w, γ, π0, β) are added here when P2 tunes them.

## Rule
Nothing here may be tuned on the frozen test split. The `lpo_test_*` numbers in `coverage_P1.json` are an eligibility check only and must never feed back into tuning.
