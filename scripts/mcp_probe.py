#!/usr/bin/env python3
"""Phase 0 probe: confirm `codex mcp-server` answers an MCP initialize over stdio
and list the tools it exposes (we expect `codex` and `codex-reply`).

Stdlib only. MCP stdio transport = newline-delimited JSON-RPC messages.
"""
import json
import subprocess
import sys
import threading
import queue

CMD = ["codex", "mcp-server"]


def main():
    proc = subprocess.Popen(
        CMD,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    out_q: "queue.Queue[str]" = queue.Queue()

    def reader():
        for line in proc.stdout:
            out_q.put(line)
        out_q.put(None)  # EOF sentinel

    t = threading.Thread(target=reader, daemon=True)
    t.start()

    def send(obj):
        line = json.dumps(obj) + "\n"
        proc.stdin.write(line)
        proc.stdin.flush()

    def recv(timeout=20):
        try:
            line = out_q.get(timeout=timeout)
        except queue.Empty:
            return None
        if line is None:
            return "EOF"
        return json.loads(line)

    # 1. initialize
    send({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "conductor-probe", "version": "0.0.1"},
        },
    })

    init_resp = None
    # Skip any notifications/log lines until we see id==1
    for _ in range(50):
        msg = recv()
        if msg in (None, "EOF"):
            break
        if isinstance(msg, dict) and msg.get("id") == 1:
            init_resp = msg
            break
    print("INITIALIZE RESPONSE:")
    print(json.dumps(init_resp, indent=2)[:1500])

    if not init_resp:
        # dump stderr for diagnosis
        proc.terminate()
        try:
            err = proc.stderr.read()
        except Exception:
            err = ""
        print("NO INITIALIZE RESPONSE. STDERR:")
        print(err[:2000])
        sys.exit(2)

    # 2. initialized notification
    send({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})

    # 3. tools/list
    send({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
    tools_resp = None
    for _ in range(50):
        msg = recv()
        if msg in (None, "EOF"):
            break
        if isinstance(msg, dict) and msg.get("id") == 2:
            tools_resp = msg
            break

    print("\nTOOLS/LIST RESPONSE (names + schemas):")
    if tools_resp and "result" in tools_resp:
        tools = tools_resp["result"].get("tools", [])
        for tdef in tools:
            print(f"\n=== TOOL: {tdef.get('name')} ===")
            print("description:", (tdef.get("description") or "")[:300])
            print("inputSchema:", json.dumps(tdef.get("inputSchema", {}), indent=2)[:2000])
    else:
        print(json.dumps(tools_resp, indent=2)[:2000])

    proc.terminate()
    try:
        proc.wait(timeout=5)
    except Exception:
        proc.kill()


if __name__ == "__main__":
    main()
