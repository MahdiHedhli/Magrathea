"""Put the repo root on sys.path so `import dashboard` / `import conductor` work
regardless of the directory pytest is invoked from, and provide a helper that
runs the dashboard server on an ephemeral localhost port for runtime tests.
"""
import contextlib
import os
import sys
import threading

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


@contextlib.contextmanager
def running_server():
    """Start the dashboard on 127.0.0.1:<ephemeral> in a thread; yield base URL."""
    from dashboard import server

    httpd = server.make_server(port=0)  # 0 => OS picks a free port
    host, port = httpd.server_address[0], httpd.server_address[1]
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    try:
        yield f"http://{host}:{port}", httpd
    finally:
        httpd.shutdown()
        httpd.server_close()
        t.join(timeout=5)
