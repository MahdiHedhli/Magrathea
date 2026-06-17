# Tasks: Magrathea Runtime

**Plan**: [plan.md](plan.md) | **Status**: in progress

Phase boundaries = commit boundaries. Class tags: test / feature / spike.

## Phase 0 — Spike, SDD & contract
- [X] T001 [spike] worker-isolation spike; record winning mechanism (SPIKE.md).
- [X] T002 [feature] spec.md, plan.md, tasks.md.
- [X] T003 [feature] contracts/descriptor.schema.json + descriptor.example.json.

## Phase 1 — Gate-first tests (before implementation)
- [X] T010 [test] test_isolation.py — worker home has no operator MCP; dispatch carries worker CODEX_HOME.
- [X] T011 [test] test_gate_runner.py — arbitrary command, exit-code pass/fail, no LLM import.
- [X] T012 [test] test_descriptor.py — loop runs from a descriptor file, fields parsed.
- [X] T013 [test] test_runstate.py — runstate validates against committed schema across lifecycle.
- [X] T014 [test] test_governance.py — always-human descriptor refused + escalated.

## Phase 2 — Implement (spike first, then gate/descriptor, then runstate/governance)
- [X] T020 [feature] worker_home.py — isolated CODEX_HOME + copied auth + clean config.
- [X] T021 [feature] gate.py — generalized exit-code gate runner.
- [X] T022 [feature] descriptor.py — loader + validation.
- [X] T023 [feature] governance.py — load always-human + floors; check/refuse.
- [X] T024 [feature] runstate.py — lifecycle writer to committed contract.
- [X] T025 [feature] runtime.py — the dogfood loop; extend mcp_client for env.
- [X] T026 [test] gate green: `pytest runtime/tests -q`.

## Phase 3 — Prove
- [X] T030 descriptor-driven task → isolated worker → gate green (worker's code).
- [X] T031 runstate written through lifecycle; dashboard panel 5 renders live.
- [X] T032 always-human descriptor refused + escalated.
- [X] T033 record outcomes (PROOF.md). Stretch: resume-on-restart by threadId.

## Phase 4 — Sweep & push
- [ ] T040 secrets sweep (no auth.json/CODEX_HOME/abs path); commit; reconcile no-force; push; NTFY.
