"""AC-auth (feature 004): the worker authenticates via a single source with no
standing divergent copy. The worker auth.json is a SYMLINK to the operator's
source, not a copy."""
import os

from runtime import config, worker_home


def test_worker_auth_is_a_symlink_to_the_single_source():
    if not (config.OPERATOR_CODEX_HOME / "auth.json").exists():
        import pytest
        pytest.skip("no operator auth.json on this machine")
    worker_home.ensure()
    dst = config.WORKER_CODEX_HOME / "auth.json"
    assert dst.is_symlink(), "worker auth must be a symlink, not a copy"
    assert worker_home.auth_is_symlink()
    # resolves to the single source — no standing divergent copy
    assert os.path.realpath(dst) == os.path.realpath(
        config.OPERATOR_CODEX_HOME / "auth.json")


def test_ensure_reasserts_the_symlink_when_replaced_by_a_copy(tmp_path):
    # simulate a prior turn's atomic-rename refresh that replaced the link
    if not (config.OPERATOR_CODEX_HOME / "auth.json").exists():
        import pytest
        pytest.skip("no operator auth.json on this machine")
    worker_home.ensure()
    dst = config.WORKER_CODEX_HOME / "auth.json"
    dst.unlink()
    dst.write_text("{}", encoding="utf-8")     # a stale regular-file copy
    assert not dst.is_symlink()
    worker_home.ensure()                        # before next dispatch
    assert dst.is_symlink(), "ensure() must self-heal the symlink"
