"""AC-2: the server binds 127.0.0.1, never 0.0.0.0."""
import pathlib

from conftest import running_server

import dashboard
from dashboard import config

DASH_DIR = pathlib.Path(dashboard.__file__).resolve().parent
SRC_FILES = sorted(p for p in DASH_DIR.glob("*.py"))


def test_host_constant_is_loopback():
    assert config.HOST == "127.0.0.1"


def test_no_zero_host_in_source():
    for p in SRC_FILES:
        text = p.read_text(encoding="utf-8")
        assert "0.0.0.0" not in text, f"{p.name} references 0.0.0.0"


def test_running_server_is_bound_to_loopback():
    with running_server() as (base, httpd):
        assert httpd.server_address[0] == "127.0.0.1"
        assert base.startswith("http://127.0.0.1:")
