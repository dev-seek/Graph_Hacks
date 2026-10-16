# ADR-0012: A disease named exactly like a sign is not a banned word

Status: accepted (P4, 2026-10-16). Touches AGENTS.md rule 1 (no disease names in parent views).

## Context
The P4 lexicon test (scripts/export_lexicon.py, from FalkorDB) compares every parent-facing string with all 20,087 Orphanet disease names (≥ 8 characters). The re-recorded Kabir demo collided on five names: "Cleft palate", "Cleft soft palate" and variants. These are also HPO sign labels, and a doctor's pack legitimately says "ask whether a doctor can look for: cleft palate". A parent who types "cleft palate" is describing a sign.

## Decision
Names that equal an HPO term name (case-insensitive) are removed from the forbidden lexicon. The set is derived by the registry query `q_all_term_names`, not hand-listed. Every other disease name stays forbidden, in the Python integration test, the Vitest test and the Playwright DOM check. The parent API still never carries diseases, candidates, scores or ranks (the key scan is unchanged).

## Consequences
- A real disease whose name is also a sign cannot be detected as a leak by the string test. The structural guard (no candidate or disease keys in any parent model) is what protects those cases.
- Counts (2026-10-16, kb_20260901): 20,121 disease names; none under 4 characters; 441 equal an HPO sign name and are exempt (examples: "Cleft palate", "Achromatopsia", "Acute myeloid leukemia", "Abducens palsy"); 19,680 stay forbidden. The exempt list is written to `data/derived/disease_lexicon_sign_overlap.json` by `make lexicon`.
- Before the change: 0 collisions on the first recording, 5 on the second. After: 0.
- Residual risk: the exempt set contains a few names a parent would read as a diagnosis (for example "Acute myeloid leukemia") if a story ever produced that sign label. Review requested from the human (STATE.md, non-blocking).
- The Vitest disease-name test needs `data/derived/disease_lexicon.json` (it needs FalkorDB to build) and skips without it; the P4 gate runs `make lexicon` first, and CI relies on the banned-word and structural tests.
