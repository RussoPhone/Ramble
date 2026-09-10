from core.experiments.registry import Experiment, ExperimentRegistry
from core.experiments.catalog import default_registry
from core.interface.server import serve
from core.main import main
from core.simulation.population import PopulationConfig, PopulationSimulation


def test_ui_selects_before_creating_simulation_and_hands_it_to_its_interface(monkeypatch):
    events = []
    simulation = object()

    def create_simulation():
        events.append("simulation")
        return simulation

    def run_interface(received, host, port):
        events.append((received, host, port))

    world = Experiment("mundo", "Mundo", create_simulation, run_interface)
    registry = ExperimentRegistry((world,))

    monkeypatch.setattr("core.main.default_registry", lambda config, resume: registry)

    def select(received, host, port):
        assert received is registry
        assert events == []
        events.append("selection")
        return world

    monkeypatch.setattr("core.main.select_experiment", select)

    main(["ui", "--port", "9012", "--population", "3"])

    assert events == ["selection", "simulation", (simulation, "127.0.0.1", 9012)]


def test_world_entry_keeps_the_current_population_runtime_and_observer():
    config = PopulationConfig(
        width=8, height=7, population=2, objects=6, stones=1, reproduction=False
    )

    world = default_registry(config).resolve(("mundo",))

    assert world.name == "Mundo"
    assert world.interface_factory is serve
    simulation = world.simulation_factory()
    assert isinstance(simulation, PopulationSimulation)
    assert simulation.config == config
