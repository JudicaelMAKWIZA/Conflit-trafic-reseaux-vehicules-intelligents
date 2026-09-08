"""Chargement YAML ; tous les seuils sont des hypothèses propres au pilote."""
from copy import deepcopy
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
SCENARIOS = {"S0": "normal", "S1": "deadlock", "S2": "congestion"}


def merge(base: dict, override: dict) -> dict:
    result = deepcopy(base)
    for key, value in override.items():
        result[key] = merge(result[key], value) if isinstance(value, dict) and isinstance(result.get(key), dict) else deepcopy(value)
    return result


def load_config(scenario: str, overrides: Path | None = None) -> dict:
    if scenario not in SCENARIOS:
        raise ValueError(f"Scénario inconnu : {scenario}")
    base = yaml.safe_load((ROOT / "configs/defaults.yaml").read_text(encoding="utf-8"))
    specific = yaml.safe_load((ROOT / f"configs/scenario_{SCENARIOS[scenario]}.yaml").read_text(encoding="utf-8"))
    config = merge(base, specific)
    if overrides:
        config = merge(config, yaml.safe_load(Path(overrides).read_text(encoding="utf-8")))
    validate_config(config)
    return config


def validate_config(config: dict) -> None:
    if config["simulation"]["step_length"] <= 0:
        raise ValueError("step_length doit être positif")
    if config["simulation"]["time_to_teleport"] != -1:
        raise ValueError("Les téléportations pour attente doivent être désactivées dans la V0")
    if config["control"]["stop_margin"] <= config["vehicle"]["length"]:
        raise ValueError("stop_margin doit laisser une marge physique avant la jonction")
    if config["control"]["zone_distance"] <= config["control"]["stop_margin"]:
        raise ValueError("La zone de contrôle doit précéder la ligne d'arrêt")
