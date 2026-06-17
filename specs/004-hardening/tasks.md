# Tasks: Runtime Hardening

**Plan**: [plan.md](plan.md) | **Status**: in progress

## Phase 0 — Spike, SDD & note
- [X] T001 [spike] auth write-mode (atomic rename, docs) + reattach mechanism
  (CLI resume works, MCP codex-reply doesn't across restart). scripts/spike_reattach.py.
- [X] T002 [feature] spec.md, plan.md, tasks.md; docs/HARDENING.md.

## Phase 1 — Gate-first tests
- [X] T010 [test] test_durable_auth.py — worker auth is a symlink to source, no copy.
- [X] T011 [test] test_reattach.py — reattach_plan resumes in-flight thread_id, fresh otherwise.

## Phase 2 — Implement
- [X] T020 [feature] worker_home.py symlink single-source (done in spike).
- [X] T021 [feature] runtime.py: write dispatched() early; reattach_plan + resume via CLI.
- [X] T022 [test] gate green: `pytest runtime/tests -q`.

## Phase 3 — Prove & push
- [ ] T030 auth: turn completes via symlink; symlink survives the turn.
- [ ] T031 reattach: real interrupt mid-flight -> restart -> same thread_id resumed,
  no new session, gate verdict. Record thread_id continuity.
- [ ] T032 stale thread -> escalate (not restart).
- [ ] T033 record (PROOF.md); secrets sweep; commit; push no-force; NTFY.
