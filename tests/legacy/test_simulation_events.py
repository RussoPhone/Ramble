from legacy.simulation.config import ScenarioConfig
from legacy.simulation.scenario import build_scenario
from core.ambient.tile import WATER


def test_evento_de_acao_registra_motivo_estado_e_consequencia():
    config = ScenarioConfig(seed=7, num_organism=5, simulation_duration=200, frame_delay=0)
    simulation = build_scenario(config)

    simulation.run(render_enabled=False)

    assert len(simulation.event_log.events) > 0

    eventos_de_gaiano = [e for e in simulation.event_log.events if e.entity_name.startswith("gaiano_")]
    assert len(eventos_de_gaiano) > 0
    evento = eventos_de_gaiano[0]
    assert evento.reason in ("fome", "sede", "fome e sede")
    assert "hunger" in evento.before and "hunger" in evento.after
    assert isinstance(evento.action, str)


def test_beber_agua_gera_evento_separado_de_consumo():
    config = ScenarioConfig(seed=3, world_width=3, world_height=3, num_organism=1, simulation_duration=1, frame_delay=0)
    simulation = build_scenario(config)

    entidade = simulation.world.entities[0]
    #sede abaixo de 50: needs_action() fica False, então a entidade NÃO tenta se mover
    #(ainda não existe affordance "ficar parado e beber" - isso é semana 3).
    #assim garantimos que ela continua sobre a água quando o environment_system roda.
    entidade.body.thirst = 20
    #força a entidade pra cima da água pra garantir o consumo nesse tick
    agua_x, agua_y = None, None
    for y in range(simulation.world.height):
        for x in range(simulation.world.width):
            if simulation.world.get_tile(x, y) is WATER:
                agua_x, agua_y = x, y
    entidade.x, entidade.y = agua_x, agua_y

    simulation.step()

    eventos_consumo = [e for e in simulation.event_log.events if e.action == "ingest"]
    assert len(eventos_consumo) == 1
    assert eventos_consumo[0].before["thirst"] > eventos_consumo[0].after["thirst"]


def test_morte_gera_evento_com_motivo_correto():
    config = ScenarioConfig(seed=1, num_organism=1, simulation_duration=1, frame_delay=0)
    simulation = build_scenario(config)

    entidade = simulation.world.entities[0]
    entidade.body.hunger = 99
    entidade.body.thirst = 0

    simulation.step()

    eventos_morte = [e for e in simulation.event_log.events if e.action == "morreu"]
    assert len(eventos_morte) == 1
    assert eventos_morte[0].reason == "fome"
    assert eventos_morte[0].after["alive"] is False


def test_entidade_ja_morta_nao_gera_novo_evento_de_morte_todo_tick():
    config = ScenarioConfig(seed=1, num_organism=1, simulation_duration=1, frame_delay=0)
    simulation = build_scenario(config)

    entidade = simulation.world.entities[0]
    entidade.body.alive = False

    simulation.step()
    simulation.step()

    eventos_morte = [e for e in simulation.event_log.events if e.action == "morreu"]
    assert len(eventos_morte) == 0


def test_mudanca_de_fase_do_ceu_entra_no_historico():
    config = ScenarioConfig(seed=5, num_organism=1, mtksptk=24, simulation_duration=30, frame_delay=0)
    simulation = build_scenario(config)

    simulation.run(render_enabled=False)

    eventos_ceu = [e for e in simulation.event_log.events if e.entity_name == "ceu"]
    assert len(eventos_ceu) > 0
    assert "fase" in eventos_ceu[0].before
    assert "fase" in eventos_ceu[0].after
