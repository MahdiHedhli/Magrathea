# Conductor — beta handoff

**From here, development is human-driven. Do not launch another unattended
one-shot to add features.** The walking skeleton is built, proven, and
smoketested; the next steps are design decisions that belong in a human-in-the-
loop session (use `claude-opus-4-8` for design, per the model tiering).

## Drive it manually (the single command)

```bash
cd ~/dev/conductor
.venv/bin/python -m conductor.orchestrator
```

This opens a sandboxed Codex worker session (`gpt-5.5`, `workspace-write` scoped
to `gate/`, network off), dispatches the PURL task, runs the `pytest` gate
itself, retries once via `codex-reply` on a gate-red, and reports over NTFY.
Expected result on a healthy machine: Codex writes `gate/purl.py`, gate **8
passed**, `OUTCOME: PASS`.

Useful variations:
```bash
.venv/bin/python phase1_control_surface.py            # prove the control surface only
.venv/bin/python -m pytest gate/test_purl.py -q       # run the gate directly
CONDUCTOR_WORKER_MODEL=<id> .venv/bin/python -m conductor.orchestrator  # override model
```

## Proven (this run + prior runs)

- **Control surface** — MCP stdio client drives `codex mcp-server`; `codex()`
  opens a session and returns a `threadId`; `codex-reply()` continues it.
- **Gate-first verify** — the orchestrator owns `gate/test_purl.py` (8
  deterministic cases); it is red until a worker writes `gate/purl.py`.
- **Green path** — Codex (`gpt-5.5`) wrote `purl.py` and passed all 8 cases,
  **first attempt, not hand-fixed**, and it is **repeatable** (two fresh
  sessions). See `SMOKETEST.md`.
- **Both failure branches** —
  - infra failure (bogus/again unavailable model) → `BLOCKED_INFRA`, gate run for
    the record, escalate, **no** wasted `codex-reply` retry;
  - gate-red → one `codex-reply` retry on the same thread, then re-gate, then
    escalate on a second red (implemented; the green ran clean so the retry was
    not needed live — exercising it remains a nice-to-have).
- **NTFY** — progress pings (green) and high-priority blocker pings both fire.

## Not yet built (the v2 backlog — design first, on Opus)

- **Multi-thread dispatch** — a session pool / registry to fan tasks out
  concurrently, each with its own `threadId` and sandboxed `cwd`.
- **Attach-to-existing-thread** — reopen a prior session rather than always
  opening a new one: `codex resume --all <id>` (CLI) and the SDK `resumeThread`.
  See the stretch de-risking note below.
- **Heartbeat scheduler** — periodic health/liveness pings and long-run
  supervision instead of one-shot dispatch.
- **Model tiering** — route by task difficulty / cost; today the worker model is
  a single config value (`WORKER_MODEL`).
- **Graceful degradation** — fall back across workers/models when one is
  unavailable, instead of escalating immediately.

## Known caveats

- **Worker model entitlement.** This ChatGPT account drives `gpt-5.5` only.
  `gpt-5.5` requires a current Codex CLI (works on `0.140.0`; failed on the older
  `0.122.0` with "requires a newer version of Codex"). Other model ids
  (`gpt-5`, `gpt-5.1`, `gpt-5.2`, all `-codex` variants) return "not supported
  when using Codex with a ChatGPT account". Keep the CLI current; the failure
  path correctly escalates if the model ever stops driving.
- **Global MCP servers can't be cleanly disabled per session on CLI 0.140.** The
  worker session inherits the user's global Codex MCP servers (MCP_DOCKER,
  openaiDeveloperDocs, etc.). The `config` override deep-merges, so
  `mcp_servers = {}` is a no-op and per-server overrides produce invalid
  transports. They start healthy in ~4s, but a transient failure of one (we saw
  `openaiDeveloperDocs` HTTP hang once) can stall a turn — which is why
  `DISPATCH_TIMEOUT` is 420s (fail fast) rather than 900s. If this recurs, the
  cleanest fix is operator-side (prune the worker's global MCP config), not a
  per-session override.
- **Desktop vs. CLI session visibility.** Sessions opened through
  `codex mcp-server` are persisted as rollout files under
  `~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl` (the `session_configured` event
  reports the exact `rollout_path`). These CLI/MCP-created sessions are not
  guaranteed to appear in the Codex **desktop app's** session list. For the v2
  attach work, resume from the rollout/threadId (verified below), and do not rely
  on a session being visible in the desktop UI.

## Stretch — resume/attach de-risking (the door opens)

A read-only probe (no feature built) confirmed a session opened through the MCP
control surface can be **reopened from a separate process** with its context
intact:

1. Opened a throwaway read-only session via `codex()` (threadId
   `019ed1a1-0b2c-7203-8d5e-416f9d942575`) and told the worker to remember the
   codeword `PELICAN-7` → it replied `STORED`.
2. In a **separate process**:
   `codex exec --skip-git-repo-check -s read-only -C ~/dev/conductor resume <threadId> "What was the codeword?"`
   → the resumed session replied `PELICAN-7`. Context survived the reattach.

Conclusion for v2: attach-to-existing-thread is viable today via
`codex exec resume <threadId>` (CLI). The SDK `resumeThread` is the programmatic
equivalent over the same persisted rollout (`~/.codex/sessions/.../rollout-*.jsonl`);
it was not exercised here to avoid adding an SDK dependency to the beta, but the
rollout-based reopen it relies on is proven to work. Build the attach feature on
the threadId, not on desktop-app session visibility.

## Status: BETA

Tagged `v0.1-beta`. The skeleton is ready for human-driven iteration.
