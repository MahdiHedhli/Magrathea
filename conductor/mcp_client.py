"""Codex MCP stdio client — the Conductor's control surface over the worker.

This is the orchestrator's default and primary way to drive Codex: it launches
`codex mcp-server`, performs the MCP initialize handshake, and calls the server's
two tools:

  * ``codex``       — start a session (returns a threadId)
  * ``codex-reply`` — continue a session by threadId

The MCP stdio transport is newline-delimited JSON-RPC 2.0. Codex streams its
work as ``codex/event`` notifications while a ``tools/call`` is in flight; the
threadId is present on every notification's ``params._meta.threadId`` as well as
in the final tool result's ``structuredContent.threadId``. The final agent text
and an ``isError`` flag come back in the tool result.

Stdlib only — no third-party dependencies.
"""
from __future__ import annotations

import json
import queue
import subprocess
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional


@dataclass
class CodexResult:
    """Outcome of one ``codex`` / ``codex-reply`` tool call."""

    thread_id: Optional[str]
    is_error: bool
    text: str                      # final agent message, or the error payload
    raw_result: dict = field(default_factory=dict)
    events: list = field(default_factory=list)        # list of {type, msg}
    error_events: list = field(default_factory=list)  # msg dicts of type "error"
    timed_out: bool = False

    @property
    def ok(self) -> bool:
        return (not self.is_error) and (not self.timed_out)


class CodexMCPError(RuntimeError):
    pass


