from legacy.simulation.config import ScenarioConfig
from legacy.simulation.scenario import build_scenario
from toys.toy001_survival_instinct.naive_policy import NaivePolicy 

def build_toy_world(seed=671, num_organism=10, duration=10000):
  config = ScenarioConfig(seed=seed, num_organism=num_organism, simulation_duration=duration, frame_delay=0.1)

  simulation = build_scenario(config)
  for entity in simulation.world.entities:
    entity.decision_system = NaivePolicy(simulation.rng)
  return simulation 
