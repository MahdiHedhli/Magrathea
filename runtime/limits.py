"""Stop-threshold policy (feature 006 C). The runtime/queue stop STARTING new work
when a provider's headroom falls below the governance stop threshold. The
threshold is read from governance/model-limit-policy.md — never hardcoded.
"""
from __future__ import annotations

import re
from typing import Optional

from runtime import config


def stop_threshold_pct(default: float = 15.0) -> float:
    """Parse the '… N% remaining headroom' stop threshold from the model/limit
    policy. Falls back to `default` only if the policy can't be read."""
    try:
        pol = (config.GOVERNANCE_DIR / "model-limit-policy.md").read_text(encoding="utf-8")
    except Exception:
        return default
    m = re.search(r"(\d+(?:\.\d+)?)\s*%\s*remaining headroom", pol)
    return float(m.group(1)) if m else default


def provider(snapshot, name) -> Optional[dict]:
    for p in (snapshot or {}).get("providers", []):
        if p.get("provider") == name:
            return p
    return None


def min_remaining_pct(provider_usage) -> Optional[float]:
    """Lowest remaining headroom across a provider's tracked windows (or None)."""
    vals = [w["remaining_pct"] for w in (provider_usage or {}).get("windows", [])
            if w.get("remaining_pct") is not None]
    return min(vals) if vals else None


def headroom_below_threshold(provider_usage, threshold: Optional[float] = None) -> bool:
    threshold = threshold if threshold is not None else stop_threshold_pct()
    m = min_remaining_pct(provider_usage)
    return m is not None and m < threshold