class CodexMCPClient:
    """A minimal, robust MCP stdio client specialized for ``codex mcp-server``."""

    def __init__(self, cmd, log_path: Optional[Path] = None):
        self.cmd = list(cmd)
        self.log_path = Path(log_path) if log_path else None
        self._proc: Optional[subprocess.Popen] = None
        self._q: "queue.Queue" = queue.Queue()
        self._next_id = 0
        self._log_fh = None
        self._readers: list[threading.Thread] = []

    # -- lifecycle ------------------------------------------------------------
    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *exc):
        self.close()

    def start(self):
        if self.log_path:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            self._log_fh = self.log_path.open("a", encoding="utf-8")
        self._proc = subprocess.Popen(
            self.cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        t_out = threading.Thread(target=self._read_stdout, daemon=True)
        t_err = threading.Thread(target=self._drain_stderr, daemon=True)
        t_out.start()
        t_err.start()
        self._readers = [t_out, t_err]

    def close(self):
        if self._proc and self._proc.poll() is None:
            try:
                self._proc.terminate()
                self._proc.wait(timeout=5)
            except Exception:
                self._proc.kill()
        if self._log_fh:
            self._log_fh.close()
            self._log_fh = None

    # -- low-level io ---------------------------------------------------------
    def _log(self, direction: str, obj):
        if self._log_fh:
            rec = {"t": time.time(), "dir": direction, "msg": obj}
            self._log_fh.write(json.dumps(rec) + "\n")
            self._log_fh.flush()

    def _read_stdout(self):
        assert self._proc and self._proc.stdout
        for line in self._proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                self._log("stdout-nonjson", line)
                continue
            self._log("recv", obj)
            self._q.put(obj)
        self._q.put(None)  # EOF sentinel

    def _drain_stderr(self):
        assert self._proc and self._proc.stderr
        for line in self._proc.stderr:
            self._log("stderr", line.rstrip("\n"))

    def _send(self, obj):
        assert self._proc and self._proc.stdin
        self._log("send", obj)
        self._proc.stdin.write(json.dumps(obj) + "\n")
        self._proc.stdin.flush()

    def _request_id(self) -> int:
        self._next_id += 1
        return self._next_id

    def _recv(self, timeout):
        try:
            obj = self._q.get(timeout=timeout)
        except queue.Empty:
            return "TIMEOUT"
        return "EOF" if obj is None else obj

    # -- handshake ------------------------------------------------------------
    def initialize(self, timeout: int = 30):
        rid = self._request_id()
        self._send({
            "jsonrpc": "2.0", "id": rid, "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "conductor", "version": "0.1.0"},
            },
        })
        deadline = time.time() + timeout
        while time.time() < deadline:
            msg = self._recv(timeout=deadline - time.time())
            if msg in ("EOF", "TIMEOUT"):
                raise CodexMCPError(f"initialize failed: {msg}")
            if isinstance(msg, dict) and msg.get("id") == rid:
                if "error" in msg:
                    raise CodexMCPError(f"initialize error: {msg['error']}")
                self._send({"jsonrpc": "2.0",
                            "method": "notifications/initialized", "params": {}})
                return msg.get("result", {})
        raise CodexMCPError("initialize timed out")

    def list_tools(self, timeout: int = 30) -> list:
        rid = self._request_id()
        self._send({"jsonrpc": "2.0", "id": rid,
                    "method": "tools/list", "params": {}})
        deadline = time.time() + timeout
        while time.time() < deadline:
            msg = self._recv(timeout=deadline - time.time())
            if msg in ("EOF", "TIMEOUT"):
                raise CodexMCPError(f"tools/list failed: {msg}")
            if isinstance(msg, dict) and msg.get("id") == rid:
                return msg.get("result", {}).get("tools", [])
        raise CodexMCPError("tools/list timed out")

    # -- tool calls -----------------------------------------------------------
    def _call_tool(self, name: str, arguments: dict, timeout: int,
                   on_event: Optional[Callable] = None) -> CodexResult:
        rid = self._request_id()
        self._send({"jsonrpc": "2.0", "id": rid, "method": "tools/call",
                    "params": {"name": name, "arguments": arguments}})

        thread_id: Optional[str] = None
        events: list = []
        error_events: list = []
        deadline = time.time() + timeout

        while True:
            remaining = deadline - time.time()
            if remaining <= 0:
                return CodexResult(thread_id, True,
                                   "tool call timed out", {}, events,
                                   error_events, timed_out=True)
            msg = self._recv(timeout=remaining)
            if msg == "TIMEOUT":
                return CodexResult(thread_id, True,
                                   "tool call timed out", {}, events,
                                   error_events, timed_out=True)
            if msg == "EOF":
                return CodexResult(thread_id, True,
                                   "codex mcp-server closed the stream", {},
                                   events, error_events)

            # Notification (streamed event) — no id, has method.
            if isinstance(msg, dict) and msg.get("method") and "id" not in msg:
                if msg["method"] == "codex/event":
                    params = msg.get("params", {})
                    tid = params.get("_meta", {}).get("threadId")
                    if tid:
                        thread_id = tid
                    emsg = params.get("msg", {})
                    events.append(emsg)
                    if emsg.get("type") == "error":
                        error_events.append(emsg)
                    if on_event:
                        on_event(emsg, thread_id)
                continue

            # A request *from* the server (has id + method). With approval-policy
            # "never" we don't expect these; decline so nothing hangs.
            if isinstance(msg, dict) and msg.get("method") and "id" in msg:
                self._send({"jsonrpc": "2.0", "id": msg["id"],
                            "error": {"code": -32601,
                                      "message": "client declines server requests"}})
                continue

            # The tool result for our call.
            if isinstance(msg, dict) and msg.get("id") == rid:
                if "error" in msg:
                    return CodexResult(thread_id, True,
                                       json.dumps(msg["error"]), msg,
                                       events, error_events)
                result = msg.get("result", {})
                sc = result.get("structuredContent", {}) or {}
                tid = sc.get("threadId") or thread_id
                text = sc.get("content")
                if text is None:
                    content = result.get("content", [])
                    text = content[0].get("text", "") if content else ""
                return CodexResult(tid, bool(result.get("isError", False)),
                                   text or "", result, events, error_events)

    def codex(self, prompt: str, cwd: str, sandbox: str,
              approval_policy: str = "never", model: Optional[str] = None,
              config: Optional[dict] = None, timeout: int = 900,
              on_event: Optional[Callable] = None) -> CodexResult:
        args = {
            "prompt": prompt,
            "cwd": cwd,
            "sandbox": sandbox,
            "approval-policy": approval_policy,
        }
        if model:
            args["model"] = model
        if config:
            args["config"] = config
        return self._call_tool("codex", args, timeout, on_event)

    def codex_reply(self, thread_id: str, prompt: str, timeout: int = 900,
                    on_event: Optional[Callable] = None) -> CodexResult:
        args = {"threadId": thread_id, "prompt": prompt}
        return self._call_tool("codex-reply", args, timeout, on_event)
