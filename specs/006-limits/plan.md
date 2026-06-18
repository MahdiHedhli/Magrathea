# Implementation Plan: Limit Awareness

**Spec**: [spec.md](spec.md) | **Status**: Implemented

## Technical context
Python 3.14, stdlib; builds on the 003/004/005 runtime. Worker isolated +
symlink auth. Reads usage from Codex `token_count.rate_limits`; writes the usage
snapshot to `.magrathea/usage.json` (gitignored — usage data stays out of source).

## Constitution check
- [x] V/VI two budgets + floors (read vs detect adapters). [x] VII recovery
  (limit-hit = pause; reset recorded). [x] III governance read for the threshold.
  [x] IV dashboard read-only / model-free. [x] VIII reproducible.

## Modules
```
runtime/usage.py
  parse_codex_rate_limits(rate_limits) -> [window]   # 100 - used_percent, resets_at
  read_codex_usage(env) -> provider dict (adapter="read")  # trivial refresh turn
  capture_from_event(emsg) -> Optional[rate_limits]  # opportunistic, no extra turn
  DetectAdapter (Claude): classify_limit_hit(text), tally_spend(tokens),
    compute_reset(window_minutes, now) -> iso, snapshot() -> provider dict (adapter="detect")
  build_snapshot() -> usage.json (contract shape: stop_threshold_pct + providers)
  refresh() / main()  -> write .magrathea/usage.json
runtime/limits.py
  stop_threshold_pct() <- governance/model-limit-policy.md (not hardcoded)
  headroom_below_threshold(usage, provider) -> bool      # min window remaining < threshold
```

## Phase A — read
`parse_codex_rate_limits`: primary(300min)→"5h", secondary(10080min)→"weekly",
`remaining_pct = 100 - used_percent`, `resets_at` epoch → ISO. `read_codex_usage`
runs one trivial read-only turn (isolated) to capture the live block.

## Phase B — detect
Claude detect adapter reuses `runtime._is_limit_hit` (third outcome), keeps a
local spend tally (tokens/turns), and computes reset from the window config
(`compute_reset`). The queue's limit-hit pause records the computed reset in
`runstate.paused_reset_time` (extend `run_queue`'s `mark_paused`).

## Phase C — stop threshold
`limits.stop_threshold_pct()` parses the "15% remaining headroom" line from
`governance/model-limit-policy.md`. `run_queue` (and `run`) check the worker
provider's headroom before starting an item; below threshold → pause + page +
record (status `paused`), do not dispatch.

## Phase D — panel live
`usage.py refresh` writes `.magrathea/usage.json`; the dashboard's existing
`sources.budget()` reads it (pending only when absent). Verify `renderBudget`
shows per-provider headroom/windows/resets; capture panel 6 non-pending. No model,
no writes added to the dashboard.

## Verification
Gate: `pytest runtime/tests -q`. Live proof (`specs/006-limits/PROOF.md`): real
Codex usage in panel 6; simulated limit-hit (not forced); threshold halt; panel 6
captured live.
