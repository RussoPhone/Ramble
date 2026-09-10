import pickle
import os
import random

from core.ambient.tile import WATER
from core.representation.projector import RepresentationProjector
from core.simulation.population import PopulationConfig, PopulationSimulation


def simulation():
    return PopulationSimulation(PopulationConfig(width=12, height=10, population=6,
        objects=35, stones=3, reproduction=False, metabolism=0))


def test_bootstrap_and_frame_have_explicit_layers_and_preserve_grass():
    s = simulation()
    p = RepresentationProjector(s)
    b = p.bootstrap()
    f = p.frame()
    assert b['schemaVersion'] == 2
    assert b['worldRevision'] == f['worldRevision']
    assert len(b['terrain']) == 120
    assert {t['kind'] for t in b['terrain']} == {'grass', 'stone'}
    assert all(t['layer'] == 'terrain' for t in b['terrain'])
    assert all(o['layer'] == 'object' for o in f['objects'])
    assert all(a['layer'] == 'agent' for a in f['agents'])
    assert not {'terrain', 'config', 'catalog'} & f.keys()
    assert b['config']['seed'] == s.config.seed


def test_projection_details_do_not_mutate_any_runtime_state_or_rng():
    s = simulation()
    for _ in range(10):
        s.step()
    before = pickle.dumps(s)
    p = RepresentationProjector(s)
    for _ in range(3):
        p.bootstrap()
        p.frame()
        p.agent(next(iter(s.agents)))
        p.object(next(iter(s.objects)))
        p.cell(0, 0)
    assert pickle.dumps(s) == before


def test_projection_needs_no_random_source_even_for_revision_identity(monkeypatch):
    s = simulation()

    def forbidden(*args, **kwargs):
        raise AssertionError('projection requested random data')

    monkeypatch.setattr(os, 'urandom', forbidden)
    monkeypatch.setattr(random, 'random', forbidden)
    monkeypatch.setattr(random.Random, 'random', forbidden)
    monkeypatch.setattr(random.Random, 'getrandbits', forbidden)
    p = RepresentationProjector(s)
    p.bootstrap()
    p.frame()
    p.detail('agent', next(iter(s.agents)))
    p.detail('agent', next(iter(s.agents)), 'memory')
    p.detail('agent', next(iter(s.agents)), 'log')
    p.detail('terrain', (0, 0))


def test_projection_returns_detached_records_and_does_not_call_runtime_snapshot():
    s = simulation()
    s.snapshot = lambda *_: (_ for _ in ()).throw(AssertionError('legacy snapshot'))
    p = RepresentationProjector(s)
    f = p.frame()
    f['agents'][0]['body']['hunger'] = 999
    assert next(iter(s.agents.values())).body.hunger == 0
    assert p.bootstrap()['terrain']


def test_agent_summary_detail_carries_the_field_of_view():
    s = simulation()
    a = next(iter(s.agents.values()))
    detail = RepresentationProjector(s).detail('agent', a.uid)['detail']
    assert detail['vision'] == s.field_of_view(a)
    assert [a.x, a.y] in detail['vision']
    # Frames stay lean: vision is a per-selection cost, never broadcast.
    assert 'vision' not in RepresentationProjector(s).frame()['agents'][0]
    assert RepresentationProjector(s).detail('agent', -123)['detail'] is None


def test_revisions_change_only_for_static_world_or_session_changes():
    s = simulation()
    p = RepresentationProjector(s)
    revision = p.bootstrap()['worldRevision']
    s.step()
    assert p.frame()['worldRevision'] == revision
    s.world.set_tile(0, 0, WATER)
    assert p.frame()['worldRevision'] != revision
    assert RepresentationProjector(s).frame()['worldRevision'] != p.frame()['worldRevision']


def test_cell_details_preserve_all_objects_and_agent():
    s = simulation()
    a = next(iter(s.agents.values()))
    first = s.add_object(a.x, a.y, (1, 2, 3), kind='food')
    second = s.add_object(a.x, a.y, (3, 2, 1), kind='stone')
    p = RepresentationProjector(s)
    cell = p.cell(a.x, a.y)
    assert cell['terrain']['layer'] == 'terrain'
    assert cell['agent']['id'] == a.uid
    assert {first.uid, second.uid} <= {o['id'] for o in cell['objects']}
    assert p.agent(-123) is None
    assert p.object(-123) is None
    assert p.cell(-1, 0) is None


def test_carried_object_uses_carrier_position_and_is_not_duplicated_on_ground():
    s = simulation()
    a = next(iter(s.agents.values()))
    obj = s.add_object(a.x, a.y, (13, 4, 2), kind='food')
    s._detach(obj)
    obj.carrier, a.carried = a.uid, obj.uid
    obj.x, obj.y = -1, -1  # Carried object's old coordinates are not authoritative.
    p = RepresentationProjector(s)
    carried = p.agent(a.uid)['carrying']
    assert carried['layer'] == 'object' and carried['kind'] == 'food'
    assert (carried['x'], carried['y']) == (a.x, a.y)
    assert p.object(obj.uid) == carried
    assert obj.uid not in {item['id'] for item in p.frame()['objects']}


def test_projection_exposes_microcell_agent_geometry_without_internal_effects():
    s = simulation()
    a = next(iter(s.agents.values()))
    obj = s.add_object(a.x, a.y, (13, 4, 2), effect=(-99, 0), shape=((0, 0), (1, 1), (2, 2)))
    p = RepresentationProjector(s)

    agent = p.agent(a.uid)
    projected = p.object(obj.uid)

    assert agent["micro_position"] == (a.micro_x, a.micro_y)
    assert agent["collision_cells"] == s.physical.cells_for("agent", a.uid)
    assert (agent["x"], agent["y"]) == (a.micro_x // 3, a.micro_y // 3)
    assert len(agent["collision_cells"]) == 2
    assert projected["cells"] == ((0, 0), (1, 1), (2, 2))
    assert "effect" not in projected


def test_same_kind_in_distinct_layers_and_configuration_revision():
    s = simulation()
    s.world.set_tile(0, 0, WATER)
    obj = s.add_object(0, 0, (29, 7, 3), kind='water')
    p = RepresentationProjector(s)
    cell = p.cell(0, 0)
    assert cell['terrain']['kind'] == p.object(obj.uid)['kind'] == 'water'
    assert cell['terrain']['layer'] != p.object(obj.uid)['layer']
    revision = p.bootstrap()['worldRevision']
    s.config.renewal += 1
    assert p.bootstrap()['worldRevision'] != revision
    assert p.bootstrap()['config']['renewal'] == s.config.renewal


def test_observed_and_unobserved_simulations_evolve_identically():
    observed, control = simulation(), simulation()
    p = RepresentationProjector(observed)
    for _ in range(40):
        p.bootstrap()
        p.frame()
        for uid in observed.agents:
            p.agent(uid)
        observed.step()
        control.step()
    assert pickle.dumps(observed) == pickle.dumps(control)
