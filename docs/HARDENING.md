# Hardening notes (feature 004)

## Durable worker auth

**Mechanism: the worker `auth.json` is a symlink to the operator's single source,
re-asserted before every dispatch.** No standing divergent copy; reads are always
current.

Why this and not the alternatives (resolution order from the spec):
- **(a) auth-path independent of `CODEX_HOME`** — not available on Codex CLI
  0.140. Auth lives at `$CODEX_HOME/auth.json`; the only related knob,
  `cli_auth_credentials_store` (`file`/`keyring`/`auto`), would require switching
  the operator to a keyring and re-logging-in — a settings + credential action we
  do not take.
- **(b) symlink that survives writes** — Codex persists `auth.json` with an
  **atomic-rename** pattern (write temp, rename over the file; per the OpenAI
  Codex docs), so a token refresh *replaces* the file rather than writing in
  place. A refresh in the worker home would therefore replace the symlink.
- **(c) re-sync a copy before each dispatch** — the robust fallback, but it
  leaves a standing copy.

We take the **symlink** because it is the only option with *no standing divergent
copy* (the worker entry is a pointer to the one source, not a second file), and
we **re-assert it on every `ensure()`** (before every dispatch) so it self-heals:
if a prior turn's refresh replaced the link with a regular file, the next dispatch
restores the symlink to the single source. This combines the cleanliness of a
symlink with the freshness of "re-sync before each dispatch."

### Residual risk
A token **refresh during a single worker turn**. Because writes are atomic-rename,
such a refresh would replace the symlink in the worker home with a fresh file
holding a rotated (single-use) refresh token, and the operator's source would keep
the now-consumed token — a divergence until the next operator login. This is
**unlikely in practice**: a worker turn is minutes, the access token lives ~1 hour,
and the link is re-asserted (and the access token thereby refreshed from source)
before every dispatch, so a turn rarely crosses an expiry. It is **not fully
eliminable** while the worker holds write access to a rotatable token; only a
true shared in-place file (option a, unavailable) would remove it. Verified: a
worker turn completes via the symlink and the link is still a symlink afterward
(no refresh occurred).

## Reattach-on-restart

**Mechanism: `codex exec resume <thread_id>` (CLI), isolated to the worker
`CODEX_HOME`.** On startup the runtime reads runstate; if the task is in-flight
(`dispatched`, not terminal) and carries a `thread_id`, it resumes that thread
instead of opening a fresh session. The gate is the arbiter, so continuation is
idempotent.

Why CLI resume, not MCP `codex-reply`: the spike showed a fresh `codex mcp-server`
process's `codex-reply` returns `"Session not found for thread_id"` (the MCP
session is in-memory). `codex exec resume <id>` loads the persisted rollout and
continues the **same** session (recalled the spike codeword across a restart, same
session id). A stale/gone thread (resume errors) **escalates** (NTFY), it does not
silently restart.
