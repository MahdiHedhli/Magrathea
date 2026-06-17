"""AC-runstate: the writer produces a runstate.json that validates against the
committed dashboard schema at each lifecycle stage."""
import json
import os

import jsonschema

from runtime import descriptor, runstate

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SCHEMA = json.load(open(os.path.join(
    REPO_ROOT, "specs", "002-dashboard", "contracts", "runstate.schema.json")))


def _valid(path):
    jsonschema.validate(json.load(open(path)), SCHEMA)


def _descriptor(tmp_path):
    p = tmp_path / "d.json"
    p.write_text('{"id":"T1","goal":"g","task_class":"feature",'
                 '"working_dir":"gate","gate_command":"true"}', encoding="utf-8")
    return descriptor.load(str(p))


def test_runstate_validates_through_the_lifecycle(tmp_path):
    rs = tmp_path / "runstate.json"
    d = _descriptor(tmp_path)
    w = runstate.RunstateWriter(str(rs), run_id="run-test", current_sprint="003-runtime")

    w.queue(d);                              _valid(rs)
    state = json.load(open(rs))
    assert state["status"] == "running"
    assert state["task_queue"][0]["status"] == "queued"

    w.dispatched("019ed-thread", "openai-codex", "gpt-5.5"); _valid(rs)
    state = json.load(open(rs))
    assert state["in_flight"]["thread_id"] == "019ed-thread"
    assert state["task_queue"][0]["status"] == "dispatched"

    w.gate_recorded(True, "8 passed", 0);    _valid(rs)
    state = json.load(open(rs))
    assert state["task_queue"][0]["gate_result"]["passed"] is True

    w.done();                                _valid(rs)
    state = json.load(open(rs))
    assert state["status"] == "done"
    assert state["in_flight"] is None
    assert state["task_queue"][0]["status"] == "passed"


def test_runstate_escalation_path_validates(tmp_path):
    rs = tmp_path / "runstate.json"
    d = _descriptor(tmp_path)
    w = runstate.RunstateWriter(str(rs), run_id="run-test2", current_sprint="003-runtime")
    w.queue(d)
    w.escalated("always-human class refused")
    _valid(rs)
    state = json.load(open(rs))
    assert state["status"] == "blocked"
    assert state["task_queue"][0]["status"] == "escalated"
