"""AC-read (feature 006 A): the readable adapter normalizes real Codex
rate_limits to the usage contract shape (headroom = 100 - used_percent)."""
import json

import jsonschema

from runtime import config, usage

USAGE_SCHEMA = json.load(open(config.REPO_ROOT / "specs" / "002-dashboard"
                              / "contracts" / "usage.schema.json"))

# a real rate_limits block (from scripts/spike_usage.py)
SAMPLE = {
    "limit_id": "codex", "plan_type": "pro",
    "primary": {"used_percent": 19.0, "window_minutes": 300, "resets_at": 1781803156},
    "secondary": {"used_percent": 12.0, "window_minutes": 10080, "resets_at": 1782335909},
}


def test_parse_codex_rate_limits_to_contract_windows():
    windows = usage.parse_codex_rate_limits(SAMPLE)
    by = {w["window"]: w for w in windows}
    assert by["5h"]["remaining_pct"] == 81.0      # 100 - 19
    assert by["weekly"]["remaining_pct"] == 88.0  # 100 - 12
    assert by["5h"]["resets_at"]                  # epoch -> ISO present
    assert by["5h"]["used"] is None and by["5h"]["limit"] is None  # percent-only


def test_provider_and_snapshot_validate_against_contract():
    provider = {"provider": "openai-codex", "adapter": "read",
                "windows": usage.parse_codex_rate_limits(SAMPLE)}
    snap = usage.build_snapshot([provider], stop_threshold_pct=15)
    jsonschema.validate(snap, USAGE_SCHEMA)
    assert snap["stop_threshold_pct"] == 15
    assert snap["providers"][0]["provider"] == "openai-codex"
    assert snap["generated_at"]


def test_capture_from_event_extracts_rate_limits():
    assert usage.capture_from_event(
        {"type": "token_count", "rate_limits": SAMPLE}) == SAMPLE
    assert usage.capture_from_event({"type": "task_started"}) is None
