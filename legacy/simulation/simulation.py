import os
import sys 
import time
from core.being.organism import Organism
from legacy.sense.perception import Perception
from legacy.sense.spatial import Spatial
from core.ambient.tile import WATER, FOOD, GRASS
from legacy.systems.environment_system import EnvironmentSystem
from legacy.systems.affordance_system import AffordanceSystem
from legacy.simulation.event import Event
from legacy.simulation.event_log import EventLog
class Simulation: #È aqui que fica os parametros da simulação.
    def __init__(self, world, sky, renderer, gtime, simulation_duration=120, frame_delay=0.05):
        self.world = world
        self.sky = sky
        self.renderer = renderer
        self.gtime = gtime
        self.simulation_duration = simulation_duration
        self.frame_delay = frame_delay
        self.environment_system = EnvironmentSystem()
        self.affordance_system = AffordanceSystem()
        self.event_log = EventLog() 

 

    def _build_frame(self):
        linhas = [self.gtime.debug_text(), ""]

        light = self.sky.get_light(self.gtime)
        linhas.append(f"Light: {light}")
        linhas.append("")

        for entity in self.world.entities:
            linhas.append(entity.debug_text())
            if entity.needs_action():
                linhas.append(f"{entity.name} needs_action")
            linhas.append("")

        linhas.append(self.renderer.render_lit(self.world, light))
        return "\n".join(linhas)

        os.system("cls" if os.name == "nt" else "clear")
    def log_event(self, entity_name, action, reason, before, after, context=None):
        #monta e guarda um Event. usa o tick fechado get_tk()).
        self.event_log.record(Event(
            tick=self.gtime.get_tk(),
            entity_name=entity_name,
            action=action,
            reason=reason,
            before=before,
            after=after,
            context=context or {},
        ))
    
    def death_reason(self, state):
        fome = state["hunger"] >= 100
        sede = state["thirst"] >= 100
        if fome and sede: return "fome e sede"
        elif fome: return "fome"
        elif sede: return "sede"
        return "desconhecido"

    def capture_state(self, entity):
        return {
            "x": entity.x, "y": entity.y,
            "hunger": entity.body.hunger,
            "thirst": entity.body.thirst,
            "alive": entity.body.alive,

        }
    def body_reason(self, entity):
        fome = entity.body.hunger >= 50
        sede = entity.body.thirst >=50
        if fome and sede: return "fome e sede"
        elif fome: return "fome"
        elif sede: return "sede"
        return "nenhum"

    def process_entity(self, entity):
        if not isinstance(entity, Organism):
            return
        was_alive = entity.body.alive 
        before_update = self.capture_state(entity)

        entity.update(self.world)

        if was_alive and not entity.body.alive:
            after_update = self.capture_state(entity)
            self.log_event(
                entity_name=entity.name, 
                action="morreu",
                reason=self.death_reason(after_update),
                before=before_update,
                after=after_update,
                context={"posicao": (entity.x, entity.y)},
            )
            return 
        if not entity.body.alive:
            return 
        perception = self.perceive(entity)

        if entity.needs_action():
            reason = self.body_reason(entity)
            before_action = self.capture_state(entity)

            action = self.decide_action(entity, perception)
            applied = self.act(entity, action)
            entity.record_action(applied)

            after_action = self.capture_state(entity)

            self.log_event(
                entity_name=entity.name,
                action=applied,
                reason=reason,
                before=before_action,
                after=after_action,
                context={"tile": self.world.get_tile(entity.x, entity.y).tile_type},
            )
        tile_before = self.world.get_tile(entity.x, entity.y)
        body_before = self.capture_state(entity)

        self.environment_system.apply(self, entity)

        tile_after = self.world.get_tile(entity.x, entity.y)
        body_after = self.capture_state(entity)

        if body_before["hunger"] != body_after["hunger"] or body_before["thirst"] != body_after["thirst"]:
        #uma causa, um evento. 
         self.log_event(
            entity_name=entity.name,
            action="ingest",
            reason=tile_before.tile_type,
            before=body_before,
            after=body_after,
            context={"tile_antes": tile_before.tile_type, "tile_depois": tile_after.tile_type},
        )




    def perceive(self, entity):
        if getattr(entity, "sensor", None) is None:
            return None
        percepcao = Perception()
        luz = self.sky.get_light(self.gtime)
        alcance = entity.sensor.range_

        for ddx in range(-alcance, alcance +1):
            for ddy in range(-alcance, alcance +1):
                if ddx == 0 and ddy == 0:
                    continue

                tx, ty = entity.x + ddx, entity.y + ddy
                if not self.world.is_inside(tx, ty):
                    continue 

                spatial = Spatial(entity.x, entity.y, tx, ty)
                if not entity.sensor.can_perceive(spatial, entity.orientation, luz):
                    continue

                tile = self.world.get_tile(tx, ty)
                ocupado = self.world.get_entity_at(tx, ty) is not None
                percepcao.add(spatial, tile, ocupado)
        return percepcao

    def decide_action(self, entity, perception):
        if entity.decision_system is not None:
            return entity.decision_system.decide(entity, perception)
        return self.affordance_system.legal_actions(self.world, entity)

    def act(self, entity, directions):
        for dx, dy in directions:
            if self.world.move_entity(entity, dx, dy):
                if (dx, dy) != (0, 0):
                    entity.orientation = (dx, dy)
                return f"moved ({dx}, {dy})"
        return "tried to move"


    def step(self):
        fase_antes = self.sky.get_state(self.gtime)
        luz_antes = self.sky.get_light(self.gtime)

        for entity in self.world.entities:
            self.process_entity(entity)

        self.gtime.adv()

        fase_depois = self.sky.get_state(self.gtime)
        luz_depois = self.sky.get_light(self.gtime)

        if fase_antes != fase_depois:
            self.log_event(
                entity_name="ceu",
                action="mudou_fase",
                reason="ciclo natural",
                before={"fase": fase_antes, "luz": round(luz_antes, 2)},
                after={"fase": fase_depois, "luz": round(luz_depois, 2)},
                context={"mtk": self.gtime.mtk},
            )
    
    def advance_one(self, render_enabled=False):
        if self.gtime.mtk >= self.simulation_duration:
            return False
        self.step()

        if render_enabled:
            self.render()

        return True

    def run(self, render_enabled=True, steps_per_frame=1):
        #steps_per_frame=1 aceleração. Roda diversos ticks entre cada frame redenrizado.
        while self.gtime.mtk < self.simulation_duration:
            for _ in range(steps_per_frame):
                if self.gtime.mtk >= self.simulation_duration:
                    break 
                self.step()

            if render_enabled:
                self.render()
                time.sleep(self.frame_delay)


    def render(self):
        
        frame = self._build_frame()
        sys.stdout.write("\033[H\033[J")
        sys.stdout.write(frame + "\n")
        sys.stdout.flush()
