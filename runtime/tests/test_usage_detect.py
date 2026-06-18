"""AC-detect (feature 006 B): the detect adapter classifies a limit-hit as the
third outcome and tallies local spend; reset computation matches known windows;
the queue's limit-hit pause records the computed reset time."""
import json
from datetime import datetime, timezone

import jsonschema

from runtime import config, usage
from runtime import queue as Q

USAGE_SCHEMA = json.load(open(config.REPO_ROOT / "specs" / "002-dashboard"
                              / "contracts" / "usage.schema.json"))
RUNSTATE_SCHEMA = json.load(open(config.REPO_ROOT / "specs" / "002-dashboard"
                                 / "contracts" / "runstate.schema.json"))


def test_classify_limit_hit_is_the_third_outcome():
    a = usage.DetectAdapter()
    assert a.classify("Error 429: rate limit exceeded") == "limit-hit"
    assert a.classify("You have hit your usage limit for the week") == "limit-hit"
    assert a.classify("ModuleNotFoundError: no module named 'x'") == "other"
    assert a.classify("2 failed in 0.1s") == "other"


def test_local_spend_tally():
    a = usage.DetectAdapter()
    a.tally(1200)
    a.tally(800)
    assert a.spend_tokens == 2000 and a.turns == 2


def test_compute_reset_matches_known_windows():
    at = datetime(2026, 6, 17, 12, 0, 0, tzinfo=timezone.utc)
    assert usage.compute_reset(300, at) == "2026-06-17T17:00:00Z"      # +5h
    assert usage.compute_reset(10080, at) == "2026-06-24T12:00:00Z"    # +7 days


def test_detect_snapshot_validates_against_contract():
    snap = usage.build_snapshot([usage.DetectAdapter().snapshot()],
                                stop_threshold_pct=15)
    jsonschema.validate(snap, USAGE_SCHEMA)
    p = snap["providers"][0]
    assert p["adapter"] == "detect" and p["provider"] == "anthropic-claude"


def test_limit_reset_from_rate_limits():
    rl = {"primary": {"used_percent": 100, "window_minutes": 300,
                      "resets_at": 1781803156}}
    assert usage.limit_reset_from_rate_limits(rl)            # ISO string
    assert usage.limit_reset_from_rate_limits(None) is None


def test_queue_limit_hit_pauses_records_reset_and_stops(tmp_path, monkeypatch):
    monkeypatch.setattr(Q.ntfy, "blocker", lambda *a, **k: True)
    monkeypatch.setattr(Q.ntfy, "progress", lambda *a, **k: True)
    monkeypatch.setattr(config, "RUNSTATE_PATH", tmp_path / "runstate.json")
    RESET = "2026-06-17T17:00:00Z"

    def fake_exec(d, handle, log_path=None):
        handle.dispatched("019ed-x", "openai-codex", "gpt-5.5")
        return Q.runtime.Outcome("BLOCKED_LIMIT", "019ed-x", None,
                                 "limit-hit: rate limit", reset_time=RESET)

    monkeypatch.setattr(Q.runtime, "execute_descriptor", fake_exec)
    manifest = tmp_path / "q.json"
    manifest.write_text(json.dumps({"descriptors": [
        str(config.REPO_ROOT / "descriptors" / "purl.json"),
        str(config.REPO_ROOT / "descriptors" / "slug.json")]}), encoding="utf-8")

    res = Q.run_queue(str(manifest))
    data = json.load(open(tmp_path / "runstate.json"))
    jsonschema.validate(data, RUNSTATE_SCHEMA)
    assert res.status == "paused"
    assert data["status"] == "paused"
    assert data["paused_reset_time"] == RESET
    assert data["task_queue"][1]["status"] == "queued"  # second not dispatched
