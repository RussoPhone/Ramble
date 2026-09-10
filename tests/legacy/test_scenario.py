from legacy.simulation.config import ScenarioConfig
from legacy.simulation.scenario import build_scenario
from core.ambient.tile import STONE

def test_nenhum_gaiano_nasce_em_cima_de_pedra():
    config = ScenarioConfig(seed=17, num_organism=10, num_stone_tiles=40)
    simulation = build_scenario(config)

    for entity in simulation.world.entities:
        tile = simulation.world.get_tile(entity.x, entity.y)
        assert tile is not STONE

def test_todo_gaiano_nasce_com_sensor():
    config = ScenarioConfig(seed=5, num_organism=5)
    simulation = build_scenario(config)

    for entity in simulation.world.entities:
        assert entity.sensor is not None

def test_mundo_contem_a_quantidade_de_pedras_configurada():
    config = ScenarioConfig(seed=5, world_width=20, world_height=20, num_stone_tiles=12)
    simulation = build_scenario(config)

    total_pedras = sum(
        1
        for row in simulation.world.tiles
        for tile in row
        if tile is STONE
    )
    assert total_pedras == 12
