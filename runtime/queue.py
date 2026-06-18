#!/usr/bin/env python3
"""The descriptor queue (feature 005): process a backlog of descriptors
sequentially through the proven runtime core. Skip a blocked item and continue;
pause on a limit-hit; resume by reattach + recorded position.
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from conductor import ntfy
from runtime import config, descriptor as descriptor_mod, limits, runtime, usage

_TERMINAL = runtime._TERMINAL_TASK  # passed / failed / escalated


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# --- manifest ----------------------------------------------------------------
def load_manifest(path) -> list:
    """Load an ordered list of Descriptors from a queue manifest."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    out = []
    for p in data["descriptors"]:
        resolved = p if os.path.isabs(p) else str(config.REPO_ROOT / p)
        out.append(descriptor_mod.load(resolved))
    return out


# --- multi-task runstate (the queue the dashboard panel 5 already reads) -----
class _Handle:
    """The handle protocol (dispatched/gate_recorded/done/escalated) over one
    task inside the queue runstate — the same interface RunstateWriter exposes,
    so runtime.execute_descriptor / reattach_descriptor drive it unchanged."""

    def __init__(self, q: "QueueRunstate", task_id: str):
        self.q = q
        self.tid = task_id

    def dispatched(self, thread_id, provider, model):
        t = self.q._task(self.tid)
        t["status"] = "dispatched"
        t["thread_id"] = thread_id
        self.q.state["in_flight"] = {"id": self.tid, "thread_id": thread_id,
                                     "provider": provider, "model": model,
                                     "started_at": _now()}
        self.q.write()

    def gate_recorded(self, passed, summary, returncode):
        t = self.q._task(self.tid)
        t["gate_result"] = {"passed": bool(passed), "summary": summary,
                            "returncode": int(returncode)}
        t["status"] = "passed" if passed else "failed"
        self.q.write()

    def done(self):
        self.q._task(self.tid)["status"] = "passed"
        self.q.state["in_flight"] = None
        self.q._checkpoint()
        self.q.write()

    def escalated(self, reason):
        self.q._task(self.tid)["status"] = "escalated"
        self.q.state["in_flight"] = None
        self.q._checkpoint(reason)
        self.q.write()


class QueueRunstate:
    def __init__(self, path, run_id, current_sprint, descriptors):
        self.path = Path(path)
        self.tasks = [{"id": d.id, "status": "queued", "thread_id": None,
                       "gate_result": None} for d in descriptors]
        self.state = {
            "schema_version": "1.0.0", "run_id": run_id, "status": "running",
            "current_sprint": current_sprint, "updated_at": _now(),
            "task_queue": self.tasks, "in_flight": None,
            "checkpoint": {"completed_task_ids": [], "note": ""},
            "paused_reset_time": None,
        }

    def _task(self, task_id):
        for t in self.tasks:
            if t["id"] == task_id:
                return t
        raise KeyError(task_id)

    def handle(self, task_id) -> _Handle:
        return _Handle(self, task_id)

    def _checkpoint(self, note=None):
        self.state["checkpoint"]["completed_task_ids"] = [
            t["id"] for t in self.tasks if t["status"] in
            ("passed", "failed", "escalated", "blocked")]
        if note is not None:
            self.state["checkpoint"]["note"] = note[:200]

    def write(self):
        self.state["updated_at"] = _now()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(self.state, indent=2), encoding="utf-8")
        os.replace(tmp, self.path)

    def mark_done(self):
        self.state["status"] = "done"
        self.state["in_flight"] = None
        self.write()

    def mark_paused(self, reset_time=None, note=""):
        self.state["status"] = "paused"     # keep in_flight for reattach on resume
        self.state["paused_reset_time"] = reset_time
        self.state["checkpoint"]["note"] = note[:200]
        self.write()

    def seed(self, prior):
        """Copy per-task status from a prior runstate of the SAME queue (resume)."""
        by_id = {t["id"]: t for t in (prior.get("task_queue") or [])}
        for t in self.tasks:
            p = by_id.get(t["id"])
            if p:
                t["status"] = p.get("status", "queued")
                t["thread_id"] = p.get("thread_id")
                t["gate_result"] = p.get("gate_result")
        self.state["in_flight"] = prior.get("in_flight")
        self._checkpoint()


