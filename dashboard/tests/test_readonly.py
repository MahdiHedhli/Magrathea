"""AC-1: the dashboard is read-only.

- no mutating routes (GET only; POST/PUT/DELETE are not served as 2xx)
- imports no LLM client and no orchestrator dispatch
- performs no on-disk writes
"""
import os
import pathlib
import re
import sys
import urllib.error
import urllib.request

from conftest import running_server, REPO_ROOT

import dashboard
from dashboard import server

DASH_DIR = pathlib.Path(dashboard.__file__).resolve().parent
SRC_FILES = sorted(p for p in DASH_DIR.glob("*.py"))

FORBIDDEN_IMPORT = re.compile(
    r"^\s*(?:import|from)\s+"
    r"(anthropic|openai|cohere|mistralai|groq|llama_cpp|transformers"
    r"|google\.generativeai|conductor\.orchestrator|conductor\.mcp_client)\b",
    re.MULTILINE,
)
# disk-write indicators (note: socket writes via wfile.write are allowed)
DISK_WRITE = re.compile(
    r"""(\.write_text\(|\.write_bytes\(|\bos\.(remove|unlink|mkdir|makedirs|rename|replace|rmdir)\b|\bshutil\.|\.mkdir\(|open\([^)]*,\s*['"][^'"]*[wax+])""",
)


def test_source_has_no_forbidden_imports():
    for p in SRC_FILES:
        m = FORBIDDEN_IMPORT.search(p.read_text(encoding="utf-8"))
        assert not m, f"{p.name} imports forbidden module: {m.group(1) if m else ''}"


def test_source_has_no_disk_writes():
    for p in SRC_FILES:
        m = DISK_WRITE.search(p.read_text(encoding="utf-8"))
        assert not m, f"{p.name} contains a disk-write call: {m.group(0)!r}"


def test_no_llm_or_dispatch_module_loaded():
    # importing the dashboard must not pull in an LLM SDK or the dispatch path
    forbidden = ("anthropic", "openai", "conductor.orchestrator",
                 "conductor.mcp_client", "google.generativeai")
    for mod in forbidden:
        assert mod not in sys.modules, f"{mod} was imported by the dashboard"


def test_handler_serves_get_only():
    h = server.DashboardHandler
    assert hasattr(h, "do_GET"), "handler must serve GET"
    for verb in ("do_POST", "do_PUT", "do_DELETE", "do_PATCH"):
        assert not hasattr(h, verb), f"handler must not implement {verb}"


def test_post_is_not_accepted():
    with running_server() as (base, _httpd):
        req = urllib.request.Request(base + "/api/health", data=b"{}", method="POST")
        try:
            resp = urllib.request.urlopen(req, timeout=5)
            status = resp.status
        except urllib.error.HTTPError as e:
            status = e.code
        assert status >= 400, f"POST should be rejected, got {status}"


def _snapshot(root):
    skip = {".git", ".venv", "__pycache__", ".pytest_cache"}
    snap = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip]
        for fn in filenames:
            fp = os.path.join(dirpath, fn)
            try:
                snap[os.path.relpath(fp, root)] = os.path.getsize(fp)
            except OSError:
                pass
    return snap


def test_serving_requests_writes_nothing_to_disk():
    before = _snapshot(REPO_ROOT)
    with running_server() as (base, _httpd):
        for path in ("/", "/api/health", "/api/topology", "/api/sprint",
                     "/api/timeline", "/api/governance", "/api/runstate",
                     "/api/budget"):
            try:
                urllib.request.urlopen(base + path, timeout=5).read()
            except urllib.error.HTTPError:
                pass  # status is checked elsewhere; here we only watch the disk
    after = _snapshot(REPO_ROOT)
    added = set(after) - set(before)
    changed = {k for k in before if k in after and before[k] != after[k]}
    assert not added, f"dashboard created files: {sorted(added)}"
    assert not changed, f"dashboard modified files: {sorted(changed)}"
