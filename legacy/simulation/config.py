from dataclasses import dataclass

@dataclass
class ScenarioConfig: #Config central de um cenario de simulação
    seed: int = 42
    num_water_tiles: int = 15
    num_food_tiles: int = 10
    num_stone_tiles: int = 8
    world_width: int = 20
    world_height: int = 10
    num_organism: int = 10
    mtksptk: int = 24
    simulation_duration: int = 120
    frame_delay: float = 0.08
