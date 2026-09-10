const MIN_CELL = 8;
const MAX_CELL = 96;

function clamp(value, minimum, maximum) {
  return Math.max(minimum, Math.min(maximum, value));
}

export function fitCamera(columns, rows, width, height, margin = 32) {
  const safeColumns = Math.max(1, Number(columns) || 1);
  const safeRows = Math.max(1, Number(rows) || 1);
  const usableWidth = Math.max(1, width - margin * 2);
  const usableHeight = Math.max(1, height - margin * 2);
  const cell = clamp(
    Math.min(usableWidth / safeColumns, usableHeight / safeRows),
    MIN_CELL,
    MAX_CELL,
  );
  return {
    cell,
    offsetX: (width - safeColumns * cell) / 2,
    offsetY: (height - safeRows * cell) / 2,
  };
}

export function panCamera(camera, dx, dy) {
  return {
    ...camera,
    offsetX: camera.offsetX + dx,
    offsetY: camera.offsetY + dy,
  };
}

export function zoomCameraAt(camera, screenX, screenY, factor) {
  const cell = clamp(camera.cell * factor, MIN_CELL, MAX_CELL);
  const worldX = (screenX - camera.offsetX) / camera.cell;
  const worldY = (screenY - camera.offsetY) / camera.cell;
  return {
    cell,
    offsetX: screenX - worldX * cell,
    offsetY: screenY - worldY * cell,
  };
}

export function worldToScreen(camera, x, y) {
  return {
    x: camera.offsetX + x * camera.cell,
    y: camera.offsetY + y * camera.cell,
  };
}

export function screenToWorld(camera, x, y) {
  return {
    x: (x - camera.offsetX) / camera.cell,
    y: (y - camera.offsetY) / camera.cell,
  };
}

export function centerCameraOn(camera, worldX, worldY, viewport) {
  return {
    ...camera,
    offsetX: viewport.width / 2 - (worldX + 0.5) * camera.cell,
    offsetY: viewport.height / 2 - (worldY + 0.5) * camera.cell,
  };
}

export function visibleBounds(camera, viewport, columns, rows) {
  const left = clamp(Math.floor(-camera.offsetX / camera.cell), 0, columns - 1);
  const top = clamp(Math.floor(-camera.offsetY / camera.cell), 0, rows - 1);
  const right = clamp(
    Math.ceil((viewport.width - camera.offsetX) / camera.cell) - 1,
    0,
    columns - 1,
  );
  const bottom = clamp(
    Math.ceil((viewport.height - camera.offsetY) / camera.cell) - 1,
    0,
    rows - 1,
  );
  return { left, top, right, bottom };
}
