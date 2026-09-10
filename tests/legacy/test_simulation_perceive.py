from core.ambient.world import World
from core.ambient.tile import WATER, GRASS
from core.being.organism import Organism
from legacy.sense.sensor import Sensor
from legacy.ambient.sky import Sky
from legacy.simulation.renderer import Renderer
from legacy.simulation.gtime import Gtime
from legacy.simulation.simulation import Simulation


def build_simulacao(width=6, height=3):
    world = World(width, height)
    simulation = Simulation(
        world=world, sky=Sky(), renderer=Renderer(),
        gtime=Gtime(mtksptk=24), simulation_duration=10, frame_delay=0,
    )
    return simulation, world


def test_percebe_agua_a_frente_dentro_do_alcance():
    simulation, world = build_simulacao()
    world.set_tile(4, 1, WATER)

    gaiano = Organism("g", "@", 1, 1, sensor=Sensor(range_=5, requires_light=False))
    gaiano.orientation = (1, 0)
    world.add_entity(gaiano)

    percepcao = simulation.perceive(gaiano)
    assert percepcao is not None 
    superficies = [r["appearance"] for r in percepcao.reading]
    assert WATER.appearance in superficies

def test_nao_percebe_o_que_esta_atras():
    simulation, world = build_simulacao()
    world.set_tile(0, 1, WATER)

    gaiano = Organism("g", "@", 3, 1, sensor=Sensor(range_=5, requires_light=False))
    gaiano.orientation = (1, 0)  # de costas pra água, que está à esquerda
    world.add_entity(gaiano)

    percepcao = simulation.perceive(gaiano)
    assert percepcao is not None 
    superficies = [r["appearance"] for r in percepcao.reading]
    assert WATER.appearance not in superficies
 
def test_sem_sensor_nao_percebe_nada():
    simulation, world = build_simulacao()
    gaiano = Organism("g", "@", 1, 1, sensor=None)
    world.add_entity(gaiano)

    assert simulation.perceive(gaiano) is None

def test_nao_percebe_alem_do_proprio_alcance():
    simulation, world = build_simulacao(width=10, height=3)
    world.set_tile(9, 1, WATER)

    gaiano = Organism("g", "@", 0, 1, sensor=Sensor(range_=2, requires_light=False))
    gaiano.orientation = (1, 0)
    world.add_entity(gaiano)

    percepcao = simulation.perceive(gaiano)
    assert percepcao is not None 
    superficies = [r["appearance"] for r in percepcao.reading]
    assert WATER.appearance not in superficies

def test_percepcao_nao_inclui_a_propria_posicao():
    simulation, world = build_simulacao()
    gaiano = Organism("g", "@", 2, 1, sensor=Sensor(range_=3, requires_light=False))
    world.add_entity(gaiano)

    percepcao = simulation.perceive(gaiano)
    assert percepcao is not None 
    posicoes = [(r["dx"], r["dy"]) for r in percepcao.reading]
    assert (0, 0) not in posicoes
