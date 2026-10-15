# ADR-0008: Q2 rewritten for performance (spec deviation)

Status: accepted (2026-10-15)

## Context
Spec §11 (Q2a, Q2b, Q2d) as written scans every `HAS_PHENOTYPE` relationship first and filters by term afterwards (`GRAPH.EXPLAIN`: `Conditional Traverse (x)<-[r]-(d)` under `Unwind`). On the full dev kb this blows the per-round budget (Q1+Q2 < 300 ms).

## Decision
Bind the term first and force the order with `WITH DISTINCT` before the relationship match (registry files `q2a_exact_or_specific`, `q2b_broader`, `q2c_not_present`, `q2d_absent`). Results are identical to the spec text; only the plan changes.
Second deviation: Q2a and Q2d take one `$fid` per call, because `UNWIND` followed by a downward variable-length match silently returns 0 rows in FalkorDB 6.0.2 (repro in `docs/VERIFIED.md`). The reasoner calls them once per finding.

## Timings (full dev kb `kb_20260901`, median of 3, FalkorDB 6.0.2, this laptop)
| Query | spec text | rewritten |
|---|---|---|
| Q2a, one finding (median over 8 findings) | 598 ms | 0.8 ms |
| Q2b, 8 findings together | 9,257 ms | 31 ms |
| Q2d | 0.7–1.2 s (P2 task 3 measurement, see VERIFIED.md) | ~14 ms |

Per-round p90 with prune, retrieve, score and plan together: retrieve 80 ms, score 31 ms, plan 98 ms (`test_benchmark_p2.py`).

## Equivalence
`backend/tests/test_graph_q2_equivalence.py` runs the spec text and the registry queries on the small kb and asserts equal rows for Q2a–d (Q2b's `hops` agrees because the rewritten path stops before the annotation edge, so `length(p)` equals the spec's `length(p) - 1`). The test deepens two fixture terms so the broader-annotation branch is exercised.

## Consequences
Python merge rules (spec: exact wins over broader, NOT overrides both) are unchanged. If a later FalkorDB release fixes the UNWIND issue, Q2a/Q2d could be batched again.
