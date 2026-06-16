"""Dashboard configuration. Localhost-only by construction; paths and the
reporting topic come from here / conductor.config — never hardcoded in handlers.
"""
from __future__ import annotations

import os
from pathlib import Path

# --- Network: loopback only, never a wildcard/public bind, never a tunnel ----
HOST = "127.0.0.1"
PORT = int(os.environ.get("MAGRATHEA_DASHBOARD_PORT", "8787"))

# --- Paths (everything read-only) --------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
GOVERNANCE_DIR = REPO_ROOT / "governance"
SPECS_DIR = REPO_ROOT / "specs"
STATIC_DIR = Path(__file__).resolve().parent / "static"

# v2 stores the dashboard READS but never writes (absent now -> pending panels)
MAGRATHEA_DIR = REPO_ROOT / ".magrathea"
RUNSTATE_PATH = MAGRATHEA_DIR / "runstate.json"
USAGE_PATH = MAGRATHEA_DIR / "usage.json"

# Names surfaced when a v2 store is absent, so the pending panel says who fills it
RUNSTATE_LANDS_IN = "the runtime sprint (runstate writer not built yet)"
USAGE_LANDS_IN = "the usage-adapter sprint (read/detect adapters not built yet)"

# How many commits the timeline shows
TIMELINE_LIMIT = int(os.environ.get("MAGRATHEA_DASHBOARD_COMMITS", "25"))


def current_sprint() -> str:
    """The sprint the dashboard shows: env pointer, else the latest specs/NNN dir."""
    pin = os.environ.get("MAGRATHEA_DASHBOARD_SPRINT")
    if pin:
        return pin
    dirs = sorted(
        (p.name for p in SPECS_DIR.glob("[0-9][0-9][0-9]-*") if p.is_dir()),
        reverse=True,
    )
    return dirs[0] if dirs else ""


def ntfy_topic() -> str:
    """Reporting topic, read from conductor.config (config, not the dispatch path)."""
    try:
        from conductor import config as cc  # config only; never orchestrator
        return getattr(cc, "NTFY_TOPIC", "") or ""
    except Exception:
        return os.environ.get("CONDUCTOR_NTFY_TOPIC", "")


def ntfy_base_url() -> str:
    try:
        from conductor import config as cc
        return getattr(cc, "NTFY_BASE_URL", "https://ntfy.sh")
    except Exception:
        return os.environ.get("CONDUCTOR_NTFY_URL", "https://ntfy.sh")
