# Feature Specification: Descriptor Queue (continuous backlog)

**Feature branch**: `005-queue`
**Status**: Draft → Implemented
**Created**: 2026-06-17

## Summary
Process a backlog of descriptors **sequentially** through the proven feature
003/004 runtime loop, so a safe backlog runs unattended without launching each
task by hand. The queue, nothing else.

## Out of scope (do NOT build)
The auto-resume scheduler (waking on a reset/cadence), concurrency (sequential
only), usage adapters / live budget, other-provider workers. This is the queue,
not the scheduler.

## Behavior
- A **queue manifest** (`queues/*.json`) is an ordered list of descriptor files.
  The runtime works them one at a time through the existing dispatch → gate →
  runstate → escalate loop. Each descriptor is loaded and governed on its own
  (feature 003 per-descriptor loading).
- **Governance is not bypassed.** Each descriptor passes the same enforcement; an
  always-human class is escalated, never auto-dispatched.
- A **blocked/escalated** descriptor (always-human, or two gate failures) is
  recorded in runstate, NTFY'd, and **skipped** — the queue continues. One
  blocked item does not freeze the backlog.
- **runstate carries the queue**: `task_queue` holds every descriptor with its
  per-item status (queued / dispatched+`thread_id` / passed / failed / escalated /
  blocked); `in_flight` is the current item; `checkpoint` records the position.
  This is the field the dashboard's panel 5 already reads, so the backlog renders
  with **no dashboard change**.
- A **limit-hit pauses** the queue: checkpoint the position and the in-flight
  `thread_id`, NTFY, and stop (`status=paused`). Resume is the existing reattach
  plus continuing the remaining queue (manual restart; auto-resume is the
  deferred scheduler).
- The run **ends** when the queue is exhausted or a stop condition hits. Final
  NTFY with the tally: done / blocked / skipped.

## Acceptance (gate — deterministic)
- **AC-order**: the queue processes descriptors in manifest order through the loop.
- **AC-skip**: a blocked descriptor is recorded and skipped; the queue continues.
- **AC-runstate**: runstate reflects per-descriptor queue state across the run and
  validates against the committed runstate schema.
- **AC-resume**: on restart with an in-flight descriptor, the queue resumes by
  reattach (feature 004) and continues the remainder.

## Manual proof (recorded)
A queue of two known-good tasks (PURL + a trivial `slugify`) runs to completion
sequentially, each green with the worker's own code; a queue with an always-human
descriptor escalates+skips it while the others complete; a mid-queue interrupt
restarts and reattaches the in-flight descriptor, finishing the remainder; the
dashboard's panel 5 renders the backlog.

## Review checklist
- [x] Sequential only; governance enforced per descriptor.
- [x] Blocked item skipped, queue continues, operator paged.
- [x] runstate is the multi-task queue the dashboard already reads.
- [x] Limit-hit pauses + checkpoints; resume by reattach + position.
