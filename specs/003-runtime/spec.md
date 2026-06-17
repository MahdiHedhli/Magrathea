# Feature Specification: Magrathea Runtime (dogfood loop)

**Feature branch**: `003-runtime`
**Status**: Draft → Implemented
**Created**: 2026-06-17

## Summary

The runtime that makes Magrathea usable: read a task descriptor, dispatch to an
**isolated** worker, verify with the project's own gate, write runstate to the
contract, and **enforce governance at execution time** (always-human classes and
model floors enforced, not just documented). It lights the dashboard's dark
panel 5.

## In scope
Worker config isolation; the gate-runner abstraction (arbitrary gate command,
exit-code only); the task descriptor; the runstate writer to
`specs/002-dashboard/contracts/runstate.schema.json`; governance enforcement.

## Deferred (do NOT build)
Auto-resume scheduler; usage adapters / live budget data; true multi-thread
concurrency; Gemini/Grok workers. Sequential, OpenAI/Codex worker, on demand.
Resume-on-restart is a stretch only.

## User Scenarios & Testing

### Primary scenario
As the operator, I drop a task descriptor and run the runtime. It refuses the
task if its class is always-human; otherwise it dispatches an isolated worker
(no inherited global MCP), the worker satisfies the project's own gate, and the
runtime records every lifecycle transition to `runstate.json` — which the
dashboard's panel 5 then renders live.

### Acceptance (the gate — deterministic)
- **AC-isolation**: the worker is dispatched against a dedicated `CODEX_HOME`
  with no operator `[mcp_servers]`; the dispatch carries that home, not the
  operator's. (Live proof: 0 inherited servers — see `SPIKE.md`.)
- **AC-gate**: the gate-runner executes an arbitrary command from the descriptor,
  decides pass/fail by **exit code** only, and imports no LLM client.
- **AC-descriptor**: the loop runs from a descriptor file, not a hardcoded task.
- **AC-runstate**: the writer produces a `runstate.json` that **validates against
  the committed schema** at each lifecycle stage (queued → in-flight → gate
  result → done/escalated).
- **AC-governance**: a descriptor whose class is always-human (security-sensitive,
  bulk deletes, git/GitHub history modification) is **refused and escalated**,
  never dispatched.

### Manual proof (recorded)
Descriptor-driven task → isolated worker → gate green with the worker's own code
(not hand-fixed); runstate written through the lifecycle; dashboard panel 5 live;
an always-human descriptor refused.

## Requirements

### Functional
- **FR-1 isolation**: dispatch via a dedicated worker `CODEX_HOME` (copied auth,
  no operator MCP). Path resolved from env/`Path.home()`, never committed.
- **FR-2 gate-runner**: run `descriptor.gate_command` in `descriptor.gate_dir`,
  pass iff exit 0; capture summary/returncode; no model.
- **FR-3 descriptor**: load a descriptor file (target repo, working dir, goal,
  task class, gate command/dir, retry budget, per-task timeout). Per-task
  timeout retires the global 420 s cap.
- **FR-4 runstate writer**: write `.magrathea/runstate.json` (gitignored) to the
  committed contract through the lifecycle, with `thread_id`, provider, model,
  gate result, checkpoint.
- **FR-5 governance enforcement**: read `governance/orchestrator.md` +
  `governance/model-limit-policy.md`. Refuse always-human classes; pin sensitive
  classes to the strong floor; ordinary classes use the policy default.

### Non-functional
- Runtime is **stdlib-only at runtime** (reuses `conductor.mcp_client`); the only
  added dependency is `jsonschema` for the runstate validation **test**, pinned.
- No model in the gate. No worker writes outside its sandboxed scope.

## Out of scope
Scheduler, usage adapters, concurrency, non-OpenAI workers, credential creation.

## Review checklist
- [x] Isolation mechanism recorded (`SPIKE.md`).
- [x] Gate is exit-code only, no model.
- [x] Governance is enforced by the runtime, not just written.
- [x] Runstate matches the committed dashboard contract.
