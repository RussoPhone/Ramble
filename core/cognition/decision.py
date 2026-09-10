"""Consequence prediction over experienced signatures; no world references."""
from core.cognition.records import Action, candidates, local_signal


class Decision:
    def __init__(self, rng, exploration=.18):
        self.rng = rng
        self.exploration = exploration
        self.last = {}

    def prediction(self, view, memory, signature, verb, signal=None):
        numerator, denominator, imitation = 0., 0., 0.
        used = []
        for r in memory.related(signature, verb):
            similarity = 1 / (1 + sum(abs(v / 25 - b - .5) for v, b in zip(view.body, r.body_context)))
            if r.signal != signal:
                similarity *= .35
            weight = similarity * r.confidence
            if r.delta is not None:
                # Deficits are sensed by this body, never a semantic resource objective.
                value = -sum(d * max(.02, b / 100) for b, d in zip(view.body, r.delta))
                numerator += weight * value
                denominator += weight
            else:
                # Social exposure is a prior to TRY, not evidence of another body's relief.
                imitation = max(imitation, .8 * weight)
            used.append(r.id)
        return (numerator / denominator if denominator else imitation), used

    def choose(self, view, memory, actions=None):
        actions = candidates(view) if actions is None else actions
        items = {o.token: o for o in view.items}
        if view.carried:
            items[view.carried.token] = view.carried
        predictions = {}
        context_signal = local_signal(view)

        def predict(signature, verb, signal=None):
            if signal is None:
                signal = context_signal
            key = (signature, verb, signal)
            if key not in predictions:
                predictions[key] = self.prediction(view, memory, signature, verb, signal)
            return predictions[key]

        scored = []
        for action in actions:
            item = items.get(action.target)
            signature = item.appearance if item else ()
            value, used = predict(signature, action.verb, item.signal if item else None)
            if action.verb == 'move':
                # One motor step toward a currently perceived pattern with learned effects.
                # No search for named objects and no pathfinding through unknown cells.
                for o in view.items:
                    distance = abs(o.dx) + abs(o.dy)
                    next_distance = abs(o.dx - action.dx) + abs(o.dy - action.dy)
                    if distance <= 1 or next_distance >= distance:
                        continue
                    for verb in ('ingest', 'touch', 'pick', 'give'):
                        estimate, evidence = predict(o.appearance, verb, o.signal)
                        propagated = estimate * .8 ** distance
                        if propagated > value:
                            value, used = propagated, evidence
            scored.append((value, action, used))
        exploring = self.rng.random() < self.exploration
        if exploring:
            chosen = self.rng.choice(scored)
        else:
            best = max(row[0] for row in scored)
            chosen = self.rng.choice([row for row in scored if abs(row[0] - best) < 1e-9])
        for r in memory.relations.values():
            r.active = r.id in chosen[2]
        self.last = {'exploration': exploring, 'expected_body_value': round(chosen[0], 4),
                     'relations': chosen[2], 'action': chosen[1].verb,
                     'alternatives': [{'action': a.verb, 'target': a.target, 'dx': a.dx, 'dy': a.dy,
                                       'value': round(v, 4)} for v, a, _ in sorted(scored, key=lambda row: -row[0])[:8]]}
        return chosen[1]
