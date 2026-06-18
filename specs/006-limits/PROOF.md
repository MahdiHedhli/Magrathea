# Limit awareness — proof

Recorded 2026-06-17. Gate: `.venv/bin/python -m pytest runtime/tests -q` → **42
passed** (usage read/detect, limits) + dashboard **13 passed** (read-only intact).

## A — readable Codex adapter (real usage)
`read_codex_usage()` captured the operator's **real** Codex `rate_limits` and
normalized to the contract: `5h` 79% remaining (resets 2026-06-18T17:19:16Z),
`weekly` 88% (resets 2026-06-24T21:18:29Z). Headroom = 100 − used_percent. Unit
test normalizes the sample and validates against `usage.schema.json`.

## B — Claude detect adapter (third outcome)
`DetectAdapter.classify` maps a limit-hit error to `"limit-hit"` (the third
outcome), else `"other"`; local spend tally; `compute_reset(300)` / `(10080)`
match the known 5h / weekly windows. The queue's limit-hit pause records the
computed reset in `runstate.paused_reset_time` (unit test: pause records reset
and stops, second item not dispatched). **The limit-hit path is proven by unit
test + a simulated rate-limit error — not by forcing a real limit, which is not
something to force** (as the prior runs stated for the untriggered pause).

## C — stop threshold (from governance)
`limits.stop_threshold_pct()` reads **15%** from
`governance/model-limit-policy.md` (not hardcoded). `run_queue` checks the worker
provider's headroom before starting new (fresh) work; below threshold it
**pauses + pages + records** and does not dispatch (unit test: a 5%-headroom
snapshot halts the queue, `execute_descriptor` never called).

## D — budget panel live (dashboard complete)
`python -m runtime.usage` wrote `.magrathea/usage.json` (real Codex read +
Claude detect stub). Panel 6 is **no longer pending** — it renders:
`stop at 15% remaining · openai-codex/read 5h 79% (resets 3h), weekly 88%
(resets 6d) · anthropic-claude/detect 5h —, weekly —`. The dashboard stays
**read-only and model-free** (13 tests; it only reads the adapter output).
`execute_descriptor` also writes the snapshot opportunistically from each
dispatch's `rate_limits` (no extra turn). The last dark panel is lit — the
dashboard is complete.

## Deferred (deliberately)
The **auto-resume scheduler** is untouched — it would register a launchd agent
(persistent system config), which an unattended run must not do. Build it
attended as its own sprint. This run is the visibility half; the scheduler is the
action half. Also deferred: concurrency, other-provider workers, dedicated worker
login.
