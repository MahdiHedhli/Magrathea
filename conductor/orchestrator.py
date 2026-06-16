#!/usr/bin/env python3
"""Phase 3 — dispatch one real task to the Codex worker and gate the result.

Flow:
  1. Open a worker session via the MCP ``codex`` tool (sandbox workspace-write,
     cwd = gate/, network off, approvals never). Capture the threadId.
  2. Classify the worker's result:
       * infrastructure failure (session/model error, timeout) -> the gate is
         run for the record, then the orchestrator ESCALATES immediately. A
         reply retry cannot fix an environment problem.
       * worker completed a turn -> run the gate.
  3. Gate green  -> PASS.
     Gate red    -> feed the failing output back ONCE via ``codex-reply`` on the
                    same thread, then re-run the gate.
     Still red   -> ESCALATE (two consecutive gate failures) and stop.

The orchestrator runs the gate itself; it never hand-fixes the worker's code.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Optional

from . import config, ntfy
from .gate_runner import GateResult, run_gate
from .mcp_client import CodexMCPClient, CodexResult

PHASE = "Phase 3"

TASK_CONTRACT = """\
Create a file named `purl.py` in your current working directory that defines a
single pure function:

    def parse_purl(purl: str) -> dict

It parses a Package URL ("purl") string into its components and returns a dict
with EXACTLY these keys:

    type       lowercased str                               (required)
    namespace  percent-decoded str, segments joined by '/'  (or None if absent)
    name       percent-decoded str                          (required)
    version    percent-decoded str                          (or None if absent)
    qualifiers dict {lowercased_key: percent-decoded value} ({} if absent)
    subpath    percent-decoded str, leading/trailing '/' stripped (or None)

Parsing order (canonical purl algorithm), splitting LEFT-to-RIGHT:
    1. split once on '#'  -> right side is the subpath
    2. split once on '?'  -> right side is the qualifiers
    3. split once on ':'  -> left side is the scheme, which MUST equal 'pkg'
                             (case-insensitive); strip any leading '//'
    4. split once on '/'  -> left side is the type (lowercased)
    5. split once on '@'  -> right side is the version
    6. split the rest on the LAST '/' -> left is namespace, right is name

Use urllib.parse.unquote for percent-decoding. Lowercase qualifier keys; drop a
qualifier whose value is empty. Strip leading/trailing slashes from the subpath.
Raise ValueError when the string is not a valid purl (scheme missing/not 'pkg',
no type, or no name).
"""

TASK_PROMPT = f"""\
You are a worker driven by an orchestrator. Your ONLY job is to make the existing
failing test pass — nothing more.

There is a pytest file `test_purl.py` in your current working directory. Read it
to see the exact expected behaviour. Then create `purl.py` implementing the
contract below so that every test passes.

{TASK_CONTRACT}

