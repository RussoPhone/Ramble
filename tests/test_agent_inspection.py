import pickle

from core.cognition.records import Experience
from core.representation import RepresentationProjector
from tests.test_representation import simulation
from tests.test_population_interface import running_server, request


def populated():
    s = simulation()
    a = next(iter(s.agents.values()))
    a.memory.record(Experience(0, (30., 20.), (13, 4, 2), 'ingest', (-42., 0.), True,
                               actor=a.uid, target=20))
    a.memory.record(Experience(0, (30., 20.), (29, 7, 3), 'touch', None, None,
                               source='observed', actor=999, target=21))
    s._event(a.uid, 'pick', target=20, position=(a.x, a.y))
    s._event(999, 'give', target=a.uid, position=(0, 0))
    s._event(998, 'pick', target=1000, position=(0, 0))
    return s, a


def test_memory_is_explicit_detached_and_preserves_uncertainty_without_kind_inference():
    s, a = populated()
    p = RepresentationProjector(s)
    before = pickle.dumps(s)
    data = p.detail('agent', a.uid, 'memory')['detail']
    assert data['agentId'] == a.uid
    assert len(data['relations']) == 2
    own, observed = data['relations']
    assert own['signature'] == (13, 4, 2)
    assert own['delta'] == (-42., 0.)
    assert observed['delta'] is None
    assert observed['evidence'][0]['success'] is None
    assert 'kind' not in own and 'kind' not in own['evidence'][0]
    data['relations'][0]['sources']['self'] = 999
    assert pickle.dumps(s) == before
    assert not {'memory', 'relations', 'experiences'} & p.frame()['agents'][0].keys()


def test_log_filters_physical_participation_and_keeps_experience_sources_separate():
    s, a = populated()
    p = RepresentationProjector(s)
    before = pickle.dumps(s)
    log = p.detail('agent', a.uid, 'log')['detail']
    assert [e['actor'] for e in log['events']] == [a.uid, 999]
    assert {e['source'] for e in log['experiences']} == {'self', 'observed'}
    assert log['eventCapacity'] == 200
    assert log['experienceCapacity'] == s.config.experience_capacity
    assert pickle.dumps(s) == before
    assert p.detail('agent', -1, 'memory')['detail'] is None
    assert p.detail('agent', -1, 'log')['detail'] is None


def test_inspection_http_never_uses_snapshot_or_perception_and_is_read_only():
    s, a = populated()
    before = pickle.dumps(s)
    with running_server(s) as server:
        for section in ('memory', 'log'):
            status, data = request(server, 'GET', f'/api/selection/agent/{a.uid}/{section}')
            assert status == 200
            assert data['detail']['agentId'] == a.uid
            assert data['tick'] == 0 and data['worldRevision']
        assert request(server, 'GET', '/api/selection/agent/1/unknown')[0] == 400
    assert pickle.dumps(s) == before

    def forbidden(*args):
        raise AssertionError('inspection crossed an active runtime method')

    s.snapshot = s.perceive = a.memory.snapshot = forbidden
    p = RepresentationProjector(s)
    assert p.detail('agent', a.uid, 'memory')['detail']['relations']
    assert p.detail('agent', a.uid, 'log')['detail']['experiences']


def test_deep_readings_do_not_change_subsequent_population_evolution():
    observed, control = simulation(), simulation()
    p = RepresentationProjector(observed)
    for _ in range(20):
        for uid in observed.agents:
            p.detail('agent', uid, 'memory')
            p.detail('agent', uid, 'log')
        observed.step()
        control.step()
    assert pickle.dumps(observed) == pickle.dumps(control)
