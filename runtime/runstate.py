"""Runstate writer — writes .magrathea/runstate.json to the contract defined in
specs/002-dashboard/contracts/runstate.schema.json, through the task lifecycle.
The dashboard's panel 5 reads exactly this file. (Gitignored runtime state.)
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class RunstateWriter:
    def __init__(self, path, run_id: str, current_sprint: str):
        self.path = Path(path)
        self.state = {
            "schema_version": "1.0.0",
            "run_id": run_id,
            "status": "running",
            "current_sprint": current_sprint,
            "updated_at": _now(),
            "task_queue": [],
            "in_flight": None,
            "checkpoint": None,
            "paused_reset_time": None,
        }
        self._task = None

    # -- atomic write ---------------------------------------------------------
    def _write(self):
        self.state["updated_at"] = _now()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(self.state, indent=2), encoding="utf-8")
        os.replace(tmp, self.path)
        return dict(self.state)

    # -- lifecycle ------------------------------------------------------------
    def queue(self, descriptor):
        self._task = {"id": descriptor.id, "status": "queued",
                      "thread_id": None, "gate_result": None}
        self.state["task_queue"] = [self._task]
        self.state["status"] = "running"
        return self._write()

    def dispatched(self, thread_id: str, provider: str, model: str):
        self._task["status"] = "dispatched"
        self._task["thread_id"] = thread_id
        self.state["in_flight"] = {
            "id": self._task["id"], "thread_id": thread_id,
            "provider": provider, "model": model, "started_at": _now(),
        }
        return self._write()

    def gate_recorded(self, passed: bool, summary: str, returncode: int):
        self._task["gate_result"] = {"passed": bool(passed), "summary": summary,
                                     "returncode": int(returncode)}
        self._task["status"] = "passed" if passed else "failed"
        return self._write()

    def done(self):
        self.state["status"] = "done"
        self.state["in_flight"] = None
        if self._task:
            self._task["status"] = "passed"
            self.state["checkpoint"] = {"completed_task_ids": [self._task["id"]],
                                        "note": "done"}
        return self._write()

    def escalated(self, reason: str):
        self.state["status"] = "blocked"
        self.state["in_flight"] = None
        if self._task:
            self._task["status"] = "escalated"
        self.state["checkpoint"] = {"completed_task_ids": [], "note": reason[:200]}
        return self._write()

    def paused(self, reset_time: str):
        self.state["status"] = "paused"
        self.state["in_flight"] = None
        self.state["paused_reset_time"] = reset_time
        return self._write()
