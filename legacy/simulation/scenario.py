import random

from core.ambient.world import World
from legacy.ambient.sky import Sky
from core.ambient.tile import WATER, FOOD, GRASS, STONE
from core.being.organism import Organism
from legacy.simulation.renderer import Renderer
from legacy.simulation.gtime import Gtime
from legacy.simulation.simulation import Simulation
from legacy.sense.sensor import Sensor

def place_tiles(world, tile, amount, reserve_grass=0, rng=None):
    rng = rng or random.Random()
    available = [
        (x, y)
        for y in range(world.height)
        for x in range(world.width)
        if world.get_tile(x, y) == GRASS
    ]
    amount_to_place = min(amount, max(0, len(available) - reserve_grass))

    for x, y in rng.sample(available, amount_to_place):
        world.set_tile(x, y, tile)

def random_passable_position(world, rng=None):
    rng = rng or random.Random()
    available = [
        (x, y)
        for y in range(world.height)
        for x in range(world.width)
        if world.get_tile(x, y) == GRASS and world.is_passable(x, y)
    ]
    if not available:
        raise ValueError("não há posição livre de grama para a entidade")
    return rng.choice(available)

def build_scenario(config): #monta um cenario completo a partir da scenarioconfig
    rng = random.Random(config.seed)
    
    world = World(config.world_width, config.world_height)

    capacity = config.world_width * config.world_height
    if config.num_organism > capacity:
        raise ValueError("quantidade de organismos excede a capacidade do mundo")
    
    place_tiles(world, WATER, config.num_water_tiles, reserve_grass=config.num_organism, rng=rng)
    place_tiles(world, FOOD, config.num_food_tiles, reserve_grass=config.num_organism, rng=rng)
    place_tiles(world, STONE, config.num_stone_tiles, reserve_grass=config.num_organism, rng=rng)

    for i in range(config.num_organism):
        x, y = random_passable_position(world, rng=rng)
        organism = Organism(
            f"gaiano_{i}",
            str(i),
            x,
            y,
            sensor=Sensor(range_=6))
        
        world.add_entity(organism)

    sky = Sky()
    renderer = Renderer()
    gtime = Gtime(mtksptk=config.mtksptk)

    simulation = Simulation(
        world=world,
        sky=sky,
        renderer=renderer,
        gtime=gtime,
        simulation_duration=config.simulation_duration,
        frame_delay=config.frame_delay,
        )

    simulation.rng = rng
    return simulation
