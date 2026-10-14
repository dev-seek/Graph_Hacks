# AI usage disclosure (hackathon Rules 11–13)

Truthful record of who drafted, decided and reviewed each part. AI-written text is never presented as human-written.

| Part | Drafted by | Reviewed / edited by | Tool |
|---|---|---|---|
| Product spec v2 and locked decisions (`docs/spec/`, `docs/DECISIONS.md`) | Before the build; provenance to be filled in by the human | Human (to confirm) | Claude (to confirm) |
| P0 scaffold: repo layout, ports, Makefile, CI, API skeleton, web skeleton | Claude (autonomous build) | pending (human) | Claude Code (Sonnet 5.5, advisor Opus) |
| `review/safety_rules.yaml` | Claude (draft) | pending (human) | Claude Code |
| `review/negatives.yaml` | Claude (draft) | pending (human) | Claude Code |
| Safety-rule negation/matcher fixes and adversarial tests | Claude (Sonnet 5.5) acting on Opus advisor feedback | pending (human) | Claude Code advisor |
| Source URLs and emergency/crisis numbers in `review/safety_rules.yaml` | Claude fetched and read each page (2026-10-15) | pending (human) | WebFetch |
| `review/demo_stories.md`, `review/doctor_letters.md` | Claude (draft) | Human (Manoj, 2026-10-15; marked REVIEWED; body text unchanged from the draft, header lines reformatted) | Claude Code |
| P1 knowledge graph: data manifest, parsers, kb builder, resolver, rule-based `cx_*` labels, split script, coverage report | Claude (Sonnet 5.5; advisor Opus; `test-engineer` subagent wrote the parser, structure and label tests) | pending (human) | Claude Code |
| `backend/tests/kb/lay_phrases.yaml` (30 verbatim HPO layperson synonyms + 20 more, all verbatim) and `lay_rewordings.yaml` (20 parent-style sentences) | Claude (expected IDs checked against hp.json) | pending (human) | Claude Code |
| `docs/DATA_LICENSES.md` HPO / Phenopacket Store text | Copied verbatim from the HPO site source and the Phenopacket Store repo by Claude (2026-10-15) | pending (human) | curl |
| Rule-based term labels and `data/derived/spotcheck_100.csv` | Claude (rules only; no LLM labels, no API key set) | spot-check pending (human, non-blocking) | Claude Code |
