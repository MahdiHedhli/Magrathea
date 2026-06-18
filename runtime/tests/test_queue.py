"""Gate-first tests for the descriptor queue (feature 005). Deterministic parts;
live multi-worker runs are in PROOF.md."""
import json
import os

import jsonschema

from runtime import config
from runtime import queue as Q

REPO = config.REPO_ROOT
SCHEMA = json.load(open(REPO / "specs" / "002-dashboard" / "contracts"
                       / "runstate.schema.json"))


def test_load_manifest_is_ordered():
    ds = Q.load_manifest(str(REPO / "queues" / "backlog.json"))
    assert [d.id for d in ds] == ["purl-parser", "slugify"]


def test_queue_runstate_is_multitask_and_schema_valid(tmp_path):
    ds = Q.load_manifest(str(REPO / "queues" / "backlog.json"))
    rs = tmp_path / "runstate.json"
    q = Q.QueueRunstate(str(rs), "run-q", "005-queue", ds)
    q.write()
    jsonschema.validate(json.load(open(rs)), SCHEMA)
    data = json.load(open(rs))
    assert [t["id"] for t in data["task_queue"]] == ["purl-parser", "slugify"]
    assert all(t["status"] == "queued" for t in data["task_queue"])

    h = q.handle("purl-parser")
    h.dispatched("019ed-thread", "openai-codex", "gpt-5.5")
    h.gate_recorded(True, "8 passed", 0)
    h.done()
    jsonschema.validate(json.load(open(rs)), SCHEMA)
    data = json.load(open(rs))
    assert data["task_queue"][0]["status"] == "passed"
    assert data["task_queue"][0]["thread_id"] == "019ed-thread"
    assert data["task_queue"][1]["status"] == "queued"  # untouched


def test_queue_action_decisions():
    assert Q.queue_action("passed", "x") == "skip"
    assert Q.queue_action("failed", "x") == "skip"
    assert Q.queue_action("escalated", "x") == "skip"
    assert Q.queue_action("dispatched", "tid") == "reattach"
    assert Q.queue_action("queued", None) == "fresh"
    assert Q.queue_action("dispatched", None) == "fresh"  # no thread to reattach


def _always_human_descriptor(tmp_path, name, task_class):
    p = tmp_path / f"{name}.json"
    p.write_text(json.dumps({
        "id": name, "goal": "g", "task_class": task_class,
        "working_dir": ".", "gate_command": "true",
        "retry_budget": 0, "timeout_seconds": 30,
    }), encoding="utf-8")
    return str(p)


def test_run_queue_skips_blocked_and_continues(tmp_path, monkeypatch):
    # two always-human descriptors: governance refuses both BEFORE any dispatch,
    # so this is deterministic (no worker). Proves the queue continues past a block.
    monkeypatch.setattr(Q.ntfy, "progress", lambda *a, **k: True)
    monkeypatch.setattr(Q.ntfy, "blocker", lambda *a, **k: True)
    monkeypatch.setattr(config, "RUNSTATE_PATH", tmp_path / "runstate.json")

    manifest = tmp_path / "q.json"
    manifest.write_text(json.dumps({"id": "blocked-q", "descriptors": [
        _always_human_descriptor(tmp_path, "rewrite-x", "git-history"),
        _always_human_descriptor(tmp_path, "secret-y", "security-sensitive"),
    ]}), encoding="utf-8")

    result = Q.run_queue(str(manifest))
    data = json.load(open(tmp_path / "runstate.json"))
    jsonschema.validate(data, SCHEMA)
    assert data["status"] == "done"                       # queue exhausted
    assert [t["status"] for t in data["task_queue"]] == ["escalated", "escalated"]
    assert result.done == 0 and result.blocked == 2 and result.dispatched == 0
