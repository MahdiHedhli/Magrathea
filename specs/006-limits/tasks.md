# Tasks: Limit Awareness

**Plan**: [plan.md](plan.md) | **Status**: in progress

## Phase 0 — SDD & spike
- [X] T001 spec.md, plan.md, tasks.md; rate_limits source recorded (scripts/spike_usage.py).

## Phase A — readable Codex adapter
- [X] T010 [test] test_usage_read.py — parse_codex_rate_limits -> contract windows (schema-valid).
- [X] T011 [feature] runtime/usage.py: parse_codex_rate_limits, read_codex_usage, capture_from_event.

## Phase B — detect adapter + reset wiring
- [X] T020 [test] test_usage_detect.py — classify limit-hit as third outcome; spend tally; reset compute.
- [X] T021 [feature] DetectAdapter (Claude); compute_reset; wire queue pause -> runstate.paused_reset_time.

## Phase C — stop threshold
- [ ] T030 [test] test_limits.py — stop_threshold from governance; halts queue below threshold + pages.
- [ ] T031 [feature] runtime/limits.py; run_queue pre-dispatch headroom check.

## Phase D — panel 6 live + prove
- [ ] T040 [feature] usage.py refresh writes .magrathea/usage.json; build_snapshot (contract).
- [ ] T041 prove: real Codex usage in panel 6; simulated limit-hit (not forced); threshold halt; capture panel 6.
- [ ] T042 record PROOF.md; sweep; final NTFY tally.
