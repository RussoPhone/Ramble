"""Read-only public projection. Caller must hold the simulation controller lock.

Frames replace dynamic layers in full. A static-content digest and a projector
session ID force bootstrap after terrain/config changes or server replacement.
The digest scans terrain, but frames never serialize or transmit terrain.
No call to snapshot(), perceive(), step(), memory methods or RNGs is made.
"""
from copy import deepcopy
from dataclasses import asdict
import hashlib
import json
import os
import time

from .models import SCHEMA_VERSION, AgentView, BodyView, ObjectView, TerrainView
from .inspection import memory_record, log_record


class RepresentationProjector:
    def __init__(self, simulation):
        self._simulation = simulation
        # Session identity is not simulation time and requires no random source.
        self._session = f'{os.getpid():x}-{time.monotonic_ns():x}'

    def _terrain(self, x, y):
        t = self._simulation.world.get_tile(x, y)
        return TerrainView(f'{x},{y}', x, y, t.tile_type, t.blocking, tuple(t.appearance))

    def _object(self, obj):
        carrier = self._simulation.agents.get(obj.carrier)
        x, y = (carrier.x, carrier.y) if carrier else (obj.x, obj.y)
        return ObjectView(obj.uid, obj.kind, x, y, obj.quantity, tuple(obj.appearance),
                          obj.portable, obj.ingestible, obj.carrier, tuple(obj.shape.cells))

    def _agent(self, a):
        carried = self._simulation.objects.get(a.carried)
        return AgentView(a.uid, a.x, a.y, tuple(a.orientation), a.last_action,
            BodyView(a.body.hunger, a.body.thirst), a.generation, a.age,
            self._object(carried) if carried else None, (a.micro_x, a.micro_y),
            self._simulation.physical.cells_for('agent', a.uid))

    def _revision(self):
        s = self._simulation
        digest = hashlib.sha256(json.dumps(asdict(s.config), sort_keys=True).encode())
        for row in s.world.tiles:
            for tile in row:
                digest.update(repr((tile.tile_type, tile.blocking, tile.appearance)).encode())
        digest.update(f'{s.world.width},{s.world.height}'.encode())
        return f'{self._session}:{digest.hexdigest()[:24]}'

    def _envelope(self):
        return dict(schemaVersion=SCHEMA_VERSION, worldRevision=self._revision(),
                    tick=self._simulation.tick)

    def bootstrap(self):
        s = self._simulation
        terrain = [asdict(self._terrain(x, y)) for y in range(s.world.height)
                   for x in range(s.world.width)]
        catalog = ([dict(layer='terrain', kind=k) for k in sorted({t['kind'] for t in terrain})]
                   + [dict(layer='object', kind=k) for k in sorted({'object', 'food', 'water', 'stone'}
                       | {o.kind for o in s.objects.values()})]
                   + [dict(layer='agent', kind='gaiano')])
        return dict(**self._envelope(), width=s.world.width, height=s.world.height,
                    terrain=terrain, catalog=catalog, config=asdict(s.config),
                    **self._dynamic())

    def _dynamic(self):
        s = self._simulation
        return dict(agents=[asdict(self._agent(a)) for a in s.agents.values()],
            objects=[asdict(self._object(o)) for o in s.objects.values() if o.carrier is None],
            events=deepcopy(list(s.events)), population=len(s.agents))

    def frame(self):
        return dict(**self._envelope(), **self._dynamic())

    def agent(self, uid):
        a = self._simulation.agents.get(uid)
        return asdict(self._agent(a)) if a else None

    def object(self, uid):
        obj = self._simulation.objects.get(uid)
        return asdict(self._object(obj)) if obj else None

    def cell(self, x, y):
        s = self._simulation
        if not s.world.is_inside(x, y):
            return None
        a = s.world.get_entity_at(x, y)
        return dict(terrain=asdict(self._terrain(x, y)),
            objects=[asdict(self._object(s.objects[uid]))
                     for uid in sorted(s.object_cells.get((x, y), ()))],
            agent=asdict(self._agent(a)) if a else None)

    def detail(self, layer, identifier, section='summary'):
        """Stateless detail query; no retained UI selection."""
        if section not in ('summary', 'memory', 'log') or (section != 'summary' and layer != 'agent'):
            raise ValueError('seção de inspeção inválida')
        if layer == 'agent' and section != 'summary':
            agent = self._simulation.agents.get(identifier)
            result = None if agent is None else (
                memory_record(agent, self._simulation.tick) if section == 'memory'
                else log_record(self._simulation, agent))
        elif layer == 'agent':
            result = self.agent(identifier)
            agent = self._simulation.agents.get(identifier)
            if result is not None and agent is not None and hasattr(self._simulation, 'field_of_view'):
                result['vision'] = self._simulation.field_of_view(agent)
        elif layer == 'object':
            result = self.object(identifier)
        elif layer == 'terrain':
            result = self.cell(*identifier)
        else:
            raise ValueError('camada inválida')
        return dict(**self._envelope(), detail=result)
