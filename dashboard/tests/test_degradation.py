"""AC-3: with runstate.json and the usage output absent, the dashboard serves 200
and panels 5 (live tasks) and 6 (budget) show a clear pending state — no error.

Hermetic: the v2 stores are pointed at guaranteed-absent temp paths, so this
holds whether or not the runtime (feature 003/004) has written a real
.magrathea/runstate.json locally.
"""
import json
import urllib.request

import pytest

from conftest import running_server

from dashboard import config, sources


@pytest.fixture(autouse=True)
def absent_stores(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "RUNSTATE_PATH", tmp_path / "runstate.json")
    monkeypatch.setattr(config, "USAGE_PATH", tmp_path / "usage.json")
    return tmp_path


def _get(base, path):
    resp = urllib.request.urlopen(base + path, timeout=5)
    return resp.status, json.loads(resp.read().decode("utf-8"))


def test_stub_files_are_absent_for_this_test():
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
