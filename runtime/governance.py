"""Governance enforcement at execution time.

Reads the always-human classes and model policy from governance/ (never hardcoded)
and decides whether a descriptor may be dispatched. An always-human class is
refused and escalated — never auto-dispatched (Constitution II/III).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from runtime import config

_STOP = {"or", "and", "the", "a", "an", "to", "of", "log", "modification", "task",
         "class", "classes", "never", "human"}


def _section(text: str, heading_contains: str) -> str:
    out, cap = [], False
    for ln in text.splitlines():
        if ln.startswith("## "):
            if cap:
                break
            cap = heading_contains.lower() in ln.lower()
            continue
        if cap:
            out.append(ln)
    return "\n".join(out)


def _bold_bullets(section: str):
    return [m.group(1).strip()
            for m in re.finditer(r"^\s*-\s+\*\*(.+?)\*\*", section, re.MULTILINE)]


def _tokens(s: str):
    return {t for t in re.split(r"[^a-z0-9]+", s.lower())
            if len(t) >= 3 and t not in _STOP}


@dataclass
class Decision:
    allowed: bool
    reason: str
    model: Optional[str] = None
    matched: Optional[str] = None


@dataclass
class Governance:
    always_human: list = field(default_factory=list)   # phrases, data-driven
    default_model: str = config.DEFAULT_WORKER_MODEL
    floors: dict = field(default_factory=dict)         # provider -> floor model

    def _matches_always_human(self, task_class: str):
        ct = _tokens(task_class)
        for phrase in self.always_human:
            pt = _tokens(phrase)
            for a in ct:
                for b in pt:
                    if a.startswith(b) or b.startswith(a):
                        return phrase
        return None

    def check(self, descriptor) -> Decision:
        hit = self._matches_always_human(descriptor.task_class)
        if hit:
            return Decision(
                allowed=False,
                reason=(f"task_class '{descriptor.task_class}' is an always-human "
                        f"class ('{hit}'); refused and escalated, never auto-dispatched."),
                matched=hit,
            )
        return Decision(allowed=True,
                        reason=f"task_class '{descriptor.task_class}' is auto-dispatchable.",
                        model=self.default_model)


def load() -> Governance:
    orch = (config.GOVERNANCE_DIR / "orchestrator.md").read_text(encoding="utf-8")
    always_human = _bold_bullets(_section(orch, "Always-human"))

    floors, default_model = {}, config.DEFAULT_WORKER_MODEL
    pol_path = config.GOVERNANCE_DIR / "model-limit-policy.md"
    if pol_path.exists():
        pol = pol_path.read_text(encoding="utf-8")
        for ln in pol.splitlines():
            if not ln.strip().startswith("|"):
                continue
            cells = [c.strip(" `*") for c in ln.strip("|").split("|")]
            if len(cells) >= 4 and "default worker" in cells[1].lower():
                m = re.search(r"gpt[\w.\-]+", cells[2])
                if m:
                    default_model = m.group(0)
                if cells[3] and not cells[3].upper().startswith("TODO"):
                    floors[cells[0]] = cells[3]
    return Governance(always_human=always_human, default_model=default_model, floors=floors)
