import pytest

from core.experiments.registry import Experiment, ExperimentRegistry


def runnable(slug, name, calls=None):
    calls = calls if calls is not None else []

    def create_simulation():
        calls.append(slug)
        return object()

    return Experiment(slug, name, create_simulation, lambda simulation, host, port: None)


def test_registry_resolves_nested_experiments_without_starting_them():
    calls = []
    messiah = runnable("messias", "Messias", calls)
    cooking = Experiment("culinaria", "Culinária", subexperiments=(messiah,))
    world = runnable("mundo", "Mundo", calls)

    registry = ExperimentRegistry((world, cooking))

    assert registry.entries == (world, cooking)
    assert registry.resolve(("culinaria",)) is cooking
    assert registry.resolve(("culinaria", "messias")) is messiah
    assert calls == []


def test_registry_rejects_duplicate_sibling_slugs():
    with pytest.raises(ValueError, match="duplicado"):
        ExperimentRegistry((runnable("mundo", "Mundo"), runnable("mundo", "Outro")))


@pytest.mark.parametrize("slug", ["", "Mundo", "dois mundos", "../mundo"])
def test_experiment_slug_is_a_safe_short_route(slug):
    with pytest.raises(ValueError, match="slug"):
        runnable(slug, "Mundo")


def test_experiment_is_either_runnable_or_a_group():
    with pytest.raises(ValueError, match="factory"):
        Experiment("vazio", "Vazio")
    with pytest.raises(ValueError, match="subexperimentos"):
        Experiment(
            "ambiguo",
            "Ambíguo",
            lambda: object(),
            lambda simulation, host, port: None,
            (runnable("filho", "Filho"),),
        )

