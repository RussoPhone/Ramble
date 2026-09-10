import { makeScene } from './scene-model.mjs';

function envelope(data) {
  if (data?.schemaVersion !== 2 || typeof data.worldRevision !== 'string' ||
      !Number.isInteger(data.tick) || data.tick < 0) throw new Error('Representação incompatível');
}
function pair(value) {
  return Array.isArray(value) && value.length === 2 && value.every(Number.isInteger);
}
function records(items, layer) {
  if (!Array.isArray(items)) throw new Error(`Camada ${layer} ausente`);
  const ids = new Set();
  for (const item of items) {
    if (!item || item.layer !== layer || item.id == null || typeof item.kind !== 'string' ||
        !Number.isInteger(item.x) || !Number.isInteger(item.y) || ids.has(String(item.id))) {
      throw new Error(`Registro inválido: ${layer}`);
    }
    if (layer === 'terrain' && (typeof item.blocking !== 'boolean' || item.id !== `${item.x},${item.y}`))
      throw new Error('Terreno inválido');
    if (layer === 'object' && (!Number.isInteger(item.quantity) || item.quantity < 1))
      throw new Error('Quantidade inválida');
    if (layer === 'agent') {
      if (!Number.isFinite(item.body?.hunger) || !Number.isFinite(item.body?.thirst) ||
          !pair(item.orientation) || !pair(item.micro_position) ||
          !Array.isArray(item.collision_cells) || item.collision_cells.length !== 2 ||
          !item.collision_cells.every(pair)) throw new Error('Agente inválido');
      if (item.carrying) records([item.carrying], 'object');
    }
    ids.add(String(item.id));
  }
}
function agentGeometry(items, width, height) {
  const maxX = width * 3, maxY = height * 3;
  for (const item of items) {
    const [base, nose] = item.collision_cells;
    const [mx, my] = item.micro_position;
    if (base[0] !== mx || base[1] !== my ||
        Math.abs(nose[0] - mx) + Math.abs(nose[1] - my) !== 1 ||
        nose[0] - mx !== item.orientation[0] || nose[1] - my !== item.orientation[1] ||
        item.x !== Math.floor(mx / 3) || item.y !== Math.floor(my / 3) ||
        item.collision_cells.some(([x,y])=>x<0 || y<0 || x>=maxX || y>=maxY)) {
      throw new Error('Geometria física inválida');
    }
  }
}
function dynamics(data) {
  records(data.objects, 'object'); records(data.agents, 'agent');
  if (!data.control || typeof data.control.running !== 'boolean' ||
      !Number.isFinite(data.control.speed) || data.control.speed <= 0 ||
      !Number.isInteger(data.control.remaining) || data.control.remaining < 0) throw new Error('Relógio inválido');
  if (!Array.isArray(data.events)) throw new Error('Eventos inválidos');
}
function bounds(items, width, height) {
  if (items.some(i=>i.x<0 || i.y<0 || i.x>=width || i.y>=height)) throw new Error('Posição fora do mundo');
}
export class SimulationStore {
  scene = null;
  previous = null;
  bootstrap(data) {
    envelope(data); dynamics(data); records(data.terrain, 'terrain');
    if (!Number.isInteger(data.width) || !Number.isInteger(data.height) ||
        data.width < 1 || data.height < 1) throw new Error('Dimensões inválidas');
    if (data.terrain.length !== data.width * data.height) throw new Error('Terreno incompleto');
    bounds([...data.terrain,...data.objects,...data.agents],data.width,data.height);
    agentGeometry(data.agents,data.width,data.height);
    const scene = makeScene(structuredClone(data));
    this.previous = null;
    this.scene = scene;
  }
  applyFrame(data) {
    if (this.scene && data?.schemaVersion !== this.scene.schemaVersion) return 'resync';
    envelope(data);
    if (!this.scene || data.worldRevision !== this.scene.worldRevision) return 'resync';
    if (data.tick < this.scene.tick) return 'stale';
    dynamics(data);
    bounds([...data.objects,...data.agents],this.scene.width,this.scene.height);
    agentGeometry(data.agents,this.scene.width,this.scene.height);
    const dynamic = structuredClone({tick:data.tick, agents:data.agents, objects:data.objects,
      events:data.events || [], control:data.control, population:data.population});
    const next = makeScene({...this.scene, ...dynamic});
    this.previous = this.scene;
    this.scene = next;
    return 'applied';
  }
}
