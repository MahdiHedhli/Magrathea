# Model & Limit Policy

**Owner**: human. **Compiled by**: preflight (sections D, E). **Version**: 1.0.0
(2026-06-16). Realizes Constitution V (security model-floor) and VI (two budgets).
Worker-unwritable. The planner may pick the cheapest model that clears a gate,
but **never below a floor here**.

## Two budgets (Constitution VI)

| Budget | Who | Provider/tier | Scarcity |
|---|---|---|---|
| Orchestrator | the planner/dispatcher itself | **Claude Sonnet** (Opus only for planning calls) | scarce — shared across chat, Code, Cowork |
| Worker | dispatched implementers | the abundant provider (default **OpenAI/Codex `gpt-5.5`**) | abundant |

Never starve the scarce bucket to do work the abundant one can do.

## Providers in play

All four are registered; the default worker provider biases to most headroom.
Build scope for v0.1 is OpenAI/Codex only — the others reserve a slot and a
TODO adapter.

| Provider | Role | Default worker model | Strong-model floor | Usage adapter (E18) | Status |
|---|---|---|---|---|---|
| **OpenAI / Codex** | default worker | `gpt-5.5` | `gpt-5.5` | **read** (daily/weekly/cumulative readable) | active |
| **Google / Gemini** | worker (reserve) | TODO | TODO (top tier) | read (API) — confirm | slot reserved |
| **xAI / Grok** | worker (reserve) | TODO | TODO (top tier) | read (API) — confirm | slot reserved |
| **Anthropic / Claude** | orchestrator + last-resort worker | (worker use deprioritized) | Opus | **detect** (coarse; detect limit-hit + count locally) | active (orchestrator) |

> Worker headroom order (most → least): OpenAI/Codex → Gemini → Grok → Claude.
> Claude is last for worker use (it is the scarce shared bucket). **Confirm the
> Gemini/Grok ordering and adapters when those providers are wired (v2).**

## Limit windows (E17) — confirm against your actual subscriptions

| Provider | Windows tracked | Source |
|---|---|---|
| OpenAI / Codex | 5-hour, weekly, cumulative | read programmatically |
| Claude | 5-hour, weekly | detect on hit + local count |
| Gemini / Grok | billing/monthly or rate — TODO | read if API exposes |

## Stop threshold (E19)

**Stop starting new work at 15% remaining headroom**, per provider, per tracked
window. At the threshold the orchestrator finishes in-flight work if safe, then
pauses and reports (Constitution VII; see `cadence.md` for the limit-pause ping).
A limit-hit is a third outcome — pause, not fail, not retry.

## Model floors (Constitution V)

- **Ordinary classes** (feature, refactor, test-authoring, dep-bump): default
  worker model (`gpt-5.5`). The planner may down-pick to the cheapest model that
  clears the gate, **never below the default for the class**.
- **Security-relevant work**: pinned to the provider's **strong-model floor**
  regardless of cost, and never down-picked. Note: the *security-sensitive task
  class is always-human* (see `orchestrator.md`); this pin covers security-
  relevant work that surfaces inside an otherwise-ordinary task.
- A cheap model that passes a gate can still ship an exploitable change the gate
  cannot see — so the floor is by task sensitivity, not by price.

## Usage adapters (to build)

- `read` adapter (OpenAI/Codex): query daily/weekly/cumulative usage; compute
  remaining headroom per window.
- `detect` adapter (Claude): no fine usage API — detect a limit-hit response and
  count local spend against the known window; treat as coarse.
- Gemini/Grok adapters: TODO (v2), default to `read` if the API exposes usage.
