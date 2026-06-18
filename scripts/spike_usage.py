#!/usr/bin/env python3
"""Probe how Codex exposes usage/rate-limits: run a trivial turn via the isolated
worker home and dump any event mentioning rate limits / token counts, so we know
what the readable adapter (Phase A) can normalize."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from conductor.mcp_client import CodexMCPClient
from runtime import config, worker_home


def main():
    worker_home.ensure()
    env = worker_home.codex_env()
    hits = []

    def on_event(emsg, thread_id):
        t = emsg.get("type", "")
        blob = json.dumps(emsg).lower()
        if any(k in t.lower() for k in ("token_count", "rate", "limit", "usage")) \
                or "rate_limit" in blob or "reset" in blob:
            hits.append(emsg)

    with CodexMCPClient(config.CODEX_MCP_CMD, env=env) as c:
        c.initialize(timeout=30)
        c.codex(prompt="Reply with exactly: OK", cwd=str(config.REPO_ROOT / "gate"),
                sandbox="read-only", approval_policy="never", model="gpt-5.5",
                timeout=120, on_event=on_event)

    print(f"=== {len(hits)} usage/rate-limit-ish events ===")
    seen_types = set()
    for e in hits:
        t = e.get("type")
        if t in seen_types:
            continue
        seen_types.add(t)
        print(f"\n--- type={t} ---")
        print(json.dumps(e, indent=2)[:1600])


if __name__ == "__main__":
    main()
