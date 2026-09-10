from toys.toy001_survival_instinct.world import build_toy_world


def test_toy_rng_does_not_depend_on_other_simulations():
    a = build_toy_world(seed=42, num_organism=4, duration=80)
    b = build_toy_world(seed=42, num_organism=4, duration=80)
    a.run(render_enabled=False)
    b.run(render_enabled=False)
    assert [(e.x, e.y, e.body.hunger, e.body.thirst) for e in a.world.entities] == [
        (e.x, e.y, e.body.hunger, e.body.thirst) for e in b.world.entities]
