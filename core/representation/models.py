"""Version 2 public records; agents expose coarse and microcell positions."""
from dataclasses import dataclass
from typing import Literal

SCHEMA_VERSION = 2


@dataclass(frozen=True, slots=True)
class TerrainView:
    id: str
    x: int
    y: int
    kind: str
    blocking: bool
    appearance: tuple[int, ...]
    layer: Literal['terrain'] = 'terrain'


@dataclass(frozen=True, slots=True)
class ObjectView:
    id: int
    kind: str
    x: int
    y: int
    quantity: int
    appearance: tuple[int, ...]
    portable: bool
    ingestible: bool
    carrier: int | None
    cells: tuple[tuple[int, int], ...]
    layer: Literal['object'] = 'object'


@dataclass(frozen=True, slots=True)
class BodyView:
    hunger: float
    thirst: float


@dataclass(frozen=True, slots=True)
class AgentView:
    id: int
    x: int
    y: int
    orientation: tuple[int, int]
    action: str | None
    body: BodyView
    generation: int
    age: int
    carrying: ObjectView | None
    micro_position: tuple[int, int]
    collision_cells: tuple[tuple[int, int], tuple[int, int]]
    kind: str = 'gaiano'
    layer: Literal['agent'] = 'agent'
