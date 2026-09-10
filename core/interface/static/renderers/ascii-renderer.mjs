import { BaseRenderer } from './base-renderer.mjs';

const TERRAIN_GLYPH = Object.freeze({ grass: '"', stone: '#', water: '~' });
const TERRAIN_COLOR = Object.freeze({ grass: '#526044', stone: '#818577', water: '#5f7e83' });
const OBJECT_GLYPH = Object.freeze({ food: 'o', water: '~', stone: '*' });
const OBJECT_COLOR = Object.freeze({ food: '#b6885e', water: '#86a4a7', stone: '#aaa797' });

export function asciiGlyph(item, cellSize = 0) {
  if (item.layer === 'agent') return '@';
  if (item.kind === 'stack') return '&';
  if (item.layer === 'terrain') return TERRAIN_GLYPH[item.kind] || '.';
  return OBJECT_GLYPH[item.kind] || '?';
}

export function asciiColor(item) {
  if (item.layer === 'agent') return '#6e5a3d';
  if (item.kind === 'stack') return '#c3b597';
  if (item.layer === 'terrain') return TERRAIN_COLOR[item.kind] || '#777';
  return OBJECT_COLOR[item.kind] || '#aaa';
}

export function paintAsciiPreview(canvas, item) {
  const side = canvas.id === 'inspector-symbol' ? 40 : 26;
  const ratio = 2;
  canvas.width = canvas.height = side * ratio;
  const ctx = canvas.getContext('2d');
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
  ctx.fillStyle = '#20261f';
  ctx.fillRect(0, 0, side, side);
  ctx.fillStyle = asciiColor(item);
  ctx.font = `bold ${Math.floor(side * 0.62)}px monospace`;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText(asciiGlyph(item), side / 2, side / 2);
}

export class AsciiRenderer extends BaseRenderer {
  background = '#e3d5b8';

  mark(item, camera, glyph, color) {
    const ctx = this.ctx;
    ctx.fillStyle = color;
    ctx.font = `bold ${Math.max(8, Math.floor(camera.cell * 0.75))}px monospace`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    const point=item.layer==='agent'?this.agentWorldPoint(item):{x:item.x+.5,y:item.y+.5};
    ctx.fillText(glyph,camera.offsetX+point.x*camera.cell,camera.offsetY+point.y*camera.cell);
  }

  tile(item, camera) {
    this.mark(item, camera, asciiGlyph(item), asciiColor(item));
  }

  object(item, camera, stack) {
    if (item.id !== stack[stack.length - 1].id) return;
    if (camera.cell >= 34) {
      this.physicalCells(item, camera, stack.length > 1 ? '#c3b597' : asciiColor(item));
      return;
    }
    this.mark(item, camera, stack.length > 1 ? '&' : asciiGlyph(item), asciiColor(item));
  }

  agent(item, camera, options={}) {
    if (camera.cell >= 34) {
      if(options.showCollisions)this.collisionCells(item,camera);
      this.triangle(item, camera);
      return;
    }
    this.mark(item, camera, asciiGlyph(item, camera.cell), asciiColor(item));
  }

  collisionCells(item,camera) {
    const unit=camera.cell/3,ctx=this.ctx;
    ctx.fillStyle='rgba(195, 181, 151, 0.68)';
    for(const [mx,my] of item.collision_cells)ctx.fillRect(
      camera.offsetX+mx*unit,camera.offsetY+my*unit,unit,unit);
  }

  physicalCells(item, camera, color) {
    const ctx = this.ctx;
    const cells = item.cells?.length ? item.cells : [[1, 1]];
    const unit = camera.cell / 3;
    ctx.fillStyle = color;
    for (const [dx, dy] of cells) {
      ctx.fillRect(
        camera.offsetX + item.x * camera.cell + dx * unit,
        camera.offsetY + item.y * camera.cell + dy * unit,
        Math.max(1, unit - 1),
        Math.max(1, unit - 1),
      );
    }
  }

  triangle(item, camera) {
    const [dx = 0, dy = -1] = item.orientation || [];
    const ctx = this.ctx;
    const unit = camera.cell / 3;
    const point=this.agentWorldPoint(item);
    const cx=camera.offsetX+point.x*camera.cell,cy=camera.offsetY+point.y*camera.cell;
    const half=unit*.42;
    ctx.fillStyle = asciiColor(item);
    ctx.beginPath();
    ctx.moveTo(cx + dx * unit * 1.45, cy + dy * unit * 1.45);
    ctx.lineTo(cx + dy * half, cy - dx * half);
    ctx.lineTo(cx - dy * half, cy + dx * half);
    ctx.closePath();
    ctx.fill();
  }
}
