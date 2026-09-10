import http.client
import threading

from core.experiments.registry import Experiment, ExperimentRegistry
from core.interface.launcher import create_launcher_server


def entry(slug, name):
    return Experiment(slug, name, lambda: object(), lambda simulation, host, port: None)


def request(server, method, path, headers=None):
    host, port = server.server_address[:2]
    connection = http.client.HTTPConnection(host, port, timeout=2)
    request_headers = {"Host": f"127.0.0.1:{port}"}
    request_headers.update(headers or {})
    connection.request(method, path, headers=request_headers)
    response = connection.getresponse()
    body = response.read()
    connection.close()
    return response.status, body


def test_launcher_shows_only_short_names_and_buttons():
    registry = ExperimentRegistry((entry("mundo", "Mundo"), entry("memoria", "Memória")))
    server = create_launcher_server(registry, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        status, html = request(server, "GET", "/")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert status == 200
    assert html.count(b"<button") == 2
    assert b"Mundo" in html and b"Mem\xc3\xb3ria" in html
    assert b"description" not in html.lower()
    assert b"<p" not in html


def test_launcher_navigates_groups_and_selects_only_a_runnable_leaf():
    messiah = entry("messias", "Messias")
    registry = ExperimentRegistry(
        (entry("mundo", "Mundo"), Experiment("culinaria", "Culinária", subexperiments=(messiah,)))
    )
    server = create_launcher_server(registry, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        status, root = request(server, "GET", "/")
        submenu_status, submenu = request(server, "GET", "/experiments/culinaria")
        group_status, _ = request(server, "POST", "/experiments/culinaria")
        selected_status, transition = request(
            server, "POST", "/experiments/culinaria/messias"
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert status == 200 and b"Culin\xc3\xa1ria" in root
    assert submenu_status == 200 and b"Messias" in submenu
    assert group_status == 400
    assert selected_status == 200 and b"location.replace" in transition
    assert server.selected is messiah


def test_launcher_rejects_unknown_paths_without_selecting_anything():
    server = create_launcher_server(ExperimentRegistry((entry("mundo", "Mundo"),)), port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        status, _ = request(server, "POST", "/experiments/desconhecido")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert status == 404
    assert server.selected is None


def test_launcher_rejects_selection_from_an_external_origin():
    server = create_launcher_server(ExperimentRegistry((entry("mundo", "Mundo"),)), port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        status, _ = request(
            server,
            "POST",
            "/experiments/mundo",
            {"Origin": "https://example.test"},
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert status == 400
    assert server.selected is None
