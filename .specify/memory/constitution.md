<!--
SYNC IMPACT REPORT
- Version: (none) → 1.0.0  (initial ratification)
- Principles defined: I Gate-First Verification, II Escalate Don't Barrel,
  III Human-Owned Governance, IV Sandboxed Least-Privilege Workers,
  V Security Pinned to a Strong Model, VI Two Budgets, VII Recovery by Reattach,
  VIII Reproducible & Auditable
- Added sections: Governance Artifacts, Operational Defaults, Governance
- Templates aligned: .specify/templates/spec-template.md ✅,
  plan-template.md ✅, tasks-template.md ✅
- Deferred (filled by per-repo preflight): governance/model-limit-policy.md,
  governance/cadence.md, governance/orchestrator.md, governance/worker.AGENTS.md,
  governance/gate.md  → marked TODO until the preflight sprint compiles them.
-->

# Magrathea Constitution

Magrathea governs autonomous coding runs: an **orchestrator** plans and
dispatches work to sandboxed **workers** (e.g. Codex), verifies each result with
a deterministic **gate**, and reports. This constitution states the principles
that hold across every run and every governed repo. It is human-owned; no worker
may amend it.

## Core Principles

### I. Gate-First Verification
Every change is accepted or rejected by a **deterministic, exit-code-only gate
that the orchestrator owns and writes before dispatch**. No model sits in the
gate. "Done" is a command (test/typecheck/lint/build) that returns 0, run in a
named directory — never a model's opinion. A worker that cannot turn the gate
green does not ship; it escalates. Rationale: a cheap model can produce
plausible-but-wrong output; only a reproducible check defends the main branch.

### II. Escalate, Don't Barrel
Any decision that is genuinely the operator's — an architecture fork, an
ambiguous spec, a repeated failure, a prohibited action — is a **blocker**. The
orchestrator reports it and stops; it never loops indefinitely or guesses
through it. Repeated gate failure on one task escalates after the configured
threshold. Rationale: an unattended run that barrels is more dangerous than one
that pauses.

### III. Human-Owned Governance
The governance artifacts (this constitution, the orchestrator rules, the worker
rules, the gate definition, the model/limit policy, the cadence config) are
**human-owned, version-controlled, and outside every worker's writable scope**.
A worker that can edit the rules that govern workers is a self-modifying-
permission hole. Governance changes happen by human-reviewed commit, never by a
dispatched run. Rationale: authority must not be self-granted.

### IV. Sandboxed, Least-Privilege Workers
A worker runs **sandboxed** (`workspace-write`, scoped to explicitly named
writable directories; network and arbitrary shell off by default) and gets
**exactly the tools a task needs, default none**. The sandbox — not an approval
prompt — is the safety boundary, because no human is watching to approve. Desktop
fidelity is opt-in: a worker receives only the QA/browser servers named in its
per-repo rules, never the operator's full interactive tool set. Rationale:
least privilege contains a wrong or compromised worker.

### V. Security Pinned to a Strong Model
Security-relevant task classes are **pinned to a strong model regardless of
cost**, and are never optimized below that floor. The planner may pick the
cheapest model that clears a gate for ordinary work, but a cheap model that
passes a gate can still ship an exploitable change the gate cannot see.
Rationale: model-floor by task class, not by price.

### VI. Two Budgets
Implementation runs on the **abundant worker provider**; the orchestrator spends
the **scarce shared bucket** (Claude, shared across chat, Code, and Cowork) on
itself. The orchestrator defaults to the cheap-but-capable tier (Sonnet),
reserving the strong tier (Opus) for planning calls. Rationale: never starve the
scarce bucket to do work the abundant one can do.

### VII. Recovery by Reattach
A provider limit-hit is a **third outcome — pause, not fail, not retry**. A
cut-short run checkpoints durable state (done, queued, and the `threadId` of
anything in flight), names its reset time, and on resume **reattaches the
in-flight thread by `threadId`** rather than restarting. Reattach is proven
before it is relied on. Rationale: work is never lost to a ceiling.

### VIII. Reproducible & Auditable
Dependencies are pinned and installed locally, never globally. Work commits at
defined boundaries with clear messages so progress is recoverable. Every run
reports on the configured channel at start, phase, blocker, limit-pause, and
run-end. Rationale: a run you cannot reproduce or audit you cannot trust.

## Governance Artifacts

Per governed repo, this constitution is realized by five human-owned files
(compiled by the per-repo **preflight**, never by a worker):

| Artifact | Path | Read by |
|---|---|---|
| Orchestrator rules | `governance/orchestrator.md` | the orchestrator |
| Worker rules | `governance/worker.AGENTS.md` | the isolated worker |
| Gate definition | `governance/gate.md` | the orchestrator (Principle I) |
| Model & limit policy | `governance/model-limit-policy.md` | the orchestrator (V, VI) |
| Cadence config | `governance/cadence.md` | the orchestrator (VIII) |

Until the preflight runs for a repo, these are TODO. The generated role files are
what the collision test reads first, before any task runs.

## Operational Defaults

Global defaults, overridable per repo in the files above: orchestrator model
**Sonnet** (Opus for planning); worker sandbox **`workspace-write`** scoped to the
repo's writable dirs; worker tools **none**; recovery **pause-and-resume** on a
limit-hit; commit **per phase**; escalate after the configured consecutive
gate-failure count; per-task (not global) timeouts.

## Governance

This constitution supersedes other process docs where they conflict. It is
human-owned and amended only by human-reviewed commit. Amendments record a
version bump (semantic: MAJOR for principle removals/redefinitions, MINOR for a
new principle or section, PATCH for clarifications), the date, and a migration
note when behavior changes. Per-repo governance files may tighten but never relax
these principles; any relaxation is itself a blocker requiring the operator.

**Version**: 1.0.0 | **Ratified**: 2026-06-16 | **Last Amended**: 2026-06-16
