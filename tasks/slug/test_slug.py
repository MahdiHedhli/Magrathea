"""Acceptance gate for a second backlog task (orchestrator-owned).

A deterministic gate for a pure `slugify` function. Red until the worker writes
`slug.py`. Mirrors the PURL gate, smaller.

----------------------------------------------------------------------------
CONTRACT (also handed to the worker)
----------------------------------------------------------------------------
``slugify(text: str) -> str`` returns a URL-friendly slug:
  - lowercase
  - every run of non-alphanumeric characters becomes a single hyphen "-"
  - leading and trailing hyphens are stripped
  - an empty / all-non-alphanumeric input returns "" (empty string)
Standard library only; pure function.
----------------------------------------------------------------------------
"""
import pytest

from slug import slugify

CASES = [
    ("Hello World", "hello-world"),
    ("  Trim  Me!  ", "trim-me"),
    ("C++ & Rust", "c-rust"),
    ("already-a-slug", "already-a-slug"),
    ("Multiple___Spaces and---dashes", "multiple-spaces-and-dashes"),
    ("123 ABC", "123-abc"),
    ("!!!", ""),
    ("", ""),
]


@pytest.mark.parametrize("text,expected", CASES, ids=[repr(c[0]) for c in CASES])
def test_slugify(text, expected):
    assert slugify(text) == expected
