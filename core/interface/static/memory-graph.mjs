function list(value) {
  return Array.isArray(value) ? value : [];
}

function signatureLabel(signature) {
  const values = list(signature);
  return values.length ? values.join("·") : "∅";
}

export function experienceId(item) {
  const signature = list(item?.signature).join(",");
  return `experience:${item?.tick}:${item?.source}:${item?.actor}:${item?.action}:${item?.target ?? "-"}:${signature}`;
}

export function buildMemoryGraph(memory) {
  const relations = list(memory?.relations)
    .slice()
    .sort((left, right) => Number(right.weight || 0) - Number(left.weight || 0));
  const experiences = new Map();
  for (const experience of list(memory?.experiences)) {
    experiences.set(experienceId(experience), experience);
  }
  for (const relation of relations) {
    for (const evidence of list(relation.evidence)) {
      experiences.set(experienceId(evidence), evidence);
    }
  }

  const nodes = relations.map((relation) => ({
    id: `relation:${relation.id}`,
    kind: "relation",
    label: `assinatura ${signatureLabel(relation.signature)} · ${relation.action || "sem ação"}`,
    weight: Number(relation.weight || 0),
    confidence: Number(relation.confidence || 0),
    contradictions: Number(relation.contradictions || 0),
    data: relation,
  }));
  const orderedExperiences = [...experiences.entries()]
    .sort(([, left], [, right]) => Number(right.tick || 0) - Number(left.tick || 0));
  for (const [id, experience] of orderedExperiences) {
    nodes.push({
      id,
      kind: "experience",
      label: `t ${experience.tick} · ${experience.action || "sem ação"}`,
      data: experience,
    });
  }

  const known = new Set(experiences.keys());
  const edges = [];
  for (const relation of relations) {
    for (const evidence of list(relation.evidence)) {
      const target = experienceId(evidence);
      if (known.has(target)) edges.push({ from: `relation:${relation.id}`, to: target });
    }
  }
  return { nodes, edges };
}

function placeRing(nodes, center, radius, startAngle = -Math.PI / 2) {
  return nodes.map((node, index) => {
    const angle = startAngle + (index / Math.max(1, nodes.length)) * Math.PI * 2;
    return {
      ...node,
      x: center.x + Math.cos(angle) * radius,
      y: center.y + Math.sin(angle) * radius,
    };
  });
}

function placeInBands(nodes, center, innerRadius, outerRadius) {
  if (!nodes.length) return [];
  const capacity = Math.max(8, Math.floor((Math.PI * 2 * outerRadius) / 32));
  if (nodes.length <= capacity) return placeRing(nodes, center, outerRadius);
  const result = [];
  const bands = Math.ceil(nodes.length / capacity);
  for (let band = 0; band < bands; band += 1) {
    const start = band * capacity;
    const items = nodes.slice(start, start + capacity);
    const progress = bands === 1 ? 1 : band / (bands - 1);
    const radius = outerRadius - (outerRadius - innerRadius) * progress;
    result.push(...placeRing(items, center, radius, -Math.PI / 2 + band * 0.17));
  }
  return result;
}

export function layoutMemoryGraph(graph, width, height) {
  const center = { x: width / 2, y: height / 2 };
  const radius = Math.max(40, Math.min(width, height) * 0.28);
  const relations = list(graph?.nodes).filter((node) => node.kind === "relation");
  const experiences = list(graph?.nodes).filter((node) => node.kind === "experience");
  return [
    ...placeInBands(relations, center, radius * 0.18, radius * 0.55),
    ...placeInBands(experiences, center, radius * 0.64, radius),
  ];
}

export class MemoryGraphRenderer {
  constructor(canvas) {
    this.canvas = canvas;
    this.context = canvas.getContext("2d");
  }

  resize() {
    const bounds = this.canvas.getBoundingClientRect();
    const viewport = { width: Math.max(1, bounds.width), height: Math.max(1, bounds.height) };
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

  draw(graph, selectedId = null) {
    const viewport = this.resize();
    const ctx = this.context;
    ctx.clearRect(0, 0, viewport.width, viewport.height);
    ctx.fillStyle = "#0a0d09";
    ctx.fillRect(0, 0, viewport.width, viewport.height);
    const nodes = layoutMemoryGraph(graph, viewport.width, viewport.height);
    const byId = new Map(nodes.map((node) => [node.id, node]));

    ctx.strokeStyle = "rgba(188, 181, 139, .16)";
    ctx.lineWidth = 1;
    for (const edge of list(graph?.edges)) {
      const from = byId.get(edge.from);
      const to = byId.get(edge.to);
      if (!from || !to) continue;
      ctx.beginPath();
      ctx.moveTo(from.x, from.y);
      ctx.lineTo(to.x, to.y);
      ctx.stroke();
    }

    const hits = [];
    for (const node of nodes) {
      const relation = node.kind === "relation";
      const radius = relation ? Math.max(7, Math.min(18, 7 + Math.sqrt(node.weight || 0) * 2.4)) : 4.5;
      const selected = node.id === selectedId;
      ctx.save();
      ctx.globalAlpha = relation ? Math.max(0.32, Math.min(1, Number(node.confidence || 0) + 0.3)) : 0.72;
      ctx.translate(node.x, node.y);
      ctx.fillStyle = relation ? "#b5c77f" : "#78a39a";
      ctx.strokeStyle = selected ? "#fff0a6" : "rgba(235, 225, 184, .54)";
      ctx.lineWidth = selected ? 3 : 1;
      ctx.beginPath();
      if (relation) {
        ctx.moveTo(0, -radius);
        ctx.lineTo(radius, 0);
        ctx.lineTo(0, radius);
        ctx.lineTo(-radius, 0);
        ctx.closePath();
      } else {
        ctx.rect(-radius, -radius, radius * 2, radius * 2);
      }
      ctx.fill();
      ctx.stroke();
      if (relation && node.contradictions > 0) {
        ctx.strokeStyle = "#bd7361";
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.arc(0, 0, radius + 4, -Math.PI * 0.15, Math.PI * 0.55);
        ctx.stroke();
      }
      ctx.restore();
      if (selected || relation && nodes.length < 45) {
        ctx.fillStyle = selected ? "#f3ebc8" : "rgba(220, 213, 176, .68)";
        ctx.font = `${selected ? 650 : 500} 10px ui-monospace, monospace`;
        ctx.textAlign = "center";
        ctx.fillText(node.label, node.x, node.y + radius + 14, 190);
      }
      hits.push({ id: node.id, x: node.x, y: node.y, radius: Math.max(10, radius + 4) });
    }
    if (!nodes.length) {
      ctx.fillStyle = "rgba(194, 188, 155, .58)";
      ctx.font = "12px ui-monospace, monospace";
      ctx.textAlign = "center";
      ctx.fillText("Nenhuma memória registrada.", viewport.width / 2, viewport.height / 2);
    }
    return hits;
  }
}
