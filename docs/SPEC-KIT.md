# Conductor → GitHub Spec Kit mapping

This repo (Conductor, the Magrathea walking skeleton) is organized to be
**compatible with [GitHub Spec Kit](https://github.com/github/spec-kit)**:
spec-driven development where a human-owned *constitution* governs, features are
*specified* before they are *planned*, and tasks are dispatched and verified.

## How the pieces map

| Spec Kit concept | Here | Notes |
|---|---|---|
| Constitution | `.specify/memory/constitution.md` | The Magrathea governance principles. |
| Templates | `.specify/templates/{spec,plan,tasks}-template.md` | For future features. |
| Feature spec | `specs/001-walking-skeleton/spec.md` | What & why (the gate as acceptance). |
| Plan | `specs/001-walking-skeleton/plan.md` | Architecture & tech context. |
| Tasks | `specs/001-walking-skeleton/tasks.md` | Phased, gate-verified, all done. |
| Agent context | `AGENTS.md` | What an agent reads on entry. |
| Implementation | `conductor/`, `gate/` | The proven `v0.1-beta` code. |

## Magrathea extension: governance/

Spec Kit's constitution is principles. Magrathea adds **`governance/`** — the
five human-owned, worker-unwritable policy files (orchestrator rules, worker
rules, gate definition, model/limit policy, cadence) compiled by the per-repo
**preflight**. This is the governance layer the orchestrator and the isolated
worker read at run time. See `governance/README.md`.

## Workflow

```
/constitution → /specify → /clarify → /plan → /tasks → /analyze → /implement
```

1. **constitution** — amend the principles (human-owned, versioned).
2. **specify** — write `specs/NNN-name/spec.md` from `spec-template.md`.
3. **clarify** — resolve `[NEEDS CLARIFICATION]` markers.
4. **plan** — write `plan.md`; run the Constitution Check.
5. **tasks** — break into gate-verified, dispatchable tasks tagged by class.
6. **analyze** — cross-check spec ↔ plan ↔ tasks for gaps.
7. **implement** — the orchestrator dispatches tasks to sandboxed workers; the
   gate decides done.

The generated `governance/` role files are what the collision test reads first,
before any task runs.
