"""Entrada do mundo populacional atual sem alterar seu runtime."""

from pathlib import Path

from core.experiments.registry import Experiment
from core.interface.server import serve
from core.simulation.experiments import load_checkpoint
from core.simulation.population import PopulationConfig, PopulationSimulation


def world_experiment(config: PopulationConfig, resume: Path | None = None) -> Experiment:
    def create_simulation():
        return load_checkpoint(resume) if resume else PopulationSimulation(config)

    return Experiment("mundo", "Mundo", create_simulation, serve)

