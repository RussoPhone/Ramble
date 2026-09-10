"""Physical consequences, sensory isolation, and persistent manipulations."""
import json
from dataclasses import asdict

from core.simulation import population


def arena():
    return population.PopulationSimulation(population.PopulationConfig(
        width=9, height=7, population=0, objects=0, stones=0,
        metabolism=0, reproduction=False, seed=7))


def test_sensor_never_receives_hidden_effects_and_walls_occlude():
    s = arena()
    a = s.spawn(2, 3)
    a.orientation = (1, 0)
    s.add_object(3, 3, appearance=(7, 2, 1), effect=(-40, 0))
    s.add_object(5, 3, appearance=(8, 2, 1), effect=(0, -40))
    from core.ambient.tile import STONE
    s.world.set_tile(4, 3, STONE)
    view = s.perceive(a)
    assert any(o.appearance == (7, 2, 1) for o in view.items)
    assert not any(o.appearance == (8, 2, 1) for o in view.items)
    encoded = json.dumps(asdict(view))
    assert all(word not in encoded for word in ('food', 'water', 'stone', 'effect', 'resource'))
    assert all(not hasattr(o, 'body') for o in view.items)


def test_field_of_view_matches_perceived_terrain_and_respects_occlusion():
    s = arena()
    a = s.spawn(4, 3)
    a.orientation = (1, 0)
    from core.ambient.tile import STONE
    s.world.set_tile(6, 3, STONE)

    fov = s.field_of_view(a)
    cells = {tuple(cell) for cell in fov}
    perceived = {(a.x + o.dx, a.y + o.dy) for o in s.perceive(a).terrain}

    assert cells == perceived
    assert all(isinstance(cell, list) and len(cell) == 2 for cell in fov)
    assert [a.x, a.y] in fov                       # own cell is always in view
    assert (6, 3) in cells                         # the blocking wall itself is seen
    assert (7, 3) not in cells                     # but nothing behind it
    assert (1, 3) not in cells                     # nor the half plane behind the body
    assert s.field_of_view(a) == fov and s.tick == 0  # pure: repeatable, no advance


def test_ingestion_requires_an_action_and_failure_is_experienced():
    s = arena()
    a = s.spawn(2, 3, micro_position=(8, 10))
    assert s._set_agent_position(a, 8, 10, (1, 0))
    a.body.hunger = 70
    obj = s.add_object(3, 3, appearance=(3, 4, 5), effect=(-30, 0))
    s.step({a.uid: population.Action('wait')})
    assert a.body.hunger == 70
    s.step({a.uid: population.Action('ingest', target=obj.uid)})
    assert a.body.hunger == 40
    assert obj.uid not in s.objects
    s.step({a.uid: population.Action('ingest', target=obj.uid)})
    assert a.memory.experiences[-1].success is False


