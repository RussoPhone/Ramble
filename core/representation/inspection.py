"""Read-only, researcher-facing inspection. Never resolve signatures to kinds.

These records are requested separately from frames. They expose stored evidence,
not a newly computed perception or a claim about what the agent understands.
"""
from copy import deepcopy
from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class ExperienceView:
    tick: int
    signature: tuple[int, ...]
    action: str
    source: str
    actor: int | None
    target: int | None
    delta: tuple[float, float] | None
    success: bool | None


def experience_record(e):
    return asdict(ExperienceView(e.tick, tuple(e.signature), e.action, e.source,
                                e.actor, e.target, e.delta, e.success))


def memory_record(agent, tick):
    memory = agent.memory
    relations = []
    for r in memory.relations.values():
        relations.append(dict(id=r.id, signature=tuple(r.signature), action=r.action,
            bodyContext=tuple(r.body_context), signal=r.signal, delta=r.delta,
            weight=r.weight, confidence=r.confidence, contradictions=r.contradictions,
            sources=dict(r.sources), evidence=[experience_record(e) for e in r.evidence],
            lastTick=r.last_tick, age=tick-r.last_tick, active=r.active))
    return dict(agentId=agent.uid,
        relations=sorted(relations, key=lambda r: (not r['active'], -r['weight'], r['id'])),
        capacity=memory.capacity, forgotten=memory.forgotten,
        experienceCount=len(memory.experiences), experienceCapacity=memory.experiences.maxlen)


def log_record(simulation, agent):
    # The runtime's event deque is global and bounded. Participation is explicit,
    # never guessed from proximity; this is not a complete individual lifetime log.
    allowed = ('tick', 'actor', 'action', 'target', 'child', 'generation',
               'position', 'target_position', 'delta')
    events = [deepcopy({k: e[k] for k in allowed if k in e}) for e in simulation.events
              if agent.uid in (e.get('actor'), e.get('target'), e.get('child'))]
    return dict(agentId=agent.uid, events=events,
        experiences=[experience_record(e) for e in agent.memory.experiences],
        eventCapacity=simulation.events.maxlen,
        experienceCapacity=agent.memory.experiences.maxlen)
