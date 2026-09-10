"""Fine physical occupancy inside coarse world tiles."""
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Shape:
    cells: tuple[tuple[int, int], ...] = ((1, 1),)

    def __post_init__(self):
        normalized = tuple(dict.fromkeys((int(x), int(y)) for x, y in self.cells))
        if not normalized:
            raise ValueError("shape deve ocupar ao menos uma microcélula")
        object.__setattr__(self, "cells", normalized)


@dataclass(frozen=True, slots=True)
class _PhysicalRecord:
    cells: tuple[tuple[int, int], ...]
    visible_cells: tuple[tuple[int, int], ...]
    blocks: bool
    anchor: tuple[int, int] | None = None


class PhysicalSpace:
    def __init__(self, width, height, scale=3):
        if scale < 1:
            raise ValueError("escala física inválida")
        self.width = width
        self.height = height
        self.scale = scale
        self._records = {}
        self._blocking = {}
        self._occupancy = {}

    def _key(self, layer, token):
        return (layer, token)

    def _absolute_cells(self, x, y, shape):
        return tuple((x * self.scale + dx, y * self.scale + dy) for dx, dy in shape.cells)

    def _inside_micro(self, mx, my):
        return 0 <= mx < self.width * self.scale and 0 <= my < self.height * self.scale

    @staticmethod
    def _normalized(cells):
        return tuple(dict.fromkeys((int(x), int(y)) for x, y in cells))

    def can_place_cells(self, cells, ignore=None, blocks=True):
        ignore = ignore or ()
        for cell in self._normalized(cells):
            if not self._inside_micro(*cell):
                return False
            if blocks:
                blocker = self._blocking.get(cell)
                if blocker is not None and blocker != ignore:
                    return False
        return True

    def can_place(self, token, x, y, shape, ignore=None, blocks=True):
        return self.can_place_cells(self._absolute_cells(x, y, shape), ignore, blocks)

    def _install(self, key, record):
        self._records[key] = record
        for cell in record.cells:
            self._occupancy.setdefault(cell, set()).add(key)
            if record.blocks:
                self._blocking[cell] = key

    def place_cells(self, layer, token, cells, *, blocks=False, visible_cells=None, anchor=None):
        key = self._key(layer, token)
        cells = self._normalized(cells)
        visible = self._normalized(visible_cells if visible_cells is not None else cells)
        if not cells or len(visible) != len(cells):
            raise ValueError("shape deve ocupar ao menos uma microcélula")
        if not self.can_place_cells(cells, ignore=key, blocks=blocks):
            raise ValueError("shape sem espaço físico")
        if key in self._records:
            self.remove(layer, token)
        self._install(key, _PhysicalRecord(cells, visible, bool(blocks), anchor))

    def place(self, layer, token, x, y, shape=None, blocks=False):
        shape = shape or Shape()
        self.place_cells(layer, token, self._absolute_cells(x, y, shape), blocks=blocks,
                         visible_cells=shape.cells, anchor=(x, y))

    def remove(self, layer, token):
        key = self._key(layer, token)
        record = self._records.pop(key, None)
        if record is None:
            return
        for cell in record.cells:
            tokens = self._occupancy.get(cell)
            if tokens:
                tokens.discard(key)
                if not tokens:
                    del self._occupancy[cell]
            if record.blocks and self._blocking.get(cell) == key:
                del self._blocking[cell]

    def move_cells(self, layer, token, cells, *, visible_cells=None, anchor=None):
        key = self._key(layer, token)
        old = self._records[key]
        cells = self._normalized(cells)
        visible = self._normalized(visible_cells if visible_cells is not None else old.visible_cells)
        if not cells or len(visible) != len(cells):
            return False
        if not self.can_place_cells(cells, ignore=key, blocks=old.blocks):
            return False
        self.remove(layer, token)
        self._install(key, _PhysicalRecord(cells, visible, old.blocks, anchor))
        return True

    def move(self, layer, token, x, y):
        key = self._key(layer, token)
        record = self._records[key]
        shape = Shape(record.visible_cells)
        return self.move_cells(layer, token, self._absolute_cells(x, y, shape),
                               visible_cells=shape.cells, anchor=(x, y))

    def cells_for(self, layer, token):
        return self._records[self._key(layer, token)].cells

    def local_cells_for(self, layer, token):
        return self._records[self._key(layer, token)].visible_cells

    def tokens_at_tile(self, x, y):
        left = x * self.scale
        top = y * self.scale
        result = set()
        for my in range(top, top + self.scale):
            for mx in range(left, left + self.scale):
                result.update(self._occupancy.get((mx, my), ()))
        return tuple(sorted(result))

    def _same_anchor(self, left, right):
        left_record = self._records.get(left)
        right_record = self._records.get(right)
        return bool(left_record and right_record and left_record.anchor is not None
                    and left_record.anchor == right_record.anchor)

    def _line_clear(self, x0, y0, x1, y1, target, ignore=()):
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
        err = dx + dy
        while (x0, y0) != (x1, y1):
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy
            if (x0, y0) != (x1, y1):
                blocker = self._blocking.get((x0, y0))
                if (blocker is not None and blocker != target and blocker not in ignore
                        and not self._same_anchor(blocker, target)):
                    return False
        return True

    def visible_parts_from_micro(self, viewer_micro_x, viewer_micro_y, layer, token, ignore=()):
        key = self._key(layer, token)
        cells = self.cells_for(layer, token)
        origin = (viewer_micro_x, viewer_micro_y)
        record = self._records[key]
        visible = []
        for local, cell in zip(record.visible_cells, cells):
            if self._line_clear(origin[0], origin[1], cell[0], cell[1], key, ignore):
                visible.append(local)
        return tuple(visible)

    def visible_parts(self, viewer_x, viewer_y, layer, token, ignore=()):
        return self.visible_parts_from_micro(
            viewer_x * self.scale + self.scale // 2,
            viewer_y * self.scale + self.scale // 2,
            layer, token, ignore,
        )
