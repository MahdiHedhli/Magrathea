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

## Status: compiled v1.0.0 (preflight 2026-06-16)

All five files are compiled from the Magrathea project preflight (sections A–G)
and are human-owned. Key decisions captured: providers OpenAI/Codex (default
worker, `gpt-5.5`), Claude (orchestrator + last-resort), Gemini & Grok (reserved
slots); stop at 15% remaining headroom; limit-hit → pause + auto-resume at reset
(scheduler is v2); always-human = security-sensitive, bulk deletes, and
**git/GitHub history & log modification (immutable history)**; commit per phase;
report to `Mahdi-Dev`; escalate after 2 gate failures; 420 s per-task timeout.

**Deferred to v2** (intent captured, build later): the heartbeat/auto-resume
scheduler; Gemini/Grok worker adapters and their usage `read` adapters; the
Claude `detect` usage adapter.

> Editing rule: change these by human-reviewed commit only. No worker's writable
> scope includes this directory, the constitution, secrets, or CI/infra config.
> Rewriting history or altering these files is always-human (`orchestrator.md`).
