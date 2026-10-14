# AI usage disclosure (hackathon Rules 11–13)

Truthful record of who drafted, decided and reviewed each part. AI-written text is never presented as human-written.

| Part | Drafted by | Reviewed / edited by | Tool |
|---|---|---|---|
| Product spec v2 and locked decisions (`docs/spec/`, `docs/DECISIONS.md`) | Human with AI assistance (before the build) | Human | Claude |
| P0 scaffold: repo layout, ports, Makefile, CI, API skeleton, web skeleton | Claude (autonomous build) | pending (human) | Claude Code (Sonnet 5.5, advisor Opus) |
| `review/safety_rules.yaml` | Claude (draft) | pending (human) | Claude Code |
| `review/negatives.yaml` | Claude (draft) | pending (human) | Claude Code |
| `review/demo_stories.md`, `review/doctor_letters.md` | Claude (draft) | pending (human) | Claude Code |
| Safety-rule negation/matcher fixes and adversarial tests | Claude (Sonnet 5.5) acting on Opus advisor feedback | pending (human) | Claude Code advisor |
| Source URLs and emergency/crisis numbers in `review/safety_rules.yaml` | Claude fetched and read each page (2026-10-15) | pending (human) | WebFetch |
