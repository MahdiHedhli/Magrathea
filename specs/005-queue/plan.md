# Implementation Plan: Descriptor Queue

**Spec**: [spec.md](spec.md) | **Status**: Implemented

## Technical context
Python 3.14, stdlib; reuses the feature 003/004 runtime. Worker isolated +
symlink auth (004). Codex 0.140.0, `gpt-5.5`.

## Constitution check
- [x] II Escalate (blocked skipped + paged; limit-hit pauses). [x] III Governance
  enforced per descriptor. [x] IV Sandboxed worker. [x] VII Recovery by reattach.
  [x] VIII Reproducible.

## Reuse, don't duplicate
`runtime.py` is refactored so the per-descriptor work is a shared core:
- `execute_descriptor(descriptor, handle, log_path) -> Outcome` — governance →
  isolated dispatch (early `dispatched()` on the threadId) → gate → retry →
  resolve. Writes via a small **handle protocol** (`dispatched`, `gate_recorded`,
  `done`, `escalated`) so both the single run and the queue use it. Detects a
  **limit-hit** in the worker error and returns `BLOCKED_LIMIT` (pause, not
  escalate).
- `run(descriptor)` = a single-task `RunstateWriter` (which already implements the
  handle protocol) + `execute_descriptor`. Behavior unchanged.

## Queue (`runtime/queue.py`)
- `load_manifest(path) -> list[Descriptor]` (ordered).
- `QueueRunstate(path, run_id, descriptors)` — multi-task runstate to the
  committed schema; `task_queue` = every descriptor; `handle(task_id)` returns a
  handle (the protocol above) that updates that task + `in_flight`/`checkpoint`.
- `run_queue(manifest, resume=auto)`:
  - seed per-item status from a prior runstate if the manifest matches (resume).
  - for each descriptor in order: skip if terminal; **reattach** if in-flight
    (feature 004 `resume`); else `execute_descriptor`.
  - on `BLOCKED_LIMIT` → `paused` + checkpoint + NTFY + **stop**.
  - on any other non-PASS → already escalated by the handle; NTFY skip; **continue**.
  - on exhaustion → `status=done`; final NTFY tally (done/blocked/skipped).

## Why no dashboard change
The runstate `task_queue` is already a list; the queue just fills it with N tasks.
Panel 5 iterates `task_queue`, so the backlog renders as-is.

## Verification
Gate: `pytest runtime/tests -q`. Live proof (`specs/005-queue/PROOF.md`): a
2-task backlog runs green; an always-human item escalates+skips; mid-queue
interrupt → restart → reattach + finish; dashboard panel 5 shows the backlog.
