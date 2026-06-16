# Tasks: Magrathea Dashboard

**Plan**: [plan.md](plan.md) | **Status**: in progress

Phase boundaries are commit boundaries. `[P]` = parallelizable. Class tags:
test / feature. No task here is security/infra/always-human.

## Phase 0 — Design & contracts
- [X] T001 [feature] spec.md, plan.md, tasks.md.
- [X] T002 [feature] contracts/runstate.schema.json + runstate.example.json (no writer).
- [X] T003 [feature] contracts/usage.schema.json + usage.example.json (stub shape).

## Phase 1 — Gate-first tests (write BEFORE implementation)
- [ ] T010 [test] test_readonly.py — no mutating routes; no LLM/orchestrator-dispatch
  import; no on-disk writes.
- [ ] T011 [test] test_localhost.py — binds 127.0.0.1, never 0.0.0.0.
- [ ] T012 [test] test_degradation.py — runstate+usage absent → 200, panels 5/6 pending.

## Phase 2 — Backend read endpoints
- [ ] T020 [feature] config.py — HOST/PORT/paths/current-sprint/NTFY topic (from conductor.config).
- [ ] T021 [feature] sources.py — topology, sprint, timeline, governance, runstate, budget (read-only).
- [ ] T022 [feature] server.py — stdlib http.server, do_GET only, 127.0.0.1, /api/* + static.
- [ ] T023 [test] gate green: `pytest dashboard/tests -q`.

## Phase 3 — Responsive frontend
- [ ] T030 [feature] static/index.html — single page, 6 panels.
- [ ] T031 [feature] static/style.css — mobile-first, dark-mode, no h-scroll.
- [ ] T032 [feature] static/app.js — fetch /api/*, render, graceful pending.

## Phase 4 — Wire & prove
- [ ] T040 [feature] panels 1–4 wired to real files; 5–6 pending.
- [ ] T041 [test] prove: start on localhost, verify panels + narrow-viewport reflow. Record.

## Phase 5 — Sweep & push
- [ ] T050 secrets sweep; commit; reconcile (no force); push; governed NTFY.
