"""Generalized gate-runner. Runs the project's own verification command and
decides pass/fail by EXIT CODE only. No model — ever (Constitution I).
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass


@dataclass
class GateResult:
    passed: bool
    returncode: int
    summary: str
    output: str

    @property
    def feedback(self) -> str:
        return "\n".join(self.output.strip().splitlines()[-40:])


def run_gate(command: str, cwd: str, timeout: int = 420) -> GateResult:
    """Run `command` in `cwd`; pass iff it exits 0."""
    try:
        proc = subprocess.run(
            command, cwd=cwd, shell=True, capture_output=True, text=True,
            timeout=timeout,
        )
        output = (proc.stdout or "") + (proc.stderr or "")
        rc = proc.returncode
    except subprocess.TimeoutExpired as e:
        output = (e.stdout or "") + (e.stderr or "") if isinstance(e.stdout, str) else ""
        return GateResult(False, 124, f"gate timed out after {timeout}s", output)

    summary = ""
    for line in reversed(output.strip().splitlines()):
        s = line.strip()
        if any(tok in s for tok in ("passed", "failed", "error", "ok", "no tests")):
            summary = s.strip("= ")
            break
    return GateResult(rc == 0, rc, summary or f"exit {rc}", output)
