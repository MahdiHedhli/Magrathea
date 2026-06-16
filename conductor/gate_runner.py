"""Deterministic gate runner — the orchestrator's own verification step.

The orchestrator (never the worker) runs this. It executes the pytest gate with
the project venv and returns a structured, deterministic verdict. Green
(returncode 0) is the only pass.
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass

from . import config


@dataclass
class GateResult:
    passed: bool
    returncode: int
    output: str          # combined stdout+stderr (for the reply feedback / logs)
    summary: str         # last meaningful line, e.g. "8 passed" / "2 failed"

    @property
    def feedback(self) -> str:
        """The tail of the gate output, suitable for handing back to the worker."""
        lines = self.output.strip().splitlines()
        return "\n".join(lines[-40:])


def run_gate() -> GateResult:
    proc = subprocess.run(
        [str(config.VENV_PYTHON), "-m", "pytest",
         str(config.TEST_FILE), "-q", "--no-header"],
        cwd=str(config.PROJECT_ROOT),
        capture_output=True, text=True,
    )
    output = (proc.stdout or "") + (proc.stderr or "")
    summary = ""
    for line in reversed(output.strip().splitlines()):
        line = line.strip()
        if any(tok in line for tok in ("passed", "failed", "error", "no tests")):
            summary = line.strip("= ")
            break
    return GateResult(
        passed=(proc.returncode == 0),
        returncode=proc.returncode,
        output=output,
        summary=summary or f"pytest exit {proc.returncode}",
    )


if __name__ == "__main__":
    r = run_gate()
    print(f"passed={r.passed} rc={r.returncode} :: {r.summary}")
