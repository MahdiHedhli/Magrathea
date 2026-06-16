# Gate Definition

**Owner**: human. **Compiled by**: preflight (section A). **Version**: 1.0.0
(2026-06-16). Worker-unwritable. Realizes Constitution I (gate-first). The
orchestrator owns and runs this; **no model sits in the gate.**

## Stack
Python 3.14, standard library + `pytest`. The only third-party dependency is the
test runner, pinned in `requirements.txt` (`pytest==8.4.2`) and installed into a
project-local `./.venv` — never global.

## "Done" in machine terms
A change is accepted **iff** this command returns exit code 0, run from the repo
root (`~/dev/conductor`):

```bash
.venv/bin/python -m pytest gate/test_purl.py -q
```

- Green (exit 0) = pass. Anything else (red / collection error / timeout) = fail.
- The orchestrator runs it; `conductor/gate_runner.py` wraps it into a structured
  verdict.
- Per-task timeout: 420s (`cadence.md`).

## What the gate verifies
The acceptance contract for the current feature lives in `gate/test_purl.py`
(8 deterministic cases pinning `parse_purl`). The orchestrator writes the gate
**before** dispatch (gate-first); the worker only satisfies it.

## Future gates (when the stack grows)
Add deterministic, exit-code-only checks in this order of preference
(deterministic-first): test → typecheck → lint → build. Each runs from a named
directory and returns 0/non-0. Never introduce a model-judged check as the gate.

## Work with NO machine gate (escalates, never auto-runs)
These have no deterministic gate and therefore **escalate** rather than
auto-run: documentation/prose, governance/constitution edits, architecture
decisions, and any task whose acceptance is a judgment call. The orchestrator
lists them for the operator (Constitution II).
