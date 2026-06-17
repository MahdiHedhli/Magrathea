"""AC-reattach (feature 004): given runstate with an in-flight thread_id, the
runtime resumes that thread; otherwise it starts fresh. (The live resume + stale
escalation is proven in PROOF.md.)"""
from runtime import runtime


def _rs(task_status, thread_id, status="running", in_flight=None):
    return {
        "run_id": "r", "status": status, "current_sprint": "004",
        "task_queue": [{"id": "T", "status": task_status,
                        "thread_id": thread_id, "gate_result": None}],
        "in_flight": in_flight,
    }


def test_in_flight_dispatched_thread_is_resumed():
    tid = "019ed6ae-2909-7331-8933-652216d8cafa"
    assert runtime.reattach_plan(_rs("dispatched", tid)) == tid


def test_done_is_not_resumed():
    assert runtime.reattach_plan(_rs("passed", "x", status="done")) is None


def test_escalated_is_not_resumed():
    assert runtime.reattach_plan(_rs("escalated", "x", status="blocked")) is None


def test_failed_is_not_resumed():
    assert runtime.reattach_plan(_rs("failed", "x")) is None


def test_queued_without_thread_is_fresh():
    assert runtime.reattach_plan(_rs("queued", None)) is None


def test_no_runstate_is_fresh():
    assert runtime.reattach_plan(None) is None
    assert runtime.reattach_plan({}) is None


def test_resume_entrypoint_exists():
    assert callable(getattr(runtime, "resume", None))
