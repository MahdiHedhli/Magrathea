# Implementation Plan: Magrathea Dashboard

**Spec**: [spec.md](spec.md) | **Status**: Implemented

## Technical context
- **Language/runtime**: Python 3.14, **standard library only** (`http.server`,
  `json`, `subprocess`, `urllib`, `re`, `pathlib`). Zero added runtime deps
  (NFR-1).
- **Frontend**: one static HTML page + vanilla JS + CSS, served by the backend.
  No framework, no build step (NFR-2/3).
- **Gate runner**: `pytest==8.4.2` (already pinned).

## Constitution check
- [x] I Gate-first — read-only/localhost/degradation tests written first.
- [x] II Escalate — N/A (read-only), but no silent failures: panels degrade.
- [x] III Governance untouched — dashboard only **reads** `governance/`.
- [x] IV Least privilege — no writes, no network-binding beyond loopback, no
  model, no orchestrator import.
- [x] VI Two budgets — N/A (no model). VIII Reproducible — pinned, no build step.

## Architecture
```
dashboard/
  config.py     HOST=127.0.0.1, PORT, repo paths, current-sprint pointer,
                NTFY topic (imported from conductor.config, NOT hardcoded)
  sources.py    pure READ functions -> dicts (no writes, no model, no dispatch):
                  topology()  <- governance/*.md
                  sprint()    <- specs/<current>/tasks.md
                  timeline()  <- git log (+ optional ntfy GET, degrade to git-only)
                  governance()<- governance/orchestrator.md + model-limit-policy.md
                  runstate()  <- .magrathea/runstate.json (pending if absent)
                  budget()    <- usage output (pending if absent)
  server.py     stdlib ThreadingHTTPServer bound to 127.0.0.1; Handler with
                do_GET ONLY; routes / , /static/*, /api/<panel>, /api/health
  static/       index.html, app.js, style.css  (single responsive page)
  tests/        test_readonly.py, test_localhost.py, test_degradation.py
```

### Read-only enforcement (how the tests bite)
- **No mutating routes**: the handler defines `do_GET` only; `do_POST`/`PUT`/
  `DELETE` are absent (BaseHTTPRequestHandler answers `501` for them). Tests
  assert the handler class has no `do_POST/do_PUT/do_DELETE` and that a POST gets
  a non-2xx.
- **No LLM / no dispatch import**: importing `dashboard.*` must not pull in
  `anthropic`/`openai`/etc. or `conductor.orchestrator`/`conductor.mcp_client`.
  Tests scan `sys.modules` after import and scan source for forbidden imports.
- **No on-disk writes**: source contains no write-mode `open()`/`os.remove`/
  `mkdir`/`write_text`; a runtime test snapshots the repo dir before/after a
  request and asserts no new/changed files.

### Localhost
`config.HOST == "127.0.0.1"`; source never contains `0.0.0.0`. `server.py`
binds `(config.HOST, PORT)`. Tests assert the constant and the absence of
`0.0.0.0`.

### Degradation
`runstate()` / `budget()` catch FileNotFoundError → return
`{"status":"pending", "reason":..., "lands_in":...}`. The `/api/*` endpoints
always return `200` with a status field; the page renders a pending card.

### Timeline network use
`git log` is local and primary. The optional ntfy fetch is a GET to
`{NTFY_BASE}/{TOPIC}/json?poll=1&since=…` with a short timeout; any failure →
git-only. Topic comes from `conductor.config.NTFY_TOPIC`.

## Project structure
New: `dashboard/`, `specs/002-dashboard/`. Touches nothing in `conductor/` or
`governance/` (reads only).

## Risks & mitigations
- **Markdown parsing brittleness** → parsers target known governance structure,
  default to "unknown"/raw on miss; never crash a panel.
- **Sandbox blocks outbound ntfy** → timeline degrades to git-only by design.

## Verification
Gate: `.venv/bin/python -m pytest dashboard/tests -q` (read-only, localhost,
degradation). Manual proof recorded in `tasks.md` / commit.
