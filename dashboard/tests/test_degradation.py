"""AC-3: with runstate.json and the usage output absent, the dashboard serves 200
and panels 5 (live tasks) and 6 (budget) show a clear pending state — no error.
"""
import json
import urllib.request

from conftest import running_server

from dashboard import config, sources


def _get(base, path):
    resp = urllib.request.urlopen(base + path, timeout=5)
    return resp.status, json.loads(resp.read().decode("utf-8"))


def test_stub_files_are_absent_for_this_test():
    # The v2 stores do not exist yet; that is exactly the degraded case.
    assert not config.RUNSTATE_PATH.exists()
    assert not config.USAGE_PATH.exists()


def test_runstate_source_degrades_to_pending():
    data = sources.runstate()
    assert data["status"] == "pending"
    assert data.get("lands_in")  # names the runtime sprint that will write it


def test_budget_source_degrades_to_pending():
    data = sources.budget()
    assert data["status"] == "pending"
    assert data.get("lands_in")


def test_endpoints_return_200_when_stores_absent():
    with running_server() as (base, _httpd):
        for path in ("/", "/api/health", "/api/topology", "/api/sprint",
                     "/api/timeline", "/api/governance"):
            resp = urllib.request.urlopen(base + path, timeout=5)
            assert resp.status == 200, f"{path} -> {resp.status}"

        status, rs = _get(base, "/api/runstate")
        assert status == 200 and rs["status"] == "pending"

        status, bg = _get(base, "/api/budget")
        assert status == 200 and bg["status"] == "pending"
