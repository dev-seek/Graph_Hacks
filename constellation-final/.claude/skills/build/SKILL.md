---
name: build
description: Build Constellation autonomously from .build/STATE.md and the current phase work order. Run when the user types /build or asks to start or continue the build.
disable-model-invocation: false
argument-hint: "[optional phase id to resume from, e.g. P3]"
---

Run the operating loop in CLAUDE.md now.

- If an argument names a phase (e.g. `P3`) and that phase is not marked done, set `phase:` to it in `.build/STATE.md`; otherwise use the phase already in STATE.md. Argument: $ARGUMENTS
- Do not read the whole repository or the whole spec. Load only `.build/phases/<phase>-*.md` and the spec files it lists, when a task needs them.
- Work without asking for approval. Stop only for the reasons in CLAUDE.md step 7, after writing them into STATE.md.
- At the end of your turn, make sure STATE.md reflects reality: ticked tasks, phase table, notes for the next session.
