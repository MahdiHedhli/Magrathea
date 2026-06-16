"""Read-only dashboard HTTP server (stdlib only).

GET-only handler bound to 127.0.0.1. Serves the single static page and JSON from
the read-only `sources`. It does not implement POST/PUT/DELETE, opens nothing for
writing, imports no model client, and never touches orchestrator dispatch.
"""
from __future__ import annotations

import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from dashboard import config, sources

_CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
}
_SAFE_NAME = re.compile(r"^[A-Za-z0-9._-]+$")


class DashboardHandler(BaseHTTPRequestHandler):
    server_version = "MagratheaDashboard/1.0"

    # Quiet by default (writes to no file; just suppresses stderr spam).
    def log_message(self, *args):  # noqa: D401
        return

    # --- GET only. No do_POST/do_PUT/do_DELETE on purpose (read-only). -------
    def do_GET(self):
        path = self.path.split("?", 1)[0].rstrip("/") or "/"

        if path == "/":
            return self._send_static("index.html")
        if path == "/api/health":
            return self._send_json({
                "status": "ok",
                "service": "magrathea-dashboard",
                "read_only": True,
                "panels": sorted(sources.PANELS.keys()),
                "sprint": config.current_sprint(),
            })
        if path.startswith("/api/"):
            panel = path[len("/api/"):]
            fn = sources.PANELS.get(panel)
            if fn is None:
                return self._send_json({"error": "unknown panel"}, status=404)
            try:
                return self._send_json(fn())
            except Exception as e:  # a panel never takes the server down
                return self._send_json(
                    {"status": "error", "panel": panel, "reason": str(e)},
                    status=200)
        if path.startswith("/static/"):
            return self._send_static(path[len("/static/"):])
        if path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return
        return self._send_json({"error": "not found", "path": path}, status=404)

    # --- helpers -------------------------------------------------------------
    def _send_json(self, obj, status=200):
        body = json.dumps(obj, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)  # socket write (the HTTP response), not a disk write

    def _send_static(self, name):
        if not _SAFE_NAME.match(name or ""):
            return self._send_json({"error": "bad path"}, status=404)
        fpath = config.STATIC_DIR / name
        if not fpath.is_file():
            return self._send_json({"error": "not found", "file": name}, status=404)
        data = fpath.read_bytes()  # read-only
        ext = fpath.suffix.lower()
        self.send_response(200)
        self.send_header("Content-Type", _CONTENT_TYPES.get(ext, "text/plain; charset=utf-8"))
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def make_server(port: int = None) -> ThreadingHTTPServer:
    """Create (but do not start) the server, bound to loopback only."""
    if port is None:
        port = config.PORT
    return ThreadingHTTPServer((config.HOST, port), DashboardHandler)


def main():
    httpd = make_server()
    host, port = httpd.server_address[0], httpd.server_address[1]
    print(f"Magrathea dashboard (read-only) on http://{host}:{port}  — Ctrl-C to stop")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopping")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
