"""Catálogo mostrado pelo launcher padrão."""

from pathlib import Path

from core.experiments.registry import ExperimentRegistry
from core.experiments.world import world_experiment
from core.simulation.population import PopulationConfig


def default_registry(
    config: PopulationConfig, resume: Path | None = None
) -> ExperimentRegistry:
    return ExperimentRegistry((world_experiment(config, resume),))

