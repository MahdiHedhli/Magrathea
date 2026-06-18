# Descriptor queue — proof

Recorded 2026-06-17. Gate: `.venv/bin/python -m pytest runtime/tests -q` → **30
passed** (incl. `test_queue`). Each live worker ran isolated (004 symlink auth).

## 1. Two-task backlog runs sequentially to completion
`python -m runtime.queue queues/backlog.json` (PURL + slugify), outputs cleared
(both gates red):
- `dispatch 'purl-parser' (1/2)` → `gate(1): passed=True :: 8 passed`
- `dispatch 'slugify' (2/2)` → `gate(1): passed=True :: 8 passed`
- runstate: `status=done`; `purl-parser→passed`, `slugify→passed`; in_flight null.
- Tally NTFY: `done | backlog 'backlog' exhausted | done=2 blocked=0 skipped=0`.
- Each green with the **worker's own code** (`gate/purl.py`, `tasks/slug/slug.py`).

## 2. A blocked (always-human) descriptor is escalated and skipped, queue continues
`python -m runtime.queue queues/backlog-with-block.json` (PURL +
history-rewrite[git-history] + slugify):
- `purl-parser → passed`
- `rewrite-history-DEMO` → `REFUSED (governance): … always-human …` → recorded,
  NTFY'd, **skipped, continuing** (not dispatched).
- `slugify → passed`
- runstate `done`; statuses `passed / escalated / passed`. Tally
  `done=2 blocked=1 skipped=0`. One block did not freeze the backlog.

## 3. Mid-queue interrupt resumes by reattach and finishes the remainder
- Ran `queues/backlog.json`, interrupted while the **first** item was in-flight:
  runstate `running`, `purl-parser→dispatched thread 019edb08-1d9f-…`,
  `slugify→queued`, `purl.py` absent.
- **Restart**: `resuming 'backlog' from prior runstate` → `reattach 'purl-parser'
  thread 019edb08-1d9f-7fa2-b874-26bcf03a6c8f` (no new session) → `gate after
  reattach: passed=True` → `dispatch 'slugify' (2/2)` → green → `done=2`.
- The in-flight descriptor resumed by **reattach (feature 004)** at the recorded
  queue position; the remaining descriptor then completed.

## 4. Dashboard renders the backlog (no dashboard change)
Panel 5 (`/api/runstate`) rendered both items live:
`run queue-backlog · done … ✓ purl-parser · passed ✓ slugify · passed`. The
runstate `task_queue` is already a list, so the multi-descriptor backlog shows
with no dashboard change.

## Limit-hit pause (mechanism)
`execute_descriptor` detects a limit-hit in the worker error and returns
`BLOCKED_LIMIT`; `run_queue` then `mark_paused` (checkpoint + `paused`), NTFYs a
pause, and stops. Resume is a manual restart → reattach + remaining queue (the
auto-resume scheduler is deferred). Not triggered live (no limit reached); the
path is unit-covered by the BLOCKED_LIMIT branch.
