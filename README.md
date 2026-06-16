# Magrathea / Conductor

A walking-skeleton orchestrator that drives **Codex as a controllable, gated
worker**. It proves exactly one path end to end:

> orchestrator → launch Codex over MCP → dispatch one real task → verify with a
> deterministic gate the orchestrator itself defines → report over NTFY.

This repo is organized for **[GitHub Spec Kit](https://github.com/github/spec-kit)**
compatibility and governed by the **Magrathea Constitution**:

- Governance principles: [`.specify/memory/constitution.md`](.specify/memory/constitution.md)
- Per-repo policy (human-owned, worker-unwritable): [`governance/`](governance/) *(compiled by the preflight)*
- The implemented feature: [`specs/001-walking-skeleton/`](specs/001-walking-skeleton/)
- The mapping explained: [`docs/SPEC-KIT.md`](docs/SPEC-KIT.md)

Out of scope (by design): multi-thread dispatch, model tiering, graceful
degradation, additional workers. See [`STATUS.md`](STATUS.md) for the full
build report and [`BETA.md`](BETA.md) for the v2 backlog.

## How it works

1. **Control surface** — `conductor/mcp_client.py` speaks newline-delimited
   JSON-RPC to `codex mcp-server`, calls the `codex()` tool to open a sandboxed
   session, captures the `threadId`, and can continue it with `codex-reply()`.
2. **The gate** — `gate/test_purl.py` is 8 deterministic pytest cases for a pure
   `parse_purl()` function. The orchestrator owns the test; the worker satisfies
   it (gate-first: the test is red until the worker writes `gate/purl.py`).
3. **Dispatch + verify** — `conductor/orchestrator.py` sends the task to the
   worker (sandbox `workspace-write`, scoped to `gate/`, network off), runs the
   gate itself, feeds one failure back via `codex-reply()`, and **escalates**
   over NTFY rather than looping.

## Quickstart

```bash
cd ~/dev/conductor
.venv/bin/python phase1_control_surface.py        # prove the control surface
.venv/bin/python -m pytest gate/test_purl.py -q   # the gate (red until satisfied)
.venv/bin/python -m conductor.orchestrator        # dispatch + verify + report
```

Dependencies are pinned in `requirements.txt` (`pytest==8.4.2`) and installed
into a project-local `.venv` — never globally.

## Status: v0.1-beta

The full loop is **proven green**: on a current Codex CLI (`0.140.0`), the worker
(`gpt-5.5`) writes `purl.py` and the gate passes 8/8 — repeatably, not hand-fixed.
Both failure branches and NTFY are verified, and resume/attach is de-risked.
Development is human-driven from here.

- Handoff + drive command + caveats: [`BETA.md`](BETA.md)
- Smoketest record (both branches, threadIds): [`SMOKETEST.md`](SMOKETEST.md)
- Original build report (historical; its model-availability blocker is now
  resolved by the current CLI): [`STATUS.md`](STATUS.md)
