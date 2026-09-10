from core.ambient.world import World
from core.ambient.tile import WATER, FOOD, GRASS
from core.being.organism import Organism
from legacy.systems.environment_system import EnvironmentSystem

class SimulacaoFalsa:
    def __init__(self, world):
        self.world = world

def test_apply_hidrata_o_corpo_real_da_entidade():
    world = World(5, 5)
    world.set_tile(2, 2, WATER)
    organism = Organism("teste", "@", 2, 2)
    organism.body.thirst = 40
    simulacao = SimulacaoFalsa(world)

    EnvironmentSystem().apply(simulacao, organism)

    assert organism.body.thirst == 10

def test_apply_alimenta_o_corpo_real_e_remove_a_comida():
    world = World(5, 5)
    world.set_tile(2, 2, FOOD)
    organism = Organism("teste", "@", 2, 2)
    organism.body.hunger = 40
    simulacao = SimulacaoFalsa(world)

    EnvironmentSystem().apply(simulacao, organism)

    assert organism.body.hunger == 10
    assert world.get_tile(2, 2) is GRASS

def test_apply_em_grama_nao_altera_nada():
    world = World(5, 5)
    organism = Organism("teste", "@", 2, 2)
    organism.body.hunger = 40
    organism.body.thirst = 40
    simulacao = SimulacaoFalsa(world)

    EnvironmentSystem().apply(simulacao, organism)

    assert organism.body.hunger == 40
    assert organism.body.thirst == 40

