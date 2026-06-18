# Feature Specification: Limit Awareness (usage adapters + live budget)

**Feature branch**: `006-limits`
**Status**: Draft → Implemented
**Created**: 2026-06-17

## Summary
The limit-awareness layer: per-provider usage adapters (read where exposed,
detect where not), reset-time computation, the governance stop-threshold wired to
real headroom, and the dashboard's budget panel (panel 6) going live. This lights
the last dark dashboard panel.

## Out of scope (deliberately)
- **The auto-resume scheduler** is held back from this unattended run on purpose:
  it installs a launchd agent (persistent system config), which an away-run must
  not register. Build it attended, as its own sprint. This run is the visibility
  half; the scheduler is the action half.
- Concurrency, other-provider workers, the dedicated worker login.

## How Codex exposes usage (spike)
There is no `codex usage` command. Every turn emits a `token_count` event whose
`rate_limits` block carries the windows:
`primary` = 5h (`window_minutes: 300`, `used_percent`, `resets_at` epoch),
`secondary` = weekly (`window_minutes: 10080`, `used_percent`, `resets_at`),
plus `plan_type`. **Headroom = 100 − used_percent.** The read adapter captures
this — opportunistically from any dispatch, or via a trivial refresh turn.

## Phases (each independently valuable; commit + push + NTFY per phase)
- **A — readable adapter**: read Codex `rate_limits` and normalize to the usage
  contract (`specs/002-dashboard/contracts/usage.schema.json`): per-provider
  window headroom. Read-only.
- **B — detect adapter**: formalize limit-hit classification (Claude / scarce
  subscription, not cleanly queryable): classify a limit-hit error as the **third
  outcome** (not infra, not gate-red), maintain a **local spend tally**, compute
  the **reset time** from the window config, and wire the queue's existing
  limit-hit pause to record that reset in runstate. Do not probe/hammer to
  discover a limit — only classify limit-hits that arise normally.
- **C — stop threshold**: runtime/queue stop starting new work when a provider's
  headroom falls below the governance stop threshold (15%, read from
  `governance/model-limit-policy.md`, not hardcoded), page, and record.
- **D — budget panel live**: panel 6 renders per-provider headroom / windows /
  reset times from the adapters, no longer pending. The dashboard stays
  **read-only and model-free** — it reads the adapter output and nothing more.

## Acceptance (gate — deterministic)
- **AC-read**: the readable adapter normalizes real Codex `rate_limits` to the
  contract shape (schema-valid; headroom = 100 − used_percent).
- **AC-detect**: the detect adapter classifies a simulated limit-hit error as the
  third outcome and tallies local spend; reset computation matches known windows.
- **AC-stop**: the stop threshold halts new work below the governance threshold
  and pages.
- **AC-panel**: panel 6 renders adapter output and stays read-only / model-free.

## Manual proof (recorded)
The Codex adapter reads the operator's **real** usage and panel 6 renders it
live. The detect limit-hit path is proven by **unit test + a simulated rate-limit
error, not by forcing a real limit** (stated plainly, as the prior runs did for
the untriggered pause). The stop threshold halts a queue run below threshold in a
test and pages. Panel 6 is no longer pending — captured.

## Review checklist
- [x] Read where exposed (Codex), detect where not (Claude).
- [x] Stop threshold from governance, not hardcoded.
- [x] Dashboard stays read-only and model-free.
- [x] Scheduler untouched (no system registration).
