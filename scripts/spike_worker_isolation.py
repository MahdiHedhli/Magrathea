#!/usr/bin/env python3
"""Worker-isolation spike. Probe whether a dedicated worker CODEX_HOME yields a
worker that loads ZERO inherited global MCP servers AND still completes a turn
(auth carried over via the copied auth.json).

Usage: spike_worker_isolation.py <CODEX_HOME>   (defaults to ~/.magrathea-worker-codex)
Prints: mcp_startup count, isError, final text. Stdlib only.
"""
import json
import os
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path

CODEX_HOME = sys.argv[1] if len(sys.argv) > 1 else str(Path.home() / ".magrathea-worker-codex")


def main():
    env = dict(os.environ)
    env["CODEX_HOME"] = CODEX_HOME
    cmd = ["codex", "mcp-server"] + sys.argv[2:]  # extra args, e.g. --disable apps
    proc = subprocess.Popen(
        cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True, bufsize=1, env=env,
    )
    q: "queue.Queue" = queue.Queue()

    def rd():
        for line in proc.stdout:
            q.put(line)
        q.put(None)
    threading.Thread(target=rd, daemon=True).start()

    def snd(o):
        proc.stdin.write(json.dumps(o) + "\n"); proc.stdin.flush()

    def rcv(t=120):
        try:
            line = q.get(timeout=t)
        except queue.Empty:
            return "TIMEOUT"
        return "EOF" if line is None else json.loads(line)

    snd({"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                    "clientInfo": {"name": "spike", "version": "0"}}})
    while True:
        m = rcv()
        if isinstance(m, dict) and m.get("id") == 1:
            break
        if m in ("EOF", "TIMEOUT"):
            print("init failed:", m); return
    snd({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})

    t0 = time.time()
    snd({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {
        "name": "codex", "arguments": {
            "prompt": "Reply with exactly one word: ISOLATED",
            "cwd": str(Path.home() / "dev" / "conductor" / "gate"),
            "sandbox": "workspace-write", "approval-policy": "never",
            "model": "gpt-5.5"}}})
    mcp_servers = set()
    while True:
        m = rcv(180)
        if m in ("EOF", "TIMEOUT"):
            print(f"STREAM_{m} after {time.time()-t0:.1f}s"); break
        if isinstance(m, dict) and m.get("method") == "codex/event":
            msg = m.get("params", {}).get("msg", {})
            if msg.get("type") in ("mcp_startup_update", "mcp_startup_complete"):
                if msg.get("server"):
                    mcp_servers.add(msg.get("server"))
        if isinstance(m, dict) and m.get("id") == 2:
            r = m.get("result", {}); sc = r.get("structuredContent", {})
            text = (sc.get("content") or r.get("content", [{}])[0].get("text", ""))
            print(f"RESULT: isError={r.get('isError')} elapsed={time.time()-t0:.1f}s text={text[:80]!r}")
            break
    print(f"INHERITED MCP SERVERS: {len(mcp_servers)} -> {sorted(mcp_servers)}")
    print("ISOLATION:", "CLEAN (0 servers)" if not mcp_servers else f"LEAKED {len(mcp_servers)}")
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except Exception:
        proc.kill()


if __name__ == "__main__":
    main()
