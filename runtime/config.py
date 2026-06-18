"""Runtime configuration. Paths are derived (never absolute literals in source);
the worker CODEX_HOME lives outside the repo and is never committed.
"""
from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Worker isolation (SPIKE.md): a dedicated Codex home outside the repo.
WORKER_CODEX_HOME = Path(
    os.environ.get("MAGRATHEA_WORKER_CODEX_HOME")
    or (Path.home() / ".magrathea-worker-codex")
)
# The operator's default Codex home (whose global MCP config we must NOT inherit).
OPERATOR_CODEX_HOME = Path(os.environ.get("CODEX_HOME") or (Path.home() / ".codex"))

# Worker provider/model (policy default; floors come from governance).
DEFAULT_WORKER_PROVIDER = "openai-codex"
DEFAULT_WORKER_MODEL = "gpt-5.5"

# Runstate (gitignored runtime state) + the committed contract it must satisfy.
MAGRATHEA_DIR = REPO_ROOT / ".magrathea"
RUNSTATE_PATH = MAGRATHEA_DIR / "runstate.json"
USAGE_PATH = MAGRATHEA_DIR / "usage.json"   # usage adapter output (dashboard panel 6)
RUNSTATE_SCHEMA = (REPO_ROOT / "specs" / "002-dashboard" / "contracts"
                   / "runstate.schema.json")

# Governance the runtime enforces (read-only).
GOVERNANCE_DIR = REPO_ROOT / "governance"

CODEX_MCP_CMD = ["codex", "mcp-server"]
INITIALIZE_TIMEOUT = 30
