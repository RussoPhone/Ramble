"""Bounded contextual hyperedges backed by actual experiences, without concepts."""
from collections import deque
from dataclasses import dataclass, field, asdict
import math

from core.cognition.records import Experience


@dataclass(slots=True)
class Relation:
    id: int
    signature: tuple[int, ...]
    action: str
    body_context: tuple[int, int]
    signal: int | None
    delta: tuple[float, float] | None = None
    weight: float = 0.0
    confidence: float = 0.0
    error: float = 0.0
    contradictions: int = 0
    sources: dict = field(default_factory=dict)
    evidence: list = field(default_factory=list)
    last_tick: int = 0
    active: bool = False


class RelationalMemory:
    def __init__(self, capacity=192, experience_capacity=128, half_life=1200, initial_tick=0):
        self.capacity = capacity
        self.half_life = half_life
        self.experiences = deque(maxlen=experience_capacity)
        self.relations = {}
        self.index = {}
        self.forgotten = 0
        self._next_id = 0
        self._decayed_at = initial_tick

    def record(self, experience: Experience):
        self.experiences.append(experience)
        bins = tuple(int(max(0, min(99, x)) // 25) for x in experience.body)
        key = (experience.signature, experience.action, bins, experience.signal, experience.source)
        if key not in self.relations:
            if len(self.relations) >= self.capacity:
                victim = min(self.relations, key=lambda k: self.relations[k].weight)
                self._remove(victim)
            relation = Relation(self._next_id, experience.signature, experience.action, bins, experience.signal)
            self._next_id += 1
            self.relations[key] = relation
            self.index.setdefault((relation.signature, relation.action), []).append(relation)
        r = self.relations[key]
        if experience.delta is not None:
            if r.delta is None:
                r.delta = experience.delta
            else:
                error = sum(abs(a-b) for a, b in zip(r.delta, experience.delta))
                if error > 8:
                    r.contradictions += 1
                r.error = .7 * r.error + .3 * error
                r.delta = tuple(.65*a + .35*b for a, b in zip(r.delta, experience.delta))
        r.weight = min(24., r.weight + (1. if experience.source == 'self' else .3))
        r.confidence = r.weight / (r.weight + 2 + r.error / 5)
        if experience.source == 'observed':
            r.confidence = min(.4, r.confidence)
        r.sources[experience.source] = r.sources.get(experience.source, 0) + 1
        r.evidence.append(experience)
        del r.evidence[:-4]
        r.last_tick = experience.tick

    def _remove(self, key):
        r = self.relations.pop(key)
        group = self.index[(r.signature, r.action)]
        group.remove(r)
        if not group:
            del self.index[(r.signature, r.action)]
        self.forgotten += 1

    def decay(self, tick):
        elapsed = max(0, tick - self._decayed_at)
        if not elapsed:
            return
        factor = math.exp2(-elapsed / self.half_life)
        for key, r in list(self.relations.items()):
            r.weight *= factor
            r.confidence *= factor
            if r.weight < .04:
                self._remove(key)
        self._decayed_at = tick

    def related(self, signature, action):
        return self.index.get((signature, action), ())

    def snapshot(self, tick):
        relations = []
        for r in self.relations.values():
            row = asdict(r)
            row['age'] = tick - r.last_tick
            relations.append(row)
        return {'relations': sorted(relations, key=lambda r: (not r['active'], -r['weight'])),
                'experiences': [asdict(e) for e in self.experiences], 'forgotten': self.forgotten}
