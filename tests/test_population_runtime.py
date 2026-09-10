import copy
import pickle

from core.simulation.population import PopulationSimulation, PopulationConfig, Action


def small(**kw):
    return PopulationSimulation(PopulationConfig(width=12, height=10, population=6,
        objects=35, stones=3, reproduction=False, **kw))


def test_interleaved_runs_and_observation_do_not_change_evolution():
    a, b = small(seed=12), small(seed=12)
    for _ in range(100):
        a.snapshot(next(iter(a.agents)))
        a.step()
        b.step()
    assert a.snapshot() == b.snapshot()
    for uid in a.agents:
        assert a.agents[uid].memory.snapshot(a.tick) == b.agents[uid].memory.snapshot(b.tick)


def test_snapshot_is_detached_from_live_memory_and_decision():
    s = small()
    for _ in range(10):
        s.step()
    uid = next(iter(s.agents))
    original = copy.deepcopy(s.snapshot(uid))
    snapshot = s.snapshot(uid)
    snapshot['selected']['decision']['alternatives'].clear()
    snapshot['events'][0]['action'] = 'corrupted'
    assert s.snapshot(uid) == original


def test_reproduction_costs_body_reserves_and_never_copies_memory():
    s = PopulationSimulation(PopulationConfig(width=7, height=7, population=1, objects=0,
        stones=0, metabolism=0, maturity=1, birth_interval=10, reproduction=True))
    parent = next(iter(s.agents.values()))
    s.step({parent.uid: Action('wait')})
    children = [a for a in s.agents.values() if a is not parent]
    assert len(children) == 1
    assert parent.body.hunger == 35 and children[0].body.hunger == 35
    assert children[0].generation == 1
    assert not children[0].memory.relations and parent.memory.relations


def test_environment_renews_without_unbounded_object_or_event_growth():
    s = small(metabolism=0, renewal=2)
    for _ in range(500):
        s.step()
    assert len(s.objects) <= s.config.objects*2
    assert len(s.events) <= 200
    assert all(len(a.memory.relations) <= s.config.memory_capacity for a in s.agents.values())


def test_saved_rng_and_memories_continue_identically():
    s = small()
    for _ in range(30):
        s.step()
    restored = pickle.loads(pickle.dumps(s))
    for _ in range(70):
        s.step()
        restored.step()
    assert s.snapshot() == restored.snapshot()


def test_moving_inert_objects_does_not_create_new_matter_at_old_location():
    s = PopulationSimulation(PopulationConfig(width=7, height=7, population=0, objects=12,
        stones=0, renewal=1, metabolism=0, reproduction=False))
    inert = [o for o in s.objects.values() if not o.ingestible]
    for obj in inert:
        a = s.spawn(obj.x, obj.y)
        s._apply(a, Action('pick', obj.uid))
    s.step({a.uid: Action('wait') for a in s.agents.values()})
    assert sum(not o.ingestible for o in s.objects.values()) == 4


def test_newborn_memory_does_not_decay_since_the_start_of_the_world():
    s = PopulationSimulation(PopulationConfig(width=7, height=7, population=0, objects=0,
        stones=0, metabolism=0, reproduction=False))
    s.tick = 12000
    a = s.spawn(3, 3)
    for _ in range(31):
        s.step({a.uid: Action('wait')})
    relation = next(iter(a.memory.relations.values()))
    s.step({a.uid: Action('wait')})
    assert a.memory.forgotten == 0
    assert next(iter(a.memory.relations.values())).id == relation.id
    assert next(iter(a.memory.relations.values())).weight > 20
