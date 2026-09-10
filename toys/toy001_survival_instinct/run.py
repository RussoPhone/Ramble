from toys.toy001_survival_instinct.world import build_toy_world 

simulation = build_toy_world(seed=43, num_organism=5, duration=300)
simulation.run(render_enabled=True)
