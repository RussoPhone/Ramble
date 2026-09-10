from core.ambient.world import World
from core.being.organism import Organism
from legacy.sense.sensor import Sensor
from legacy.ambient.sky import Sky
from legacy.simulation.renderer import Renderer
from legacy.simulation.gtime import Gtime
from legacy.simulation.simulation import Simulation


def test_organism_nasce_com_orientacao_padrao():
    gaiano = Organism("g", "@", 0, 0)
    assert gaiano.orientation == (0, -1)

def test_organism_aceita_sensor_customizado():
    sensor = Sensor(range_=8)
    gaiano = Organism("g", "@", 0, 0, sensor=sensor)
    assert gaiano.sensor is sensor

def test_act_atualiza_orientacao_ao_mover():
    world = World(5, 5)
    gaiano = Organism("g", "@", 2, 2)
    world.add_entity(gaiano)
    simulation = Simulation(
        world=world, sky=Sky(), renderer=Renderer(),
        gtime=Gtime(mtksptk=24), simulation_duration=10, frame_delay=0,
    )

    simulation.act(gaiano, [(1, 0)])

    assert gaiano.orientation == (1, 0)

def test_act_nao_atualiza_orientacao_ao_esperar():
    world = World(5, 5)
    gaiano = Organism("g", "@", 2, 2)
    gaiano.orientation = (0, -1)
    world.add_entity(gaiano)
    simulation = Simulation(
        world=world, sky=Sky(), renderer=Renderer(),
        gtime=Gtime(mtksptk=24), simulation_duration=10, frame_delay=0,
    )

    simulation.act(gaiano, [(0, 0)])

    assert gaiano.orientation == (0, -1)
