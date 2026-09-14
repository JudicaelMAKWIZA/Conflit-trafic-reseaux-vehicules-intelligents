"""Lancer une expérience locale reproductible."""
import argparse
import json
from pathlib import Path

from traffic_conflict.config import ROOT, load_config
from traffic_conflict.simulation.runner import run_experiment


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=["S0", "S1", "S2"], default="S0")
    parser.add_argument("--method", choices=["observe", "naive", "fcfs", "cooperative"], default="fcfs")
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--gui", action="store_true")
    parser.add_argument(
        "--gui-delay",
        type=int,
        default=0,
        help="Délai graphique SUMO en millisecondes entre deux pas de simulation"
    )
    parser.add_argument("--overwrite", action="store_true", help="Remplacer explicitement un run existant")
    args = parser.parse_args()
    config = load_config(args.scenario, args.config)
    output = args.output_dir or ROOT / "outputs/runs" / f"{args.scenario}_{config['name']}" / args.method / f"seed_{args.seed:03d}"
    if (output / "summary.json").exists() and not args.overwrite:
        parser.error("Ce run existe. Choisir --output-dir ou ajouter --overwrite.")
    result = run_experiment(
        args.scenario,
        args.method,
        args.seed,
        args.output_dir,
        config,
        gui=args.gui,
        gui_delay=args.gui_delay
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
