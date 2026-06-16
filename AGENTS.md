# AGENTS.md — Magrathea / Conductor

Agent context for this repo. Spec-driven via [GitHub Spec Kit](https://github.com/github/spec-kit);
governed by the [Magrathea Constitution](.specify/memory/constitution.md).

## What this repo is
A walking-skeleton orchestrator that drives Codex as a sandboxed, gated worker:
orchestrator → launch Codex (MCP) → dispatch one task → verify with a
deterministic gate → report (NTFY). Proven at `v0.1-beta` (see `STATUS.md`,
`SMOKETEST.md`, `BETA.md`).

## Read first (in order)
1. `.specify/memory/constitution.md` — the non-negotiable principles.
2. `governance/` — the human-owned, worker-unwritable policy files (orchestrator
   rules, worker rules, gate, model/limit policy, cadence). **TODO until the
   preflight sprint compiles them.**
3. `specs/001-walking-skeleton/` — the implemented feature (spec → plan → tasks).

## Hard rules for any agent working here
- **Gate-first**: a change is done only when its deterministic gate returns 0.
  Today's gate: `.venv/bin/python -m pytest gate/test_purl.py -q` (run from repo
  root). No model in the gate.
- **Workers never write governance**: `governance/`, `.specify/`, secrets, and
  CI/infra config are off-limits to dispatched workers (Constitution III).
  Worker writable scope is `gate/` only.
- **Sandbox is the boundary**: workers run `workspace-write` scoped to their
  writable dirs, network off, tools none-by-default.
- **Escalate, don't barrel**: operator decisions and repeated failures stop and
  report; never loop.
- **Two budgets**: orchestrator on Sonnet (Opus only for planning); workers on
  the abundant provider (`gpt-5.5`).

## Drive it (manual)
```bash
cd ~/dev/conductor
.venv/bin/python -m conductor.orchestrator        # dispatch + verify + report
.venv/bin/python phase1_control_surface.py         # prove the control surface
.venv/bin/python -m pytest gate/test_purl.py -q    # run the gate directly
```

## Spec Kit workflow for new work
`constitution → specify → (clarify) → plan → tasks → implement`, using the
templates in `.specify/templates/`. New features live in `specs/NNN-name/`.
See `docs/SPEC-KIT.md` for the mapping.
