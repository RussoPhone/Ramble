

def reconstruct_event(event):
    return {
        "tick": event.tick,
        "quem": event.entity_name,
        "estado_anterior": event.before,
        "motivo": event.reason, 
        "acao": event.action,
        "consequencia": event.after,
        "contexto": event.context,
    }

def describe_event(event):
    return (
        f"[tick {event.tick}] {event.entity_name} | motivo: {event.reason} |"
        f"ação: {event.action} | antes: {event.before} -> depois: {event.after}"
    )

def narrate(event_log):
    eventos_ordenados = sorted(event_log.events, key=lambda e: e.tick)
    return [describe_event(e) for e in eventos_ordenados]

def narrate_entity(event_log, entity_name):
    eventos = sorted(event_log.for_entity(entity_name), key=lambda e: e.tick)
    return [describe_event(e) for e in  eventos]

def print_replay(event_log):
    for linha in narrate(event_log):
        print(linha)
