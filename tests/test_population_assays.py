"""Closed physical arenas. Interventions are researcher controls, not agent rules."""
from statistics import mean

from core.simulation.population import PopulationSimulation, PopulationConfig, Action


def arena(seed=1, observation=True):
    s = PopulationSimulation(PopulationConfig(seed=seed, width=7, height=7, population=0,
        objects=0, stones=0, metabolism=0, reproduction=False, observe=observation))
    a = s.spawn(3, 3, micro_position=(11, 10))
    assert s._set_agent_position(a, 11, 10, (1, 0))
    x = s.add_object(4, 3, (91, 3, 7), (-30., 0.), quantity=1000)
    y = s.add_object(4, 3, (82, 8, 2), (0., 0.), quantity=1000)
    return s, a, x, y


def selections(s, a, x, y, n=100):
    a.body.hunger, a.body.thirst = 70., 10.
    view = s.perceive(a)
    actions = (Action('ingest', x.uid), Action('ingest', y.uid))
    return [a.decision_system.choose(view, a.memory, actions).target for _ in range(n)]


def test_real_ingestion_is_learned_and_effect_swap_reverses_behavior():
    s, a, x, y = arena()
    before = selections(s, a, x, y).count(x.uid)
    assert 25 < before < 75
    for _ in range(15):
        for obj in (x, y):
            a.body.hunger = 70.
            s.step({a.uid: Action('ingest', obj.uid)})
    assert selections(s, a, x, y).count(x.uid) >= 80
    x.effect, y.effect = y.effect, x.effect
    for _ in range(40):
        for obj in (x, y):
            a.body.hunger = 70.
            s.step({a.uid: Action('ingest', obj.uid)})
    assert selections(s, a, x, y).count(y.uid) >= 80
    assert any(e.delta == (-30., 0.) and e.signature == y.appearance for e in a.memory.experiences)


def trial_latency(seed, observation):
    s, a, x, y = arena(seed, observation)
    # Y is beneficial in this scenario; X is not. Same cognitive code.
    x.effect, y.effect = (0., 0.), (-30., 0.)
    demonstrator = s.spawn(4, 4, micro_position=(13, 12))
    assert s._set_agent_position(demonstrator, 13, 12, (0, -1))
    for _ in range(5):
        demonstrator.body.hunger = 70.
        s.step({a.uid: Action('wait'), demonstrator.uid: Action('ingest', y.uid)})
    observed = [e for e in a.memory.experiences if e.source == 'observed']
    assert all(e.delta is None for e in observed)
    # Same motor choices and physical feedback for exposed and unexposed agents.
    for trial in range(1, 25):
        a.body.hunger = 70.
        action = a.decision_system.choose(s.perceive(a), a.memory,
                                         (Action('ingest', x.uid), Action('ingest', y.uid)))
        s.step({a.uid: action, demonstrator.uid: Action('wait')})
        if a.body.hunger < 70.:
            return trial
    return 25


def test_visible_demonstration_reduces_trials_to_first_personal_discovery():
    exposed = [trial_latency(seed, True) for seed in range(40)]
    controls = [trial_latency(seed, False) for seed in range(40)]
    assert mean(exposed) < mean(controls) * .75


def test_same_appearance_different_effect_does_not_change_naive_choice():
    a, ga, x, y = arena(8)
    b, gb, bx, by = arena(8)
    bx.effect, by.effect = by.effect, bx.effect
    assert selections(a, ga, x, y) == selections(b, gb, bx, by)