Rules:
- Create ONLY `purl.py`. Do NOT modify `test_purl.py` or `conftest.py`.
- Pure function, Python standard library only. No new dependencies.
- Keep it minimal and correct. Do not add anything the test does not require.
When done, reply with a one-line confirmation.
"""


@dataclass
class DispatchOutcome:
    status: str                       # PASS | BLOCKED_INFRA | BLOCKED_GATE
    thread_id: Optional[str]
    worker_error: bool
    gate: Optional[GateResult]
    detail: str


def _retry_prompt(feedback: str) -> str:
    return (
        "The test is still failing. Here is the pytest output:\n\n"
        f"{feedback}\n\n"
        "Fix `purl.py` so all tests pass. Change only `purl.py`. "
        "Reply with a one-line confirmation when done."
    )


def _log_event(emsg, thread_id):
    t = emsg.get("type")
    if t == "session_configured":
        print(f"[phase3] session_configured threadId={thread_id} "
              f"model={emsg.get('model')} sandbox={emsg.get('sandbox_policy')}")
    elif t in ("task_started", "task_complete", "error"):
        print(f"[phase3] event: {t} {emsg.get('message', '')[:160]}")
    elif t == "item_completed":
        item = emsg.get("item", {})
        if item.get("type") in ("CommandExecution", "FileChange", "AgentMessage"):
            print(f"[phase3] item_completed: {item.get('type')}")


def run() -> DispatchOutcome:
    log_path = config.LOGS_DIR / "phase3.jsonl"
    print(f"[phase3] dispatching task to worker "
          f"(cwd={config.WORKER_CWD}, sandbox={config.WORKER_SANDBOX}, "
          f"model={config.WORKER_MODEL or 'codex-default'})")

    with CodexMCPClient(config.CODEX_MCP_CMD, log_path=log_path) as client:
        client.initialize(timeout=config.INITIALIZE_TIMEOUT)

        result: CodexResult = client.codex(
            prompt=TASK_PROMPT,
            cwd=config.WORKER_CWD,
            sandbox=config.WORKER_SANDBOX,
            approval_policy=config.WORKER_APPROVAL_POLICY,
            model=config.WORKER_MODEL,
            config=config.WORKER_CONFIG,
            timeout=config.DISPATCH_TIMEOUT,
            on_event=_log_event,
        )
        thread_id = result.thread_id
        print(f"[phase3] threadId captured: {thread_id}")
        print(f"[phase3] worker turn: ok={result.ok} is_error={result.is_error} "
              f"timed_out={result.timed_out}")

        # --- infrastructure failure: escalate, do not retry -----------------
        if result.is_error or result.timed_out:
            gate = run_gate()  # for the record
            why = result.text.strip().replace("\n", " ")[:240]
            detail = (f"worker session/model failed: {why} | "
                      f"gate: {gate.summary}")
            print(f"[phase3] INFRASTRUCTURE BLOCKER -> {detail}")
            ntfy.blocker(
                PHASE,
                "blocked | worker model unavailable | session+threadId OK, "
                f"worker errored ({why[:120]}); gate {gate.summary}; see STATUS.md",
            )
            return DispatchOutcome("BLOCKED_INFRA", thread_id, True, gate, detail)

        # --- worker completed a turn: run the gate --------------------------
        gate = run_gate()
        print(f"[phase3] gate (attempt 1): passed={gate.passed} :: {gate.summary}")
        if gate.passed:
            ntfy.progress(PHASE,
                          f"done | dispatch+verify | worker satisfied the gate "
                          f"({gate.summary}); threadId {thread_id}")
            return DispatchOutcome("PASS", thread_id, False, gate,
                                   "gate green on first attempt")

        # --- one retry on the same thread -----------------------------------
        print("[phase3] gate red -> feeding failing output back via codex-reply")
        result2 = client.codex_reply(thread_id, _retry_prompt(gate.feedback),
                                      timeout=config.DISPATCH_TIMEOUT,
                                      on_event=_log_event)
        if result2.is_error or result2.timed_out:
            gate2 = run_gate()
            why = result2.text.strip().replace("\n", " ")[:200]
            ntfy.blocker(PHASE,
                         "blocked | worker failed on retry | "
                         f"{why[:120]}; gate {gate2.summary}; stopping")
            return DispatchOutcome("BLOCKED_INFRA", thread_id, True, gate2,
                                   f"retry errored: {why}")

        gate2 = run_gate()
        print(f"[phase3] gate (attempt 2): passed={gate2.passed} :: {gate2.summary}")
        if gate2.passed:
            ntfy.progress(PHASE,
                          f"done | dispatch+verify | gate green after one retry "
                          f"({gate2.summary}); threadId {thread_id}")
            return DispatchOutcome("PASS", thread_id, False, gate2,
                                   "gate green after one retry")

        ntfy.blocker(PHASE,
                     f"blocked | gate failing twice | {gate2.summary}, stopping")
        return DispatchOutcome("BLOCKED_GATE", thread_id, False, gate2,
                               "two consecutive gate failures")


def main() -> int:
    outcome = run()
    print(f"\n[phase3] OUTCOME: {outcome.status} :: {outcome.detail}")
    return 0 if outcome.status == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
