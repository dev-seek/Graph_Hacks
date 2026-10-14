# STATUS: TEMPLATE — Claude drafts this in P0; the human reviews and edits it, then replaces this line with: # STATUS: REVIEWED by <name> on <date>
# After that line says REVIEWED, Claude may read this file but a hook blocks it from editing it.

<!--
What this is: the three example families judges will click through. All made up.
How to draft it (Claude) and review it (human) (≈ 30 min): replace every FILL_ME. Write each story in a parent's own voice (80–150 words),
the way a tired parent would type it on a phone. No disease names. `make review-check` validates this file.
The build picks the dev-split case whose signs best match each story (+ the doctor letter for Kabir) and
uses that case to answer the follow-up questions in replay.
-->

## Kabir
- age_months: FILL_ME
- expected_path: story → 2 home rounds → see a doctor → doctor letter → referral ready → "6 months later" check
- match_criteria: multi-system (nervous system + at least one other), ≥ 8 recorded signs, presenting signs a parent can see
- story: |
  FILL_ME

## Arjun
- age_months: FILL_ME
- expected_path: story → 1–2 rounds → no escalation ("mention at your next routine visit")
- match_criteria: none (uses a case from review/negatives.yaml with expected: no_escalation)
- story: |
  FILL_ME

## Maya
- age_months: FILL_ME
- expected_path: story → emergency rule fires → urgent screen, nothing else
- match_criteria: none (story must trigger rule seizure_long_or_repeated)
- story: |
  FILL_ME
