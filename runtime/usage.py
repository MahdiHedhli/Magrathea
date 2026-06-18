#!/usr/bin/env python3
"""Usage adapters (feature 006).

Phase A — readable Codex adapter: normalize Codex `token_count.rate_limits` into
the usage contract (specs/002-dashboard/contracts/usage.schema.json). Headroom =
100 - used_percent. Read-only; no model judgement.
(Phase B adds the Claude detect adapter below.)
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from conductor.mcp_client import CodexMCPClient
from runtime import config, worker_home

_WINDOW_NAMES = {300: "5h", 1440: "daily", 10080: "weekly", 43200: "monthly"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _epoch_to_iso(epoch) -> Optional[str]:
    if not epoch:
        return None
    return datetime.fromtimestamp(epoch, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _window_name(minutes) -> str:
    return _WINDOW_NAMES.get(minutes, "cumulative")


# --- Phase A: readable Codex adapter ----------------------------------------
def parse_codex_rate_limits(rate_limits: dict) -> list:
    """Codex rate_limits (primary=5h, secondary=weekly) -> contract windows."""
    windows = []
    for key in ("primary", "secondary"):
        w = (rate_limits or {}).get(key)
        if not w:
            continue
        used = w.get("used_percent")
        windows.append({
            "window": _window_name(w.get("window_minutes")),
            "used": None, "limit": None,   # Codex exposes percent, not absolute
            "remaining_pct": round(100 - used, 1) if used is not None else None,
            "resets_at": _epoch_to_iso(w.get("resets_at")),
        })
    return windows


def capture_from_event(emsg) -> Optional[dict]:
    """Opportunistic capture: the rate_limits block off a token_count event
    (so a normal dispatch updates usage with no extra turn)."""
    if isinstance(emsg, dict) and emsg.get("type") == "token_count":
        return emsg.get("rate_limits")
    return None


def read_codex_usage(env=None, timeout: int = 120) -> Optional[dict]:
    """Run one trivial read-only turn (isolated worker home) to capture the live
    rate_limits, normalized to a provider entry. Returns None if unavailable."""
    worker_home.ensure()
    env = env or worker_home.codex_env()
    captured = {"rl": None}

    def on_event(emsg, thread_id):
        rl = capture_from_event(emsg)
        if rl:
            captured["rl"] = rl

    with CodexMCPClient(config.CODEX_MCP_CMD, env=env) as client:
        client.initialize(timeout=config.INITIALIZE_TIMEOUT)
        client.codex(prompt="Reply with exactly: OK",
                     cwd=str(config.REPO_ROOT / "gate"), sandbox="read-only",
                     approval_policy="never", model=config.DEFAULT_WORKER_MODEL,
                     timeout=timeout, on_event=on_event)
    if not captured["rl"]:
        return None
    return {"provider": "openai-codex", "adapter": "read",
            "windows": parse_codex_rate_limits(captured["rl"])}


def build_snapshot(providers: list, stop_threshold_pct) -> dict:
    """Assemble the usage snapshot in the committed contract shape."""
    return {"schema_version": "1.0.0", "generated_at": _now_iso(),
            "stop_threshold_pct": stop_threshold_pct, "providers": providers}
