#!/usr/bin/env python3
"""Reattach spike (feature 004 item 2): does MCP codex-reply resume a PERSISTED
thread across a runtime restart (a fresh mcp-server process) in the isolated
worker home? Also exercises the new symlink auth (a turn must complete).

Client A opens a session and stores a codeword, then closes (the "restart").
Client B is a brand-new mcp-server process (same worker CODEX_HOME) that resumes
the thread by id via codex-reply and must recall the codeword.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from conductor.mcp_client import CodexMCPClient
from runtime import config, worker_home

CODEWORD = "REATTACH-42"
GATE_DIR = str(config.REPO_ROOT / "gate")


def main():
    worker_home.ensure()
    print("auth is symlink to source:", worker_home.auth_is_symlink())
    env = worker_home.codex_env()

    # --- Client A: open a session, store the codeword, then "restart" --------
    with CodexMCPClient(config.CODEX_MCP_CMD, env=env) as a:
        a.initialize(timeout=30)
        r = a.codex(
            prompt=f"Remember this codeword for later: {CODEWORD}. Reply with exactly: STORED.",
            cwd=GATE_DIR, sandbox="read-only", approval_policy="never",
            model="gpt-5.5", timeout=120,
        )
        thread_id = r.thread_id
        print(f"A: threadId={thread_id} ok={r.ok} text={(r.text or '')[:40]!r}")
    print("auth still symlink after a turn:", worker_home.auth_is_symlink())

    if not thread_id:
        print("SPIKE FAIL: no threadId"); return

    # --- Client B: brand-new process, resume the SAME thread by id -----------
    with CodexMCPClient(config.CODEX_MCP_CMD, env=env) as b:
        b.initialize(timeout=30)
        r2 = b.codex_reply(
            thread_id,
            "What was the codeword I asked you to remember? Reply with ONLY the codeword.",
            timeout=120,
        )
        recalled = CODEWORD in (r2.text or "")
        # did B open a NEW session, or resume the same thread?
        same_thread = (r2.thread_id == thread_id)
        print(f"B: replied={ (r2.text or '')[:60]!r } thread_match={same_thread} "
              f"is_error={r2.is_error}")
        print("REATTACH:", "WORKS (codeword recalled, same thread)" if (recalled and same_thread)
              else f"recalled={recalled} same_thread={same_thread}")


if __name__ == "__main__":
    main()
