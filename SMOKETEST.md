# Conductor — smoketest record

Date: 2026-06-16 (wrap-to-beta run). Worker model `gpt-5.5`, Codex CLI `0.140.0`.
Both orchestrator branches were exercised against a **real Codex worker** and
both NTFY pings fired. Times are local (EDT).

## Branch 1 — happy path (green is real and repeatable)

The point of this branch: prove the green is reproducible, not a one-time fluke.
The orchestrator (never a human) ran `pytest`; Codex wrote `gate/purl.py`.

| Run | threadId | Result | Gate |
|---|---|---|---|
| Phase 1 (first green) | `019ed197-fd13-7c71-a5b7-f7e46b38e11a` | PASS, first attempt | 8 passed |
| Phase 2 repeat | `019ed19b-308d-7331-9f32-ce8df11471ee` | PASS, first attempt | 8 passed |

Sequence for the repeat run:
1. `14:04:19` — deleted `gate/purl.py`; confirmed the gate goes **red**
   (`ModuleNotFoundError: No module named 'purl'`, pytest exit 2).
2. Dispatched `python -m conductor.orchestrator` (new session
   `019ed19b-…`). Codex wrote a fresh `purl.py` (1517 bytes — distinct from the
   Phase-1 file of 1411 bytes, i.e. genuinely regenerated, not cached).
3. `~14:06:38` — orchestrator ran the gate: **8 passed**, `OUTCOME: PASS`.
4. NTFY progress ping fired (HTTP 200):
   `done | dispatch+verify | worker satisfied the gate (8 passed …); threadId 019ed19b-…`

The worker's code is its own: it uses `str.partition` / `rpartition`, unlike the
throwaway reference implementation (which used `split` / `rsplit` and was deleted
before any dispatch). No human hand-fixed `purl.py`.

## Branch 2 — failure path (infra failure escalates, no retry)

The point of this branch: prove the orchestrator classifies a worker/model
failure as infrastructure (not a gate-red), runs the gate for the record,
escalates, and does **not** waste a `codex-reply` retry on an unfixable error.

- `14:07:38` — deleted `gate/purl.py` (clean state), then dispatched with a
  bogus model id: `CONDUCTOR_WORKER_MODEL=gpt-nonexistent-zzz9`.
- Session opened, threadId `019ed19e-1789-79e3-a46d-1a125553eedc` captured.
- Worker turn: `ok=False is_error=True timed_out=False`. Error:
  `400 invalid_request_error — "The 'gpt-nonexistent-zzz9' model is not supported
  when using Codex with a ChatGPT account."`
- Orchestrator classified it `INFRASTRUCTURE BLOCKER`, ran the gate for the
  record (**1 error**, red — no impl), and returned `OUTCOME: BLOCKED_INFRA`.
- **No `codex-reply` retry was attempted** (the retry branch is reserved for a
  worker that completed but produced failing code; an infra/model error cannot be
  fixed by replying).
- NTFY blocker ping fired (HTTP 200, `Priority: high`, `Tags: warning`):
  `blocked | worker model unavailable | … gate 1 error …; see STATUS.md`
- `14:07:48` — finished (~10s; fast-fail, no stall).
- The bogus model was an inline env override for that single run; the committed
  default (`conductor/config.py` → `WORKER_MODEL = "gpt-5.5"`) is unchanged.

## Post-conditions

- Effective `WORKER_MODEL` restored to `gpt-5.5`.
- Repo left in the gate-first state: `gate/purl.py` absent, gate red. The drive
  command regenerates a green `purl.py` on the next dispatch.
- `gate/purl.py` is worker output and is gitignored; it is intentionally not
  committed.
