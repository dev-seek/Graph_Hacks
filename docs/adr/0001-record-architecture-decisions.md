# ADR 0001: Record architecture decisions

Status: accepted (2026-10-15)

## Context
Constellation's scoring, safety, data and architecture choices must be explainable to judges and to future maintainers, and tuned values must be traceable.

## Decision
Every choice that changes architecture, data, scoring or safety, and every tuned value, gets a short ADR in `docs/adr/NNNN-title.md` with Status, Context, Decision, Consequences. Locked product decisions stay in `docs/DECISIONS.md` and are not reopened.

## Consequences
Small overhead per decision; the git history plus ADRs form the project's record.
