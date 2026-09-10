// RenderScene uses public world coordinates and records, with no DOM or transport.
const indices = new WeakMap();
function freeze(value) {
  if (value && typeof value === 'object' && !Object.isFrozen(value)) {
    Object.values(value).forEach(freeze); Object.freeze(value);
  }
  return value;
}
export function makeScene(data) {
  const byCell = new Map(), byId = new Map();
  for (const item of [...data.terrain, ...data.objects, ...data.agents]) {
    const key = `${item.x},${item.y}`;
    if (!byCell.has(key)) byCell.set(key, []);
    byCell.get(key).push(item);
    byId.set(`${item.layer}:${item.id}`, item);
  }
  freeze(data);
  for (const items of byCell.values()) Object.freeze(items);
  indices.set(data, {byCell, byId});
  return data;
}
export function cellRecords(scene, x, y) {
  return indices.get(scene)?.byCell.get(`${x},${y}`) || [];
}
export function entityRecord(scene, layer, id) {
  return indices.get(scene)?.byId.get(`${layer}:${id}`) || null;
}
