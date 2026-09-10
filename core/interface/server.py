"""Servidor HTTP local da interface observadora de Gaea.

O controlador é o único dono do acesso concorrente à simulação. Tanto os
passos do worker quanto snapshots e métricas passam pela mesma condição.
"""

from __future__ import annotations

import ipaddress
import json
import math
import mimetypes
import re
import socket
import threading
import time
from dataclasses import is_dataclass, replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

from core.representation import RepresentationProjector


DEFAULT_SPEED = 20.0
MIN_SPEED = 0.1
MAX_SPEED = 100_000.0
MAX_BURST = 1_000_000
MAX_REQUEST_BODY = 64 * 1024
STATIC_ROOT = Path(__file__).with_name("static")


class ControlError(ValueError):
    """Erro de entrada que pode ser devolvido com segurança ao cliente."""


def _is_local_hostname(hostname: str | None) -> bool:
    if not hostname:
        return False
    normalized = hostname.rstrip(".").lower()
    if normalized == "localhost":
        return True
    try:
        return ipaddress.ip_address(normalized).is_loopback
    except ValueError:
        return False


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ControlError(f"{label} deve ser numérico")
    try:
        number = float(value)
    except (OverflowError, ValueError) as exc:
        raise ControlError(f"{label} deve ser finito") from exc
    if not math.isfinite(number):
        raise ControlError(f"{label} deve ser finito")
    return number


def _selected_id(value: str | None) -> str | int | None:
    if not value:
        return None
    if re.fullmatch(r"[+-]?\d+", value):
        return int(value)
    return value


class SimulationController:
    """Serializa observação e avanço e mantém o relógio em um worker dedicado."""

    def __init__(self, simulation):
        self.simulation = simulation
        self._projector = None
        self._condition = threading.Condition(threading.RLock())
        self._running = False
        self._speed = DEFAULT_SPEED
        self._remaining = 0
        self._stopped = False
        self._worker_error = None
        self.worker = threading.Thread(
            target=self._worker_loop,
            name="gaea-simulation-worker",
            daemon=True,
        )
        self.worker.start()

    def _state_unlocked(self) -> dict[str, bool | float | int]:
        state = {
            "running": self._running,
            "speed": self._speed,
            "remaining": self._remaining,
        }
        if self._worker_error:
            state["error"] = self._worker_error
        return state

    def control_state(self) -> dict[str, bool | float | int]:
        with self._condition:
            return self._state_unlocked()

    def snapshot(self, selected_id: str | None = None) -> dict[str, Any]:
        with self._condition:
            raw = self.simulation.snapshot(selected_id)
            if not isinstance(raw, dict):
                raise TypeError("simulation.snapshot() deve devolver dict")
            snapshot = dict(raw)
            snapshot["tick"] = self.simulation.tick
            snapshot["metrics"] = self.simulation.metrics()

            config = self.simulation.config
            width = getattr(config, "world_width", getattr(config, "width", None))
            height = getattr(config, "world_height", getattr(config, "height", None))
            if width is not None:
                snapshot.setdefault("width", width)
            if height is not None:
                snapshot.setdefault("height", height)
            snapshot["control"] = self._state_unlocked()
            return snapshot

    def command(self, command: str, value: Any = None) -> dict[str, Any]:
        with self._condition:
            if self._stopped:
                raise ControlError("servidor encerrado")

            if command == "run":
                self._worker_error = None
                self._running = True
                self._remaining = 0
                self._condition.notify_all()
            elif command == "pause":
                self._running = False
                self._remaining = 0
                self._condition.notify_all()
            elif command == "step":
                if self._running or self._remaining:
                    raise ControlError("step exige simulação pausada")
                self._worker_error = None
                try:
                    self.simulation.step()
                except Exception as exc:
                    self._worker_error = f"{type(exc).__name__}: {exc}"
                    raise
            elif command == "burst":
                amount = _number(value, "value")
                if not amount.is_integer() or not 1 <= amount <= MAX_BURST:
                    raise ControlError(f"rajada deve ter entre 1 e {MAX_BURST} ticks")
                self._worker_error = None
                self._running = False
                self._remaining = int(amount)
                self._condition.notify_all()
            elif command == "speed":
                speed = _number(value, "value")
                if not MIN_SPEED <= speed <= MAX_SPEED:
                    raise ControlError(
                        f"velocidade deve estar entre {MIN_SPEED} e {MAX_SPEED}"
                    )
                self._speed = speed
                self._condition.notify_all()
            elif command == "regenerate":
                return self._regenerate(value)
            else:
                raise ControlError("comando inválido")

            return {
                "tick": self.simulation.tick,
                "control": self._state_unlocked(),
            }

    def _regenerate(self, seed_value):
        """Replace the running world with a fresh one, optionally reseeded.

        Caller holds the condition. The current config is reused verbatim except
        for the seed, so dimensions and populations stay put across a new draw.
        """
        config = getattr(self.simulation, "config", None)
        if not is_dataclass(config) or isinstance(config, type):
            raise ControlError("esta simulação não permite gerar um novo mundo")
        overrides = {}
        if seed_value is not None:
            seed = _number(seed_value, "value")
            if not seed.is_integer() or not 0 <= seed <= 2**31 - 1:
                raise ControlError("seed deve ser inteiro entre 0 e 2147483647")
            overrides["seed"] = int(seed)
        try:
            fresh = type(self.simulation)(replace(config, **overrides))
        except (ValueError, TypeError) as exc:
            raise ControlError(f"configuração inválida: {exc}") from exc
        self.simulation = fresh
        self._projector = None
        self._running = False
        self._remaining = 0
        self._worker_error = None
        self._condition.notify_all()
        return {
            "tick": fresh.tick,
            "seed": getattr(fresh.config, "seed", None),
            "control": self._state_unlocked(),
        }

    def representation(self, resource, layer=None, identifier=None, section='summary'):
        with self._condition:
            if self._projector is None:
                self._projector = RepresentationProjector(self.simulation)
            if resource == 'bootstrap':
                result = self._projector.bootstrap()
            elif resource == 'frame':
                result = self._projector.frame()
            else:
                result = self._projector.detail(layer, identifier, section)
            result['control'] = self._state_unlocked()
            return result

    def close(self) -> None:
        with self._condition:
            if self._stopped:
                return
            self._stopped = True
            self._running = False
            self._remaining = 0
            self._condition.notify_all()
        if threading.current_thread() is not self.worker:
            self.worker.join()

    def _worker_loop(self) -> None:
        burst_steps = 0
        while True:
            with self._condition:
                while (
                    not self._stopped
                    and not self._running
                    and self._remaining == 0
                ):
                    self._condition.wait()
                if self._stopped:
                    return

                is_burst = self._remaining > 0 and not self._running
                started_at = time.monotonic()
                try:
                    self.simulation.step()
                except Exception as exc:
                    self._worker_error = f"{type(exc).__name__}: {exc}"
                    self._running = False
                    self._remaining = 0
                    continue
                if is_burst and self._remaining:
                    self._remaining -= 1
                speed = self._speed

            if is_burst:
                burst_steps += 1
                if burst_steps % 64 == 0:
                    time.sleep(0)
                continue

            burst_steps = 0
            delay = max(0.0, 1.0 / speed - (time.monotonic() - started_at))
            with self._condition:
                if self._stopped:
                    return
                if self._running and delay:
                    self._condition.wait(timeout=delay)


class ObserverHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, server_address, handler_class, simulation):
        self.controller = SimulationController(simulation)
        try:
            super().__init__(server_address, handler_class)
        except BaseException:
            self.controller.close()
            raise

    def shutdown(self):
        super().shutdown()
        self.controller.close()

    def server_close(self):
        self.controller.close()
        super().server_close()


class IPv6ObserverHTTPServer(ObserverHTTPServer):
    address_family = socket.AF_INET6


class ObserverRequestHandler(BaseHTTPRequestHandler):
    server: ObserverHTTPServer

    def log_message(self, format, *args):
        return

    def _send_bytes(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _send_json(self, status: int, payload: Any) -> None:
        body = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
        self._send_bytes(status, body, "application/json; charset=utf-8")

    def _error(self, status: int, message: str) -> None:
        self._send_json(status, {"error": message})

    def _serve_static(self, path: str) -> None:
        files = {
            "/": "index.html",
            "/index.html": "index.html",
            "/app.mjs": "app.mjs",
            "/camera.mjs": "camera.mjs",
            "/presentation.mjs": "presentation.mjs",
            "/memory-graph.mjs": "memory-graph.mjs",
            "/world-renderer.mjs": "world-renderer.mjs",
            "/style.css": "style.css",
        }
        filename = files.get(path)
        if filename is None and re.fullmatch(r'/[a-zA-Z0-9_/-]+\.(mjs|css|json|png|woff2)', path):
            candidate = (STATIC_ROOT / path.lstrip('/')).resolve()
            if candidate.is_relative_to(STATIC_ROOT.resolve()) and candidate.is_file():
                filename = path.lstrip('/')
        if filename is None:
            self._error(404, "recurso não encontrado")
            return
        target = STATIC_ROOT / filename
        try:
            body = target.read_bytes()
        except FileNotFoundError:
            self._error(404, "recurso não encontrado")
            return
        content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        if content_type.startswith("text/") or content_type == "application/javascript":
            content_type += "; charset=utf-8"
        self._send_bytes(200, body, content_type)

    def _valid_command_source(self) -> bool:
        host_header = self.headers.get("Host")
        if not host_header:
            return False
        try:
            host_parts = urlsplit("//" + host_header)
            host_port = host_parts.port
        except ValueError:
            return False
        if not _is_local_hostname(host_parts.hostname):
            return False
        expected_port = self.server.server_address[1]
        if host_port != expected_port:
            return False

        origin = self.headers.get("Origin")
        if origin is None:
            return True
        try:
            origin_parts = urlsplit(origin)
            origin_port = origin_parts.port
        except ValueError:
            return False
        return (
            origin_parts.scheme == "http"
            and _is_local_hostname(origin_parts.hostname)
            and origin_parts.hostname.rstrip(".").lower()
            == host_parts.hostname.rstrip(".").lower()
            and origin_port == expected_port
        )

    def _read_json_object(self) -> dict[str, Any]:
        if self.headers.get_content_type() != "application/json":
            raise ControlError("Content-Type deve ser application/json")
        try:
            length = int(self.headers.get("Content-Length", ""))
        except ValueError as exc:
            raise ControlError("Content-Length inválido") from exc
        if not 0 < length <= MAX_REQUEST_BODY:
            raise ControlError("corpo vazio ou grande demais")
        raw = self.rfile.read(length)

        def reject_constant(value):
            raise ValueError(f"número não finito: {value}")

        try:
            payload = json.loads(raw, parse_constant=reject_constant)
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            raise ControlError("JSON inválido") from exc
        if not isinstance(payload, dict):
            raise ControlError("JSON deve ser um objeto")
        if set(payload) - {"command", "value"}:
            raise ControlError("campo desconhecido")
        if not isinstance(payload.get("command"), str):
            raise ControlError("command deve ser texto")
        return payload

    def do_GET(self):
        parsed = urlsplit(self.path)
        if parsed.path in ('/api/bootstrap', '/api/frame') or parsed.path.startswith('/api/selection/'):
            try:
                resource = parsed.path.rsplit('/', 1)[-1]
                layer = identifier = None
                section = 'summary'
                if parsed.path.startswith('/api/selection/'):
                    parts = parsed.path.split('/')[3:]
                    if len(parts) == 3 and parts[0] == 'cell':
                        layer, identifier = 'terrain', (int(parts[1]), int(parts[2]))
                    elif len(parts) == 2 and parts[0] in ('agent', 'object'):
                        layer, identifier = parts[0], int(parts[1])
                    elif len(parts) == 3 and parts[0] == 'agent' and parts[2] in ('memory', 'log'):
                        layer, identifier, section = 'agent', int(parts[1]), parts[2]
                    else:
                        raise ValueError('seleção inválida')
                    resource = 'detail'
                result = self.server.controller.representation(resource, layer, identifier, section)
                self._send_json(200, result)
            except ValueError:
                self._error(400, 'consulta inválida')
            except Exception:
                self._error(500, 'não foi possível obter representação')
            return
        if parsed.path == "/api/snapshot":
            selected_values = parse_qs(parsed.query, keep_blank_values=True).get("selected", [])
            if len(selected_values) > 1:
                self._error(400, "selected deve aparecer uma vez")
                return
            selected_id = _selected_id(selected_values[0] if selected_values else None)
            try:
                snapshot = self.server.controller.snapshot(selected_id)
                self._send_json(200, snapshot)
            except Exception:
                self._error(500, "não foi possível obter snapshot")
            return
        self._serve_static(parsed.path)

    def do_HEAD(self):
        parsed = urlsplit(self.path)
        if parsed.path.startswith("/api/"):
            self._error(405, "método não permitido")
            return
        self._serve_static(parsed.path)

    def do_POST(self):
        parsed = urlsplit(self.path)
        if parsed.path != "/api/control":
            self._error(404, "recurso não encontrado")
            return
        if parsed.query:
            self._error(400, "query não permitida")
            return
        try:
            if not self._valid_command_source():
                raise ControlError("Host ou Origin inválido")
            payload = self._read_json_object()
            result = self.server.controller.command(
                payload["command"], payload.get("value")
            )
        except ControlError as exc:
            self._error(400, str(exc))
            return
        except Exception:
            self._error(500, "não foi possível executar comando")
            return
        self._send_json(200, result)


def create_server(simulation, host="127.0.0.1", port=8765):
    """Cria um servidor local, já com worker pausado, sem iniciar o loop HTTP."""
    if not _is_local_hostname(host):
        raise ValueError("o servidor deve usar host local")
    if isinstance(port, bool) or not isinstance(port, int) or not 0 <= port <= 65535:
        raise ValueError("porta inválida")
    server_class = IPv6ObserverHTTPServer if host.rstrip(".") == "::1" else ObserverHTTPServer
    return server_class((host, port), ObserverRequestHandler, simulation)


def serve(simulation, host="127.0.0.1", port=8765):
    """Serve a interface até interrupção e sempre encerra o worker."""
    server = create_server(simulation, host, port)
    try:
        server.serve_forever()
    finally:
        server.server_close()
