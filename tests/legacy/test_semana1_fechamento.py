from legacy.simulation.config import ScenarioConfig
from legacy.simulation.scenario import build_scenario

def snapshot(simulation):
    return [
        (e.name, e.x, e.y, e.body.hunger, e.body.thirst, e.body.alive, e.last_action)
        for e in simulation.world.entities
    ]

def test_dez_gaianos_rodam_mil_passos_sem_render():
    config = ScenarioConfig(seed=42, num_organism=10, simulation_duration=1000, frame_delay=0)
    simulation = build_scenario(config)

    simulation.run(render_enabled=False)

    assert simulation.gtime.mtk == 1000
    assert len(simulation.world.entities) == 10

    for entity in simulation.world.entities:
        assert entity.last_action !="criado"

def test_mesma_seed_produz_o_mesmo_resultado():
    config = ScenarioConfig(seed=123, num_organism=10, simulation_duration=1000, frame_delay=0)
    simulacao_a = build_scenario(config)
    simulacao_a.run(render_enabled=False)

    simulacao_b = build_scenario(config)
    simulacao_b.run(render_enabled=False)

    assert snapshot(simulacao_a) == snapshot(simulacao_b)

def test_seeds_diferentes_podem_gerar_resultados_diferentes():
    config_a = ScenarioConfig(seed=1, num_organism=10, simulation_duration=1, frame_delay=0)
    config_b = ScenarioConfig(seed=2, num_organism=10, simulation_duration=1, frame_delay=0)

    simulacao_a = build_scenario(config_a)
    simulacao_a.run(render_enabled=False)

    simulacao_b = build_scenario(config_b)
    simulacao_b.run(render_enabled=False)

    assert snapshot(simulacao_a) != snapshot(simulacao_b)

