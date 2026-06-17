# Implementation Plan: Magrathea Runtime

**Spec**: [spec.md](spec.md) | **Status**: Implemented

## Technical context
- Python 3.14, stdlib at runtime; reuses `conductor.mcp_client` (extended to pass
  a custom `env`, for the worker `CODEX_HOME`). Test-only dep: `jsonschema`
  (pinned) for runstate schema validation.
- Worker: Codex `0.140.0`, model `gpt-5.5`, isolated via a dedicated
  `CODEX_HOME` (see `SPIKE.md`).

## Constitution check
- [x] I Gate-first — exit-code gate runner, no model; tests before impl.
- [x] II Escalate — always-human refused & escalated; 2nd gate-red escalates.
- [x] III Governance untouched — runtime only READS `governance/`.
- [x] IV Sandboxed worker — workspace-write to the descriptor's scope only;
  isolated MCP via worker home.
- [x] V Floors — sensitive classes pinned to floor. VII Recovery — runstate
  carries `thread_id` for reattach (stretch). VIII Reproducible — pinned dep.

## Architecture
```
runtime/
  config.py        worker-home path (Path.home()-derived, never committed), defaults
  worker_home.py   ensure(): create CODEX_HOME, copy auth.json, write clean config.toml
  descriptor.py    Descriptor dataclass + load() + validate against schema
  gate.py          run_gate(command, cwd) -> GateResult (exit-code, no model)
  governance.py    load always-human classes + floors from governance/; check(descriptor)
  runstate.py      RunstateWriter -> .magrathea/runstate.json (committed contract)
  runtime.py       loop: load descriptor -> governance gate -> dispatch isolated
                   worker -> gate -> runstate -> retry/escalate/done
descriptors/purl.json   the known-good dogfood descriptor (targets ., gate/, pytest)
specs/003-runtime/contracts/descriptor.schema.json + example
```

### Isolation (FR-1)
`worker_home.ensure()` builds `~/.magrathea-worker-codex` (copied `auth.json`,
no `[mcp_servers]`). The MCP client is started with `env[CODEX_HOME]` = that
home, so the worker session loads none of the operator's global servers.

### Gate-runner (FR-2)
`run_gate(command, cwd, timeout)` runs the command via `subprocess`, pass iff
returncode 0; returns `{passed, returncode, summary, output}`. Imports no model.

### Governance enforcement (FR-5)
`governance.load()` parses the always-human classes and floors from
`governance/*.md`. `check(descriptor)` → `refused` if the task class matches an
always-human keyword (→ runtime escalates, never dispatches); else returns the
model (floor for sensitive classes, default otherwise).

### Runstate (FR-4)
`RunstateWriter` writes the full object at each transition: queued → dispatched
(thread_id/provider/model/started_at, in_flight set) → gate_result → done |
escalated | blocked, with checkpoint. Atomic-ish write (tmp then replace) inside
`.magrathea/` (gitignored).

### Lifecycle (runtime.py)
load descriptor → governance.check → (refuse→escalate) | dispatch isolated worker
(capture threadId) → run gate → green: done | red: codex-reply retry up to
`retry_budget` → still red: escalate. Runstate updated at each step.

## Risks
- Copied `auth.json` could go stale if the token rotates → the dispatch errors;
  surfaced as an infra failure (re-copy by re-running `worker_home.ensure`).
- A live worker turn is non-deterministic → the fast gate tests verify the
  mechanism/config; the live loop is exercised in the prove step (`PROOF.md`).

## Verification
Gate: `.venv/bin/python -m pytest runtime/tests -q`. Live proof recorded in
`specs/003-runtime/PROOF.md`; dashboard panel 5 confirmed live.
