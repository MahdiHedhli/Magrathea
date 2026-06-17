"""AC-isolation: the worker is dispatched against a dedicated CODEX_HOME with no
operator [mcp_servers]; the dispatch carries that home, not the operator's.

This is the deterministic proxy for the spike (SPIKE.md): we verify the worker
home is built clean and the dispatch env points at it. The live "0 inherited
servers" result is recorded in SPIKE.md / PROOF.md (a real turn is not run in the
fast gate).
"""
import os

from runtime import config, worker_home

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def test_worker_home_is_outside_the_repo():
    home = config.WORKER_CODEX_HOME
    assert REPO_ROOT not in str(home), "worker CODEX_HOME must live outside the repo"


def test_ensure_builds_a_clean_home_with_no_operator_mcp():
    home = worker_home.ensure()
    assert home.exists()
    cfg = (home / "config.toml").read_text(encoding="utf-8")
    assert "[mcp_servers" not in cfg, "worker config must define no MCP servers"


def test_dispatch_env_carries_worker_home_not_operator():
    env = worker_home.codex_env()
    assert env["CODEX_HOME"] == str(config.WORKER_CODEX_HOME)
    assert env["CODEX_HOME"] != str(config.OPERATOR_CODEX_HOME)
