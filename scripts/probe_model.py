#!/usr/bin/env python3
"""Find a model that works with this Codex CLI version (default gpt-5.5 is too new).
Tries candidate models in order with a trivial read-only prompt; reports the first
that returns a non-error result. Also disables worker MCP servers for speed/safety.
"""
import json
import subprocess
import threading
import queue
import sys

CANDIDATES = ["gpt-5.2-codex", "gpt-5.2", "gpt-5.1-codex", "gpt-5-codex", "gpt-5.1", "gpt-5"]


def try_model(model):
    proc = subprocess.Popen(
        ["codex", "mcp-server"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True, bufsize=1,
    )
    out_q: "queue.Queue" = queue.Queue()

    def reader():
        for line in proc.stdout:
            out_q.put(line)
        out_q.put(None)
    threading.Thread(target=reader, daemon=True).start()

    def send(obj):
        proc.stdin.write(json.dumps(obj) + "\n"); proc.stdin.flush()

    def recv(timeout=120):
        try:
            line = out_q.get(timeout=timeout)
        except queue.Empty:
            return "TIMEOUT"
        return "EOF" if line is None else json.loads(line)

    send({"jsonrpc": "2.0", "id": 1, "method": "initialize",
          "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                     "clientInfo": {"name": "conductor-probe", "version": "0.0.1"}}})
    while True:
        m = recv()
        if isinstance(m, dict) and m.get("id") == 1:
            break
        if m in ("EOF", "TIMEOUT"):
            return ("init-failed", m, None)
    send({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})

    send({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
          "params": {"name": "codex", "arguments": {
              "prompt": "Respond with exactly the single word: READY. Do not run any commands or write any files.",
              "sandbox": "read-only",
              "approval-policy": "never",
              "model": model,
              "cwd": "/Users/mhedhli/dev/conductor",
              "config": {"mcp_servers": {}},
          }}})

    thread_id = None
    err_msg = None
    while True:
        m = recv(timeout=180)
        if m in ("EOF", "TIMEOUT"):
            res = ("stream-end", m, thread_id)
            break
        if isinstance(m, dict) and m.get("method") == "codex/event":
            p = m.get("params", {})
            tid = p.get("_meta", {}).get("threadId")
            if tid:
                thread_id = tid
            msg = p.get("msg", {})
            if msg.get("type") == "error":
                err_msg = msg.get("message")
        elif isinstance(m, dict) and m.get("id") == 2:
            r = m.get("result", {})
            is_err = r.get("isError", False)
            text = r.get("structuredContent", {}).get("content", "")
            tid = r.get("structuredContent", {}).get("threadId", thread_id)
            res = ("error" if is_err else "ok", text[:200], tid)
            break

    proc.terminate()
    try:
        proc.wait(timeout=5)
    except Exception:
        proc.kill()
    return res


def main():
    only = sys.argv[1:] if len(sys.argv) > 1 else CANDIDATES
    for model in only:
        print(f"\n>>> trying model: {model}")
        status, detail, tid = try_model(model)
        print(f"    status={status} threadId={tid}")
        print(f"    detail={detail}")
        if status == "ok":
            print(f"\n*** WORKING MODEL: {model} ***")
            return
    print("\n!!! no candidate model worked")


if __name__ == "__main__":
    main()
