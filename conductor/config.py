"""Conductor configuration — single source of truth for paths and worker policy.

Everything here is intentionally explicit so the orchestrator is reproducible and
so an operator can flip the worker model in exactly one place once the model
availability blocker (see STATUS.md) is resolved.
"""
from __future__ import annotations

import os
from pathlib import Path

# --- Paths (everything stays under the project root) -------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
GATE_DIR = PROJECT_ROOT / "gate"
TEST_FILE = GATE_DIR / "test_purl.py"
TARGET_MODULE = GATE_DIR / "purl.py"          # the worker must create this
LOGS_DIR = PROJECT_ROOT / "logs"
VENV_PYTHON = PROJECT_ROOT / ".venv" / "bin" / "python"

# --- Worker (Codex) control surface ------------------------------------------
# The default control surface is the Codex MCP stdio server. The worker session
# is sandboxed to GATE_DIR so it can only read the test and write the impl.
CODEX_MCP_CMD = ["codex", "mcp-server"]
WORKER_CWD = str(GATE_DIR)
WORKER_SANDBOX = "workspace-write"   # writable root == WORKER_CWD; network off
WORKER_APPROVAL_POLICY = "never"     # sandbox is the boundary; nobody is watching

# Worker model.
#   None  -> let Codex use its configured default.
#   str   -> per-session override passed to the `codex` MCP tool.
# Default is 'gpt-5.5', which drives once Codex CLI is current (>= 0.140.0).
# History: under Codex CLI 0.122.0 the ChatGPT account could not drive 'gpt-5.5'
# ("requires a newer version of Codex") and every other cloud model was "not
# supported when using Codex with a ChatGPT account"; that block is gone on the
# updated CLI (verified 2026-06-16, threadId 019ed170-...). Override per-run with
# CONDUCTOR_WORKER_MODEL (the smoketest uses this to inject a bogus model id).
WORKER_MODEL = os.environ.get("CONDUCTOR_WORKER_MODEL") or "gpt-5.5"

# Extra Codex config overrides for the worker session. We disable the user's
# global MCP servers — a pure-function task needs none, and it shrinks the
# worker's prompt and attack surface.
WORKER_CONFIG = {"mcp_servers": {}}

# Timeouts (seconds)
INITIALIZE_TIMEOUT = 30
# A full worker turn (MCP startup + reasoning + file write + self-check). A
# healthy session starts its MCP servers in ~4s and a trivial turn finishes in
# ~7s, so 420s is generous for the real task while still failing fast if a
# global MCP server hangs on startup (a transient failure we have observed).
DISPATCH_TIMEOUT = 420

# --- NTFY reporting ----------------------------------------------------------
NTFY_BASE_URL = os.environ.get("CONDUCTOR_NTFY_URL", "https://ntfy.sh")
NTFY_TOPIC = os.environ.get("CONDUCTOR_NTFY_TOPIC", "Mahdi-Dev")
