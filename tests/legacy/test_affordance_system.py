from core.ambient.world import World
from core.ambient.tile import STONE
from core.being.entity import Entity
from legacy.systems.affordance_system import AffordanceSystem


def test_esperar_sempre_e_legal():
    world = World(5, 5)
    entity = Entity("teste", "@", 2, 2)
    world.add_entity(entity)

    acoes = AffordanceSystem().legal_actions(world, entity)

    assert (0, 0) in acoes

def test_direcao_bloqueada_por_pedra_nao_e_legal():
    world = World(5, 5)
    world.set_tile(3, 2, STONE)
    entity = Entity("teste", "@", 2, 2)
    world.add_entity(entity)

    acoes = AffordanceSystem().legal_actions(world, entity)

    assert (1, 0) not in acoes
    assert (-1, 0) in acoes

def test_direcao_para_fora_do_mundo_nao_e_legal():
    world = World(5, 5)
    entity = Entity("teste", "@", 0, 0)
    world.add_entity(entity)

    acoes = AffordanceSystem().legal_actions(world, entity)

    assert (-1, 0) not in acoes
    assert (0, -1) not in acoes
    assert (1, 0) in acoes
    assert (0, 1) in acoes

def test_direcao_ocupada_por_outra_entidade_nao_e_legal():
    world = World(5, 5)
    a = Entity("a", "@", 2, 2)
    b = Entity("b", "@", 3, 2)
    world.add_entity(a)
    world.add_entity(b)

    acoes = AffordanceSystem().legal_actions(world, a)

    assert (1, 0) not in acoes
