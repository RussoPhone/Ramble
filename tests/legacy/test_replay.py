from legacy.simulation.event import Event
from legacy.simulation.event_log import EventLog
from legacy.simulation.replay import reconstruct_event, describe_event, narrate, narrate_entity


def make_event(tick, name="gaiano_0", action="moved (1, 0)"):
    return Event(
        tick=tick,
        entity_name=name,
        action=action,
        reason="fome",
        before={"hunger": 55, "x": 2, "y": 2},
        after={"hunger": 55, "x": 3, "y": 2},
        context={"tile": "grass"},
    )


def test_reconstruct_event_traz_estado_anterior_acao_e_consequencia():
    evento = make_event(tick=3)

    reconstrucao = reconstruct_event(evento)

    assert reconstrucao["tick"] == 3
    assert reconstrucao["quem"] == "gaiano_0"
    assert reconstrucao["estado_anterior"] == evento.before
    assert reconstrucao["acao"] == evento.action
    assert reconstrucao["consequencia"] == evento.after
    assert reconstrucao["motivo"] == "fome"


def test_describe_event_gera_texto_legivel():
    evento = make_event(tick=1)
    texto = describe_event(evento)

    assert "gaiano_0" in texto
    assert "fome" in texto
    assert "moved (1, 0)" in texto


def test_narrate_ordena_por_tick():
    log = EventLog()
    log.record(make_event(tick=5))
    log.record(make_event(tick=1))
    log.record(make_event(tick=3))

    linhas = narrate(log)

    assert "tick 1" in linhas[0]
    assert "tick 3" in linhas[1]
    assert "tick 5" in linhas[2]


def test_narrate_entity_filtra_e_ordena():
    log = EventLog()
    log.record(make_event(tick=2, name="gaiano_1"))
    log.record(make_event(tick=1, name="gaiano_0"))
    log.record(make_event(tick=4, name="gaiano_0"))

    linhas = narrate_entity(log, "gaiano_0")

    assert len(linhas) == 2
    assert "tick 1" in linhas[0]
    assert "tick 4" in linhas[1]
