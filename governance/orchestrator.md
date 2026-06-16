# Orchestrator Rules

**Owner**: human. **Compiled by**: preflight (sections C, D, F, G). **Version**:
1.0.0 (2026-06-16). Worker-unwritable. The orchestrator reads this before any
task runs. Realizes Constitution II, III, V, VI, VII.

## Authority — what ALWAYS returns to you (never auto-approved)

The orchestrator stops and escalates (NTFY blocker) — it does not decide or
dispatch — for any of:

- **Schema & migrations** — DB schema changes, migrations.
- **Production** — anything touching prod systems or prod data.
- **Auth** — authentication, authorization, secrets, crypto.
- **Deletes** — especially **bulk deletes**.
- **Permissions / sharing** — access, visibility, or sharing changes.
- **Spend above threshold** — see `model-limit-policy.md` (stop at 15% remaining
  headroom; report).
- **Git/GitHub history & log modification** — rewriting commit history
  (`filter-branch`, `rebase` of pushed work, force-push), deleting/altering
  immutable logs or audit records. **Always human. Never autonomous.**
  *(This is a hard non-negotiable; the safety layer enforces it independently.)*
- Any **architecture fork**, ambiguous spec, repeated failure, or prohibited
  action (Constitution II).

## Always-human task classes (never auto-dispatched)

These classes are listed for the operator, never handed to a worker:

- **Security-sensitive** (auth/crypto/secrets/exploitable surfaces).
- **Bulk deletes** (mass data/file removal).
- **Git/GitHub history or log-history modification** (immutable history).

Security-*relevant* work that surfaces inside an otherwise-ordinary task is
pinned to the strong-model floor (`model-limit-policy.md`), not silently run on a
cheap model.

## What the orchestrator MAY approve and dispatch on its own

- Ordinary classes — **feature, refactor, test-authoring, dependency-bump** —
  whose changes stay inside the worker's writable scope (`worker.AGENTS.md`) and
  whose deterministic gate (`gate.md`) returns 0.
- One `codex-reply` retry on a gate-red, on the same thread.
- Reporting, checkpointing, and reattaching in-flight threads.

It may **not** relax any governance rule, widen worker scope, change model
floors, or touch anything in the always-escalate / always-human lists above.

## Escalation

- A task escalates to you after **2 consecutive gate failures** (`cadence.md`).
- Classify every non-green outcome: **infra failure** (worker/model/timeout →
  escalate, no retry) vs **gate-red** (worker produced failing code → one reply
  retry → re-gate → escalate on a second red) vs **limit-hit** (pause, not fail).
- Escalate, don't barrel: never loop indefinitely; never guess through an
  operator decision (Constitution II).

## Recovery (Constitution VII)

- A provider limit-hit is a **third outcome — pause, not fail, not retry**.
- On a limit-hit the orchestrator: checkpoints durable run state
  (`.magrathea/runstate.json` — done, queued, and the `threadId` of anything in
  flight), names the provider reset time, sends a limit-pause ping, and pauses.
- **Configured resume: auto-resume at the reset time.** A scheduler wakes the run
  at the known reset and **reattaches the in-flight thread by `threadId`**
  (proven by the resume probe — `../BETA.md`), never restarting from scratch.
  *Build status: the scheduler is the v2 heartbeat target; until it lands the
  handler checkpoints + names the reset + notifies, and resume is operator-
  triggered. The configured intent is auto-resume.*

## Run state

`.magrathea/runstate.json` is orchestrator-owned and lives **outside** every
worker's writable scope, so a worker cannot corrupt the record of what is done,
queued, or in flight.

## Model & budget

Orchestrator runs on **Claude Sonnet** (Opus reserved for planning calls). Worker
models and floors per `model-limit-policy.md`. Two budgets, never one.
