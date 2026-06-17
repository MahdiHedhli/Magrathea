# Feature Specification: Runtime Hardening (durable auth + reattach)

**Feature branch**: `004-hardening`
**Status**: Draft → Implemented
**Created**: 2026-06-17

## Summary
Two hardening items on the proven feature-003 runtime — nothing new:
1. **Durable worker auth** — replace the copy of `auth.json` (which goes stale
   when the operator's token rotates) with a single-source mechanism, no standing
   divergent copy.
2. **Reattach-on-restart** — on startup, resume an in-flight thread by its
   `thread_id` (already in runstate) rather than opening a fresh session.

## Out of scope (do NOT build)
Auto-resume scheduler, usage adapters / live budget panel, concurrency,
other-provider workers. Reattach is the resume half; scheduling is not this pass.

## User Scenarios & Testing

### AC-auth
The worker authenticates via a single source with **no standing divergent copy**,
and a worker turn completes through it. Mechanism + residual risk documented.

### AC-reattach
Given runstate with an in-flight `thread_id` from an actually-opened session, a
restart **reattaches that same thread** (same id, no new session) and resolves
through the gate. A **stale/gone thread escalates** (NTFY) rather than silently
restarting.

## Requirements

### FR-1 durable auth
- No `auth.json` copy that can diverge. Resolution order probed:
  (a) auth-path independent of `CODEX_HOME` — **not available** on CLI 0.140;
  (b) symlink if Codex writes in place — Codex writes by **atomic rename** (docs),
      so a refresh would replace the link;
  (c) re-sync before each dispatch — the robust fallback.
- **Chosen: symlink, re-asserted before every dispatch.** The worker `auth.json`
  is a symlink to the operator's single source (zero copy, always current on
  read); `worker_home.ensure()` re-creates it before each dispatch, self-healing
  if a prior turn's refresh replaced it. Never creates/enters/regenerates a
  credential.
- Residual risk (documented in `docs/HARDENING.md`): a token **refresh during a
  worker turn** would, under atomic-rename writes, replace the link in the worker
  home and rotate the single-use refresh token there, diverging the operator's
  copy. Mitigated by short turns (minutes) vs token lifetime (~1h) and the
  per-dispatch re-assertion.

### FR-2 reattach-on-restart
- On startup, read runstate. If the task is in-flight/dispatched (not done,
  failed, or escalated) and carries a `thread_id`, **reattach** it.
- Reattach uses **`codex exec resume <thread_id>`** (CLI) — the MCP `codex-reply`
  tool resumes only within a live process and returns "Session not found" across a
  restart; the CLI loads the persisted rollout (proven). Run isolated (worker
  `CODEX_HOME`), sandboxed `workspace-write` to the working dir.
- **Idempotent**: the gate is the arbiter — resume the thread, prompt it to
  complete the task to satisfy the gate, run the gate, resolve. Partial prior work
  does not double-apply.
- **Stale thread → escalate**, never silently restart.

## Review checklist
- [x] Auth has no standing divergent copy; mechanism + residual risk documented.
- [x] Reattach uses thread_id continuity (same session), gate as arbiter.
- [x] Stale thread escalates, not restarts.
