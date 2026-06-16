# Tasks: [FEATURE NAME]

**Plan**: [plan.md](plan.md) | **Status**: Draft

Rules: phase boundaries are commit boundaries (Constitution VIII). Each task is
dispatchable to a worker and verified by the gate. `[P]` = parallelizable
(touches independent files). Tag each task with its class (feature / refactor /
test / dep-bump / security / infra) so the model-floor policy applies.

## Phase 0 — Preflight
- [ ] T001 [class] [task] — gate: [command]

## Phase 1 — [name]
- [ ] T010 [class] [task]
- [ ] T011 [P] [class] [task]

## Phase 2 — [name]
- [ ] T020 …

## Escalation
Always-human classes (per `governance/orchestrator.md`) are listed, not
dispatched. Security-class tasks are pinned to the strong model
(`governance/model-limit-policy.md`).
