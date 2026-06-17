"""Worker isolation (the spike, productionized).

Build a dedicated Codex home outside the repo with the operator's login copied in
and NO MCP servers, so a dispatched worker inherits none of the operator's global
MCP config. Never creates/enters/transmits/regenerates a credential — it only
copies an existing auth.json.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from runtime import config

_CLEAN_CONFIG = """\
# Magrathea worker Codex home — generated, do not edit by hand.
# Intentionally defines NO MCP servers, so the worker inherits none of the
# operator's global Codex MCP config (see specs/003-runtime/SPIKE.md).
# Auth is the operator's existing login, copied in (never created here).
"""


class WorkerHomeError(RuntimeError):
    pass


def ensure() -> Path:
    """Create/refresh the worker CODEX_HOME and return its path.

    Copies the operator's auth.json if present. Raises if no login can be reused
    (we never create one).
    """
    home = config.WORKER_CODEX_HOME
    home.mkdir(parents=True, exist_ok=True)
    (home / "config.toml").write_text(_CLEAN_CONFIG, encoding="utf-8")

    src_auth = config.OPERATOR_CODEX_HOME / "auth.json"
    dst_auth = home / "auth.json"
    if src_auth.exists():
        shutil.copy2(src_auth, dst_auth)
        dst_auth.chmod(0o600)
    elif not dst_auth.exists():
        raise WorkerHomeError(
            f"no reusable login: {src_auth} not found and {dst_auth} absent. "
            "Refusing to create a credential."
        )
    return home


def codex_env() -> dict:
    """Environment for launching `codex mcp-server` as the isolated worker."""
    import os
    env = dict(os.environ)
    env["CODEX_HOME"] = str(config.WORKER_CODEX_HOME)
    return env


def config_has_mcp_servers() -> bool:
    cfg = config.WORKER_CODEX_HOME / "config.toml"
    if not cfg.exists():
        return False
    return "[mcp_servers" in cfg.read_text(encoding="utf-8")