def test_ground_object_interaction_requires_base_nose_target_alignment():
    cases = (
        ((8, 10), (1, 0), True),
        ((7, 10), (1, 0), False),
        ((8, 10), (0, -1), False),
    )
    for base, orientation, expected in cases:
        s = arena()
        a = s.spawn(base[0] // 3, base[1] // 3, micro_position=base)
        assert s._set_agent_position(a, *base, orientation)
        obj = s.add_object(3, 3, appearance=(3, 4, 5), effect=(-30, 0), quantity=2)
        a.body.hunger = 70

        assert s._apply(a, population.Action('ingest', target=obj.uid)) is expected
        assert a.body.hunger == (40 if expected else 70)


def test_touch_and_pick_use_the_microcell_directly_beyond_the_nose():
    s = arena()
    a = s.spawn(2, 3, micro_position=(8, 10))
    assert s._set_agent_position(a, 8, 10, (1, 0))
    target = s.add_object(3, 3, appearance=(3, 4, 5), quantity=2)
    distant = s.add_object(4, 3, appearance=(5, 4, 3), quantity=2)

    assert s._apply(a, population.Action('touch', target=target.uid))
    assert not s._apply(a, population.Action('touch', target=distant.uid))
    assert s._apply(a, population.Action('pick', target=target.uid))


def test_agent_interaction_requires_the_other_body_directly_beyond_the_nose():
    s = arena()
    a = s.spawn(2, 3, micro_position=(7, 10))
    b = s.spawn(3, 3, micro_position=(10, 10))
    assert s._set_agent_position(a, 7, 10, (1, 0))

    assert not s._apply(a, population.Action('touch', target=b.uid))
    assert s._set_agent_position(a, 8, 10, (1, 0))
    assert s._apply(a, population.Action('touch', target=b.uid))


def test_pick_carry_transfer_and_drop_persist_for_other_agents():
    s = arena()
    a = s.spawn(2, 3, micro_position=(8, 10))
    b = s.spawn(3, 3, micro_position=(10, 10))
    assert s._set_agent_position(a, 8, 10, (1, 0))
    obj = s.add_object(3, 3, appearance=(3, 4, 5), effect=(-30, 0))
    s.step({a.uid: population.Action('pick', target=obj.uid), b.uid: population.Action('wait')})
    assert a.carried == obj.uid and s.objects[obj.uid].carrier == a.uid
    s.step({a.uid: population.Action('give', target=b.uid), b.uid: population.Action('wait')})
    assert b.carried == obj.uid and a.carried is None
    s.step({a.uid: population.Action('wait'), b.uid: population.Action('drop')})
    assert s.objects[obj.uid].carrier is None
    assert (s.objects[obj.uid].x, s.objects[obj.uid].y) == (3, 3)


def test_observation_has_visible_action_but_never_other_body_delta():
    s = arena()
    a, b = s.spawn(2, 3), s.spawn(3, 3)
    a.orientation = (1, 0)
    obj = s.add_object(3, 3, appearance=(3, 4, 5), effect=(-30, 0))
    b.body.hunger = 80
    s.step({a.uid: population.Action('wait'), b.uid: population.Action('ingest', target=obj.uid)})
    observed = [e for e in a.memory.experiences if e.source == 'observed']
    assert observed and observed[-1].action == 'ingest'
    assert observed[-1].delta is None
    assert observed[-1].actor == b.uid


def test_dead_body_releases_occupancy_and_carried_object():
    s = arena()
    a = s.spawn(2, 3)
    obj = s.add_object(2, 3, appearance=(3, 4, 5), effect=(-30, 0))
    s.step({a.uid: population.Action('pick', target=obj.uid)})
    a.body.hunger = 100
    s.step()
    assert s.world.get_entity_at(2, 3) is None
    assert s.objects[obj.uid].carrier is None


def test_signal_is_local_and_has_no_predefined_meaning():
    s = arena()
    a, b, c = s.spawn(2, 3), s.spawn(3, 3), s.spawn(8, 6)
    a.orientation = (1, 0)
    s.step({a.uid: population.Action('wait'), b.uid: population.Action('signal', value=2), c.uid: population.Action('wait')})
    assert any(o.token == b.uid and o.signal == 2 for o in s.perceive(a).items)
    assert not any(o.token == b.uid for o in s.perceive(c).items)


def test_indistinguishable_visible_results_produce_same_social_experience():
    observations = []
    for ingestible in (True, False):
        s = arena()
        a, b = s.spawn(2, 3), s.spawn(3, 3)
        a.orientation = (1, 0)
        obj = s.add_object(3, 3, (3, 4, 5), (-30, 0), ingestible=ingestible, quantity=2)
        b.body.hunger = 80
        s.step({a.uid: population.Action('wait'), b.uid: population.Action('ingest', target=obj.uid)})
        observations.append((s.perceive(a), [e for e in a.memory.experiences if e.source == 'observed']))
    # Physical success and B's hidden body differ; sensory input does not.
    assert observations[0][0] == observations[1][0]
    assert observations[0][1] == observations[1][1]


def test_losing_sight_of_target_does_not_reveal_consumption():
    s = arena()
    a, b = s.spawn(2, 3), s.spawn(4, 3)
    a.orientation = (1, 0)
    obj = s.add_object(4, 3, (3, 4, 5), (-30, 0))
    s.step({a.uid: population.Action('move', dx=-1), b.uid: population.Action('ingest', target=obj.uid)})
    assert not any(e.action == 'ingest' for e in a.memory.experiences if e.source == 'observed')


def test_target_of_observed_gesture_is_explicitly_present_in_sensory_input():
    s = arena()
    a, b = s.spawn(2, 3), s.spawn(3, 3)
    a.orientation = (1, 0)
    obj = s.add_object(3, 3, (3, 4, 5), ingestible=False)
    s.step({a.uid: population.Action('wait'), b.uid: population.Action('touch', target=obj.uid)})
    gesture = next(o for o in s.perceive(a).items if o.token == b.uid)
    assert gesture.action_target == obj.uid
    observed = [e for e in a.memory.experiences if e.source == 'observed']
    assert observed[-1].target == gesture.action_target


def test_population_entities_have_real_microcell_shapes_in_physical_space():
    s = arena()
    a = s.spawn(2, 3)
    obj = s.add_object(2, 3, (3, 4, 5))

    assert len(s.physical.cells_for("agent", a.uid)) > 1
    assert len(s.physical.cells_for("object", obj.uid)) >= 1


def test_gaiano_occupies_base_and_nose_and_moves_one_microcell():
    s = arena()
    a = s.spawn(2, 2, micro_position=(7, 7))
    assert s._set_agent_position(a, 7, 7, (1, 0))

    assert s.physical.cells_for("agent", a.uid) == ((7, 7), (8, 7))
    assert s._apply(a, population.Action("move", dx=1, dy=0))
    assert (a.micro_x, a.micro_y) == (8, 7)
    assert (a.x, a.y) == (2, 2)
    assert a.odometry == (1, 0)


def test_three_microsteps_cross_one_tile_width():
    s = arena()
    a = s.spawn(2, 2, micro_position=(6, 7))

    for _ in range(3):
        assert s._apply(a, population.Action("move", dx=1, dy=0))

    assert (a.micro_x, a.micro_y) == (9, 7)
    assert (a.x, a.y) == (3, 2)


def test_nose_cannot_enter_blocking_terrain_before_base():
    from core.ambient.tile import STONE

    s = arena()
    a = s.spawn(2, 2, micro_position=(7, 7))
    assert s._set_agent_position(a, 7, 7, (1, 0))
    s.world.set_tile(3, 2, STONE)
    before = (a.micro_x, a.micro_y, a.x, a.y, a.orientation, a.odometry,
              s.physical.cells_for("agent", a.uid))

    assert not s._apply(a, population.Action("move", dx=1, dy=0))
    assert (a.micro_x, a.micro_y, a.x, a.y, a.orientation, a.odometry,
            s.physical.cells_for("agent", a.uid)) == before


def test_turn_fails_atomically_when_new_nose_cell_is_occupied():
    s = arena()
    a = s.spawn(2, 2, micro_position=(7, 7))
    blocker = s.spawn(2, 2, micro_position=(8, 7))
    before = (a.orientation, s.physical.cells_for("agent", a.uid))

    assert not s._apply(a, population.Action("turn", value=1))
    assert (a.orientation, s.physical.cells_for("agent", a.uid)) == before
    assert set(s.physical.cells_for("agent", a.uid)).isdisjoint(
        s.physical.cells_for("agent", blocker.uid)
    )


def test_perception_projects_partial_visible_shape_without_hidden_effects():
    s = arena()
    a = s.spawn(2, 3)
    a.orientation = (1, 0)
    blocker = s.add_object(3, 3, (9, 9, 9), portable=False, ingestible=False, blocking=True)
    target = s.add_object(4, 3, (3, 4, 5), effect=(-30, 0), shape=((0, 0), (1, 1), (2, 2)))

    seen = next(o for o in s.perceive(a).items if o.token == target.uid)

    assert seen.shape
    assert tuple(seen.shape) != tuple(target.shape.cells)
    encoded = json.dumps(asdict(seen))
    assert "effect" not in encoded
    assert "food" not in encoded
    assert blocker.uid in s.objects


def test_self_manipulation_experience_keeps_target_material_and_terrain_context():
    s = arena()
    a = s.spawn(2, 3, micro_position=(8, 10))
    assert s._set_agent_position(a, 8, 10, (1, 0))
    obj = s.add_object(3, 3, (3, 4, 5), effect=(-30, 0), kind="food")

    s.step({a.uid: population.Action("pick", target=obj.uid)})
    experience = a.memory.experiences[-1]

    assert experience.action == "pick"
    assert experience.target == obj.uid
    assert experience.signature == obj.appearance
    assert experience.visible_change == ("changed",)
    assert experience.context
