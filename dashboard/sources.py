"""Read-only data sources for the dashboard.

Every function returns a plain dict and only READS — files (text), `git log`
(subprocess), and an optional `ntfy` GET. No writes, no model, no orchestrator
dispatch. Parsers are defensive: a parse miss degrades to a partial/pending
result, it never crashes a panel.
"""
from __future__ import annotations

import json
import re
import subprocess
import urllib.request

from dashboard import config


# --- small parsing helpers ---------------------------------------------------
def _read(path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def _section(text: str, heading_contains: str) -> str:
    """Return the body under the first '## ...heading_contains...' until the next '## '."""
    lines = text.splitlines()
    out, capturing = [], False
    for ln in lines:
        if ln.startswith("## "):
            if capturing:
                break
            capturing = heading_contains.lower() in ln.lower()
            continue
        if capturing:
            out.append(ln)
    return "\n".join(out)


def _bold_bullets(section: str):
    """Extract the bold lead-in of '- **X** ...' bullets."""
    items = []
    for m in re.finditer(r"^\s*-\s+\*\*(.+?)\*\*", section, re.MULTILINE):
        items.append(m.group(1).strip())
    return items


def _all_tables(text: str):
    """Parse every markdown table into a list of [header_row, *data_rows]."""
    tables, cur = [], []
    for ln in text.splitlines():
        s = ln.strip()
        if s.startswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if set("".join(cells)) <= set("-: "):  # separator row
                continue
            cur.append(cells)
        elif cur:
            tables.append(cur)
            cur = []
    if cur:
        tables.append(cur)
    return tables


def _table_by_header(text: str, keyword: str):
    """Data rows of the first table whose header row contains `keyword`."""
    for tbl in _all_tables(text):
        if tbl and keyword.lower() in " ".join(tbl[0]).lower():
            return tbl[1:]
    return []


def _clean(cell: str):
    c = re.sub(r"[`*]", "", cell or "").strip()
    if not c or c.upper().startswith("TODO") or c.startswith("("):
        return None
    return c


# --- panel 1: agent topology -------------------------------------------------
def topology() -> dict:
    pol = _read(config.GOVERNANCE_DIR / "model-limit-policy.md")
    worker_rules = _read(config.GOVERNANCE_DIR / "worker.AGENTS.md")
    blob = pol + "\n" + _read(config.GOVERNANCE_DIR / "orchestrator.md")

    providers = []
    orchestrator_model = None
    worker_model = worker_provider = None
    for cells in _table_by_header(pol, "Strong-model floor"):
        if len(cells) < 4:
            continue
        provider = _clean(cells[0])
        if not provider or "provider" in (provider or "").lower():
            continue
        role = (cells[1] or "").strip()
        default_model = _clean(cells[2])
        floor = _clean(cells[3])
        providers.append({"provider": provider, "role": role,
                          "default_model": default_model, "floor": floor})
        if "default worker" in role.lower() and not worker_model:
            worker_model, worker_provider = default_model, provider

    m = re.search(r"Claude\s+Sonnet", blob)
    orchestrator_model = "Claude Sonnet" if m else None

    # worker writable scope (data-driven from worker.AGENTS.md)
    sm = re.search(r"may write only\*\*:\s*`?([^\n.`]+)", worker_rules)
    worker_scope = sm.group(1).strip().rstrip("`") if sm else None

    roles = [
        {"role": "Operator", "actor": "human", "model": None,
         "note": "you — final authority; governance is human-owned"},
        {"role": "Orchestrator", "actor": "agent", "model": orchestrator_model,
         "provider": "Anthropic / Claude", "note": "Sonnet; Opus for planning"},
        {"role": "Worker", "actor": "agent", "model": worker_model,
         "provider": worker_provider, "scope": worker_scope,
         "note": "default; biases to most-headroom provider"},
        {"role": "Independent verification", "actor": "agent", "model": None,
         "note": "role reserved; no model assigned in governance yet"},
    ]
    return {"roles": roles, "providers": providers,
            "sources": ["governance/orchestrator.md", "governance/worker.AGENTS.md",
                        "governance/model-limit-policy.md"]}


# --- panel 2: sprint board ---------------------------------------------------
def sprint() -> dict:
    name = config.current_sprint()
    tasks_md = config.SPECS_DIR / name / "tasks.md"
    text = _read(tasks_md)
    phases, done, total = [], 0, 0
    cur = None
    for ln in text.splitlines():
        h = re.match(r"^##\s+(.*)$", ln)
        if h:
            cur = {"name": h.group(1).strip(), "tasks": []}
            phases.append(cur)
            continue
        t = re.match(r"^\s*-\s+\[([ xX])\]\s+(.*)$", ln)
        if t and cur is not None:
            is_done = t.group(1).lower() == "x"
            cur["tasks"].append({"text": t.group(2).strip(), "done": is_done})
            total += 1
            done += 1 if is_done else 0
    return {"sprint": name, "phases": [p for p in phases if p["tasks"]],
            "done": done, "total": total,
            "source": f"specs/{name}/tasks.md"}


# --- panel 3: timeline -------------------------------------------------------
def _git_log() -> list:
    try:
        sep = "\x1f"
        out = subprocess.run(
            ["git", "-C", str(config.REPO_ROOT), "log",
             f"-{config.TIMELINE_LIMIT}",
             f"--pretty=format:%h{sep}%an{sep}%aI{sep}%s"],
            capture_output=True, text=True, timeout=10,
        ).stdout
        commits = []
        for ln in out.splitlines():
            parts = ln.split(sep)
            if len(parts) == 4:
                commits.append({"hash": parts[0], "author": parts[1],
                                "date": parts[2], "subject": parts[3]})
        return commits
    except Exception:
        return []


def _ntfy_events() -> tuple:
    topic = config.ntfy_topic()
    if not topic:
        return [], "unconfigured"
    url = f"{config.ntfy_base_url().rstrip('/')}/{topic}/json?poll=1&since=12h"
    try:
        with urllib.request.urlopen(url, timeout=2.0) as resp:
            events = []
            for line in resp.read().decode("utf-8").splitlines():
                if not line.strip():
                    continue
                msg = json.loads(line)
                if msg.get("event") == "message":
                    events.append({"time": msg.get("time"),
                                   "title": msg.get("title", ""),
                                   "message": msg.get("message", "")})
            return events[-25:], "ntfy"
    except Exception:
        return [], "git-only"


def timeline() -> dict:
    commits = _git_log()
    events, source = _ntfy_events()
    return {"commits": commits, "events": events, "events_source": source,
            "topic": config.ntfy_topic() or None, "source": "git log"}


# --- panel 4: governance at a glance ----------------------------------------
def governance() -> dict:
    orch = _read(config.GOVERNANCE_DIR / "orchestrator.md")
    pol = _read(config.GOVERNANCE_DIR / "model-limit-policy.md")
    always_human = _bold_bullets(_section(orch, "Always-human"))
    escalate = _bold_bullets(_section(orch, "what ALWAYS returns to you"))
    floors = []
    for cells in _table_by_header(pol, "Strong-model floor"):
        if len(cells) < 4:
            continue
        prov = _clean(cells[0])
        if prov and "provider" not in prov.lower():
            floors.append({"provider": prov, "floor": _clean(cells[3])})
    thr = re.search(r"(\d+)%\s+remaining headroom", pol) or re.search(r"at\s+(\d+)%", pol)
    return {"always_human": always_human, "escalate_always": escalate,
            "model_floors": floors,
            "stop_threshold_pct": int(thr.group(1)) if thr else None,
            "sources": ["governance/orchestrator.md", "governance/model-limit-policy.md"]}


# --- panel 5: live tasks (stub now) -----------------------------------------
def runstate() -> dict:
    try:
        return json.loads(config.RUNSTATE_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"status": "pending",
                "reason": "no run in progress / runstate writer not built",
                "lands_in": config.RUNSTATE_LANDS_IN,
                "reads": ".magrathea/runstate.json"}
    except Exception as e:
        return {"status": "pending", "reason": f"unreadable runstate: {e}",
                "lands_in": config.RUNSTATE_LANDS_IN,
                "reads": ".magrathea/runstate.json"}


# --- panel 6: budget & limits (stub now) ------------------------------------
def budget() -> dict:
    try:
        return json.loads(config.USAGE_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"status": "pending",
                "reason": "usage adapters not built (read/detect)",
                "lands_in": config.USAGE_LANDS_IN,
                "reads": ".magrathea/usage.json",
                "stop_threshold_pct": governance().get("stop_threshold_pct")}
    except Exception as e:
        return {"status": "pending", "reason": f"unreadable usage: {e}",
                "lands_in": config.USAGE_LANDS_IN,
                "reads": ".magrathea/usage.json"}


PANELS = {
    "topology": topology, "sprint": sprint, "timeline": timeline,
    "governance": governance, "runstate": runstate, "budget": budget,
}
