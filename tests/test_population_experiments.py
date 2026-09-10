import json
import subprocess
import sys

from core.simulation.experiments import run_experiment, save_checkpoint, load_checkpoint
from core.simulation.population import PopulationSimulation, PopulationConfig


def config():
    return PopulationConfig(width=8, height=8, population=3, objects=15, stones=0, reproduction=False)


def test_jsonl_records_manifest_metrics_and_final_result(tmp_path):
    target = tmp_path / 'run.jsonl'
    result = run_experiment(config(), ticks=40, output=target, sample_every=10)
    rows = [json.loads(line) for line in target.read_text().splitlines()]
    assert rows[0]['type'] == 'manifest'
    assert rows[0]['config']['seed'] == 42 and rows[0]['code_hash']
    assert rows[-1]['type'] == 'result' and rows[-1]['tick'] == 40
    assert result['tick'] == 40
    assert [r['tick'] for r in rows if r['type'] == 'metrics'] == [10, 20, 30, 40]


def test_checkpoint_restores_full_evolution(tmp_path):
    a = PopulationSimulation(config())
    for _ in range(20):
        a.step()
    target = tmp_path / 'state.gaea'
    save_checkpoint(a, target)
    b = load_checkpoint(target)
    for _ in range(20):
        a.step()
        b.step()
    assert a.snapshot() == b.snapshot()
    for uid in a.agents:
        assert a.snapshot(uid) == b.snapshot(uid)


def test_cli_batch_runs_multiple_seeds_without_interface(tmp_path):
    result = subprocess.run([sys.executable, '-m', 'core.main', 'batch', '--seeds', '2,3',
        '--ticks', '5', '--population', '2', '--width', '8', '--height', '8',
        '--objects', '10', '--stones', '0', '--output', str(tmp_path)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert len(list(tmp_path.glob('*.jsonl'))) == 2
    assert all(json.loads(p.read_text().splitlines()[-1])['tick'] == 5 for p in tmp_path.glob('*.jsonl'))


def test_run_rejects_invalid_tick_count_before_creating_output(tmp_path):
    import pytest
    target = tmp_path / 'bad.jsonl'
    with pytest.raises(ValueError):
        run_experiment(config(), ticks=-1, output=target)
    assert not target.exists()
