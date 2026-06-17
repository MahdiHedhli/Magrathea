"""Task descriptor — the file the runtime reads instead of a hardcoded task.
See specs/003-runtime/contracts/descriptor.schema.json.
"""
from __future__ import annotations

import json
from dataclasses import dataclass


@dataclass
class Descriptor:
    id: str
    goal: str
    task_class: str
    working_dir: str
    gate_command: str
    target_repo: str = "."
    gate_dir: str = "."
    retry_budget: int = 1
    timeout_seconds: int = 420
    schema_version: str = "1.0.0"


_REQUIRED = ("id", "goal", "task_class", "working_dir", "gate_command")


class DescriptorError(ValueError):
    pass


def load(path: str) -> Descriptor:
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    missing = [k for k in _REQUIRED if not data.get(k)]
    if missing:
        raise DescriptorError(f"descriptor {path} missing fields: {missing}")
    known = Descriptor.__dataclass_fields__.keys()
    extra = set(data) - set(known)
    if extra:
        raise DescriptorError(f"descriptor {path} has unknown fields: {sorted(extra)}")
    return Descriptor(**{k: v for k, v in data.items() if k in known})
