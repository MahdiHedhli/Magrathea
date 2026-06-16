# Feature Specification: Conductor Walking Skeleton

**Feature branch**: `001-walking-skeleton`
**Status**: Implemented — `v0.1-beta` (proven green, smoketested)
**Created**: 2026-06-16

## Summary

Prove exactly one path end to end: an orchestrator launches Codex as a
controllable worker, dispatches one real task, verifies the result with a
deterministic gate the orchestrator itself defines, then reports over NTFY.
This is a walking skeleton, not the full platform.

## User Scenarios & Testing

### Primary scenario
As the operator, I dispatch a single coding task to a sandboxed Codex worker and
get back a trustworthy pass/fail, decided by a deterministic gate I own — without
hand-writing the solution myself.

1. The orchestrator opens a Codex session and captures a `threadId`.
2. It dispatches a task: make the failing gate pass, nothing more.
3. The worker writes the implementation inside its sandbox.
4. The orchestrator runs the gate (`pytest`) itself; green is the only pass.
5. The orchestrator reports the result over NTFY.

### Acceptance (the gate)
- **AC-1** A session opens and a `threadId` is captured. ✅
- **AC-2** The worker (not a human) writes `gate/purl.py`. ✅
- **AC-3** `pytest gate/test_purl.py` returns 0 with 8/8 passing. ✅ (repeatable)
- **AC-4** On a worker/model/infra failure, the run classifies it
  `BLOCKED_INFRA`, runs the gate for the record, escalates, and does **not**
  attempt a reply retry. ✅
- **AC-5** On a gate-red (worker produced failing code), the run feeds the
  failing output back once via `codex-reply` on the same thread, then re-gates;
  a second red escalates. ✅ (implemented; green landed first attempt so the
  retry was not needed live)
- **AC-6** Every outcome is reported over NTFY (progress or high-priority
  blocker). ✅

### Edge cases
- Worker model unavailable / wrong CLI version → infra failure, escalate
  (Principle II), never silently degrade.
- Provider limit-hit mid-run → pause and reattach by `threadId` (Principle VII).
- Worker tries to write outside its scope → blocked by the sandbox (Principle IV).

## Requirements

### Functional
- **FR-1** Programmatic control of Codex over a stable surface that yields a
  `threadId` and can continue a thread.
- **FR-2** A deterministic, exit-code-only gate the orchestrator owns and writes
  **before** dispatch (gate-first); no model in the gate.
- **FR-3** A sandboxed worker dispatch: `workspace-write` scoped to the gate
  directory, network off, no extra tools, approvals never (sandbox is the
  boundary).
- **FR-4** Dispatch → verify → (one reply retry on gate-red) → escalate logic,
  distinguishing infra failure from gate-red.
- **FR-5** Reporting on the configured channel at start, phase, blocker, and
  run-end.

### Non-functional
- Stdlib-only control surface and reporter; the only third-party dependency is
  the gate's test runner, pinned and installed locally.
- Per-task timeout; fail fast rather than stall.

### The task under test
A pure function `parse_purl(purl) -> dict` that parses a Package URL into its
components (`type`, `namespace`, `name`, `version`, `qualifiers`, `subpath`).
The full contract is pinned by `gate/test_purl.py` (the gate owns it).

## Out of scope (v2 backlog)
Multi-thread dispatch; attach-to-existing-thread as a first-class feature;
heartbeat scheduler; model tiering across providers; graceful degradation;
additional workers (Grok, Antigravity, Gemini).

## Review checklist
- [x] Acceptance is deterministic and machine-checkable.
- [x] No implementation detail leaks into requirements (see `plan.md` for those).
- [x] Every requirement maps to an acceptance criterion.
