# ADR-0009: LLM profiles (P3, task 2)

Status: accepted (2026-10-15)

## Context
Spec §10.6 asks for the cheapest Claude profile that passes a per-task contract suite. At the time of writing `ANTHROPIC_API_KEY` is **unset**, so no live call has been made.

## Decision
- **Not measured.** `make llm-contract` ran against `fake` only (plumbing check; it says so on its last line). `config/llm.yaml` keeps the spec's default profile per task (first candidate); no `chosen:` block was written. Re-run `make llm-contract` with a key to measure and write `chosen:`.
- **Model id correction.** Spec §10 named `claude-haiku-5-5`; that id is not in the verified model list (Haiku is `claude-haiku-4-5`). `config/llm.yaml` now uses `claude-haiku-4-5`. Sonnet/Opus ids are unchanged.
- **Request shape verified offline** with a stub HTTP transport (`backend/tests/llm/test_anthropic_adapter.py`): `messages.parse(output_format=…)` sends `output_config.format.type = json_schema`; the system block carries `cache_control: ephemeral`; advisor profiles go through `beta.messages.parse` with beta `advisor-tool-2026-03-01` and a tool `{type: advisor_20260301, name: advisor, model, max_uses, max_tokens}`. Whether advisor and structured output combine on the live API is **not verified**; the contract suite will mark the profile failed if they do not.
- Mode `off` always uses the deterministic fallback; `replay` on a cache miss falls back (logged), never errors.
- Budgets: per-family token cap is estimated from character counts (4 chars/token); the daily USD cap is not enforced until usage is available from live calls.
