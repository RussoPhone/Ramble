"""Population runtime: physical truth stops at immutable sensory records."""
from collections import Counter, deque
from dataclasses import dataclass, asdict, replace
import math
import random
from copy import deepcopy

from core.ambient.world import World
from core.ambient.tile import STONE
from core.ambient.objects import PhysicalObject
from core.ambient.physical_space import PhysicalSpace, Shape
from core.being.organism import Organism
from core.cognition.records import Action, Observation, View, Experience, local_signal
from core.cognition.memory import RelationalMemory
from core.cognition.decision import Decision


@dataclass
class PopulationConfig:
    seed: int = 42
    width: int = 48
    height: int = 32
    population: int = 40
    objects: int = 240
    stones: int = 35
    sensor_range: int = 5
    metabolism: float = .12
    exploration: float = .18
    renewal: int = 120
    reproduction: bool = True
    maturity: int = 600
    birth_interval: int = 600
    population_limit: int = 300
    memory_capacity: int = 192
    experience_capacity: int = 128
    observe: bool = True
    learning: bool = True

    def __post_init__(self):
        for name in ('seed', 'width', 'height', 'population', 'objects', 'stones', 'sensor_range',
                     'renewal', 'maturity', 'birth_interval', 'population_limit', 'memory_capacity', 'experience_capacity'):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError(f'{name} deve ser inteiro')
        if self.width < 3 or self.height < 3 or self.width*self.height > 1_000_000:
            raise ValueError('dimensões inválidas')
        if not 1 <= self.sensor_range <= 20:
            raise ValueError('alcance deve estar entre 1 e 20')
        if min(self.population, self.objects, self.stones, self.renewal, self.maturity, self.birth_interval) < 0:
            raise ValueError('quantidades não podem ser negativas')
        if self.population + self.stones > self.width * self.height:
            raise ValueError('população e terreno excedem capacidade')
        if self.objects > self.width * self.height - self.stones:
            raise ValueError('objetos excedem posições disponíveis')
        if min(self.memory_capacity, self.experience_capacity, self.population_limit) < 1:
            raise ValueError('limites devem ser positivos')
        if self.population > self.population_limit:
            raise ValueError('população excede limite')
        if not math.isfinite(self.metabolism) or self.metabolism < 0:
            raise ValueError('metabolismo inválido')
        if not math.isfinite(self.exploration) or not 0 <= self.exploration <= 1:
            raise ValueError('exploração deve estar entre 0 e 1')


