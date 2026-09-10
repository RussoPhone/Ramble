import test from "node:test";
import assert from "node:assert/strict";

import {
  fitCamera,
  worldToScreen,
  zoomCameraAt,
} from "../../core/interface/static/camera.mjs";
import {
  deriveWorldEffects,
  reconcileSelection,
  updateConnection,
} from "../../core/interface/static/presentation.mjs";
import {
  buildMemoryGraph,
  layoutMemoryGraph,
} from "../../core/interface/static/memory-graph.mjs";
import {
  buildWorldFrame,
  worldItemLabel,
} from "../../core/interface/static/world-renderer.mjs";

test("fitCamera keeps the complete world inside the viewport", () => {
  const camera = fitCamera(20, 10, 1000, 600, 32);

  assert.deepEqual(worldToScreen(camera, 0, 0), { x: 32, y: 66 });
  assert.deepEqual(worldToScreen(camera, 20, 10), { x: 968, y: 534 });
});

test("zoomCameraAt preserves the world point below the pointer", () => {
  const before = fitCamera(20, 10, 1000, 600, 32);
  const after = zoomCameraAt(before, 500, 300, 1.5);

  assert.deepEqual(worldToScreen(after, 10, 5), { x: 500, y: 300 });
});

test("effects contain movement and new spatial events only", () => {
  const previous = { tick: 4, agents: [{ id: 1, x: 1, y: 1 }] };
  const next = {
    tick: 5,
    agents: [{ id: 1, x: 2, y: 1 }],
    events: [
      { tick: 3, actor: 1, action: "signal", position: [1, 1] },
      { tick: 5, actor: 1, action: "signal", position: [2, 1] },
    ],
  };

  assert.deepEqual(deriveWorldEffects(previous, next), [
    { kind: "move", actor: 1, from: [1, 1], to: [2, 1], tick: 5 },
    { kind: "signal", actor: 1, at: [2, 1], target: null, tick: 5 },
  ]);
});

test("a vanished selection retains its last observation for one update", () => {
  const selected = { id: 3, body: { hunger: 90, thirst: 80 } };

  assert.deepEqual(
    reconcileSelection(3, selected, {
      tick: 8,
      agents: [],
      events: [{ tick: 8, actor: 3, action: "death", position: [4, 2] }],
    }),
    { id: 3, detail: selected, dead: true, following: false },
  );
});

test("connection status updates without a legacy connection wrapper", () => {
  const label = { textContent: "" };
  const root = {
    getElementById(id) {
      return id === "connection-label" ? label : null;
    },
  };

  updateConnection(root, true, "observando");

  assert.equal(label.textContent, "observando");
});

test("memory graph joins relations to their evidence without semantic labels", () => {
  const graph = buildMemoryGraph({
    relations: [{
      id: 7,
      signature: [2, 4, 6],
      action: "ingest",
      weight: 0.8,
      confidence: 0.5,
      contradictions: 2,
      evidence: [{
        tick: 9,
        source: "self",
        actor: 1,
        target: 4,
        action: "ingest",
        signature: [2, 4, 6],
      }],
    }],
    experiences: [{
      tick: 9,
      source: "self",
      actor: 1,
      target: 4,
      action: "ingest",
      signature: [2, 4, 6],
    }],
  });

  assert.deepEqual(graph.nodes.map(({ id, kind }) => ({ id, kind })), [
    { id: "relation:7", kind: "relation" },
    { id: "experience:9:self:1:ingest:4:2,4,6", kind: "experience" },
  ]);
  assert.deepEqual(graph.edges, [{
    from: "relation:7",
    to: "experience:9:self:1:ingest:4:2,4,6",
  }]);
  assert.equal(graph.nodes[0].label, "assinatura 2·4·6 · ingest");
});

test("world frame culls records and keeps screen-space hits", () => {
  const snapshot = {
    width: 100,
    height: 100,
    terrain: [
      { x: 9, y: 11 },
      { x: 10, y: 11 },
      { x: 14, y: 11 },
      { x: 15, y: 11 },
    ],
    objects: [{ id: 2, x: 12, y: 12 }],
    agents: [{ id: 3, x: 13, y: 11 }],
  };

  const frame = buildWorldFrame(
    snapshot,
    { cell: 20, offsetX: -200, offsetY: -200 },
    { width: 100, height: 100 },
    3,
  );

  assert.deepEqual(frame.terrain.map(({ x }) => x), [10, 14]);
  assert.deepEqual(frame.objects.map(({ id }) => id), [2]);
  assert.deepEqual(frame.hits[0], {
    id: 3,
    x: 70,
    y: 30,
    radius: 9,
    selected: true,
  });
  assert.deepEqual(frame.targets.find((target) => target.kind === "object"), {
    kind: "object",
    label: "objeto",
    x: 12,
    y: 12,
  });
});

test("world labels name physical kinds instead of appearance signatures", () => {
  assert.equal(worldItemLabel({ kind: "water" }), "água");
  assert.equal(worldItemLabel({ kind: "food" }), "comida");
  assert.equal(worldItemLabel({ kind: "stone" }), "pedra");
});

test("memory layout is deterministic and keeps nodes inside its viewport", () => {
  const graph = {
    nodes: [
      { id: "r1", kind: "relation" },
      { id: "r2", kind: "relation" },
      { id: "e1", kind: "experience" },
      { id: "e2", kind: "experience" },
      { id: "e3", kind: "experience" },
    ],
    edges: [],
  };

  const layout = layoutMemoryGraph(graph, 800, 600);

  assert.deepEqual(layout, layoutMemoryGraph(graph, 800, 600));
  assert.equal(layout.every(({ x, y }) => x >= 0 && x <= 800 && y >= 0 && y <= 600), true);
  const distance = ({ x, y }) => Math.hypot(x - 400, y - 300);
  const relations = layout.filter((node) => node.kind === "relation");
  const experiences = layout.filter((node) => node.kind === "experience");
  assert.equal(relations.every((node) => distance(node) < 168), true);
  assert.equal(experiences.every((node) => Math.abs(distance(node) - 168) < 0.000001), true);
});
