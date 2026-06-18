# Tasks: Descriptor Queue

**Plan**: [plan.md](plan.md) | **Status**: in progress

## Phase 0 — SDD, 2nd task & manifest
- [X] T001 spec.md, plan.md, tasks.md; contracts/queue.schema.json.
- [X] T002 second gateable task tasks/slug (test_slug + conftest), validated
  satisfiable then ref impl deleted; descriptors/slug.json.
- [X] T003 queues/backlog.json (purl+slug); queues/backlog-with-block.json
  (purl+history-rewrite+slug).

## Phase 1 — Gate-first tests
- [ ] T010 test_queue.py — manifest loads ordered; QueueRunstate multi-task validates against schema.
- [ ] T011 test_queue.py — run_queue processes in order, skips a blocked item and continues.
- [ ] T012 test_queue.py — resume seeds from prior runstate; reattach an in-flight item, continue remainder.

## Phase 2 — Implement
- [ ] T020 refactor runtime.execute_descriptor (shared core, handle protocol, limit-hit detect).
- [ ] T021 runtime/queue.py: load_manifest, QueueRunstate, run_queue.
- [ ] T022 gate green: `pytest runtime/tests -q`.

## Phase 3 — Prove & push
- [ ] T030 2-task backlog runs sequentially green (worker's code); runstate progresses.
- [ ] T031 backlog-with-block: always-human escalated+skipped, others complete.
- [ ] T032 interrupt mid-queue -> restart -> reattach in-flight + finish remainder.
- [ ] T033 dashboard panel 5 renders the backlog; record (PROOF.md); sweep; push; NTFY tally.
