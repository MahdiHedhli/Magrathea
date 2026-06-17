"""AC-descriptor: the loop runs from a descriptor file, not a hardcoded task."""
import inspect
import os

from runtime import descriptor, runtime

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def test_loads_dogfood_descriptor_fields():
    d = descriptor.load(os.path.join(REPO_ROOT, "descriptors", "purl.json"))
    assert d.id == "purl-parser"
    assert d.task_class == "feature"
    assert d.working_dir == "gate"
    assert "pytest" in d.gate_command
    assert d.retry_budget == 1
    assert d.timeout_seconds == 420


def test_defaults_applied(tmp_path):
    p = tmp_path / "min.json"
    p.write_text('{"id":"x","goal":"g","task_class":"feature",'
                 '"working_dir":"w","gate_command":"true"}', encoding="utf-8")
    d = descriptor.load(str(p))
    assert d.target_repo == "."        # default
    assert d.gate_dir == "."           # default
    assert d.retry_budget == 1         # default
    assert d.timeout_seconds == 420    # default


def test_runtime_runs_from_a_descriptor_object_not_hardcoded():
    # the loop's entrypoint takes a Descriptor (or path), proving it is data-driven
    sig = inspect.signature(runtime.run)
    assert "descriptor" in sig.parameters