def queue_action(task_status, thread_id) -> str:
    """Per-item decision on (re)entry: skip terminal, reattach an in-flight thread,
    else process fresh."""
    if task_status in _TERMINAL:
        return "skip"
    if task_status == "dispatched" and thread_id:
        return "reattach"
    return "fresh"


@dataclass
class QueueResult:
    done: int
    blocked: int
    skipped: int
    dispatched: int
    status: str


# --- the queue runner --------------------------------------------------------
def run_queue(manifest_path, log_path=None) -> QueueResult:
    descriptors = load_manifest(manifest_path)
    name = Path(manifest_path).stem
    prior = runtime.load_runstate()
    same_queue = bool(prior) and (
        {t["id"] for t in (prior.get("task_queue") or [])} ==
        {d.id for d in descriptors})

    qrs = QueueRunstate(config.RUNSTATE_PATH, run_id=f"queue-{name}",
                        current_sprint="005-queue", descriptors=descriptors)
    if same_queue:
        qrs.seed(prior)
        print(f"[queue] resuming '{name}' from prior runstate")
    qrs.write()

    threshold = limits.stop_threshold_pct()
    done = blocked = skipped = dispatched = 0
    for d in descriptors:
        t = qrs._task(d.id)
        action = queue_action(t["status"], t["thread_id"])

        if action == "skip":
            if t["status"] == "passed":
                done += 1
            else:
                skipped += 1
            print(f"[queue] skip '{d.id}' (already {t['status']})")
            continue

        # stop-threshold: do not START new work below the governance headroom
        if action == "fresh":
            wp = limits.provider(usage.load_snapshot(), config.DEFAULT_WORKER_PROVIDER)
            if wp and limits.headroom_below_threshold(wp, threshold):
                mr = limits.min_remaining_pct(wp)
                qrs.mark_paused(note=f"worker headroom {mr}% < {threshold}% before {d.id}")
                ntfy.blocker("Queue", f"paused | stop-threshold | worker headroom "
                             f"{mr}% < {threshold}% before {d.id}; restart after reset")
                print(f"[queue] PAUSED stop-threshold: headroom {mr}% < "
                      f"{threshold}% — not starting '{d.id}'")
                return QueueResult(done, blocked, skipped, dispatched, "paused")

        handle = qrs.handle(d.id)
        if action == "reattach":
            print(f"[queue] reattach '{d.id}' thread {t['thread_id']}")
            outcome = runtime.reattach_descriptor(d, t["thread_id"], handle, log_path)
        else:
            print(f"[queue] dispatch '{d.id}' ({descriptors.index(d)+1}/{len(descriptors)})")
            outcome = runtime.execute_descriptor(d, handle, log_path)

        if outcome.status == "PASS":
            done += 1
            dispatched += 1
        elif outcome.status == "BLOCKED_LIMIT":
            qrs.mark_paused(reset_time=outcome.reset_time,
                            note=f"limit-hit on {d.id}; resets {outcome.reset_time}")
            ntfy.blocker("Queue", f"paused | limit-hit | {d.id} resets "
                         f"{outcome.reset_time}; checkpoint saved, restart to resume")
            print(f"[queue] PAUSED on limit-hit at '{d.id}' "
                  f"(resets {outcome.reset_time}) — checkpoint saved")
            return QueueResult(done, blocked, skipped, dispatched, "paused")
        else:  # BLOCKED_GOVERNANCE / INFRA / GATE — recorded+escalated by handle
            blocked += 1
            if outcome.status != "BLOCKED_GOVERNANCE":
                dispatched += 1
            ntfy.blocker("Queue", f"blocked | {d.id} {outcome.status} | "
                         f"{outcome.detail[:90]}; skipped, continuing")
            print(f"[queue] '{d.id}' {outcome.status} — recorded, skipping, continuing")

    qrs.mark_done()
    tally = f"done={done} blocked={blocked} skipped={skipped}"
    ntfy.progress("Queue", f"done | backlog '{name}' exhausted | {tally}")
    print(f"[queue] BACKLOG DONE :: {tally}")
    return QueueResult(done, blocked, skipped, dispatched, "done")


def main(argv) -> int:
    if len(argv) < 2:
        print("usage: python -m runtime.queue <manifest.json>")
        return 2
    log_path = config.MAGRATHEA_DIR / "runtime.jsonl"
    res = run_queue(argv[1], log_path=log_path)
    print(f"\n[queue] RESULT: {res}")
    return 0 if res.status == "done" and res.blocked == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
