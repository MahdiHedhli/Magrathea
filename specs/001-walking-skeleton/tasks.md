# Tasks: Conductor Walking Skeleton

**Plan**: [plan.md](plan.md) | **Status**: all complete (`v0.1-beta`)

Phase boundaries are commit boundaries (Principle VIII). `[X]` = done and
verified.

## Phase 0 — Preflight
- [X] T001 Verify Codex CLI present, authenticated, and that `gpt-5.5` drives a
  turn (probe). `scripts/probe_model.py`.
- [X] T002 Confirm `codex mcp-server` answers MCP `initialize` and exposes
  `codex` / `codex-reply`. `scripts/mcp_probe.py`.
- [X] T003 Project venv with pinned `pytest==8.4.2`; NTFY run-start ping.

## Phase 1 — Control surface
- [X] T010 MCP stdio client: initialize, tools/list, `codex()`, `codex-reply()`,
  event streaming, `threadId` capture, JSONL logging. `conductor/mcp_client.py`.
- [X] T011 Prove the surface: open a session, capture a `threadId`.
  `phase1_control_surface.py`.
- [X] T012 Document the control-surface decision. `docs/CONTROL_SURFACE.md`.

## Phase 2 — Define the gate (gate-first)
- [X] T020 Write `gate/test_purl.py`: 8 deterministic cases pinning the
  `parse_purl` contract. The function does not exist yet → gate red.
- [X] T021 Validate the gate is satisfiable with a throwaway reference impl
  (8/8), then delete it so the worker's task stays real.

## Phase 3 — Dispatch & verify
- [X] T030 `gate_runner.py`: run pytest, green == exit 0, structured verdict.
- [X] T031 `orchestrator.py`: dispatch (sandboxed) → classify infra-failure vs
  gate-red → one `codex-reply` retry on red → escalate.
- [X] T032 Live green: worker wrote `gate/purl.py`, gate 8/8, PASS first attempt
  (threadId `019ed197-…`), **not hand-fixed**.

## Phase 4 — Smoketest & handoff
- [X] T040 Repeatability: delete `purl.py` → red → dispatch → green again
  (threadId `019ed19b-…`). `SMOKETEST.md`.
- [X] T041 Failure path: bogus model id → `BLOCKED_INFRA`, gate red, escalate, no
  retry (threadId `019ed19e-…`).
- [X] T042 Resume de-risk: reopen a session from a separate process via
  `codex exec resume <threadId>`; context survived. `BETA.md`.
- [X] T043 `BETA.md`, `STATUS.md`, `README.md`; tag `v0.1-beta`.

## Next (v2 — design first, human-driven)
- [ ] Multi-thread dispatch (session pool + registry).
- [ ] Attach-to-existing-thread as a first-class feature (`resumeThread`).
- [ ] Heartbeat scheduler; model tiering; graceful degradation.
