# Implementation Plan: Runtime Hardening

**Spec**: [spec.md](spec.md) | **Status**: Implemented

## Technical context
Python 3.14, stdlib; builds on the feature-003 runtime. Worker isolated via the
dedicated `CODEX_HOME`. Codex 0.140.0, model `gpt-5.5`.

## Constitution check
- [x] III Governance untouched. [x] IV Sandboxed worker. [x] VII Recovery by
  reattach (this feature). [x] VIII Reproducible. Never creates a credential.

## Item 1 — durable auth (`runtime/worker_home.py`)
`ensure()` makes `worker_home/auth.json` a **symlink** to
`OPERATOR_CODEX_HOME/auth.json`, re-created on every call. `auth_is_symlink()`
verifies the single-source state. No copy persists.

## Item 2 — reattach (`runtime/runtime.py`)
- `dispatched()` is now written **as soon as the threadId is known**
  (`session_configured` event), so an interrupt mid-turn leaves a true in-flight
  runstate (status `dispatched` + `thread_id`).
- `reattach_plan(runstate) -> Optional[str]`: returns the `thread_id` to resume
  iff the task is in-flight/dispatched (not done/failed/escalated) with a
  `thread_id`; else None (fresh).
- `resume(descriptor, thread_id)`: runs `codex exec resume <thread_id>` (CLI) in
  the isolated worker home, sandbox `workspace-write -C <working_dir>`; detects a
  stale thread ("Session not found"/nonzero) → NTFY + escalate; else runs the
  gate and resolves (done | escalate). Idempotent — gate is the arbiter.
- `main()`: load descriptor → `reattach_plan` → resume (if in-flight thread) else
  `run` (fresh).

## Why CLI resume, not MCP codex-reply
Spike (`scripts/spike_reattach.py`): a fresh mcp-server process's `codex-reply`
returns "Session not found for thread_id"; the MCP session is in-memory.
`codex exec resume <id>` loads the persisted rollout and continues the same
session (recalled the spike codeword across a restart).

## Verification
Gate: `pytest runtime/tests -q`. Live proof (`specs/004-hardening/PROOF.md`):
symlink auth turn; real interrupt → restart → reattach same thread_id → gate
verdict; stale thread escalates.
