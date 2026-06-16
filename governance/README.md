# governance/ — human-owned, worker-unwritable

These files are compiled by the per-repo **preflight** and realize the
[constitution](../.specify/memory/constitution.md) for this repo. They are
**human-owned, version-controlled, and outside every worker's writable scope**
(Constitution III). A worker may never write here — that would be a
self-modifying-permission hole.

The collision test (and the orchestrator) read these **before any task runs**.

| File | Role | Preflight sections |
|---|---|---|
| `orchestrator.md` | What the orchestrator reads: authority, what it may dispatch, what always escalates. | C, D, G |
| `worker.AGENTS.md` | What the isolated worker reads: writable scope, tools, sandbox, non-negotiables. | A, B, C |
| `gate.md` | The deterministic, exit-code-only gate definition for this repo. | A |
| `model-limit-policy.md` | Providers, limit windows, usage adapters (read/detect), stop thresholds, model floors. | D, E |
| `cadence.md` | Commit cadence, reporting topic and triggers, escalation threshold, per-task timeouts, heartbeat intent. | G |

## Status: TODO (awaiting the preflight sprint)

This repo has been mapped to a Spec Kit structure; the five governance files
above are produced by running the Magrathea project preflight (sections A–G).
Until then, the run-time defaults are those in the constitution's *Operational
Defaults* and the proven behavior recorded in `../STATUS.md` / `../SMOKETEST.md`
/ `../BETA.md`.

> Editing rule: change these by human-reviewed commit only. The worker's
> writable scope (see `worker.AGENTS.md` once generated) never includes this
> directory, the constitution, secrets, or CI/infra config.
