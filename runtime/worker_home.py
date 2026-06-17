"""Worker isolation (the spike, productionized).

Build a dedicated Codex home outside the repo with the operator's login copied in
and NO MCP servers, so a dispatched worker inherits none of the operator's global
MCP config. Never creates/enters/transmits/regenerates a credential — it only
copies an existing auth.json.
"""
from __future__ import annotations

import os
from pathlib import Path

from runtime import config

_CLEAN_CONFIG = """\
# Magrathea worker Codex home — generated, do not edit by hand.
# Intentionally defines NO MCP servers, so the worker inherits none of the
# operator's global Codex MCP config (see specs/003-runtime/SPIKE.md).
# Auth is the operator's existing login, single-sourced via a symlink to
# CODEX_HOME/auth.json (feature 004 — see docs/HARDENING.md).
"""


class WorkerHomeError(RuntimeError):
    pass


def _source_auth() -> Path:
    return config.OPERATOR_CODEX_HOME / "auth.json"


def ensure() -> Path:
    """Create/refresh the worker CODEX_HOME and return its path.

    Durable auth (feature 004): the worker's auth.json is a SYMLINK to the
    operator's single source auth.json — no standing divergent copy, always
    current on read. The link is re-asserted on every call (before every
    dispatch), so it self-heals if a prior turn's token refresh replaced it via
    atomic rename. Never creates/enters/regenerates a credential.
    """
    home = config.WORKER_CODEX_HOME
    home.mkdir(parents=True, exist_ok=True)
    (home / "config.toml").write_text(_CLEAN_CONFIG, encoding="utf-8")

    src_auth = _source_auth()
    dst_auth = home / "auth.json"
    if src_auth.exists():
        if dst_auth.exists() or dst_auth.is_symlink():
            dst_auth.unlink()
        dst_auth.symlink_to(src_auth)            # single source, zero copy
    elif not (dst_auth.exists() or dst_auth.is_symlink()):
        raise WorkerHomeError(
            f"no reusable login: {src_auth} not found and {dst_auth} absent. "
            "Refusing to create a credential."
        )
    return home


def codex_env() -> dict:
    """Environment for launching `codex mcp-server` as the isolated worker."""
    env = dict(os.environ)
    env["CODEX_HOME"] = str(config.WORKER_CODEX_HOME)
    return env


def auth_is_symlink() -> bool:
    """True iff the worker auth is a symlink to the single source (no copy)."""
    dst = config.WORKER_CODEX_HOME / "auth.json"
    return dst.is_symlink() and dst.resolve() == _source_auth().resolve()


def config_has_mcp_servers() -> bool:
    cfg = config.WORKER_CODEX_HOME / "config.toml"
    if not cfg.exists():
        return False
    return "[mcp_servers" in cfg.read_text(encoding="utf-8")
