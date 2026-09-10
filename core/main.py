"""python -m core.main [ui|run|batch|benchmark]. No import-time execution."""
import argparse
from dataclasses import replace
import json
from pathlib import Path

from core.experiments.catalog import default_registry
from core.interface.launcher import select_experiment
from core.simulation.population import PopulationConfig
from core.simulation.experiments import run_experiment, benchmark


def parser():
    root = argparse.ArgumentParser(description='Gaea — laboratório populacional')
    modes = root.add_subparsers(dest='mode', required=True)
    for name in ('ui', 'run', 'batch'):
        sub = modes.add_parser(name)
        for option in ('seed', 'width', 'height', 'population', 'objects', 'stones', 'sensor_range',
                       'renewal', 'population_limit', 'memory_capacity'):
            sub.add_argument('--'+option.replace('_', '-'), type=int, default=getattr(PopulationConfig(), option))
        sub.add_argument('--metabolism', type=float, default=.12)
        sub.add_argument('--exploration', type=float, default=.18)
        sub.add_argument('--no-reproduction', action='store_true')
        sub.add_argument('--no-observation', action='store_true')
        sub.add_argument('--no-learning', action='store_true')
        if name == 'ui':
            sub.add_argument('--port', type=int, default=8765)
            sub.add_argument('--resume', type=Path)
        else:
            sub.add_argument('--ticks', type=int, default=10000)
            sub.add_argument('--output', type=Path, default=Path('runs') if name == 'batch' else None)
            sub.add_argument('--sample-every', type=int, default=100)
            sub.add_argument('--events', action='store_true')
            if name == 'run':
                sub.add_argument('--checkpoint', type=Path)
                sub.add_argument('--resume', type=Path)
            else:
                sub.add_argument('--seeds', default='1,2,3,4,5')
    bench = modes.add_parser('benchmark')
    bench.add_argument('--populations', default='10,50,100')
    bench.add_argument('--ticks', type=int, default=200)
    return root


def main(argv=None):
    cli = parser()
    args = cli.parse_args(argv)
    try:
        if args.mode == 'benchmark':
            print(json.dumps(benchmark(tuple(map(int, args.populations.split(','))), args.ticks), indent=2))
            return
        names = ('seed', 'width', 'height', 'population', 'objects', 'stones', 'sensor_range',
                 'renewal', 'population_limit', 'memory_capacity', 'metabolism', 'exploration')
        config = PopulationConfig(**{name: getattr(args, name) for name in names},
            reproduction=not args.no_reproduction, observe=not args.no_observation, learning=not args.no_learning)
        if args.mode == 'ui':
            host = '127.0.0.1'
            registry = default_registry(config, args.resume)
            print(f'Gaea: http://{host}:{args.port} — escolha um experimento', flush=True)
            experiment = select_experiment(registry, host=host, port=args.port)
            simulation = experiment.simulation_factory()
            print(f'Gaea — {experiment.name}: http://{host}:{args.port} — inicia pausado', flush=True)
            experiment.interface_factory(simulation, host=host, port=args.port)
        elif args.mode == 'run':
            print(json.dumps(run_experiment(config, args.ticks, args.output, args.sample_every,
                args.events, args.checkpoint, args.resume), indent=2))
        else:
            seeds = list(dict.fromkeys(map(int, args.seeds.split(','))))
            for seed in seeds:
                result = run_experiment(replace(config, seed=seed), args.ticks,
                    args.output / f'seed-{seed}.jsonl', args.sample_every, args.events)
                print(json.dumps(result), flush=True)
    except (ValueError, OSError) as exc:
        cli.error(str(exc))


if __name__ == '__main__':
    main()
