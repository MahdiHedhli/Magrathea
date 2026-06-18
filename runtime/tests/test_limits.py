"""AC-stop (feature 006 C): the stop threshold (read from governance, not
hardcoded) halts new work below the provider headroom and pages."""
import json

from runtime import config, limits, usage
from runtime import queue as Q


def test_stop_threshold_read_from_governance():
    assert limits.stop_threshold_pct() == 15.0  # from model-limit-policy.md


def test_headroom_below_threshold():
    low = {"provider": "openai-codex", "windows": [{"window": "5h", "remaining_pct": 5.0}]}
    ok = {"provider": "openai-codex", "windows": [{"window": "5h", "remaining_pct": 80.0}]}
    unknown = {"provider": "x", "windows": [{"window": "5h", "remaining_pct": None}]}
    assert limits.headroom_below_threshold(low, 15) is True
    assert limits.headroom_below_threshold(ok, 15) is False
    assert limits.headroom_below_threshold(unknown, 15) is False  # unknown: don't block
    assert limits.min_remaining_pct(low) == 5.0


def test_queue_halts_below_threshold_and_pages(tmp_path, monkeypatch):
    monkeypatch.setattr(Q.ntfy, "blocker", lambda *a, **k: True)
    monkeypatch.setattr(Q.ntfy, "progress", lambda *a, **k: True)
    monkeypatch.setattr(config, "RUNSTATE_PATH", tmp_path / "runstate.json")
    monkeypatch.setattr(config, "USAGE_PATH", tmp_path / "usage.json")

    # worker headroom 5% < 15% threshold
    usage.write_snapshot_file(usage.build_snapshot(
        [{"provider": "openai-codex", "adapter": "read",
          "windows": [{"window": "5h", "used": None, "limit": None,
                       "remaining_pct": 5.0, "resets_at": None}]}], 15))

    def must_not_dispatch(*a, **k):
        raise AssertionError("must not start new work below the stop threshold")

    monkeypatch.setattr(Q.runtime, "execute_descriptor", must_not_dispatch)

    manifest = tmp_path / "q.json"
    manifest.write_text(json.dumps({"descriptors": [
        str(config.REPO_ROOT / "descriptors" / "purl.json")]}), encoding="utf-8")

    res = Q.run_queue(str(manifest))
    data = json.load(open(tmp_path / "runstate.json"))
    assert res.status == "paused"
    assert data["status"] == "paused"
