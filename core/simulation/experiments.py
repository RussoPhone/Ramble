"""Research-only outputs. No metrics or manifests are supplied to cognition."""
from dataclasses import asdict
import hashlib
import json
import math
import os
from pathlib import Path
import pickle
import platform
import tempfile
from time import perf_counter

from core.simulation.population import PopulationConfig, PopulationSimulation


def code_hash():
    root = Path(__file__).resolve().parents[1]
    digest = hashlib.sha256()
    for path in sorted(root.rglob('*.py')):
        digest.update(str(path.relative_to(root)).encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def save_checkpoint(simulation, path):
    """Atomic, versioned local checkpoint; pickle files must be trusted."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    sink = simulation.event_sink
    simulation.event_sink = None
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=path.name+'.', delete=False) as out:
            temporary = out.name
            out.write(b'GAEA-LOCAL-1\n')
            pickle.dump({'code_hash': code_hash(), 'simulation': simulation}, out, protocol=5)
            out.flush()
            os.fsync(out.fileno())
        os.replace(temporary, path)
    finally:
        simulation.event_sink = sink
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)


def load_checkpoint(path):
    with Path(path).open('rb') as source:
        if source.readline() != b'GAEA-LOCAL-1\n':
            raise ValueError('checkpoint incompatível')
        state = pickle.load(source)
    if state['code_hash'] != code_hash():
        raise ValueError('código mudou desde o checkpoint; use a revisão original para reproduzir')
    return state['simulation']


def run_experiment(config, ticks, output=None, sample_every=100, events=False,
                   checkpoint=None, resume=None, stop_extinct=True):
    if isinstance(ticks, bool) or not isinstance(ticks, int) or ticks < 0:
        raise ValueError('ticks deve ser inteiro não negativo')
    if not isinstance(sample_every, int) or sample_every < 1:
        raise ValueError('intervalo de métricas deve ser positivo')
    simulation = load_checkpoint(resume) if resume else PopulationSimulation(config)
    stream = None
    if output:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        stream = path.open('x', encoding='utf8')

    def record(row):
        if stream:
            stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True, allow_nan=False)+'\n')

    start_tick = simulation.tick
    start = perf_counter()
    try:
        record(dict(type='manifest', config=asdict(simulation.config), code_hash=code_hash(),
                    python=platform.python_version(), start_tick=start_tick, requested_ticks=ticks))
        if events:
            simulation.event_sink = lambda event: record(dict(type='event', **event))
        for _ in range(ticks):
            if stop_extinct and not simulation.agents:
                break
            simulation.step()
            if simulation.tick % sample_every == 0:
                record(dict(type='metrics', **simulation.metrics()))
                if stream:
                    stream.flush()
        if checkpoint:
            save_checkpoint(simulation, checkpoint)
        elapsed = perf_counter()-start
        result = dict(type='result', seed=simulation.config.seed, **simulation.metrics(),
                      elapsed_seconds=elapsed, ticks_per_second=(simulation.tick-start_tick)/max(elapsed, 1e-9),
                      extinct=not simulation.agents)
        record(result)
        return result
    finally:
        simulation.event_sink = None
        if stream:
            stream.close()


def benchmark(populations=(10, 50, 100), ticks=200, seed=42):
    """Live populations at constant density; no cheap post-extinction ticks."""
    if ticks < 1 or any(n < 1 for n in populations):
        raise ValueError('benchmark exige população e ticks positivos')
    rows = []
    for size in populations:
        width = max(10, math.ceil(math.sqrt(size*30)))
        config = PopulationConfig(seed=seed, width=width, height=width, population=size,
            objects=width*width//5, stones=width*width//30, metabolism=0,
            reproduction=False, population_limit=max(300, size))
        s = PopulationSimulation(config)
        for _ in range(30):
            s.step()
        start = perf_counter()
        for _ in range(ticks):
            s.step()
        elapsed = perf_counter()-start
        rows.append(dict(population=size, ticks=ticks, seconds=elapsed,
            milliseconds_per_tick=1000*elapsed/ticks, agent_steps_per_second=size*ticks/elapsed,
            alive=len(s.agents), relations=s.metrics()['relations']))
    return rows
