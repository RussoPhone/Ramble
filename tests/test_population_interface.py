import http.client
import json
import threading
import time
from contextlib import contextmanager

import pytest

from core.cognition.records import Action
from core.interface.server import create_server
from core.simulation.population import PopulationConfig, PopulationSimulation


class MinimalSimulation:
    """Simula o contrato público usado pela interface, sem dependências externas."""

    def __init__(self, step_delay=0):
        self.tick = 0
        self.config = type("Config", (), {"world_width": 4, "world_height": 3})()
        self.step_delay = step_delay
        self.selected_ids = []

    def step(self):
        if self.step_delay:
            time.sleep(self.step_delay)
        self.tick += 1

    def metrics(self):
        return {
            "alive": 1,
            "births": 0,
            "deaths": 0,
            "objects": 1,
            "relations": 0,
        }

    def snapshot(self, selected_id=None):
        self.selected_ids.append(selected_id)
        selected = None
        if selected_id == "agente-1":
            selected = {
                "id": "agente-1",
                "body": {"hunger": 12, "thirst": 34},
                "position": [1, 1],
                "orientation": [1, 0],
                "action": "observa",
                "perception": [],
                "memory": {"relations": [], "experiences": [], "forgotten": 0},
                "decision": {},
            }
        return {
            "tick": self.tick,
            "width": self.config.world_width,
            "height": self.config.world_height,
            "light": 0.75,
            "terrain": [
                {"x": 0, "y": 0, "appearance": [24, 64, 32], "blocking": False}
            ],
            "objects": [
                {
                    "id": "comida-1",
                    "x": 2,
                    "y": 1,
                    "appearance": [220, 170, 55],
                    "quantity": 3,
                }
            ],
            "agents": [
                {
                    "id": "agente-1",
                    "x": 1,
                    "y": 1,
                    "orientation": [1, 0],
                    "alive": True,
                    "action": "observa",
                    "body": {"hunger": 12, "thirst": 34},
                    "generation": 0,
                }
            ],
            "metrics": self.metrics(),
            "events": [],
            "selected": selected,
        }


class TimedSimulation(MinimalSimulation):
    def __init__(self, step_delay=0):
        super().__init__(step_delay)
        self.step_started_at = []

    def step(self):
        self.step_started_at.append(time.monotonic())
        super().step()


class FailingSimulation(MinimalSimulation):
    def step(self):
        raise RuntimeError("falha determinística")


