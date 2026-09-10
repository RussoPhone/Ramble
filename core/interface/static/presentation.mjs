function list(value) {
  return Array.isArray(value) ? value : [];
}

function sameId(left, right) {
  return String(left) === String(right);
}

export function updateConnection(root, _online, detail) {
  const label = root.getElementById("connection-label");
  if (label) label.textContent = detail;
}

export function actionGlyph(action) {
  return ({
    move: "›",
    turn: "↻",
    wait: "·",
    inspect: "?",
    ingest: "◇",
    pick: "↑",
    drop: "↓",
    place: "↧",
    give: "↔",
    touch: "×",
    signal: "))",
    birth: "+",
    death: "†",
  })[action] || "·";
}

export function appearanceStyle(appearance, alpha = 1) {
  let hash = 2166136261;
  for (const part of list(appearance)) {
    hash ^= Math.round((Number(part) || 0) * 1000);
    hash = Math.imul(hash, 16777619) >>> 0;
  }
  const hue = 28 + (hash % 112);
  const saturation = 28 + (hash % 34);
  const lightness = 42 + ((hash >>> 8) % 24);
  return {
    hue,
    saturation,
    lightness,
    color: `hsla(${hue}, ${saturation}%, ${lightness}%, ${Math.max(0, Math.min(1, alpha))})`,
  };
}

export function deriveWorldEffects(previous, next) {
  if (!previous || !next) return [];
  const effects = [];
  const oldAgents = new Map(list(previous.agents).map((agent) => [String(agent.id), agent]));
  for (const agent of list(next.agents)) {
    const before = oldAgents.get(String(agent.id));
    if (before && (before.x !== agent.x || before.y !== agent.y)) {
      effects.push({
        kind: "move",
        actor: agent.id,
        from: [before.x, before.y],
        to: [agent.x, agent.y],
        tick: next.tick,
      });
    }
  }
  for (const event of list(next.events)) {
    if (Number(event.tick) <= Number(previous.tick) || !Array.isArray(event.position)) continue;
    effects.push({
      kind: event.action,
      actor: event.actor,
      at: [...event.position],
      target: Array.isArray(event.target_position) ? [...event.target_position] : null,
      tick: event.tick,
    });
  }
  return effects.slice(-64);
}

export function reconcileSelection(selectedId, previousDetail, snapshot) {
  if (selectedId === null || selectedId === undefined) return null;
  if (snapshot?.selected && sameId(snapshot.selected.id, selectedId)) {
    return { id: snapshot.selected.id, detail: snapshot.selected, dead: false };
  }
  const present = list(snapshot?.agents).some((agent) => sameId(agent.id, selectedId));
  if (present) return { id: selectedId, detail: previousDetail, dead: false };
  const death = list(snapshot?.events).findLast((event) => (
    event.action === "death"
    && sameId(event.actor, selectedId)
    && Number(event.tick) === Number(snapshot?.tick)
  ));
  if (previousDetail && death) {
    return { id: selectedId, detail: previousDetail, dead: true, following: false };
  }
  return null;
}
