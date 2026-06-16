"""NTFY reporter — the orchestrator's only outbound oversight channel.

Stdlib only (urllib). Follows the run's NTFY protocol:
  Title: `Conductor · <phase>`
  Body:  `<status> | <task or issue> | <one-line detail>`
Progress pings tag white_check_mark; blockers add Priority:high + Tags:warning.
"""
from __future__ import annotations

import urllib.request

from . import config


def _publish(title: str, body: str, headers: dict) -> bool:
    url = f"{config.NTFY_BASE_URL.rstrip('/')}/{config.NTFY_TOPIC}"
    req = urllib.request.Request(url, data=body.encode("utf-8"), method="POST")
    req.add_header("Title", title)
    for k, v in headers.items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            ok = 200 <= resp.status < 300
            print(f"[ntfy] {resp.status} :: {title} :: {body}")
            return ok
    except Exception as exc:  # network failure is itself important to see
        print(f"[ntfy] FAILED to send ({exc}) :: {title} :: {body}")
        return False


def progress(phase: str, body: str) -> bool:
    """A green progress ping for a phase boundary."""
    return _publish(f"Conductor · {phase}", body, {"Tags": "white_check_mark"})


def blocker(phase: str, body: str) -> bool:
    """A high-priority blocker ping."""
    return _publish(
        f"Conductor · {phase}", body, {"Priority": "high", "Tags": "warning"}
    )


if __name__ == "__main__":
    import sys

    kind = sys.argv[1] if len(sys.argv) > 1 else "progress"
    phase = sys.argv[2] if len(sys.argv) > 2 else "Test"
    body = sys.argv[3] if len(sys.argv) > 3 else "manual test ping"
    (blocker if kind == "blocker" else progress)(phase, body)
