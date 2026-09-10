import { cellRecords } from '../scene-model.mjs';
import { paintAsciiPreview } from '../renderers/ascii-renderer.mjs';
import { actionLabel, directionLabel, layerLabel } from './inspection-format.mjs';

function rowsFor(fields) {
  const rows = new Map();
  for (const dt of fields.querySelectorAll(':scope > dt')) {
    rows.set(dt.dataset.field, [dt, dt.nextElementSibling]);
  }
  return rows;
}

function rowFor(fields, rows, label) {
  let row = rows.get(label);
  if (row) rows.delete(label);
  else {
    const dt = document.createElement('dt');
    const dd = document.createElement('dd');
    dt.dataset.field = label;
    dt.textContent = label;
    fields.append(dt, dd);
    row = [dt, dd];
  }
  return row;
}

function addField(fields, rows, label, value) {
  const [, dd] = rowFor(fields, rows, label);
  if (dd.className || dd.childElementCount) {
    dd.className = '';
    dd.replaceChildren();
  }
  dd.textContent = String(value ?? '—');
}

function addMeter(fields, rows, label, value) {
  const level = value >= 75 ? 'high' : value >= 45 ? 'mid' : 'low';
  const [, dd] = rowFor(fields, rows, label);
  dd.className = 'meter-cell';
  dd.dataset.level = level;
  let track = dd.querySelector('.meter-track');
  let amount = dd.querySelector('.meter-amount');
  if (!track || !amount) {
    track = document.createElement('div');
    track.className = 'meter-track';
    amount = document.createElement('span');
    amount.className = 'meter-amount';
    dd.replaceChildren(track, amount);
  }
  track.setAttribute('role', 'meter');
  track.setAttribute('aria-label', label);
  track.setAttribute('aria-valuemin', '0');
  track.setAttribute('aria-valuemax', '100');
  track.setAttribute('aria-valuenow', String(Math.round(value)));
  let fill = track.querySelector('.meter-fill');
  if (!fill) {
    fill = document.createElement('span');
    fill.className = 'meter-fill';
    track.append(fill);
  }
  fill.style.width = `${Math.max(0, Math.min(100, value))}%`;
  amount.textContent = value.toFixed(1);
}

export function renderInspector(root, scene, item, detail = null, options = {}) {
  root.hidden = !item;
  if (!item) return;
  const isAgent = item.layer === 'agent';
  const tab = isAgent ? options.tab || 'summary' : 'summary';
  root.classList.toggle('deep', tab !== 'summary');
  root.querySelector('[data-category]').textContent = layerLabel(item.layer);
  root.querySelector('#cell-label').textContent = `NA CÉLULA · ${item.x}, ${item.y}`;
  root.querySelector('#inspector-tabs').hidden = !isAgent;
  root.querySelector('#inspector-summary').hidden = tab !== 'summary';
  root.querySelector('#history-panel').hidden = tab === 'summary';
  root.querySelector('#history-panel').setAttribute('aria-labelledby', `tab-${tab}`);
  for (const button of root.querySelectorAll('[data-tab]')) {
    button.setAttribute('aria-selected', String(button.dataset.tab === tab));
    button.tabIndex = button.dataset.tab === tab ? 0 : -1;
  }
  paintAsciiPreview(root.querySelector('#inspector-symbol'), item);
  root.querySelector('[data-title]').textContent = `${item.kind}${item.layer === 'terrain' ? '' : ` #${item.id}`}`;
  const fields = root.querySelector('[data-fields]');
  const rows = rowsFor(fields);
  addField(fields, rows, 'camada', layerLabel(item.layer));
  addField(fields, rows, 'posição', `${item.x}, ${item.y}`);
  if (item.layer === 'agent') {
    addField(fields, rows, 'orientação', directionLabel(item.orientation));
    addField(fields, rows, 'última ação', actionLabel(item.action));
    addMeter(fields, rows, 'fome', item.body.hunger);
    addMeter(fields, rows, 'sede', item.body.thirst);
    addField(fields, rows, 'geração', item.generation);
    addField(fields, rows, 'carga', item.carrying ? `${item.carrying.kind} #${item.carrying.id}` : 'nenhuma');
  } else if (item.layer === 'object') {
    addField(fields, rows, 'quantidade', item.quantity);
    addField(fields, rows, 'portátil', item.portable ? 'sim' : 'não');
    addField(fields, rows, 'ingerível', item.ingestible ? 'sim' : 'não');
  } else {
    addField(fields, rows, 'bloqueio', item.blocking ? 'sim' : 'não');
    const occupants = cellRecords(scene, item.x, item.y).filter((i) => i.layer !== 'terrain');
    addField(fields, rows, 'presentes', occupants.map((i) => `${i.kind} #${i.id}`).join(', ') || 'nenhum');
  }
  for (const [dt, dd] of rows.values()) { dt.remove(); dd?.remove(); }
}
