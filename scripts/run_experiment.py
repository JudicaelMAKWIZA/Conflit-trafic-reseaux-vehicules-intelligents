"""Lancer une expérience locale reproductible."""
import argparse
import json
from pathlib import Path

from traffic_conflict.config import load_config
from traffic_conflict.simulation.runner import run_experiment


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=["S0", "S1", "S2"], default="S0")
    parser.add_argument("--method", default="observe")
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--gui", action="store_true")
    args = parser.parse_args()
    result = run_experiment(args.scenario, args.method, args.seed, args.output_dir,
                            load_config(args.scenario, args.config), gui=args.gui)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
