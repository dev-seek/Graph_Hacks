# Constellation — all commands. Loads .env itself so app and scripts see ANTHROPIC_API_KEY.
-include .env
export

SHELL := /bin/bash
export PATH := /opt/homebrew/opt/node@22/bin:$(PATH)
RUN := scripts/run_logged.sh
NYI = @echo "$(1): not yet implemented ($(2))"

.PHONY: reset audit seed centre kb-prev lighthouse lexicon setup data kb up down check test-int llm-key-check review-check openapi eval-smoke eval llm-contract demo-record demo-replay web e2e

setup:
	@$(RUN) setup bash -c "uv sync && ( [ ! -f web/package.json ] || pnpm --dir web install --frozen-lockfile ) && (uv run pre-commit install || true)"

data:
	@$(RUN) data uv run python scripts/data.py

kb:
	@$(RUN) kb env PYTHONPATH=backend uv run python -m app.kb.cli

centre:
	@$(RUN) centre env PYTHONPATH=backend uv run python -m app.centre.seed

reset:
	@$(RUN) reset docker compose down -v
	@$(MAKE) --no-print-directory up seed

seed:
	@$(MAKE) --no-print-directory kb kb-prev centre

kb-prev:
	@$(RUN) kb-prev env PYTHONPATH=backend uv run python -m app.kb.prev

up:
	@$(RUN) up docker compose up -d --build --wait falkordb api web
	@echo "app: http://localhost:8080   health: http://localhost:8000/api/health"

down:
	@$(RUN) down docker compose down

check:
	@bash scripts/check.sh

test-int:
	@$(RUN) test-int uv run pytest -q -m integration

llm-key-check:
	@if [ -n "$$ANTHROPIC_API_KEY" ]; then echo "ANTHROPIC_API_KEY: set"; else echo "ANTHROPIC_API_KEY: unset"; fi

review-check:
	@uv run python scripts/review_check.py

openapi:
	@uv run python scripts/export_openapi.py

eval-smoke:
	@$(RUN) eval-smoke env PYTHONPATH=backend uv run python -m app.eval.cli

eval:
	$(call NYI,eval,P5)

llm-contract:
	@$(RUN) llm-contract env PYTHONPATH=backend uv run python -m app.llm.contract $$([ -n "$$ANTHROPIC_API_KEY" ] && echo live || echo fake)

demo-record:
	@$(RUN) demo-record env PYTHONPATH=backend uv run python -m app.agents.demo_cli record

demo-replay:
	@$(RUN) demo-replay env PYTHONPATH=backend LLM_MODE=replay uv run python -m app.agents.demo_cli replay

lighthouse:
	@$(RUN) lighthouse pnpm --dir web lighthouse

lexicon:
	@uv run python scripts/export_lexicon.py --probe

web:
	pnpm --dir web dev

e2e:
	@$(RUN) e2e pnpm --dir web e2e

audit:
	@$(RUN) audit bash -c "uv run pip-audit --skip-editable && pnpm --dir web audit --prod"
