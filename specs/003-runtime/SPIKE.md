# Worker-isolation spike — outcome

Recorded 2026-06-17. The hard part: a worker must not inherit the operator's
global Codex MCP config (13 servers on this machine), with auth intact.

## Winning mechanism: #1 — dedicated worker `CODEX_HOME` + copied auth

A clean Codex home **outside the repo** that the worker session uses via the
`CODEX_HOME` env var:

- Path: `~/.magrathea-worker-codex` (computed from `Path.home()`, never an
  absolute literal in committed source; never committed).
- `auth.json`: **copied** from the operator's default home (`~/.codex/auth.json`)
  — the existing login reused, never created/entered/transmitted/regenerated.
- `config.toml`: clean, with **no `[mcp_servers]`** section.
- Dispatch: launch `codex mcp-server` with `CODEX_HOME` pointed at this home.

## Result

| Session | MCP servers loaded | Turn |
|---|---|---|
| Operator default home | ~13 (the global set; one hung a turn on 0.140) | — |
| **Worker home (mechanism 1)** | **0 of the operator's 13** + `codex_apps` only | ✅ `ISOLATED` in ~2–4 s |

`codex_apps` is a **Codex CLI built-in** (confirmed: not present in the
operator's `config.toml`), loads instantly, and is not an inherited global
server. `--disable apps` does not remove it (it is not gated by that flag), so
the worker set is "curated to the built-in baseline" — the operator's global
config is fully excluded, which is the spike's goal. Auth carried over cleanly
(the turn completed), so the login was reused without touching credentials.

## Why not the others
Not needed — mechanism 1 cleanly achieved curated MCP + intact auth + a working
turn. Mechanisms 2 (`--config` MCP replace) and 3 (profile nulling MCP) were not
required. The 0.140 finding stands: `mcp_servers = {}` deep-merges to a no-op and
per-server disable yields invalid transports, so a clean separate home is the
right answer.

## Guardrails honored
- Worker `CODEX_HOME` is outside the repo and gitignored-by-location (never
  committed); the secrets sweep confirms no `auth.json` is tracked.
- Worker writable scope comes from the task descriptor + governance, sandboxed
  `workspace-write` to that scope only — never the whole filesystem.
