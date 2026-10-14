# Constellation — all commands. Loads .env itself so app and scripts see ANTHROPIC_API_KEY.
-include .env
export

SHELL := /bin/bash
export PATH := /opt/homebrew/opt/node@22/bin:$(PATH)
RUN := scripts/run_logged.sh
NYI = @echo "$(1): not yet implemented ($(2))"

.PHONY: setup data kb up down check test-int llm-key-check review-check eval-smoke eval llm-contract demo-record demo-replay web e2e

setup:
	@$(RUN) setup bash -c "uv sync && ( [ ! -f web/package.json ] || pnpm --dir web install --frozen-lockfile ) && (uv run pre-commit install || true)"

data:
	$(call NYI,data,P1)

kb:
	$(call NYI,kb,P1)

up:
	@$(RUN) up docker compose up -d --wait falkordb api
	@echo "health: http://localhost:8000/api/health"

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

eval-smoke:
	$(call NYI,eval-smoke,P5)

eval:
	$(call NYI,eval,P5)

llm-contract:
	$(call NYI,llm-contract,P3)

demo-record:
	$(call NYI,demo-record,P3)

demo-replay:
	$(call NYI,demo-replay,P3)

web:
	pnpm --dir web dev

e2e:
	$(call NYI,e2e,P4)
