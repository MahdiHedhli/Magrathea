#!/usr/bin/env python3
"""The Magrathea runtime dogfood loop.

read descriptor -> enforce governance -> dispatch to an ISOLATED worker -> run
the project's own gate -> write runstate -> retry/escalate/done.
"""
from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from conductor import ntfy
from conductor.mcp_client import CodexMCPClient
from runtime import (config, descriptor as descriptor_mod, governance, usage,
                     worker_home)
from runtime.gate import GateResult, run_gate
from runtime.runstate import RunstateWriter

_TERMINAL_TASK = {"passed", "failed", "escalated"}


@dataclass
class Outcome:
    status: str  # PASS|BLOCKED_GOVERNANCE|BLOCKED_INFRA|BLOCKED_GATE|BLOCKED_LIMIT
    thread_id: Optional[str]
    gate: Optional[GateResult]
    detail: str
    reset_time: Optional[str] = None  # on BLOCKED_LIMIT: when the window resets


_LIMIT_MARKERS = ("rate limit", "rate_limit", "usage limit", "quota",
                  "too many requests", "429", "insufficient_quota")


def _is_limit_hit(text: str) -> bool:
    """A provider limit-hit is a third outcome — pause, not fail (Constitution VII)."""
    t = (text or "").lower()
    return any(m in t for m in _LIMIT_MARKERS)


def _retry_prompt(feedback: str) -> str:
    return ("The gate is still failing. Output:\n\n" + feedback +
            "\n\nFix only files in your working directory so the gate passes. "
            "Reply with a one-line confirmation when done.")


