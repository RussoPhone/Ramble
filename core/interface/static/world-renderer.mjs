import { fitCamera, visibleBounds, worldToScreen } from "./camera.mjs";
import { actionGlyph, appearanceStyle } from "./presentation.mjs";

export function worldItemLabel(item) {
  return ({ water: "água", food: "comida", stone: "pedra", ground: "chão" })[item?.kind] || "objeto";
}

function list(value) {
  return Array.isArray(value) ? value : [];
}

function sameId(left, right) {
  return String(left) === String(right);
}

function within(item, bounds) {
  return item.x >= bounds.left && item.x <= bounds.right
    && item.y >= bounds.top && item.y <= bounds.bottom;
}

export function buildWorldFrame(snapshot, camera, viewport, selectedId) {
  const bounds = visibleBounds(
    camera,
    viewport,
    Math.max(1, Number(snapshot.width) || 1),
    Math.max(1, Number(snapshot.height) || 1),
  );
  const agents = list(snapshot.agents).filter((item) => within(item, bounds));
  const terrain = list(snapshot.terrain).filter((item) => within(item, bounds));
  const objects = list(snapshot.objects).filter((item) => within(item, bounds));
  return {
    bounds,
    terrain,
    objects,
    agents,
    targets: [
      ...terrain.map((item) => ({ kind: "tile", label: worldItemLabel(item), x: item.x, y: item.y })),
      ...objects.map((item) => ({ kind: "object", label: worldItemLabel(item), x: item.x, y: item.y })),
      ...agents.map((item) => ({ kind: "agent", label: `Gaiano #${item.id}`, x: item.x, y: item.y, id: item.id })),
    ],
    hits: agents.map((agent) => ({
      id: agent.id,
      ...worldToScreen(camera, agent.x + 0.5, agent.y + 0.5),
      radius: Math.max(9, camera.cell * 0.35),
      selected: sameId(agent.id, selectedId),
    })),
  };
}

function direction(value) {
  const [rawX = 0, rawY = -1] = list(value);
  const length = Math.hypot(Number(rawX) || 0, Number(rawY) || 0) || 1;
  return { x: (Number(rawX) || 0) / length, y: (Number(rawY) || 0) / length };
}

function interpolatedAgents(snapshot, previous, progress) {
  if (!previous || progress >= 1) return list(snapshot.agents);
  const prior = new Map(list(previous.agents).map((agent) => [String(agent.id), agent]));
  return list(snapshot.agents).map((agent) => {
    const before = prior.get(String(agent.id));
    if (!before) return agent;
    return {
      ...agent,
      x: before.x + (agent.x - before.x) * progress,
      y: before.y + (agent.y - before.y) * progress,
    };
  });
}

export class WorldRenderer {
  constructor(canvas) {
    this.canvas = canvas;
    this.context = canvas.getContext("2d");
    this.targets = [];
  }

  viewport() {
    const bounds = this.canvas.getBoundingClientRect();
    return { width: Math.max(1, bounds.width), height: Math.max(1, bounds.height) };
  }

  resize() {
    const viewport = this.viewport();
    const ratio = Math.min(globalThis.devicePixelRatio || 1, 2);
    const width = Math.round(viewport.width * ratio);
    const height = Math.round(viewport.height * ratio);
    if (this.canvas.width !== width || this.canvas.height !== height) {
      this.canvas.width = width;
      this.canvas.height = height;
    }
    this.context.setTransform(ratio, 0, 0, ratio, 0, 0);
    return viewport;
  }

  draw(snapshot, camera, frameState = {}) {
    const viewport = this.resize();
    const ctx = this.context;
    ctx.clearRect(0, 0, viewport.width, viewport.height);
    ctx.fillStyle = "#0d110d";
    ctx.fillRect(0, 0, viewport.width, viewport.height);
    if (!snapshot || !camera) return [];

    const progress = Math.max(0, Math.min(1, Number(frameState.motionProgress ?? 1)));
    const visualSnapshot = {
      ...snapshot,
      agents: interpolatedAgents(snapshot, frameState.previousSnapshot, progress),
    };
    const frame = buildWorldFrame(
      visualSnapshot,
      camera,
      viewport,
      frameState.selectedId,
    );
    this.targets = frame.targets;
    this.#drawWorldBase(snapshot, camera);
    for (const tile of frame.terrain) this.#drawTile(tile, camera);
    for (const object of frame.objects) this.#drawObject(object, camera);
    for (const agent of frame.agents) {
      this.#drawAgent(agent, camera, sameId(agent.id, frameState.selectedId));
    }
    return frame.hits;
  }

