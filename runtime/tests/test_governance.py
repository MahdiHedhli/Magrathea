"""AC-governance: a descriptor whose class is always-human is refused and
escalated, never dispatched. Ordinary classes are allowed with the policy model.
"""
import os

from runtime import descriptor, governance

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _d(tmp_path, task_class):
    p = tmp_path / "d.json"
    p.write_text('{"id":"x","goal":"g","task_class":"%s",'
                 '"working_dir":"gate","gate_command":"true"}' % task_class,
                 encoding="utf-8")
    return descriptor.load(str(p))


def test_always_human_classes_parsed_from_governance():
    g = governance.load()
    keys = " ".join(g.always_human).lower()
    assert "security" in keys
    assert "delete" in keys
    assert "history" in keys


def test_git_history_class_is_refused(tmp_path):
    g = governance.load()
    d = _d(tmp_path, "git-history")
    decision = g.check(d)
    assert decision.allowed is False
    assert "human" in decision.reason.lower() or "escalat" in decision.reason.lower()


def test_security_sensitive_is_refused(tmp_path):
    g = governance.load()
    decision = g.check(_d(tmp_path, "security-sensitive"))
    assert decision.allowed is False


def test_bulk_delete_is_refused(tmp_path):
    g = governance.load()
    decision = g.check(_d(tmp_path, "bulk-delete"))
    assert decision.allowed is False


def test_feature_class_is_allowed_with_default_model(tmp_path):
    g = governance.load()
    decision = g.check(_d(tmp_path, "feature"))
    assert decision.allowed is True
    assert decision.model  # a concrete worker model is chosen (policy default)
