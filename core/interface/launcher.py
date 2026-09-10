"""Launcher HTTP mínimo; seleciona uma entrada e libera a porta para sua UI."""

from __future__ import annotations

import html
import ipaddress
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlsplit

from core.experiments.registry import Experiment, ExperimentRegistry


def _is_local(hostname: str | None) -> bool:
    if not hostname:
        return False
    hostname = hostname.rstrip(".").lower()
    if hostname == "localhost":
        return True
    try:
        return ipaddress.ip_address(hostname).is_loopback
    except ValueError:
        return False


def _launcher_html(entries, prefix=()) -> bytes:
    controls = []
    for entry in entries:
        path = "/experiments/" + "/".join((*prefix, entry.slug))
        method = "post" if entry.runnable else "get"
        controls.append(
            f'<form method="{method}" action="{path}"><button>{html.escape(entry.name)}</button></form>'
        )
    page = """<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Gaea</title><style>
:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;min-height:100vh;display:grid;place-items:center;background:#171b16;color:#d7d0bd;font:16px ui-monospace,monospace}main{width:min(22rem,calc(100% - 2rem));border:1px solid #655f50;padding:1rem;background:#22271f}h1{margin:0 0 1rem;font-size:1rem;font-weight:700;letter-spacing:.18em;text-transform:lowercase}form+form{margin-top:.5rem}button{width:100%;padding:.7rem;border:1px solid #77705e;background:#302f27;color:inherit;font:inherit;text-align:left;cursor:pointer}button:hover,button:focus-visible{background:#464233;outline:1px solid #b6aa8a}
</style></head><body><main><h1>gaea</h1>""" + "".join(controls) + "</main></body></html>"
    return page.encode("utf-8")


class LauncherHTTPServer(HTTPServer):
    allow_reuse_address = True

    def __init__(self, server_address, registry):
        self.registry = registry
        self.selected = None
        super().__init__(server_address, LauncherRequestHandler)


class LauncherRequestHandler(BaseHTTPRequestHandler):
    server: LauncherHTTPServer

    def log_message(self, format, *args):
        return

    def _send(self, status, body):
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _path(self):
        path = urlsplit(self.path)
        if path.query or not path.path.startswith("/experiments/"):
            return None
        return tuple(part for part in path.path.removeprefix("/experiments/").split("/") if part)

    def _entry(self):
        path = self._path()
        if not path:
            return None, path
        try:
            return self.server.registry.resolve(path), path
        except KeyError:
            return None, path

    def _valid_selection_source(self):
        try:
            host = urlsplit("//" + self.headers.get("Host", ""))
            if not _is_local(host.hostname) or host.port != self.server.server_address[1]:
                return False
            origin_header = self.headers.get("Origin")
            if origin_header is None:
                return True
            origin = urlsplit(origin_header)
            return (
                origin.scheme == "http"
                and _is_local(origin.hostname)
                and origin.hostname.rstrip(".").lower()
                == host.hostname.rstrip(".").lower()
                and origin.port == host.port
            )
        except (AttributeError, ValueError):
            return False

    def do_GET(self):
        parsed = urlsplit(self.path)
        if parsed.path == "/" and not parsed.query:
            self._send(200, _launcher_html(self.server.registry.entries))
            return
        entry, path = self._entry()
        if entry is None or entry.runnable:
            self._send(404, b"not found")
            return
        self._send(200, _launcher_html(entry.subexperiments, path))

    def do_POST(self):
        if not self._valid_selection_source():
            self._send(400, b"invalid source")
            return
        entry, _ = self._entry()
        if entry is None:
            self._send(404, b"not found")
            return
        if not entry.runnable:
            self._send(400, b"not runnable")
            return
        if self.server.selected is not None:
            self._send(409, b"already selected")
            return
        self.server.selected = entry
        body = b'<!doctype html><meta charset="utf-8"><script>setTimeout(()=>location.replace("/"),100)</script>'
        self._send(200, body)


def create_launcher_server(registry, host="127.0.0.1", port=8765):
    if not _is_local(host):
        raise ValueError("o launcher deve usar host local")
    if isinstance(port, bool) or not isinstance(port, int) or not 0 <= port <= 65535:
        raise ValueError("porta inválida")
    return LauncherHTTPServer((host, port), registry)


def select_experiment(
    registry: ExperimentRegistry, host="127.0.0.1", port=8765
) -> Experiment:
    server = create_launcher_server(registry, host, port)
    try:
        while server.selected is None:
            server.handle_request()
        return server.selected
    finally:
        server.server_close()