def execute_descriptor(descriptor, handle, log_path=None) -> Outcome:
    """Shared per-descriptor core: governance -> isolated dispatch (writing
    'dispatched' as soon as the threadId is known) -> gate -> retry -> resolve.
    Writes via the HANDLE protocol (dispatched / gate_recorded / done /
    escalated), so both run() and the queue reuse it. A limit-hit returns
    BLOCKED_LIMIT (pause, not escalate)."""
    decision = governance.load().check(descriptor)

    # --- governance enforcement: always-human is refused, never dispatched ---
    if not decision.allowed:
        print(f"[runtime] REFUSED (governance): {decision.reason}")
        handle.escalated(decision.reason)
        return Outcome("BLOCKED_GOVERNANCE", None, None, decision.reason)

    model = decision.model or config.DEFAULT_WORKER_MODEL
    repo = (config.REPO_ROOT / descriptor.target_repo).resolve()
    worker_cwd = (repo / descriptor.working_dir).resolve()
    gate_cwd = (repo / descriptor.gate_dir).resolve()

    # --- isolation: dedicated worker CODEX_HOME, no operator MCP -------------
    worker_home.ensure()
    env = worker_home.codex_env()
    print(f"[runtime] dispatch '{descriptor.id}' model={model} "
          f"cwd={worker_cwd} (isolated CODEX_HOME)")

    def _gate() -> GateResult:
        return run_gate(descriptor.gate_command, str(gate_cwd), descriptor.timeout_seconds)

    with CodexMCPClient(config.CODEX_MCP_CMD, log_path=log_path, env=env) as client:
        client.initialize(timeout=config.INITIALIZE_TIMEOUT)

        # Write 'dispatched' AS SOON as the threadId is known (session_configured),
        # so an interrupt mid-turn leaves a true in-flight runstate to reattach.
        captured = {"tid": None, "rate_limits": None}

        def _on_event(emsg, thread_id):
            if thread_id and not captured["tid"]:
                captured["tid"] = thread_id
                handle.dispatched(thread_id, config.DEFAULT_WORKER_PROVIDER, model)
                print(f"[runtime] threadId={thread_id} (in-flight)")
            rl = usage.capture_from_event(emsg)   # opportunistic usage capture
            if rl:
                captured["rate_limits"] = rl

        result = client.codex(
            prompt=descriptor.goal, cwd=str(worker_cwd), sandbox="workspace-write",
            approval_policy="never", model=model, timeout=descriptor.timeout_seconds,
            on_event=_on_event,
        )
        thread_id = result.thread_id or captured["tid"] or ""
        if not captured["tid"] and thread_id:
            handle.dispatched(thread_id, config.DEFAULT_WORKER_PROVIDER, model)
        print(f"[runtime] turn done ok={result.ok} is_error={result.is_error}")

        if result.is_error or result.timed_out:
            if _is_limit_hit(result.text):
                reset = (usage.limit_reset_from_rate_limits(captured["rate_limits"])
                         or usage.compute_reset(300))
                return Outcome("BLOCKED_LIMIT", thread_id, None,
                               f"limit-hit: {result.text[:120]}", reset_time=reset)
            g = _gate()
            handle.gate_recorded(g.passed, g.summary, g.returncode)
            handle.escalated(f"worker infra failure: {result.text[:160]}")
            return Outcome("BLOCKED_INFRA", thread_id, g, "worker infra failure")

        g = _gate()
        handle.gate_recorded(g.passed, g.summary, g.returncode)
        print(f"[runtime] gate(1): passed={g.passed} :: {g.summary}")
        if g.passed:
            handle.done()
            return Outcome("PASS", thread_id, g, "gate green (first attempt)")

        for attempt in range(1, descriptor.retry_budget + 1):
            print(f"[runtime] gate red -> codex-reply retry {attempt}/{descriptor.retry_budget}")
            reply = client.codex_reply(thread_id, _retry_prompt(g.feedback),
                                       timeout=descriptor.timeout_seconds)
            if reply.is_error or reply.timed_out:
                if _is_limit_hit(reply.text):
                    reset = (usage.limit_reset_from_rate_limits(captured["rate_limits"])
                             or usage.compute_reset(300))
                    return Outcome("BLOCKED_LIMIT", thread_id, g,
                                   f"limit-hit: {reply.text[:120]}", reset_time=reset)
                handle.escalated(f"retry infra failure: {reply.text[:160]}")
                return Outcome("BLOCKED_INFRA", thread_id, g, "retry infra failure")
            g = _gate()
            handle.gate_recorded(g.passed, g.summary, g.returncode)
            print(f"[runtime] gate(retry {attempt}): passed={g.passed} :: {g.summary}")
            if g.passed:
                handle.done()
                return Outcome("PASS", thread_id, g, f"gate green after {attempt} retry")

        handle.escalated(f"gate failing after {descriptor.retry_budget} retries: {g.summary}")
        return Outcome("BLOCKED_GATE", thread_id, g, "gate red after retries")


def run(descriptor, writer: Optional[RunstateWriter] = None,
        log_path=None) -> Outcome:
    """Single-descriptor run: a one-task runstate writer + the shared core."""
    if writer is None:
        writer = RunstateWriter(config.RUNSTATE_PATH, run_id=f"run-{descriptor.id}",
                                current_sprint="003-runtime")
    writer.queue(descriptor)
    return execute_descriptor(descriptor, writer, log_path)


# --- reattach-on-restart (feature 004) --------------------------------------
def load_runstate(path=None):
    p = Path(path) if path else config.RUNSTATE_PATH
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def reattach_plan(runstate) -> Optional[str]:
    """Return the thread_id to resume iff a task is in-flight (not terminal) and
    carries a thread_id; else None (start fresh)."""
    if not runstate:
        return None
    tq = runstate.get("task_queue") or []
    if not tq:
        return None
    task = tq[0]
    thread_id = task.get("thread_id") or (runstate.get("in_flight") or {}).get("thread_id")
    if task.get("status") not in _TERMINAL_TASK and thread_id:
        return thread_id
    return None


