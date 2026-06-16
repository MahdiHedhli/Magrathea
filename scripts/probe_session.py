#!/usr/bin/env python3
"""Phase 0/1 probe: make ONE trivial `codex` tool call and dump every JSON-RPC
message (notifications + final result) so we learn the event format and exactly
where the threadId is reported. Read-only sandbox, no commands.
"""
import json
import subprocess
import threading
import queue

CMD = ["codex", "mcp-server"]


def main():
    proc = subprocess.Popen(
        CMD, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True, bufsize=1,
    )
    out_q: "queue.Queue" = queue.Queue()

    def reader():
        for line in proc.stdout:
            out_q.put(line)
        out_q.put(None)
    threading.Thread(target=reader, daemon=True).start()

    def send(obj):
        proc.stdin.write(json.dumps(obj) + "\n")
        proc.stdin.flush()

    def recv(timeout=120):
        try:
            line = out_q.get(timeout=timeout)
        except queue.Empty:
            return "TIMEOUT"
        if line is None:
            return "EOF"
        return json.loads(line)

    send({"jsonrpc": "2.0", "id": 1, "method": "initialize",
          "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                     "clientInfo": {"name": "conductor-probe", "version": "0.0.1"}}})
    while True:
        m = recv()
        if isinstance(m, dict) and m.get("id") == 1:
            break
        if m in ("EOF", "TIMEOUT"):
            print("init failed:", m); return
    send({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})

    # trivial read-only session
    send({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
          "params": {"name": "codex", "arguments": {
              "prompt": "Respond with exactly the single word: READY. Do not run any commands or write any files.",
              "sandbox": "read-only",
              "approval-policy": "never",
              "cwd": "/Users/mhedhli/dev/conductor",
          }}})

    count = 0
    while True:
        m = recv(timeout=180)
        if m in ("EOF", "TIMEOUT"):
            print("STREAM END:", m)
            break
        count += 1
        if isinstance(m, dict) and m.get("method"):  # notification
            method = m.get("method")
            params = m.get("params", {})
            # print compact summary of each notification
            blob = json.dumps(params)
            print(f"[{count}] NOTIF method={method} :: {blob[:600]}")
        else:  # response
            print(f"[{count}] RESPONSE :: {json.dumps(m)[:1500]}")
            if isinstance(m, dict) and m.get("id") == 2:
                print("---- final result received, stopping ----")
                break

    proc.terminate()
    try:
        proc.wait(timeout=5)
    except Exception:
        proc.kill()


if __name__ == "__main__":
    main()
