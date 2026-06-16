# Conductor — walking-skeleton status

> **SUPERSEDED / HISTORICAL (first build run).** The model-availability blocker
> described below was resolved by updating the Codex CLI to `0.140.0`. The worker
> now reaches green: see [`SMOKETEST.md`](SMOKETEST.md) and [`BETA.md`](BETA.md).
> This file is kept as the original build report.

**Run:** unattended build, 2026-06-16, model `claude-opus-4-8`, effort xhigh.
**Outcome:** the orchestration skeleton is **built and proven end to end at the
control/gate/dispatch/report layers**. The one un-green step — the worker
producing code — is **environmentally blocked** (no usable worker model on this
machine) and was **correctly escalated**, which is the run's designed failure
path and counts as success per the run's own definition of done.

---

## TL;DR gate result

| Definition-of-done checkpoint | Result |
|---|---|
| Opened a Codex session | ✅ |
| Captured a `threadId` | ✅ `019ed0f1-a481-7790-a359-ecbac4db99ef` (Phase 3) |
| Received a result | ✅ (an error result — see blocker) |
| Ran the orchestrator-defined gate | ✅ red (`1 error`, no `purl.py` produced) |
| Reported the correct pass/fail | ✅ correct **fail/blocked**, NTFY sent |
| All NTFY pings sent | ✅ start, Phase 1, Phase 2, Phase 3 blocker, run end |
| Everything under `~/dev/conductor/` | ✅ |
| `STATUS.md` written + committed | ✅ (this file) |

The gate is **red on purpose**: the worker never produced `gate/purl.py` because
no worker model could run a turn (below). The gate is known-good and satisfiable
— a throwaway reference implementation passed all 8 cases before being deleted.

---

## What was built

```
~/dev/conductor/
├── conductor/                 # the orchestrator (stdlib-only except the gate's pytest)
│   ├── config.py              # paths, worker policy, model, NTFY topic — one place to change
│   ├── mcp_client.py          # Codex MCP stdio client: initialize, tools/list,
│   │                          #   codex(), codex-reply(), event streaming, threadId capture
│   ├── gate_runner.py         # deterministic pytest gate runner (green == returncode 0)
│   ├── orchestrator.py        # Phase 3: dispatch -> classify -> gate -> retry/escalate
│   └── ntfy.py                # NTFY reporter (progress / blocker)
├── gate/                      # the acceptance gate (orchestrator-owned)
│   ├── test_purl.py           # 8 deterministic pytest cases for parse_purl()
│   ├── conftest.py            # makes the worker-authored purl.py importable
│   └── purl.py                # (worker writes this; absent -> gate red. gitignored)
├── phase1_control_surface.py  # standalone proof of the control surface
├── scripts/                   # Phase-0 probes that established the protocol + blocker
│   ├── mcp_probe.py           #   initialize + tools/list
│   ├── probe_session.py       #   one trivial session, dumps every event (threadId format)
│   └── probe_model.py         #   model-availability sweep (found the blocker)
├── docs/CONTROL_SURFACE.md    # the control-surface decision + blocker write-up
├── logs/                      # per-phase JSONL transcripts of every MCP message
├── requirements.txt           # pytest==8.4.2 (pinned; installed into ./.venv, never global)
└── .venv/                     # project-local venv
```

## Control-surface decision (and why)

**Chosen: MCP stdio client against `codex mcp-server` — the mission's default
path. The Python-SDK fallback was not needed.** The MCP path exchanged messages
on the first probe, far inside the 25-minute fallback window: `codex mcp-server`
answers `initialize` (protocol `2025-06-18`), advertises the `codex` and
`codex-reply` tools, and reports a `threadId` on every `codex/event`
notification and in the final tool result. Adding the SDK would have meant a new
dependency and a second control surface for zero benefit. Full reasoning and the
wire-level details are in [`docs/CONTROL_SURFACE.md`](docs/CONTROL_SURFACE.md).

**Worker sandboxing** (the safety boundary, since nobody is approving prompts):
`cwd = gate/`, `sandbox = workspace-write` (writes confined to `cwd`, **network
off**), `approval-policy = never`, and the worker's global MCP servers disabled
(`config.mcp_servers = {}`). In the live run the session reported
`network_access: False` and writes scoped as intended; the gate dir stayed clean.

---

## The blocker (why the worker could not produce code)

No worker model can currently run a turn on this machine. This needs an
**operator decision/action** that an unattended run is forbidden to take, so the
orchestrator escalated instead of barrelling.

