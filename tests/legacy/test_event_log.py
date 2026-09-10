from legacy.simulation.event import Event
from legacy.simulation.event_log import EventLog
def make_event(tick=0, name="gaiano_0"):
    return Event(
        tick = tick,
        entity_name=name,
        action="moved (1, 0)",
        reason="hunger",
        before={"hunger": 55, "thirst": 20},
        after={"hunger": 55, "thirst": 20},
    )

def test_record_guarda_o_evento():
    log = EventLog()
    event = make_event()
    log.record(event)
    assert log.events == [event]

def test_at_tick_filtra_por_tick():
    log = EventLog()
    log.record(make_event(tick=1))
    log.record(make_event(tick=2))
    resultado = log.at_tick(1)
    assert len(resultado) == 1
    assert resultado[0].tick == 1

def test_for_entity_filtra_por_entidade():
    log = EventLog()
    log.record(make_event(name="gaiano_0"))
    log.record(make_event(name="gaiano_1"))
    resultado = log.for_entity("gaiano_1")
    assert len(resultado) == 1
    assert resultado[0].entity_name == "gaiano_1"