@contextmanager
def running_server(simulation):
    server = create_server(simulation, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def request(server, method, path, payload=None, headers=None):
    host, port = server.server_address[:2]
    connection = http.client.HTTPConnection(host, port, timeout=2)
    body = None if payload is None else json.dumps(payload)
    request_headers = {"Accept": "application/json"}
    if body is not None:
        request_headers["Content-Type"] = "application/json"
    if headers:
        request_headers.update(headers)
    connection.request(method, path, body=body, headers=request_headers)
    response = connection.getresponse()
    raw = response.read()
    content_type = response.getheader("Content-Type", "")
    parsed = json.loads(raw) if "application/json" in content_type else raw
    connection.close()
    return response.status, parsed


def wait_until(predicate, timeout=2):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return False


def test_snapshot_observa_sem_avancar_e_encaminha_selecao():
    simulation = MinimalSimulation()
    with running_server(simulation) as server:
        status, snapshot = request(
            server, "GET", "/api/snapshot?selected=agente-1"
        )

        assert status == 200
        assert snapshot["tick"] == 0
        assert snapshot["selected"]["id"] == "agente-1"
        assert snapshot["control"] == {
            "running": False,
            "speed": 20.0,
            "remaining": 0,
        }
        assert simulation.tick == 0
        assert simulation.selected_ids == ["agente-1"]


def test_snapshot_converte_id_numerico_para_o_runtime_real():
    simulation = PopulationSimulation(
        PopulationConfig(
            width=5,
            height=5,
            population=1,
            objects=0,
            stones=0,
            reproduction=False,
        )
    )
    with running_server(simulation) as server:
        status, snapshot = request(server, "GET", "/api/snapshot?selected=1")

        assert status == 200
        assert snapshot["selected"]["id"] == 1
        assert simulation.tick == 0


def test_snapshot_localiza_evento_sem_expor_efeito_fisico():
    simulation = PopulationSimulation(
        PopulationConfig(
            width=5,
            height=5,
            population=1,
            objects=0,
            stones=0,
            metabolism=0,
            reproduction=False,
        )
    )
    agent = next(iter(simulation.agents.values()))
    assert simulation._set_agent_position(agent, 5, 7, (1, 0))
    target = simulation.add_object(
        2,
        2,
        (7, 8, 9),
        effect=(-20, 0),
    )

    simulation.step({agent.uid: Action("ingest", target.uid)})

    event = simulation.snapshot()["events"][-1]
    assert event["position"] == (agent.x, agent.y)
    assert event["target_position"] == (2, 2)
    assert "effect" not in event


def test_snapshot_expoe_tipos_visuais_sem_expor_efeitos_fisicos():
    simulation = PopulationSimulation(
        PopulationConfig(
            width=7,
            height=7,
            population=0,
            objects=3,
            stones=1,
            reproduction=False,
        )
    )

    snapshot = simulation.snapshot()

    assert {tile["kind"] for tile in snapshot["terrain"]} == {"ground", "stone"}
    assert {obj["kind"] for obj in snapshot["objects"]} == {"food", "water", "stone"}
    assert all("effect" not in obj for obj in snapshot["objects"])


def test_pagina_observadora_e_assets_sao_servidos():
    simulation = MinimalSimulation()
    with running_server(simulation) as server:
        status, html = request(server, "GET", "/")
        css_status, stylesheet = request(server, "GET", "/style.css")

        assert (status, css_status) == (200, 200)
        assert html.count(b'id="world-canvas"') == 1
        for element_id in (
            b"world-status",
            b"world-hover",
            b"inspector",
            b"selection-candidates",
            b"time-controls",
            b"show-collisions",
            b"speed-value",
        ):
            assert b'id="' + element_id + b'"' in html
        assert b"renderer-select" not in html
        assert b"speed-select" not in html
        assert b'type="number" min="0.1" max="100000" step="0.1"' in html
        assert b"Geometric" not in html
        assert b"Pseudo-3D" not in html
        assert b"chave ASCII" in html
        assert b'id="show-collisions" type="checkbox"' in html
        assert b'id="show-collisions" type="checkbox" checked' not in html
        for asset in (
            "app.mjs",
            "camera.mjs",
            "presentation.mjs",
            "memory-graph.mjs",
            "world-renderer.mjs",
            "renderers/ascii-renderer.mjs",
        ):
            asset_status, body = request(server, "GET", f"/{asset}")
            assert asset_status == 200
            assert body
        assert b"canvas" in stylesheet
        assert request(server, "GET", "/renderers/style-registry.mjs")[0] == 404
        assert request(server, "GET", "/renderers/styles/geometric.mjs")[0] == 404


def test_step_pausado_avanca_exatamente_um_tick():
    simulation = MinimalSimulation()
    with running_server(simulation) as server:
        status, result = request(server, "POST", "/api/control", {"command": "step"})

        assert status == 200
        assert result["tick"] == 1
        time.sleep(0.08)
        assert simulation.tick == 1


def test_burst_assincrono_completa_e_volta_a_ficar_pausado():
    simulation = MinimalSimulation()
    with running_server(simulation) as server:
        request(server, "POST", "/api/control", {"command": "speed", "value": 500})
        status, result = request(
            server, "POST", "/api/control", {"command": "burst", "value": 12}
        )

        assert status == 200
        assert result["control"]["remaining"] > 0
        assert wait_until(lambda: simulation.tick == 12)
        _, snapshot = request(server, "GET", "/api/snapshot")
        assert snapshot["tick"] == 12
        assert snapshot["control"]["remaining"] == 0
        assert snapshot["control"]["running"] is False


def test_pause_interrompe_rajada_sem_ticks_depois_da_resposta():
    simulation = MinimalSimulation(step_delay=0.002)
    with running_server(simulation) as server:
        request(server, "POST", "/api/control", {"command": "speed", "value": 1000})
        request(server, "POST", "/api/control", {"command": "burst", "value": 100_000})
        assert wait_until(lambda: simulation.tick >= 3)

        status, result = request(server, "POST", "/api/control", {"command": "pause"})
        tick_when_paused = simulation.tick

        assert status == 200
        assert result["control"]["remaining"] == 0
        time.sleep(0.05)
        assert simulation.tick == tick_when_paused


def test_burst_nao_e_limitado_pela_velocidade_continua():
    simulation = MinimalSimulation()
    with running_server(simulation) as server:
        request(server, "POST", "/api/control", {"command": "speed", "value": 0.1})
        request(server, "POST", "/api/control", {"command": "burst", "value": 20})

        assert wait_until(lambda: simulation.tick == 20, timeout=1)


def test_run_contabiliza_custo_do_tick_no_periodo_da_velocidade():
    simulation = TimedSimulation(step_delay=0.03)
    with running_server(simulation) as server:
        request(server, "POST", "/api/control", {"command": "speed", "value": 20})
        request(server, "POST", "/api/control", {"command": "run"})
        assert wait_until(lambda: len(simulation.step_started_at) >= 5)
        request(server, "POST", "/api/control", {"command": "pause"})

        intervals = [
            later - earlier
            for earlier, later in zip(
                simulation.step_started_at[:4], simulation.step_started_at[1:5]
            )
        ]
        assert sum(intervals) / len(intervals) < 0.065


def test_falha_no_worker_pausa_e_fica_visivel_sem_matar_thread():
    simulation = FailingSimulation()
    with running_server(simulation) as server:
        request(server, "POST", "/api/control", {"command": "run"})

        assert wait_until(lambda: "error" in server.controller.control_state())
        _, snapshot = request(server, "GET", "/api/snapshot")
        assert snapshot["control"]["running"] is False
        assert "falha determinística" in snapshot["control"]["error"]
        assert server.controller.worker.is_alive()


@pytest.mark.parametrize(
    ("payload", "raw_body"),
    [
        ({"command": "desconhecido"}, None),
        ({"command": "burst", "value": 1_000_001}, None),
        ({"command": "burst", "value": -1}, None),
        ({"command": "speed", "value": 0}, None),
        ({"command": "speed", "value": 1e-300}, None),
        ({"command": "speed", "value": 1e300}, None),
        ({"command": "speed", "value": 10**400}, None),
        (None, b'{"command":"speed","value":NaN}'),
    ],
)
def test_entrada_invalida_retorna_json_400_e_preserva_estado(payload, raw_body):
    simulation = MinimalSimulation()
    with running_server(simulation) as server:
        if raw_body is None:
            status, error = request(server, "POST", "/api/control", payload)
        else:
            host, port = server.server_address[:2]
            connection = http.client.HTTPConnection(host, port, timeout=2)
            connection.request(
                "POST",
                "/api/control",
                body=raw_body,
                headers={"Content-Type": "application/json"},
            )
            response = connection.getresponse()
            status = response.status
            error = json.loads(response.read())
            connection.close()

        assert status == 400
        assert set(error) == {"error"}
        assert simulation.tick == 0
        assert server.controller.control_state() == {
            "running": False,
            "speed": 20.0,
            "remaining": 0,
        }


def test_comando_rejeita_origin_externo_sem_alterar_estado():
    simulation = MinimalSimulation()
    with running_server(simulation) as server:
        status, error = request(
            server,
            "POST",
            "/api/control",
            {"command": "step"},
            headers={"Origin": "https://exemplo.invalid"},
        )

        assert status == 400
        assert set(error) == {"error"}
        assert simulation.tick == 0


def test_regenerate_reseeds_a_fresh_world_and_resets_the_clock():
    config = PopulationConfig(width=10, height=8, population=4, objects=12, stones=2)
    simulation = PopulationSimulation(config)
    with running_server(simulation) as server:
        _, before = request(server, "GET", "/api/bootstrap")
        request(server, "POST", "/api/control", {"command": "step"})

        status, result = request(
            server, "POST", "/api/control", {"command": "regenerate", "value": 99}
        )
        assert status == 200
        assert result == {
            "tick": 0,
            "seed": 99,
            "control": {"running": False, "speed": 20.0, "remaining": 0},
        }

        fresh = server.controller.simulation
        assert fresh is not simulation
        assert fresh.config.seed == 99
        assert (fresh.config.width, fresh.config.population) == (10, 4)

        _, after = request(server, "GET", "/api/bootstrap")
        assert after["tick"] == 0
        assert after["worldRevision"] != before["worldRevision"]
        assert after["config"]["seed"] == 99
        # A different draw: agent placement no longer coincides.
        assert [a["x"] for a in after["agents"]] != [a["x"] for a in before["agents"]]


def test_regenerate_without_seed_redraws_with_the_same_seed():
    simulation = PopulationSimulation(PopulationConfig(population=3, objects=8, stones=1))
    with running_server(simulation) as server:
        status, result = request(
            server, "POST", "/api/control", {"command": "regenerate"}
        )
        assert status == 200
        assert result["seed"] == simulation.config.seed
        assert server.controller.simulation is not simulation


@pytest.mark.parametrize("value", [-1, 2**31, 1.5, "42"])
def test_regenerate_rejects_invalid_seeds_and_keeps_the_world(value):
    simulation = PopulationSimulation(PopulationConfig(population=3, objects=8, stones=1))
    with running_server(simulation) as server:
        status, error = request(
            server, "POST", "/api/control", {"command": "regenerate", "value": value}
        )
        assert status == 400
        assert set(error) == {"error"}
        assert server.controller.simulation is simulation


def test_regenerate_needs_a_dataclass_config():
    with running_server(MinimalSimulation()) as server:
        status, error = request(
            server, "POST", "/api/control", {"command": "regenerate", "value": 1}
        )
        assert status == 400
        assert "novo mundo" in error["error"]


def test_encerramento_para_worker():
    simulation = MinimalSimulation()
    server = create_server(simulation, port=0)
    worker = server.controller.worker

    server.server_close()

    assert not worker.is_alive()


def test_host_nao_local_e_rejeitado():
    with pytest.raises(ValueError, match="local"):
        create_server(MinimalSimulation(), host="0.0.0.0", port=0)
