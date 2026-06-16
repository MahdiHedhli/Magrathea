#!/usr/bin/env python3
"""Phase 1 demonstration: prove programmatic control of Codex over MCP stdio.

Success criterion (independent of which model the worker uses): the orchestrator
can launch `codex mcp-server`, complete the MCP initialize handshake, see the
`codex` and `codex-reply` tools, open a session via the `codex` tool, and read
back a threadId.

Run:  .venv/bin/python phase1_control_surface.py
"""
from __future__ import annotations

import sys

from conductor import config
from conductor.mcp_client import CodexMCPClient


def main() -> int:
    log_path = config.LOGS_DIR / "phase1.jsonl"
    print(f"[phase1] launching: {' '.join(config.CODEX_MCP_CMD)}")
    with CodexMCPClient(config.CODEX_MCP_CMD, log_path=log_path) as client:
        info = client.initialize(timeout=config.INITIALIZE_TIMEOUT)
        server = info.get("serverInfo", {})
        print(f"[phase1] initialize OK -> {server.get('name')} "
              f"v{server.get('version')} (protocol {info.get('protocolVersion')})")

        tools = {t["name"] for t in client.list_tools()}
        print(f"[phase1] tools advertised: {sorted(tools)}")
        for required in ("codex", "codex-reply"):
            if required not in tools:
                print(f"[phase1] FAIL: required tool '{required}' missing")
                return 2

        print("[phase1] opening a session via the codex() tool ...")
        captured = {"thread_id": None}

        def on_event(emsg, thread_id):
            captured["thread_id"] = thread_id
            t = emsg.get("type")
            if t == "session_configured":
                print(f"[phase1] session_configured: threadId={thread_id} "
                      f"model={emsg.get('model')} sandbox={emsg.get('sandbox_policy')}")

        result = client.codex(
            prompt="Reply with exactly the single word: READY.",
            cwd=config.WORKER_CWD,
            sandbox="read-only",                 # Phase 1 only opens a session
            approval_policy=config.WORKER_APPROVAL_POLICY,
            model=config.WORKER_MODEL,
            config=config.WORKER_CONFIG,
            timeout=120,
            on_event=on_event,
        )

        thread_id = result.thread_id or captured["thread_id"]
        print(f"[phase1] threadId captured: {thread_id}")
        print(f"[phase1] worker result: ok={result.ok} is_error={result.is_error}")
        if result.is_error:
            print(f"[phase1] worker text (truncated): {result.text[:300]}")

        if not thread_id:
            print("[phase1] FAIL: no threadId captured — control surface broken")
            return 3

        print("\n[phase1] PASS: control surface proven "
              "(handshake + tools + session + threadId).")
        if result.is_error:
            print("[phase1] NOTE: the session opened and a threadId was captured, "
                  "but the worker model returned an error (see STATUS.md blocker).")
        return 0


if __name__ == "__main__":
    sys.exit(main())
