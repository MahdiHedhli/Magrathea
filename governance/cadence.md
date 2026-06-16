# Cadence & Reporting

**Owner**: human. **Compiled by**: preflight (section G). **Version**: 1.0.0
(2026-06-16). Worker-unwritable. Realizes Constitution VIII.

## Commit cadence
**Per phase.** Commit at every phase boundary with a clear message so progress is
recoverable. Phase boundaries are commit boundaries.

## Reporting (NTFY)
- Topic: **`Mahdi-Dev`** (`https://ntfy.sh/Mahdi-Dev`; swap base URL if
  self-hosted, keep the topic).
- **Ping on**: run start, each phase, every blocker, **limit-pause**, run-end.
- Format — Title `Conductor · <phase>`, body `<status> | <task or issue> | <detail>`.
- Progress pings: `Tags: white_check_mark`. Blockers: `Priority: high` +
  `Tags: warning`. Limit-pause: `Priority: high` + `Tags: hourglass` and the
  named reset time.

## Escalation threshold
A task escalates to the operator after **2 consecutive gate failures** on that
task. (Infra failures and limit-hits are classified separately — see
`orchestrator.md`; they do not consume the gate-failure count.)

## Timeouts
- **Per-task, not one global cap.** Default per-task timeout: **420 s** (a healthy
  worker session starts its MCP servers in ~4 s and a real turn finishes well
  inside this; 420 s fails fast if a global MCP server hangs).
- Override per task class as needed (heavier builds get longer; keep it bounded).

## Heartbeat (v2 — intent captured now)
A scheduler/heartbeat is the **v2** build target. Intended behavior: a periodic
liveness check and the auto-resume waker that wakes a paused run at a provider's
reset time and **reattaches the in-flight thread by `threadId`**
(`orchestrator.md`, Constitution VII). Interval and target task: TBD at v2 build;
start simple (one liveness ping per long-run, plus the reset-time waker).
