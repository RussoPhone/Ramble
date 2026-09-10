import random

from core.ambient.world import World
from core.ambient.tile import STONE, WATER
from core.being.organism import Organism
from legacy.being.navigator import Navigator
from legacy.ambient.sky import Sky
from legacy.simulation.renderer import Renderer
from legacy.simulation.gtime import Gtime
from legacy.simulation.simulation import Simulation
from legacy.sense.sensor import Sensor
from toys.toy001_survival_instinct.naive_policy import NaivePolicy


class AlvoAtribuidoPeloTeste:
    #ATENÇÃO: isso NÃO é um decision_system de produção e nunca deve virar
    #o padrão de um Gaiano real. É um substituto usado só aqui, pra provar
    #que Navigator + percepção + affordances funcionam de ponta a ponta.
    #A escolha de QUAL tile perseguir, e o PORQUÊ (sede -> água), só pode
    #nascer de aprendizado por consequência (Semana 4). Fixar essa escolha
    #num decision_system de verdade violaria docs/rules.md item 3/11.

    def __init__(self, tile_type_alvo, fallback):
        self.tile_type_alvo = tile_type_alvo
        self.fallback = fallback

    def decide(self, entity, perception):
        if perception is None:
            return self.fallback.decide(entity, perception)

        candidatos = [r for r in perception.reading if r["appearance"] == self.tile_type_alvo]
        if not candidatos:
            return self.fallback.decide(entity, perception)

        alvo = min(candidatos, key=lambda r: r["distance"])
        return Navigator.directions_toward(alvo["dx"], alvo["dy"])


def build_cenario_com_barreira():
    world = World(width=5, height=3)
    world.set_tile(2, 1, STONE)
    world.set_tile(4, 1, WATER)

    gaiano = Organism(
        "gaiano_teste", "G", 0, 1,
        sensor=Sensor(range_=6, requires_light=False),
        decision=AlvoAtribuidoPeloTeste(tile_type_alvo=WATER.appearance, fallback=NaivePolicy()),
    )
    gaiano.orientation = (1, 0)
    world.add_entity(gaiano)

    simulation = Simulation(
        world=world, sky=Sky(), renderer=Renderer(),
        gtime=Gtime(mtksptk=24), simulation_duration=150, frame_delay=0,
    )
    return simulation, gaiano


def test_gaiano_contorna_barreira_e_alcanca_a_agua():
    random.seed(7)
    simulation, gaiano = build_cenario_com_barreira()

    simulation.run(render_enabled=False)

    consumos_de_agua = [
        evento for evento in simulation.event_log.events
        if evento.entity_name == gaiano.name
        and evento.action == "ingest"
        and evento.reason == "water"
    ]
    assert consumos_de_agua

def test_gaiano_sem_percepcao_de_recurso_cai_no_fallback():
    #mundo sem água nenhuma: o alvo nunca é encontrado, então o decision_system
    #precisa cair no fallback (NaivePolicy) sem quebrar.
    world = World(width=5, height=3)
    gaiano = Organism(
        "gaiano_teste", "G", 2, 1,
        sensor=Sensor(range_=6, requires_light=False),
        decision=AlvoAtribuidoPeloTeste(tile_type_alvo=WATER.appearance, fallback=NaivePolicy()),
    )
    world.add_entity(gaiano)
    simulation = Simulation(
        world=world, sky=Sky(), renderer=Renderer(),
        gtime=Gtime(mtksptk=24), simulation_duration=5, frame_delay=0,
    )

    #não deve lançar exceção nenhuma
    simulation.run(render_enabled=False)
    assert simulation.gtime.mtk == 5
