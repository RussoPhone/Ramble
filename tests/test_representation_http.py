from core.ambient.tile import WATER
from tests.test_population_interface import running_server, request
from tests.test_representation import simulation


def test_new_api_never_uses_legacy_snapshot_and_preserves_controls():
    s = simulation()
    s.snapshot = lambda *_: (_ for _ in ()).throw(AssertionError('legacy'))
    with running_server(s) as server:
        status, b = request(server, 'GET', '/api/bootstrap')
        assert status == 200 and b['control']['running'] is False
        status, f = request(server, 'GET', '/api/frame')
        assert status == 200 and f['worldRevision'] == b['worldRevision']
        assert 'terrain' not in f and s.tick == 0
        a = f['agents'][0]
        for path in (f"/api/selection/agent/{a['id']}",
                     f"/api/selection/object/{f['objects'][0]['id']}",
                     f"/api/selection/cell/{a['x']}/{a['y']}"):
            status, detail = request(server, 'GET', path)
            assert status == 200 and detail['detail']
            assert detail['tick'] == 0
        request(server, 'POST', '/api/control', {'command': 'step'})
        _, f = request(server, 'GET', '/api/frame')
        assert f['tick'] == 1
        assert f['worldRevision'] == b['worldRevision']
        with server.controller._condition:
            s.world.set_tile(0, 0, WATER)
        _, f = request(server, 'GET', '/api/frame')
        assert f['worldRevision'] != b['worldRevision']
        assert request(server, 'GET', '/api/selection/cell/bad/0')[0] == 400
        assert request(server, 'GET', '/api/selection/object/-1')[1]['detail'] is None


def test_new_modules_are_served_and_traversal_is_rejected():
    with running_server(simulation()) as server:
        for path in ('/transport.mjs', '/store.mjs', '/selection.mjs',
                     '/renderers/ascii-renderer.mjs', '/renderers/base-renderer.mjs'):
            assert request(server, 'GET', path)[0] == 200
        assert request(server, 'GET', '/renderers/canvas-tile-renderer.mjs')[0] == 404
        assert request(server, 'GET', '/assets/manifest.json')[0] == 404
        assert request(server, 'GET', '/../../core/main.py')[0] == 404
