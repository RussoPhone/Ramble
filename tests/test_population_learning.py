"""Behavioral assays: no semantics, real experience, reversal and social exposure."""
import random

from core.cognition.records import Action, Experience, Observation, View
from core.cognition.memory import RelationalMemory
from core.cognition.decision import Decision


X, Y = (17, 2, 6), (31, 5, 8)


def view():
    return View((70., 20.), (
        Observation(1, X, 0, 0), Observation(2, Y, 0, 0)), (), 1)


def choice_counts(memory, seed=11):
    policy = Decision(random.Random(seed), exploration=0.05)
    counts = {1: 0, 2: 0}
    for _ in range(400):
        action = policy.choose(view(), memory, (Action('ingest', 1), Action('ingest', 2)))
        counts[action.target] += 1
    return counts


def learn(memory, signature, delta, tick, source='self'):
    memory.record(Experience(tick, (70., 20.), signature, 'ingest', delta,
        True, source=source, actor=44 if source == 'observed' else 1,
        visible_change=('vanished',), location=(0, 0)))


def test_blank_agent_has_no_resource_preference():
    counts = choice_counts(RelationalMemory())
    assert 160 < counts[1] < 240


def test_repeated_consequences_change_choices_and_reversal_is_relearned():
    m = RelationalMemory()
    for t in range(12):
        learn(m, X, (-30., 0.), t)
        learn(m, Y, (0., 0.), t)
    assert choice_counts(m)[1] > 360
    for t in range(12, 70):
        learn(m, X, (0., 0.), t)
        learn(m, Y, (-30., 0.), t)
    assert choice_counts(m)[2] > 360
    assert any(r.contradictions > 0 for r in m.relations.values())


def test_observation_promotes_trials_without_inventing_internal_consequences():
    observed, blank = RelationalMemory(), RelationalMemory()
    for t in range(6):
        learn(observed, Y, None, t, source='observed')
    assert choice_counts(observed)[2] > choice_counts(blank)[2] + 100
    assert all(r.delta is None for r in observed.relations.values())
    assert all(e.delta is None for e in observed.experiences)


def test_memory_is_individual_bounded_decays_and_has_traceable_context():
    a, b = RelationalMemory(capacity=8, experience_capacity=16), RelationalMemory()
    for t in range(80):
        learn(a, (t, 2, 1), (-20., 0.), t)
    assert len(a.relations) <= 8 and len(a.experiences) <= 16
    assert not b.relations and not b.experiences
    assert a.forgotten > 0
    r = next(iter(a.relations.values()))
    assert r.body_context and r.evidence and r.action == 'ingest'
    old = r.weight
    a.decay(500)
    assert not a.relations or next(iter(a.relations.values())).weight < old


def test_context_keeps_signal_and_bodily_state_in_the_relation():
    m = RelationalMemory()
    for signal, body, delta in ((0, (80., 0.), (-30., 0.)), (1, (0., 80.), (0., -30.))):
        m.record(Experience(1, body, X, 'touch', delta, True, signal=signal))
    assert len(m.relations) == 2
    assert {r.signal for r in m.relations.values()} == {0, 1}


def test_perceived_signal_can_condition_action_without_assigned_meaning():
    m = RelationalMemory()
    for tick in range(20):
        for signal in (0, 1):
            for signature in (X, Y):
                useful = (signature == X) == (signal == 0)
                m.record(Experience(tick, (70., 20.), signature, 'ingest',
                    (-30., 0.) if useful else (0., 0.), True, signal=signal))
    policy = Decision(random.Random(10), exploration=0)
    for signal, expected in ((0, 1), (1, 2)):
        sensed = View((70., 20.), (*view().items, Observation(99, (5, 5, 5), 0, 1, signal=signal)), (), 1)
        assert policy.choose(sensed, m, (Action('ingest', 1), Action('ingest', 2))).target == expected
