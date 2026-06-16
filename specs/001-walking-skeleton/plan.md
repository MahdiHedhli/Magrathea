# Implementation Plan: Conductor Walking Skeleton

**Spec**: [spec.md](spec.md) | **Status**: Implemented (`v0.1-beta`)

## Technical context

- **Language**: Python 3.14 (stdlib only for the control surface and reporter).
- **Worker**: Codex CLI (`>= 0.140.0`) driven as an MCP stdio server; model
  `gpt-5.5`.
- **Gate runner**: `pytest==8.4.2`, pinned in `requirements.txt`, installed into
  a project-local `./.venv` (never global).
- **Reporting**: NTFY over HTTPS (`urllib`, stdlib).
- **Constitution check**: PASS — gate-first (I), escalate (II), governance
  outside worker scope (III), sandboxed worker (IV). Model floors / two-budget /
  recovery (V–VII) are exercised minimally here and specified fully by the
  per-repo governance files.

## Architecture

```
orchestrator (conductor/orchestrator.py)
  ├─ control surface  conductor/mcp_client.py   → codex mcp-server (stdio JSON-RPC)
  │     codex()        open session, capture threadId
  │     codex-reply()  continue a thread by threadId
  ├─ gate             gate/test_purl.py  (orchestrator-owned, gate-first)
  │     gate_runner.py runs pytest, green == exit 0
  └─ reporter         conductor/ntfy.py  (progress / blocker pings)
```

### Control-surface decision
MCP stdio client against `codex mcp-server` (the default path); the Python-SDK
fallback was not needed — MCP exchanged messages on the first probe. `threadId`
is reported on every `codex/event` notification and in the final tool result.
Detail: [docs/CONTROL_SURFACE.md](../../docs/CONTROL_SURFACE.md).

### Worker sandbox
`cwd = gate/`, `sandbox = workspace-write` (writable root == cwd, network off),
`approval-policy = never`. The worker can read the test and write `gate/purl.py`,
nothing else.

### Verify / retry / escalate
- Worker `isError` or timeout → **infrastructure blocker**: run the gate for the
  record, escalate, no retry.
- Gate green → PASS.
- Gate red → one `codex-reply` retry on the same thread → re-gate → second red
  escalates.
- `DISPATCH_TIMEOUT = 420s`: generous for a real turn, fails fast if a global MCP
  server hangs on startup.

## Project structure

```
conductor/      orchestrator, mcp_client, gate_runner, ntfy, config
gate/           test_purl.py (the gate), conftest.py; purl.py is worker output (gitignored)
specs/          this feature's spec/plan/tasks
.specify/       constitution + templates
governance/     per-repo human-owned policy files (compiled by the preflight)
scripts/        protocol probes
docs/           CONTROL_SURFACE.md and design notes
```

## Risks & mitigations
- **Worker model entitlement** — only `gpt-5.5` drives on this account, and it
  needs a current CLI. Mitigation: the failure path escalates cleanly if it stops
  driving.
- **Inherited global MCP servers** — the worker session inherits the operator's
  global Codex MCP servers and cannot cleanly disable them per session on CLI
  0.140. Mitigation: short dispatch timeout fails fast on a hung server; prune
  the worker's global MCP config operator-side if it recurs.

## Verification
`SMOKETEST.md` records both branches (repeatable green; infra-failure escalation)
with timestamps and threadIds. Resume/attach de-risked in `BETA.md`.
