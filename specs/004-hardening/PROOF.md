# Hardening — proof

Recorded 2026-06-17. Gate: `.venv/bin/python -m pytest runtime/tests -q` → **26
passed** (incl. `test_durable_auth`, `test_reattach`).

## Item 1 — durable auth (symlink single-source)
From `scripts/spike_reattach.py` (and `worker_home.ensure()`):
- `auth is symlink to source: True` — the worker `auth.json` is a symlink to the
  operator's single source, **no standing divergent copy**.
- A worker turn completed via the symlink (`STORED`).
- `auth still symlink after a turn: True` — the link survived (no mid-turn refresh).
- Residual risk (a refresh during a turn, under atomic-rename writes) documented in
  `docs/HARDENING.md`; mitigated by short turns + per-dispatch re-assertion.

## Item 2 — reattach-on-restart (real interrupt)
1. Cleared runstate, deleted `gate/purl.py` (gate red), dispatched
   `descriptors/purl.json`, and **interrupted the runtime mid-flight** as soon as
   it went in-flight.
   - runstate after interrupt: `run.status=running, task=dispatched,
     thread_id=019ed6b6-a13c-7fd2-b660-2f506bad4459, in_flight=True`;
     `gate/purl.py` **absent** (worker had not written it yet).
2. **Restarted** the runtime on the same descriptor:
   - `runstate shows in-flight thread 019ed6b6-… -> reattach`
   - `REATTACH thread 019ed6b6-a13c-7fd2-b660-2f506bad4459 (no new session)`
   - `gate after reattach: passed=True :: 8 passed` → `OUTCOME: PASS (same thread)`
   - runstate: `done`, task `passed`, **same** `thread_id 019ed6b6-…`; the resumed
     worker wrote `gate/purl.py`.
   - **Thread-id continuity**: `019ed6b6-…` in-flight before the interrupt ==
     resumed thread after restart. No fresh session opened.
   - Mechanism: `codex exec resume <thread_id>` (CLI). The MCP `codex-reply` tool
     cannot resume across a restart ("Session not found"); see `docs/HARDENING.md`.

## Stale thread escalates (not restart)
Seeded runstate with a bogus in-flight `thread_id` (`019e0000-…`) and restarted:
- `REATTACH thread 019e0000-… (no new session)` → `reattach failed (resume
  errored)` → NTFY blocker (`blocked | reattach resume errored | … escalating,
  not restarting`) → `OUTCOME: BLOCKED_INFRA`; runstate `blocked` / task
  `escalated`. **No fresh dispatch.**

## Suite
runtime 26 / dashboard 13 / gate 8 — all green. (Dashboard degradation test made
hermetic: the runtime now writes `.magrathea/runstate.json` locally, so the test
points the v2 stores at temp paths.)