| Path | What happens | Fix (operator only) |
|---|---|---|
| **Cloud (ChatGPT account)** | Account is entitled only to `gpt-5.5`, which **Codex CLI 0.122.0 cannot drive**: `"The 'gpt-5.5' model requires a newer version of Codex."` Every other cloud model returns `"not supported when using Codex with a ChatGPT account."` | Upgrade the Codex CLI **or** authenticate with an OpenAI API key — both are prohibited here (global install / credential action). |
| **Local OSS (LM Studio)** | `codex --oss --local-provider lmstudio` connects and a session opens, but every model is JIT-loaded at `n_ctx = 8192` while Codex's base prompt is `~21,776` tokens: `n_keep 21776 >= n_ctx 8192`. Minimal `base-instructions` doesn't help — the function-tool schemas alone exceed 8192. | Reload LM Studio models with a larger context (e.g. LM Studio UI, or `lms load <model> --context-length 32768`) — an out-of-scope change to the user's running app. |

**Why not "just fix it":** every fix is one of the run's explicit stop
conditions — credentials/account action, a global install, or touching settings
outside the project. The correct unattended behaviour is to escalate, which the
orchestrator did automatically (Phase 3 NTFY blocker).

**To turn the skeleton green once unblocked:** set the worker model in one place
— `conductor/config.py` (`WORKER_MODEL`, or env `CONDUCTOR_WORKER_MODEL`) — and
re-run `python -m conductor.orchestrator`. No other change is required; the
dispatch → gate → retry → report loop is already wired.

---

## How to run it

```bash
cd ~/dev/conductor

# Phase 1 — prove the control surface (open a session, capture a threadId)
.venv/bin/python phase1_control_surface.py

# Run the gate directly (red until a worker writes gate/purl.py)
.venv/bin/python -m pytest gate/test_purl.py -q
#   or: .venv/bin/python -m conductor.gate_runner

# Phase 3 — dispatch the task to the worker and gate the result
.venv/bin/python -m conductor.orchestrator

# Send an NTFY ping manually
.venv/bin/python -m conductor.ntfy progress "Manual" "hello"
```

Environment knobs: `CONDUCTOR_WORKER_MODEL`, `CONDUCTOR_NTFY_URL`,
`CONDUCTOR_NTFY_TOPIC` (defaults: codex-default model, `https://ntfy.sh`,
`Mahdi-Dev`).

---

## The next three things to build

1. **Multi-thread dispatch.** Generalize the orchestrator from one session to a
   pool: a small dispatcher that opens N `codex` sessions concurrently (each its
   own `threadId` + sandboxed `cwd`), tracks them by id, and fans tasks out. The
   `CodexMCPClient` is already per-process and thread-safe-per-call; the missing
   piece is a session registry + a concurrency cap + per-thread logging. This is
   where worker tiering and additional workers (Grok, Antigravity) would later
   plug in behind a common `Worker` interface.

2. **A deterministic-first gate-runner abstraction.** Promote `gate_runner.py`
   to a `Gate` protocol with pluggable runners (pytest today; later: a typed
   command runner, a schema/output validator, a property-based check), all
   returning the same structured `GateResult`. "Deterministic-first" means the
   orchestrator always prefers a cheap, reproducible check (exit code / diff /
   schema) before any model-judged check, so verification never depends on a
   model's opinion. Add gate **timeouts** and an explicit red/amber/green verdict.

3. **The NTFY escalation policy as a first-class module.** Today escalation is
   inline in the orchestrator. Extract a policy object that classifies every
   outcome (infra failure vs. gate-red vs. timeout vs. prohibited-action) and
   decides retry-vs-escalate, with severity, dedupe/rate-limiting, and a single
   place that enforces the stop conditions (e.g. "two consecutive gate failures",
   "≈15 min before the deadline"). This makes "escalate, don't barrel" a
   guarantee of the framework rather than a convention in each call site.

---

## Honest notes / deviations

- **Live demonstration uses the cloud default model** (`gpt-5.5`) because it
  returns a clean, fast `isError` that cleanly exercises the orchestrator's
  infra-blocker branch. The local OSS path was investigated (it connects) but
  can't fit Codex's prompt at ctx 8192; it is documented, not used.
- **The gate-red → `codex-reply` retry branch is implemented but not exercised
  live**, because the worker can't produce code to be wrong about. Its gate
  mechanics are proven (red with no impl, green with the reference impl).
- **No worker code was hand-fixed.** The reference implementation used to verify
  the gate's satisfiability was deleted before dispatch; `gate/purl.py` is absent
  and gitignored. The worker's task remains genuinely unsatisfied.
- **Stretch goal (second task via `codex-reply`)**: implemented in the client,
  not run, for the same model-availability reason.