class PopulationSimulation:
    def __init__(self, config=None, event_sink=None):
        self.config = config or PopulationConfig()
        self.rng = random.Random(self.config.seed)
        self.world = World(self.config.width, self.config.height)
        self.physical = PhysicalSpace(self.config.width, self.config.height)
        self.tick = 0
        self.agents = {}
        self.objects = {}
        self.object_cells = {}
        self.sites = []
        self.events = deque(maxlen=200)
        self.event_sink = event_sink
        self.births = self.deaths = 0
        self.action_counts = Counter()
        self._next_id = 1
        positions = [(x, y) for y in range(self.config.height) for x in range(self.config.width)]
        self.rng.shuffle(positions)
        for _ in range(self.config.stones):
            self.world.set_tile(*positions.pop(), STONE)
        for x, y in positions[:self.config.population]:
            self.spawn(x, y)
        # Appearance and physiological effects are separate scenario parameters.
        resources = (
            ((13, 4, 2), (-42., 0.), "food", True),
            ((29, 7, 3), (0., -42.), "water", True),
            ((41, 9, 1), (0., 0.), "stone", False),
        )
        for i, (x, y) in enumerate(self.rng.sample(positions, self.config.objects)):
            signature, effect, kind, ingestible = resources[i % len(resources)]
            self.add_object(x, y, signature, effect, ingestible=ingestible, kind=kind)
            # Only these two scenario populations have environmental production.
            # Moving an inert object must not duplicate it at its former position.
            if kind != "stone":
                self.sites.append((x, y, signature, effect, ingestible, kind))

    def _id(self):
        uid = self._next_id
        self._next_id += 1
        return uid

    def spawn(self, x, y, generation=0, micro_position=None):
        if not self.world.is_passable(x, y, allow_occupied=True):
            raise ValueError('posição de nascimento indisponível')
        a = Organism('gaiano', '@', x, y)
        a.uid = self._id()
        a.name = f'gaiano_{a.uid}'
        a.memory = RelationalMemory(self.config.memory_capacity, self.config.experience_capacity, initial_tick=self.tick)
        a.decision_system = Decision(random.Random(self.rng.getrandbits(64)), self.config.exploration)
        a.appearance = (53, 6, 4)
        a.carried = None
        a.age = 0
        a.generation = generation
        a.last_birth = -self.config.birth_interval
        a.signal = None
        a.signal_tick = -1
        a.motion = (0, 0)
        a.last_target = None
        a.shape = self._agent_shape(a.orientation)
        a.view = View((0., 0.), (), (), self.tick)
        # Dead reckoning is acquired motor feedback, not global map coordinates.
        a.odometry = (0, 0)
        candidates = [tuple(micro_position)] if micro_position is not None else [
            (x * self.physical.scale + dx, y * self.physical.scale + dy)
            for dy in range(self.physical.scale) for dx in range(self.physical.scale)
        ]
        if micro_position is None:
            self.rng.shuffle(candidates)
        base = next((candidate for candidate in candidates
                     if self._position_available(*candidate, a.orientation)), None)
        if base is None or (base[0] // self.physical.scale, base[1] // self.physical.scale) != (x, y):
            raise ValueError('posição de nascimento indisponível')
        a.micro_x, a.micro_y = base
        self.agents[a.uid] = a
        self.world.add_entity(a, allow_occupied=True)
        self.physical.place_cells("agent", a.uid, self._agent_cells(*base, a.orientation), blocks=True,
                                  visible_cells=a.shape.cells)
        return a

    @staticmethod
    def _agent_shape(orientation):
        dx, dy = orientation
        return Shape(((0, 0), (dx, dy)))

    @staticmethod
    def _agent_cells(micro_x, micro_y, orientation):
        dx, dy = orientation
        return ((micro_x, micro_y), (micro_x + dx, micro_y + dy))

    def _terrain_allows(self, cells):
        for micro_x, micro_y in cells:
            if not self.physical._inside_micro(micro_x, micro_y):
                return False
            tile = self.world.get_tile(micro_x // self.physical.scale, micro_y // self.physical.scale)
            if tile.blocking:
                return False
        return True

    def _position_available(self, micro_x, micro_y, orientation, ignore=None):
        cells = self._agent_cells(micro_x, micro_y, orientation)
        return self._terrain_allows(cells) and self.physical.can_place_cells(
            cells, ignore=ignore, blocks=True)

    def _set_agent_position(self, a, micro_x, micro_y, orientation):
        key = ("agent", a.uid)
        cells = self._agent_cells(micro_x, micro_y, orientation)
        if not self._position_available(micro_x, micro_y, orientation, ignore=key):
            return False
        old_cells = self.physical.cells_for("agent", a.uid)
        old_visible = a.shape.cells
        shape = self._agent_shape(orientation)
        if not self.physical.move_cells("agent", a.uid, cells, visible_cells=shape.cells):
            return False
        tile_x, tile_y = micro_x // self.physical.scale, micro_y // self.physical.scale
        if not self.world.reindex_entity(a, tile_x, tile_y, allow_occupied=True):
            self.physical.move_cells("agent", a.uid, old_cells, visible_cells=old_visible)
            return False
        a.micro_x, a.micro_y = micro_x, micro_y
        a.shape = shape
        a.orientation = tuple(orientation)
        return True

    def add_object(self, x, y, appearance, effect=(0., 0.), portable=True, ingestible=True, quantity=1, kind="object",
                   shape=None, blocking=False):
        if not self.world.is_inside(x, y) or quantity < 1:
            raise ValueError('objeto inválido')
        obj_shape = Shape(tuple(shape)) if shape is not None else Shape()
        obj = PhysicalObject(self._id(), x, y, tuple(appearance), tuple(effect), portable, ingestible,
                             quantity, None, kind, obj_shape, bool(blocking))
        self.objects[obj.uid] = obj
        self.object_cells.setdefault((x, y), set()).add(obj.uid)
        self.physical.place("object", obj.uid, x, y, obj.shape, blocks=obj.blocking)
        return obj

    def _detach(self, obj):
        if obj.carrier is None:
            ids = self.object_cells.get((obj.x, obj.y))
            if ids:
                ids.discard(obj.uid)
                if not ids:
                    del self.object_cells[(obj.x, obj.y)]
            self.physical.remove("object", obj.uid)
        else:
            holder = self.agents.get(obj.carrier)
            if holder:
                holder.carried = None

    def _place(self, obj, x, y):
        self._detach(obj)
        obj.x, obj.y, obj.carrier = x, y, None
        self.object_cells.setdefault((x, y), set()).add(obj.uid)
        self.physical.place("object", obj.uid, x, y, obj.shape, blocks=obj.blocking)

    def _line_clear(self, x0, y0, x1, y1):
        # Integer ray; the blocking endpoint itself remains visible.
        dx, dy = abs(x1-x0), -abs(y1-y0)
        sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
        err = dx + dy
        while (x0, y0) != (x1, y1):
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy
            if (x0, y0) != (x1, y1) and self.world.get_tile(x0, y0).blocking:
                return False
        return True

    def _shape_seen(self, viewer, layer, token):
        try:
            return self.physical.visible_parts_from_micro(
                viewer.micro_x, viewer.micro_y, layer, token, ignore=(("agent", viewer.uid),))
        except KeyError:
            return ()

    def _visible_cells(self, a):
        """Yield (x, y, dx, dy) for every world cell the agent currently perceives.

        Contact in every direction; distance vision only in the forward half plane,
        with blocking terrain occluding the ray. Pure: no records, RNG or mutation.
        """
        reach = self.config.sensor_range
        for dy in range(-reach, reach+1):
            for dx in range(-reach+abs(dy), reach-abs(dy)+1):
                x, y = a.x+dx, a.y+dy
                if not self.world.is_inside(x, y):
                    continue
                # Contact in every direction; distance vision in the forward half plane.
                if abs(dx)+abs(dy) > 1 and dx*a.orientation[0]+dy*a.orientation[1] < 0:
                    continue
                if not self._line_clear(a.x, a.y, x, y):
                    continue
                yield x, y, dx, dy

    def field_of_view(self, a):
        """Read-only list of [x, y] world cells visible to the agent, near to far."""
        return [[x, y] for x, y, _, _ in self._visible_cells(a)]

    def perceive(self, a):
        items, terrain = [], []
        for x, y, dx, dy in self._visible_cells(a):
            tile = self.world.get_tile(x, y)
            terrain.append(Observation(-1, tile.appearance, dx, dy, tile.blocking))
            for uid in sorted(self.object_cells.get((x, y), ())):
                obj = self.objects[uid]
                shape = self._shape_seen(a, "object", uid)
                if shape:
                    items.append(Observation(uid, obj.appearance, dx, dy, shape=shape))
            for other in self.world.get_entities_at(x, y):
                if other is a:
                    continue
                signal = other.signal if self.tick-other.signal_tick <= 2 else None
                items.append(Observation(other.uid, other.appearance, dx, dy, True,
                                         other.motion, other.last_action, signal,
                                         shape=self._shape_seen(a, "agent", other.uid)))
        visible_tokens = {o.token for o in items}
        for i, item in enumerate(items):
            other = self.agents.get(item.token)
            if other is not None and other.last_target in visible_tokens:
                # A visibly directed motor gesture toward an identifiable visible target.
                items[i] = replace(item, action_target=other.last_target)
        carried = None
        if a.carried is not None:
            obj = self.objects[a.carried]
            carried = Observation(obj.uid, obj.appearance, 0, 0)
        return View((a.body.hunger, a.body.thirst), tuple(items), tuple(terrain), self.tick, carried)

    def _event(self, actor, action, **fields):
        event = dict(tick=self.tick, actor=actor, action=action, **fields)
        self.events.append(event)
        if self.event_sink:
            self.event_sink(event)

    def _observable_position(self, token):
        obj = self.objects.get(token)
        if obj is not None:
            if obj.carrier is not None:
                carrier = self.agents.get(obj.carrier)
                if carrier is not None:
                    return (carrier.x, carrier.y)
            return (obj.x, obj.y)
        agent = self.agents.get(token)
        return (agent.x, agent.y) if agent is not None else None

    def _target_directly_ahead(self, a, layer, token):
        dx, dy = a.orientation
        target_cell = (a.micro_x + 2 * dx, a.micro_y + 2 * dy)
        try:
            return target_cell in self.physical.cells_for(layer, token)
        except KeyError:
            return False

    def _apply(self, a, action):
        """Execute exactly one attempt. Return only motor/visible success."""
        obj = self.objects.get(action.target)
        reachable = obj is not None and (obj.carrier == a.uid or
            (obj.carrier is None and self._target_directly_ahead(a, 'object', obj.uid)))
        a.motion = (0, 0)
        if action.verb == 'move':
            if abs(action.dx)+abs(action.dy) != 1:
                return False
            orientation = (action.dx, action.dy)
            moved = self._set_agent_position(
                a, a.micro_x + action.dx, a.micro_y + action.dy, orientation)
            if moved:
                a.motion = a.orientation
                a.odometry = (a.odometry[0]+action.dx, a.odometry[1]+action.dy)
            return moved
        if action.verb == 'turn':
            x, y = a.orientation
            orientation = (-y, x) if action.value >= 0 else (y, -x)
            return self._set_agent_position(a, a.micro_x, a.micro_y, orientation)
        if action.verb in ('wait', 'inspect'):
            return True
        if action.verb == 'signal':
            if action.value not in range(4):
                return False
            a.signal, a.signal_tick = action.value, self.tick
            return True
        if action.verb == 'touch':
            other = self.agents.get(action.target)
            return bool(reachable or (other and self._target_directly_ahead(a, 'agent', other.uid)))
        if action.verb == 'ingest' and reachable and obj.ingestible:
            a.body.hunger = max(0., min(100., a.body.hunger+obj.effect[0]))
            a.body.thirst = max(0., min(100., a.body.thirst+obj.effect[1]))
            obj.quantity -= 1
            if obj.quantity == 0:
                self._detach(obj)
                del self.objects[obj.uid]
            return True
        if action.verb == 'pick' and reachable and obj.portable and a.carried is None:
            self._detach(obj)
            obj.carrier, a.carried = a.uid, obj.uid
            return True
        if action.verb in ('drop', 'place') and a.carried is not None:
            x, y = a.x, a.y
            if action.verb == 'place':
                x, y = x+a.orientation[0], y+a.orientation[1]
                if not self.world.is_inside(x, y) or self.world.get_tile(x, y).blocking:
                    return False
            # Bound stacking by physical room, without erasing abandoned objects.
            if len(self.object_cells.get((x, y), ())) >= 8:
                return False
            self._place(self.objects[a.carried], x, y)
            return True
        if action.verb == 'give' and a.carried is not None:
            other = self.agents.get(action.target)
            if (other and other.uid != a.uid and other.carried is None
                    and self._target_directly_ahead(a, 'agent', other.uid)):
                obj = self.objects[a.carried]
                self._detach(obj)
                obj.carrier, other.carried = other.uid, obj.uid
                return True
        return False

    def _die(self, a):
        if a.carried is not None:
            self._place(self.objects[a.carried], a.x, a.y)
        a.body.alive = False
        self.world.remove_entity(a)
        self.physical.remove("agent", a.uid)
        del self.agents[a.uid]
        self.deaths += 1
        self._event(a.uid, 'death', position=(a.x, a.y), generation=a.generation)

    def _renew(self):
        if not self.config.renewal or self.tick % self.config.renewal:
            return
        # Finite site flux and global standing stock bound; no population rescue.
        limit = max(self.config.objects * 2, len(self.sites))
        for x, y, signature, effect, ingestible, kind in self.sites:
            if len(self.objects) >= limit:
                break
            if not self.object_cells.get((x, y)):
                self.add_object(x, y, signature, effect, ingestible=ingestible, kind=kind)

    def _reproduce(self):
        if not self.config.reproduction:
            return
        order = list(self.agents.values())
        self.rng.shuffle(order)
        for a in order:
            if len(self.agents) >= self.config.population_limit:
                break
            if a.age < self.config.maturity or self.tick-a.last_birth < self.config.birth_interval:
                continue
            if max(a.body.hunger, a.body.thirst) > 15:
                continue
            adjacent = [(a.x+dx, a.y+dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))]
            self.rng.shuffle(adjacent)
            for x, y in adjacent:
                try:
                    child = self.spawn(x, y, a.generation+1)
                except ValueError:
                    continue
                else:
                    child.body.hunger = child.body.thirst = 35.
                    a.body.hunger += 35.
                    a.body.thirst += 35.
                    a.last_birth = self.tick
                    self.births += 1
                    self._event(a.uid, 'birth', child=child.uid, generation=child.generation,
                                position=(child.x, child.y))
                    break

    def step(self, actions=None):
        """Optional action interventions are for physical experiments, never the UI."""
        self.tick += 1
        self._renew()
        order = list(self.agents.values())
        self.rng.shuffle(order)
        views = {}
        chosen = {}
        for a in order:
            a.age += 1
            a.body.hunger += self.config.metabolism
            a.body.thirst += self.config.metabolism * 1.4
            if not a.body.alive or max(a.body.hunger, a.body.thirst) >= 100:
                self._die(a)
                continue
            a.view = views[a.uid] = self.perceive(a)
            if self.tick % 32 == 0:
                a.memory.decay(self.tick)
            chosen[a.uid] = actions[a.uid] if actions and a.uid in actions else a.decision_system.choose(a.view, a.memory)
        # All decisions use pre-action samples; shuffled resolution avoids permanent priority.
        visible_actions = []
        for a in order:
            if a.uid not in chosen:
                continue
            view, action = views[a.uid], chosen[a.uid]
            item = next((o for o in view.items if o.token == action.target), None)
            if view.carried and action.target == view.carried.token:
                item = view.carried
            target_position = self._observable_position(action.target)
            success = self._apply(a, action)
            a.last_action = action.verb
            a.last_target = action.target
            delta = (a.body.hunger-view.body[0], a.body.thirst-view.body[1])
            change = ('changed',) if success and action.verb in ('move', 'pick', 'drop', 'place', 'give', 'signal') else ()
            if success and action.verb == 'ingest':
                change = ('vanished',) if action.target not in self.objects else ('changed',)
            signature = item.appearance if item else ()
            if self.config.learning:
                a.memory.record(Experience(self.tick, view.body, signature, action.verb, delta, success,
                    actor=a.uid, signal=local_signal(view), visible_change=change,
                    location=a.odometry, target=action.target,
                    context=tuple(o.appearance for o in (*view.terrain[:4], *view.items[:8]))))
            self.action_counts[action.verb] += 1
            if success and action.verb in ('ingest', 'pick', 'drop', 'place', 'give', 'signal'):
                self._event(a.uid, action.verb, target=action.target, delta=delta,
                            position=(a.x, a.y), target_position=target_position)
            visible_actions.append(a.uid)
        if self.config.observe and self.config.learning:
            # Invert the already local visibility lists, avoiding N² observer/action scans.
            observers = {}
            for observer_id, view in views.items():
                for item in view.items:
                    if item.token in views:
                        observers.setdefault(item.token, []).append(observer_id)
            after_views = {}
            for actor in visible_actions:
                for observer_id in observers.get(actor, ()):
                    observer = self.agents.get(observer_id)
                    if observer is None:
                        continue
                    view = views[observer_id]
                    if observer_id not in after_views:
                        after_views[observer_id] = self.perceive(observer)
                    after_view = after_views[observer_id]
                    visible_actor = next((o for o in after_view.items if o.token == actor), None)
                    if visible_actor is None:
                        continue
                    target_id = visible_actor.action_target
                    target = next((o for o in view.items if o.token == target_id), None)
                    if target is None:
                        target = next((o for o in after_view.items if o.token == target_id), None)
                    # Only compare observable records. Physical success and stock quantity
                    # are NOT available here; an unchanged-looking attempt stays uncertain.
                    change = ()
                    if target:
                        after_target = next((o for o in after_view.items if o.token == target.token), None)
                        if after_target is not None and after_target != target:
                            change = ('visible_change',)
                        elif after_target is None:
                            change = ('out_of_view',)
                    elif visible_actor.signal is not None:
                        change = ('signal',)
                    observer.memory.record(Experience(self.tick, view.body,
                        target.appearance if target else (), visible_actor.action, None, None, source='observed', actor=actor,
                        signal=visible_actor.signal if visible_actor.action == 'signal' else local_signal(view),
                        visible_change=change, location=(visible_actor.dx, visible_actor.dy),
                        target=target_id, context=tuple(o.appearance for o in view.items[:8])))
        self._reproduce()

    def metrics(self):
        return {'tick': self.tick, 'alive': len(self.agents), 'births': self.births, 'deaths': self.deaths,
                'objects': len(self.objects), 'relations': sum(len(a.memory.relations) for a in self.agents.values()),
                'generation': max((a.generation for a in self.agents.values()), default=0),
                'actions': dict(self.action_counts)}

    def snapshot(self, selected_id=None):
        selected = None
        a = self.agents.get(selected_id)
        if a:
            # Recompute a read-only sensory projection; selecting never adds experience.
            view = self.perceive(a)
            selected = dict(id=a.uid, body={'hunger': a.body.hunger, 'thirst': a.body.thirst},
                position=(a.x, a.y), odometry=a.odometry, generation=a.generation,
                orientation=a.orientation, action=a.last_action,
                carried=asdict(view.carried) if view.carried else None,
                perception=[asdict(o) for o in (*view.terrain, *view.items)],
                memory=a.memory.snapshot(self.tick), decision=deepcopy(a.decision_system.last))
        return dict(tick=self.tick, width=self.world.width, height=self.world.height, light=1.,
            terrain=[dict(x=x, y=y, appearance=t.appearance, blocking=t.blocking,
                          kind="ground" if t.tile_type == "grass" else t.tile_type)
                     for y, row in enumerate(self.world.tiles) for x, t in enumerate(row)],
            objects=[dict(id=o.uid, x=o.x, y=o.y, appearance=o.appearance, quantity=o.quantity,
                          kind=o.kind, cells=o.shape.cells)
                     for o in self.objects.values() if o.carrier is None],
            agents=[dict(id=a.uid, x=a.x, y=a.y, orientation=a.orientation, alive=True, action=a.last_action,
                         carrying=self.objects[a.carried].appearance if a.carried is not None else None,
                         body=dict(hunger=a.body.hunger, thirst=a.body.thirst), generation=a.generation,
                         cells=a.shape.cells)
                    for a in self.agents.values()], metrics=self.metrics(), events=deepcopy(list(self.events)), selected=selected)
