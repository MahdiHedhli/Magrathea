#!/usr/bin/env python3
"""The Magrathea runtime dogfood loop.

read descriptor -> enforce governance -> dispatch to an ISOLATED worker -> run
the project's own gate -> write runstate -> retry/escalate/done.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Optional

from conductor.mcp_client import CodexMCPClient
from runtime import config, descriptor as descriptor_mod, governance, worker_home
from runtime.gate import GateResult, run_gate
from runtime.runstate import RunstateWriter


@dataclass
class Outcome:
    status: str          # PASS | BLOCKED_GOVERNANCE | BLOCKED_INFRA | BLOCKED_GATE
    thread_id: Optional[str]
    gate: Optional[GateResult]
    detail: str


def _retry_prompt(feedback: str) -> str:
    return ("The gate is still failing. Output:\n\n" + feedback +
            "\n\nFix only files in your working directory so the gate passes. "
            "Reply with a one-line confirmation when done.")


def run(descriptor, writer: Optional[RunstateWriter] = None,
        log_path=None) -> Outcome:
    gov = governance.load()
    decision = gov.check(descriptor)

    if writer is None:
        writer = RunstateWriter(config.RUNSTATE_PATH, run_id=f"run-{descriptor.id}",
                                current_sprint="003-runtime")
    writer.queue(descriptor)

    # --- governance enforcement: always-human is refused, never dispatched ---
    if not decision.allowed:
        print(f"[runtime] REFUSED (governance): {decision.reason}")
        writer.escalated(decision.reason)
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
        result = client.codex(
            prompt=descriptor.goal, cwd=str(worker_cwd), sandbox="workspace-write",
            approval_policy="never", model=model, timeout=descriptor.timeout_seconds,
        )
        thread_id = result.thread_id or ""
        writer.dispatched(thread_id, config.DEFAULT_WORKER_PROVIDER, model)
        print(f"[runtime] threadId={thread_id} ok={result.ok} is_error={result.is_error}")

        # infra failure: record the gate for the record, escalate, no retry
        if result.is_error or result.timed_out:
            g = _gate()
            writer.gate_recorded(g.passed, g.summary, g.returncode)
            writer.escalated(f"worker infra failure: {result.text[:160]}")
            return Outcome("BLOCKED_INFRA", thread_id, g, "worker infra failure")

        g = _gate()
        writer.gate_recorded(g.passed, g.summary, g.returncode)
        print(f"[runtime] gate(1): passed={g.passed} :: {g.summary}")
        if g.passed:
            writer.done()
            return Outcome("PASS", thread_id, g, "gate green (first attempt)")

        # gate-red: codex-reply retries up to the descriptor's budget
        for attempt in range(1, descriptor.retry_budget + 1):
            print(f"[runtime] gate red -> codex-reply retry {attempt}/{descriptor.retry_budget}")
            reply = client.codex_reply(thread_id, _retry_prompt(g.feedback),
                                       timeout=descriptor.timeout_seconds)
            if reply.is_error or reply.timed_out:
                writer.escalated(f"retry infra failure: {reply.text[:160]}")
                return Outcome("BLOCKED_INFRA", thread_id, g, "retry infra failure")
            g = _gate()
            writer.gate_recorded(g.passed, g.summary, g.returncode)
            print(f"[runtime] gate(retry {attempt}): passed={g.passed} :: {g.summary}")
            if g.passed:
                writer.done()
                return Outcome("PASS", thread_id, g, f"gate green after {attempt} retry")

        writer.escalated(f"gate failing after {descriptor.retry_budget} retries: {g.summary}")
        return Outcome("BLOCKED_GATE", thread_id, g, "gate red after retries")


def main(argv) -> int:
    if len(argv) < 2:
        print("usage: python -m runtime.runtime <descriptor.json>")
        return 2
    d = descriptor_mod.load(argv[1])
    log_path = config.MAGRATHEA_DIR / "runtime.jsonl"
    outcome = run(d, log_path=log_path)
    print(f"\n[runtime] OUTCOME: {outcome.status} :: {outcome.detail}")
    return 0 if outcome.status == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
