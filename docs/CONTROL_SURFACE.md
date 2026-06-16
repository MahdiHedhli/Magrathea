# Control surface decision

**Decision: MCP stdio client against `codex mcp-server` (the mission's default path).
No fallback to the Python SDK was needed.**

## Why MCP, not the SDK fallback

The mission specified the default path as an MCP stdio client that connects to
`codex mcp-server`, calls the `codex()` tool to open a session, and reads back a
`threadId`; the Python SDK (`pip install openai-codex`) was the fallback only if
the MCP client could not exchange messages within 25 minutes.

The MCP path worked on the **first probe**, well inside the window:

- `codex mcp-server` answers an MCP `initialize` (protocol `2025-06-18`,
  server `codex-mcp-server` v`0.122.0`).
- It advertises exactly the two tools the mission expects: **`codex`** (start a
  session) and **`codex-reply`** (continue a session by `threadId`).
- Calling `codex()` opens a session and a `threadId` is reported on every
  `codex/event` notification (`params._meta.threadId`), in the
  `session_configured` event, and in the final tool result
  (`structuredContent.threadId`).

Because the default path exchanged messages immediately, switching to the SDK
fallback would have added a dependency and a second control surface for no
benefit. We stayed on MCP.

## How the surface works (as implemented in `conductor/mcp_client.py`)

The MCP stdio transport is newline-delimited JSON-RPC 2.0:

1. `initialize` → `notifications/initialized`.
2. `tools/call` with `name: "codex"` and arguments
   (`prompt`, `cwd`, `sandbox`, `approval-policy`, optional `model`, `config`).
3. While the call is in flight, Codex streams `codex/event` notifications
   (`session_configured`, `task_started`, `item_started/completed`, `error`,
   `task_complete`, …). The client captures the `threadId` from these.
4. The matching `tools/call` response carries the final agent text in
   `result.structuredContent.content` and an `result.isError` flag.
5. `codex-reply` continues the same thread by `threadId` (used for the gate
   retry and the stretch goal).

`CodexMCPClient` is stdlib-only (subprocess + JSON over stdio), logs every raw
message to `logs/*.jsonl`, and drains stderr so the server never blocks.

## Worker sandboxing

Per the safety constraints, the worker session is constrained, not trusted:

- `cwd` = `gate/` (the worker's writable root under `workspace-write`).
- `sandbox` = `workspace-write` (network off by default; writes confined to `cwd`).
- `approval-policy` = `never` — the sandbox is the safety boundary, since no one
  is watching to approve prompts.
- The worker's global MCP servers are disabled (`config.mcp_servers = {}`): a
  pure-function task needs none, and it shrinks the worker prompt and surface.

## Model-availability blocker (see `STATUS.md`)

The control surface is fully proven, but on this machine **no worker model can
currently run a turn**:

- The ChatGPT account is entitled only to `gpt-5.5`, which **Codex CLI 0.122.0
  cannot drive** ("requires a newer version of Codex"); every other cloud model
  is "not supported when using Codex with a ChatGPT account".
- The local LM Studio OSS fallback connects, but its models are JIT-loaded at
  `n_ctx = 8192`, while Codex's base prompt is `~21,776` tokens
  (`n_keep 21776 >= n_ctx 8192`).

Both fixes require an operator action that the unattended run is forbidden to
take (global CLI upgrade / API key / reconfiguring the user's LM Studio). The
orchestrator therefore opens the session, captures the `threadId`, receives the
worker's (error) result, runs its gate, and **escalates** — exactly the designed
failure path.