def _continue_prompt(descriptor) -> str:
    return ("Continue and complete the task so the gate passes. Task: "
            + descriptor.goal +
            " Only modify files in your working directory. Reply with a one-line "
            "confirmation when done.")


def _resume_cli(thread_id, prompt, cwd, env, timeout):
    """Resume a persisted thread via `codex exec resume` (the MCP codex-reply tool
    cannot resume across a restart). Returns (ok, stale, output)."""
    cmd = ["codex", "exec", "--skip-git-repo-check", "-s", "workspace-write",
           "-C", cwd, "resume", thread_id, prompt]
    try:
        proc = subprocess.run(cmd, env=env, capture_output=True, text=True,
                              timeout=timeout)
        out = (proc.stdout or "") + (proc.stderr or "")
    except subprocess.TimeoutExpired:
        return False, False, "resume timed out"
    stale = "Session not found" in out or "No session" in out
    return (proc.returncode == 0 and not stale), stale, out


def reattach_descriptor(descriptor, thread_id, handle, log_path=None) -> Outcome:
    """Shared reattach core: resume an in-flight thread by id (no new session) and
    drive it to a gate verdict. Writes via the handle protocol; a stale/gone
    thread escalates (NTFY), never restarts."""
    repo = (config.REPO_ROOT / descriptor.target_repo).resolve()
    worker_cwd = (repo / descriptor.working_dir).resolve()
    gate_cwd = (repo / descriptor.gate_dir).resolve()
    worker_home.ensure()
    env = worker_home.codex_env()

    handle.dispatched(thread_id, config.DEFAULT_WORKER_PROVIDER,
                      config.DEFAULT_WORKER_MODEL)  # re-assert the SAME thread
    print(f"[runtime] REATTACH thread {thread_id} (no new session) cwd={worker_cwd}")

    ok, stale, out = _resume_cli(thread_id, _continue_prompt(descriptor),
                                 str(worker_cwd), env, descriptor.timeout_seconds)
    if stale or not ok:
        why = "thread stale/gone" if stale else "resume errored"
        msg = f"reattach failed ({why}) for thread {thread_id}"
        print(f"[runtime] {msg}")
        handle.escalated(msg)
        ntfy.blocker("Runtime", f"blocked | reattach {why} | thread "
                     f"{thread_id[:12]}…; escalating, not restarting")
        return Outcome("BLOCKED_INFRA", thread_id, None, msg)

    g = run_gate(descriptor.gate_command, str(gate_cwd), descriptor.timeout_seconds)
    handle.gate_recorded(g.passed, g.summary, g.returncode)
    print(f"[runtime] gate after reattach: passed={g.passed} :: {g.summary}")
    if g.passed:
        handle.done()
        return Outcome("PASS", thread_id, g, "gate green after reattach (same thread)")
    handle.escalated(f"gate red after reattach: {g.summary}")
    return Outcome("BLOCKED_GATE", thread_id, g, "gate red after reattach")


def resume(descriptor, thread_id, log_path=None) -> Outcome:
    """Single-descriptor reattach: a one-task runstate writer + the shared core."""
    writer = RunstateWriter(config.RUNSTATE_PATH, run_id=f"run-{descriptor.id}",
                            current_sprint="004-hardening")
    writer.queue(descriptor)
    return reattach_descriptor(descriptor, thread_id, writer, log_path)


def main(argv) -> int:
    if len(argv) < 2:
        print("usage: python -m runtime.runtime <descriptor.json>")
        return 2
    d = descriptor_mod.load(argv[1])
    log_path = config.MAGRATHEA_DIR / "runtime.jsonl"

    tid = reattach_plan(load_runstate())
    if tid:
        print(f"[runtime] runstate shows in-flight thread {tid} -> reattach")
        outcome = resume(d, tid, log_path=log_path)
    else:
        outcome = run(d, log_path=log_path)

    print(f"\n[runtime] OUTCOME: {outcome.status} :: {outcome.detail}")
    return 0 if outcome.status == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
