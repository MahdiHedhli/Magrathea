# Runtime — proof of the dogfood loop

Recorded 2026-06-17. Gate: `.venv/bin/python -m pytest runtime/tests -q` → **17
passed** (isolation, gate-runner, descriptor, runstate, governance).

## 1. Governance enforced at runtime (always-human refused)
`python -m runtime.runtime descriptors/history-rewrite.json` (task_class
`git-history`):
- `REFUSED (governance): task_class 'git-history' is an always-human class
  ('Git/GitHub history or log-history modification'); refused and escalated,
  never auto-dispatched.` → `OUTCOME: BLOCKED_GOVERNANCE`.
- runstate: `status=blocked`, task `escalated`, `in_flight=None`. **Not dispatched.**

## 2. Descriptor-driven green on an ISOLATED worker
Deleted `gate/purl.py` (gate red), then
`python -m runtime.runtime descriptors/purl.json`:
- `dispatch 'purl-parser' model=gpt-5.5 cwd=…/gate (isolated CODEX_HOME)`
- `threadId=019ed624-0339-76b1-9106-d744c75dda8d ok=True is_error=False`
- `gate(1): passed=True :: 8 passed in 0.01s` → `OUTCOME: PASS (first attempt)`.
- **Isolation in the real dispatch** (from `runtime.jsonl`): MCP servers loaded =
  `['codex_apps']`; **operator global servers inherited = `[]`** (0 of 13).
- The worker wrote its **own** `gate/purl.py` (distinct code — "Minimal Package
  URL parser for the deterministic gate."), not hand-fixed.

## 3. Runstate written through the lifecycle, schema-valid
`.magrathea/runstate.json` validated against
`specs/002-dashboard/contracts/runstate.schema.json` → **VALID**. Final:
`status=done`, task `purl-parser` `passed`, `gate_result {passed:true,
returncode:0, summary:"8 passed in 0.01s"}`, `thread_id 019ed624-…`, in_flight
cleared, checkpoint set.

## 4. Dashboard panel 5 now LIVE (closes the loop with feature 002)
Started the dashboard; panel 5 ("Live tasks") renders
`run run-purl-parser · done` / `✓ purl-parser · passed` — no longer pending.
Panel 6 ("Budget & limits") remains correctly pending (usage adapters deferred).
Sprint board reads the 003-runtime `tasks.md` live (phases ticking).

## Isolation mechanism (recap; full detail in SPIKE.md)
Mechanism 1: a dedicated worker `CODEX_HOME` (`~/.magrathea-worker-codex`, outside
the repo, never committed) with the operator's `auth.json` **copied** in and no
`[mcp_servers]`. Dispatch launches `codex mcp-server` with `CODEX_HOME` set to it.

## Deferred (not built this sprint)
Resume-on-restart (stretch) — runstate already carries the in-flight `thread_id`
for reattach; the reattach path is a follow-up. Auto-resume scheduler, usage
adapters / live budget, concurrency, Gemini/Grok — out of scope by design.
