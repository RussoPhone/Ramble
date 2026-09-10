from legacy.simulation.config import ScenarioConfig
from legacy.simulation.scenario import build_scenario
from legacy.simulation.replay import reconstruct_event


def snapshot(simulation):
    return [
        (e.name, e.x, e.y, e.body.hunger, e.body.thirst, e.body.alive, e.last_action)
        for e in simulation.world.entities
    ]


def event_log_snapshot(simulation):
    #compara os eventos por conteúdo, não por identidade de objeto.
    return [
        (e.tick, e.entity_name, e.action, e.reason, e.before, e.after, e.context)
        for e in simulation.event_log.events
    ]


def test_qualquer_evento_do_log_reconstroi_estado_anterior_acao_e_consequencia():
    config = ScenarioConfig(seed=11, num_organism=10, simulation_duration=500, frame_delay=0)
    simulation = build_scenario(config)
    simulation.run(render_enabled=False)

    assert len(simulation.event_log.events) > 0

    for evento in simulation.event_log.events:
        reconstrucao = reconstruct_event(evento)

        assert reconstrucao["estado_anterior"] is not None
        assert reconstrucao["consequencia"] is not None
        assert reconstrucao["acao"] == evento.action
        assert reconstrucao["quem"] == evento.entity_name

        if evento.entity_name != "ceu":
            assert "hunger" in reconstrucao["estado_anterior"]
            assert "hunger" in reconstrucao["consequencia"]


def test_execucao_lenta_e_headless_coincidem():
    #"lenta" aqui = render_enabled=True (desenha a cada tick), mas com
    #frame_delay=0 pra não deixar o teste lento de verdade. O que importa
    #é provar que renderizar não muda em nada a lógica/estado da simulação.
    config = ScenarioConfig(seed=21, num_organism=10, simulation_duration=300, frame_delay=0)

    simulacao_headless = build_scenario(config)
    simulacao_headless.run(render_enabled=False)

    simulacao_lenta = build_scenario(config)
    simulacao_lenta.run(render_enabled=True)

    assert snapshot(simulacao_headless) == snapshot(simulacao_lenta)
    assert event_log_snapshot(simulacao_headless) == event_log_snapshot(simulacao_lenta)


def test_aceleracao_nao_muda_o_resultado_final():
    config = ScenarioConfig(seed=33, num_organism=10, simulation_duration=307, frame_delay=0)

    simulacao_passo_a_passo = build_scenario(config)
    simulacao_passo_a_passo.run(render_enabled=False, steps_per_frame=1)

    simulacao_acelerada = build_scenario(config)
    simulacao_acelerada.run(render_enabled=False, steps_per_frame=7)

    assert snapshot(simulacao_passo_a_passo) == snapshot(simulacao_acelerada)
    assert event_log_snapshot(simulacao_passo_a_passo) == event_log_snapshot(simulacao_acelerada)


def test_avanco_unitario_produz_o_mesmo_resultado_que_run():
    config = ScenarioConfig(seed=44, num_organism=5, simulation_duration=50, frame_delay=0)

    simulacao_run = build_scenario(config)
    simulacao_run.run(render_enabled=False)

    simulacao_manual = build_scenario(config)
    while simulacao_manual.advance_one(render_enabled=False):
        pass

    assert snapshot(simulacao_run) == snapshot(simulacao_manual)
    assert event_log_snapshot(simulacao_run) == event_log_snapshot(simulacao_manual)