  drawPerception(selected, viewport = this.resize()) {
    const ctx = this.context;
    ctx.clearRect(0, 0, viewport.width, viewport.height);
    ctx.fillStyle = "#090c09";
    ctx.fillRect(0, 0, viewport.width, viewport.height);
    this.targets = [];
    if (!selected) return [];
    const perception = list(selected.perception);
    const range = Math.max(1, ...perception.flatMap((item) => [
      Math.abs(Number(item.dx) || 0),
      Math.abs(Number(item.dy) || 0),
    ]));
    const side = range * 2 + 1;
    const camera = fitCamera(side, side, viewport.width, viewport.height, 48);
    const center = range;

    for (const item of perception) {
      const tile = {
        ...item,
        x: center + (Number(item.dx) || 0),
        y: center + (Number(item.dy) || 0),
      };
      if (item.token === -1) this.#drawTile(tile, camera);
      else this.#drawPerceivedItem(tile, camera);
    }
    this.#drawAgent({
      id: selected.id,
      x: center,
      y: center,
      orientation: selected.orientation,
      action: selected.action,
      carrying: selected.carried,
    }, camera, true);
    return [];
  }

  #drawWorldBase(snapshot, camera) {
    const ctx = this.context;
    const origin = worldToScreen(camera, 0, 0);
    ctx.fillStyle = "#405033";
    ctx.fillRect(origin.x, origin.y, snapshot.width * camera.cell, snapshot.height * camera.cell);
    ctx.strokeStyle = "rgba(18, 27, 18, .45)";
    ctx.lineWidth = 1;
    ctx.strokeRect(origin.x, origin.y, snapshot.width * camera.cell, snapshot.height * camera.cell);
  }

  #drawTile(tile, camera) {
    const ctx = this.context;
    const point = worldToScreen(camera, tile.x, tile.y);
    const cell = camera.cell;
    const kind = tile.kind || (tile.blocking ? "stone" : "ground");
    const colors = { ground: "#52663e", water: "#317aa1", stone: "#70736b", food: "#52663e" };
    ctx.fillStyle = colors[kind] || "#52663e";
    ctx.fillRect(point.x, point.y, cell + 0.4, cell + 0.4);
    if (kind === "water") {
      ctx.strokeStyle = "rgba(191, 226, 238, .54)";
      ctx.lineWidth = Math.max(1, cell * .045);
      for (const y of [.3, .62]) {
        ctx.beginPath();
        ctx.moveTo(point.x + cell * .16, point.y + cell * y);
        ctx.lineTo(point.x + cell * .5, point.y + cell * (y - .04));
        ctx.lineTo(point.x + cell * .84, point.y + cell * y);
        ctx.stroke();
      }
    } else if (kind === "stone") {
      ctx.fillStyle = "#50554f";
      ctx.beginPath();
      ctx.moveTo(point.x + cell * 0.12, point.y + cell * 0.82);
      ctx.lineTo(point.x + cell * 0.34, point.y + cell * 0.2);
      ctx.lineTo(point.x + cell * 0.58, point.y + cell * 0.48);
      ctx.lineTo(point.x + cell * 0.78, point.y + cell * 0.16);
      ctx.lineTo(point.x + cell * 0.92, point.y + cell * 0.84);
      ctx.closePath();
      ctx.fill();
    }
    if (cell >= 28) {
      ctx.strokeStyle = "rgba(220, 210, 174, .055)";
      ctx.strokeRect(point.x + 0.5, point.y + 0.5, cell - 1, cell - 1);
    }
  }

  #drawObject(object, camera) {
    const ctx = this.context;
    const center = worldToScreen(camera, object.x + 0.5, object.y + 0.5);
    const size = Math.max(4, Math.min(14, camera.cell * 0.24));
    ctx.save();
    ctx.translate(center.x, center.y);
    if (object.kind === "food") {
      ctx.fillStyle = "#284d2d";
      for (const [x, y] of [[0, -size * .45], [-size * .55, size * .1], [size * .55, size * .12]]) {
        ctx.beginPath(); ctx.arc(x, y, size * .62, 0, Math.PI * 2); ctx.fill();
      }
      ctx.fillStyle = "#cf674b";
      for (const [x, y] of [[0, -size * .45], [-size * .35, size * .25], [size * .4, size * .18]]) {
        ctx.beginPath(); ctx.arc(x, y, Math.max(1.4, size * .17), 0, Math.PI * 2); ctx.fill();
      }
    } else if (object.kind === "water") {
      ctx.fillStyle = "#3b90b7";
      ctx.beginPath(); ctx.ellipse(0, 0, size * 1.2, size * .72, 0, 0, Math.PI * 2); ctx.fill();
      ctx.strokeStyle = "#b9e0ed"; ctx.lineWidth = Math.max(1, size * .12);
      ctx.beginPath(); ctx.moveTo(-size * .65, 0); ctx.lineTo(size * .65, 0); ctx.stroke();
    } else {
      ctx.fillStyle = "#8a897e";
      ctx.beginPath();
      ctx.moveTo(0, -size); ctx.lineTo(size, -size * .2); ctx.lineTo(size * .58, size);
      ctx.lineTo(-size * .72, size * .75); ctx.lineTo(-size, -size * .25); ctx.closePath(); ctx.fill();
      ctx.strokeStyle = "#bdbaaa"; ctx.lineWidth = Math.max(1, size * .11); ctx.stroke();
    }
    ctx.restore();
    if (camera.cell >= 28 && Number(object.quantity) > 1) {
      ctx.fillStyle = "#f5ead0";
      ctx.font = `600 ${Math.max(9, camera.cell * 0.24)}px ui-monospace, monospace`;
      ctx.fillText(String(object.quantity), center.x + size, center.y - size);
    }
  }

  #drawAgent(agent, camera, selected) {
    const ctx = this.context;
    const center = worldToScreen(camera, agent.x + 0.5, agent.y + 0.5);
    const radius = Math.max(4.5, Math.min(14, camera.cell * 0.3));
    const facing = direction(agent.orientation);
    ctx.save();
    ctx.translate(center.x, center.y);
    ctx.rotate(Math.atan2(facing.y, facing.x) + Math.PI / 2);
    ctx.fillStyle = agent.alive === false ? "#706b5e" : "#e9d8ae";
    ctx.strokeStyle = selected ? "#fff2a6" : "#263225";
    ctx.lineWidth = selected ? 2.4 : 1.2;
    ctx.beginPath();
    ctx.ellipse(0, radius * .26, radius * .65, radius * .9, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();
    ctx.fillStyle = "#e9d8ae";
    ctx.beginPath();
    ctx.arc(0, -radius * .68, radius * .43, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();
    ctx.restore();

    if (agent.carrying) {
      ctx.fillStyle = appearanceStyle(agent.carrying.appearance || agent.carrying).color;
      ctx.fillRect(center.x + radius * 0.55, center.y + radius * 0.5, radius * 0.65, radius * 0.65);
    }
  }

  #drawPerceivedItem(item, camera) {
    const ctx = this.context;
    const center = worldToScreen(camera, item.x + 0.5, item.y + 0.5);
    const size = Math.max(4, camera.cell * 0.18);
    ctx.fillStyle = appearanceStyle(item.appearance).color;
    ctx.beginPath();
    ctx.arc(center.x, center.y, size, 0, Math.PI * 2);
    ctx.fill();
    if (item.action || item.signal !== null && item.signal !== undefined) {
      ctx.fillStyle = "#f1dfa1";
      ctx.font = `600 ${Math.max(10, camera.cell * 0.24)}px ui-monospace, monospace`;
      ctx.textAlign = "center";
      ctx.fillText(item.signal ?? actionGlyph(item.action), center.x, center.y - size - 4);
    }
  }

}
