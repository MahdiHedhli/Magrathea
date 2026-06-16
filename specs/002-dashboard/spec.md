# Feature Specification: Magrathea Dashboard (read-only ops view)

**Feature branch**: `002-dashboard`
**Status**: Draft → Implemented
**Created**: 2026-06-16

## Summary

A read-only, responsive, localhost-bound web view that renders Magrathea's
existing state — agent topology, the current sprint, the timeline, and governance
— and stubs the live-task and budget panels behind their v2 stores, degrading
gracefully until those stores exist. It is a **projection of state that already
exists**: not a source of truth, not a control plane, not model-powered.

## The one rule (non-negotiable, enforced by tests)

- **Read-only.** GET endpoints only; no POST/PUT/DELETE. Files opened read-only.
  **No on-disk writes** (in-memory cache only if any). Never imports or calls
  orchestrator dispatch.
- **No control actions in v1.** No approve/kill/reassign. If control is ever
  added, it routes through the existing gated escalation, never around it.
- **No model calls.** No LLM SDK imported, no inference. Renders data the system
  already produces.
- **Localhost only.** Binds `127.0.0.1`. Never `0.0.0.0`, never a tunnel.

## User Scenarios & Testing

### Primary scenario
As the operator, away from my desk, I open the dashboard on my phone and see —
at a glance — the agent structure and each role's model, the current sprint's
progress, recent activity, and the governance guardrails. Nothing I can click
changes anything; it only shows me what is already true.

### Acceptance (the gate — deterministic, exit-code)
- **AC-1 read-only**: no mutating route exists; the dashboard module imports no
  LLM client and no orchestrator dispatch; it performs no on-disk writes.
- **AC-2 localhost**: the server binds `127.0.0.1`, asserted; never `0.0.0.0`.
- **AC-3 graceful degradation**: with `.magrathea/runstate.json` and the usage
  output absent, the dashboard serves `200` and panels 5 & 6 show a clear
  *pending* state — no error.

### Manual proof (recorded, not gated)
Start on localhost; panels 1–4 render from the repo's real files; 5–6 show
pending; narrow viewport reflows to a single column with no horizontal scroll.

## Requirements

### Functional — panels & sources (all degrade gracefully)
- **FR-1 Agent topology (live)**: flat structure — operator, orchestrator,
  workers, independent verification — with each role's model, **data-driven**
  from `governance/orchestrator.md`, `governance/worker.AGENTS.md`,
  `governance/model-limit-policy.md`. Not hardcoded.
- **FR-2 Sprint board (live)**: the current sprint's task plan and completion
  state, parsed from `specs/NNN/tasks.md` (current sprint = latest spec dir, or a
  config pointer): phases; checked = done, unchecked = pending.
- **FR-3 Timeline (live)**: commits from `git log` (primary, always local), plus
  optional reporting events from the configured topic, **degrading to git-only**
  if unreachable. Topic read from config, never hardcoded.
- **FR-4 Governance at a glance (live)**: always-human classes and model floors
  read straight from `governance/`. Doubles as a safety surface — visible rules
  make a bad edit obvious.
- **FR-5 Live tasks (stub now, live later)**: reads `.magrathea/runstate.json`;
  renders a clear pending state when absent, naming the runtime sprint that lands
  it.
- **FR-6 Budget & limits (stub now, live later)**: reads the usage-adapter
  output; stubbed the same way against a defined read shape.

### Non-functional
- **NFR-1**: backend prefers **zero runtime dependencies** (stdlib HTTP). Any
  dependency is pinned and justified here. *(Decision: zero added deps; stdlib
  `http.server`. Test runner `pytest==8.4.2` already pinned.)*
- **NFR-2**: frontend is a single responsive page (vanilla, no library, no build
  step). Mobile-first, fluid, no horizontal scroll, legible tap targets,
  dark-mode friendly.
- **NFR-3**: everything pinned; no build step beyond what the repo already uses.

## Contracts (define now, consume now, populate later)
- `contracts/runstate.schema.json` (+ `runstate.example.json`): the agreed shape
  the live-task panel reads and the future runtime writes. **No writer is built
  here** — that is the runtime sprint. (Fields enumerated in the schema.)
- `contracts/usage.schema.json` (+ `usage.example.json`): the per-provider
  window-headroom read shape the budget panel consumes. Stub only.

## Out of scope
Any write/control action; authentication; multi-user; the runstate *writer*; the
usage *adapter* implementation (those are the runtime/v2 sprints); binding to any
non-loopback interface; any model call.

## Review checklist
- [x] Acceptance is deterministic and machine-checkable.
- [x] The one rule is enforced by tests, not convention.
- [x] Panels 5–6 degrade gracefully against a *defined* contract.
- [x] No implementation detail leaks into requirements (see `plan.md`).
