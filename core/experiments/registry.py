"""Definições pequenas e independentes de servidor para experimentos."""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any


SimulationFactory = Callable[[], Any]
InterfaceFactory = Callable[[Any, str, int], Any]
_SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


@dataclass(frozen=True)
class Experiment:
    slug: str
    name: str
    simulation_factory: SimulationFactory | None = None
    interface_factory: InterfaceFactory | None = None
    subexperiments: tuple["Experiment", ...] = ()

    def __post_init__(self) -> None:
        if not _SLUG.fullmatch(self.slug):
            raise ValueError("slug de experimento inválido")
        if not self.name.strip():
            raise ValueError("nome de experimento vazio")

        has_factory = self.simulation_factory is not None or self.interface_factory is not None
        runnable = self.simulation_factory is not None and self.interface_factory is not None
        if has_factory and not runnable:
            raise ValueError("simulation_factory e interface_factory devem aparecer juntas")
        if runnable == bool(self.subexperiments):
            raise ValueError("experimento deve ter factory de simulação e interface ou subexperimentos")
        _ensure_unique(self.subexperiments)

    @property
    def runnable(self) -> bool:
        return self.simulation_factory is not None


def _ensure_unique(entries: Sequence[Experiment]) -> None:
    slugs = [entry.slug for entry in entries]
    if len(slugs) != len(set(slugs)):
        raise ValueError("slug de experimento duplicado")


class ExperimentRegistry:
    def __init__(self, entries: Sequence[Experiment]):
        self.entries = tuple(entries)
        _ensure_unique(self.entries)

    def resolve(self, path: Sequence[str]) -> Experiment:
        if not path:
            raise KeyError("caminho de experimento vazio")
        entries = self.entries
        selected = None
        for slug in path:
            selected = next((entry for entry in entries if entry.slug == slug), None)
            if selected is None:
                raise KeyError("experimento não encontrado")
            entries = selected.subexperiments
        return selected
