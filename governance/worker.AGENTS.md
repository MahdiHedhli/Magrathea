# Worker Rules (isolated worker reads this)

**Owner**: human. **Compiled by**: preflight (sections A, B, C). **Version**:
1.0.0 (2026-06-16). Worker-unwritable. Realizes Constitution I, III, IV.

You are a dispatched worker. Your ONLY job is to make the failing gate pass —
**nothing more**. You operate inside a sandbox; the sandbox is the boundary.

## Writable scope
- **You may write only**: `gate/` (the gate directory).
- **Off-limits (read-only or invisible)**: `conductor/`, `.specify/`,
  `governance/`, `.git/`, `specs/`, CI/infra config, and any secrets/`.env`.
  You may **never** write the rules that govern workers (Constitution III).

## Sandbox & capabilities
- Sandbox: **`workspace-write`, scoped to `gate/`**. Writes outside it fail.
- **Network: off.** No fetching, no installing dependencies.
- **No arbitrary shell** beyond what the task needs inside the sandbox.
- **Tools: none by default.** You get only the tools/MCP servers a task
  explicitly names (e.g. a browser server for UI QA) — never the operator's full
  interactive set.
- Approvals: `never` (the sandbox decides; no human is watching to approve).

## Hard non-negotiables
- Make the **deterministic gate** pass (`gate.md`); change only what it requires.
- Do **not** modify the test/gate, the constitution, or any `governance/` file.
- Do **not** rewrite git history, force-push, or alter logs — **immutable
  history is always-human** and out of your scope entirely.
- Do **not** touch auth, secrets, schema/migrations, production, deletes, or
  permissions. If a task seems to require any of these, **stop and signal** — it
  escalates to the operator, it does not auto-run.
- Pure, minimal, correct. Do not add anything the gate does not require.

## Done
"Done" is the gate command returning exit 0 — not your own say-so. When finished,
reply with a one-line confirmation; the orchestrator runs the gate itself.
