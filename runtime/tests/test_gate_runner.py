"""AC-gate: the gate-runner executes an arbitrary command, decides pass/fail by
exit code only, and imports no LLM client."""
import pathlib
import re
import sys

from runtime import gate

GATE_SRC = pathlib.Path(gate.__file__).read_text(encoding="utf-8")
FORBIDDEN = re.compile(
    r"^\s*(?:import|from)\s+(anthropic|openai|cohere|mistralai|groq|google\.generativeai)\b",
    re.MULTILINE,
)


def test_pass_on_exit_zero(tmp_path):
    r = gate.run_gate("exit 0", cwd=str(tmp_path))
    assert r.passed is True and r.returncode == 0


def test_fail_on_nonzero(tmp_path):
    r = gate.run_gate("exit 3", cwd=str(tmp_path))
    assert r.passed is False and r.returncode == 3


def test_captures_output(tmp_path):
    r = gate.run_gate("echo hello-gate", cwd=str(tmp_path))
    assert "hello-gate" in r.output


def test_gate_imports_no_llm_client():
    m = FORBIDDEN.search(GATE_SRC)
    assert not m, f"gate runner imports a model client: {m.group(1) if m else ''}"
    for mod in ("anthropic", "openai"):
        assert mod not in sys.modules, f"{mod} imported by the gate runner"
