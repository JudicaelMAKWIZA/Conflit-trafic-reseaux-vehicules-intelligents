"""Boucle fermée générique ; aucune règle de résolution spécifique ici."""
from __future__ import annotations

import csv
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess

import yaml

from traffic_conflict.communication.v2v_bus import V2VBus
from traffic_conflict.config import ROOT, load_config
from traffic_conflict.detection.traffic_state import TrafficStateEstimator
from traffic_conflict.control.action_controller import ActionController
from traffic_conflict.resolution.registry import make_resolver
from traffic_conflict.simulation.scenario_loader import build_scenario
from traffic_conflict.simulation.state_collector import StateCollector
from traffic_conflict.simulation.sumo_client import SumoClient, tool_versions


def git_revision():
    try:
        return subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        # Windows Git may be available through interoperability when Linux Git is absent.
        try:
            return subprocess.check_output(["git.exe", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        except (OSError, subprocess.CalledProcessError):
            return None


def run_experiment(scenario="S0", method="observe", seed=1, output_dir=None,
                   config=None, resolver=None, controller_class=None, gui=False):
    config = config or load_config(scenario)
    resolver = resolver or make_resolver(method, config)
    controller_class = controller_class or (ActionController if resolver else None)
    output = Path(output_dir or ROOT / "outputs/runs" / f"{scenario}_{config['name']}" / method / f"seed_{seed:03d}").resolve()
    output.mkdir(parents=True, exist_ok=True)
    sumocfg = build_scenario(scenario, seed, output / "scenario", config)
    (output / "config.yaml").write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8")
    metadata = {"scenario": scenario, "method": method, "seed": seed, "git_commit": git_revision(),
                "created_utc": datetime.now(timezone.utc).isoformat(), **tool_versions()}
    (output / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    bus, estimator = V2VBus(), TrafficStateEstimator(config)
    completed, departed_ids = set(), set()
    collisions, teleports, controller_errors = 0, 0, 0
    trajectory_fields = ["time", "vehicle_id", "x", "y", "speed", "lane_id", "road_id", "route_id",
                         "waiting_time", "cumulative_waiting_time", "sumo_waiting_time", "heading",
                         "distance_to_junction", "is_stopped", "approach", "movement", "length", "lane_position",
                         "detected_state", "action", "method", "scenario", "seed"]
    step_fields = ["time", "active", "mean_speed", "stopped", "queue_N", "queue_E", "queue_S", "queue_W",
                   "mean_wait", "max_wait", "state", "departed", "arrived", "completed", "v2v_deliveries"]
    with (output / "trajectories.csv").open("w", newline="", encoding="utf-8") as tf, \
         (output / "steps.csv").open("w", newline="", encoding="utf-8") as sf, \
         (output / "events.jsonl").open("w", encoding="utf-8") as ef, \
         SumoClient(sumocfg, seed, output, gui) as conn:
        trajectory_writer = csv.DictWriter(tf, fieldnames=trajectory_fields)
        step_writer = csv.DictWriter(sf, fieldnames=step_fields)
        trajectory_writer.writeheader()
        step_writer.writeheader()
        collector = StateCollector(conn, config)
        controller = controller_class(conn, config) if controller_class else None
        context = {"config": config}
        while conn.simulation.getTime() < config["simulation"]["duration"]:
            conn.simulationStep()
            time = conn.simulation.getTime()
            departed, arrived = conn.simulation.getDepartedIDList(), conn.simulation.getArrivedIDList()
            departed_ids.update(departed)
            completed.update(arrived)
            states = collector.collect()
            views = bus.broadcast(states)
            snapshot = estimator.update(states, views, time, departed, arrived)
            requested = resolver.resolve(snapshot, views, context) if resolver else []
            applied = controller.apply(requested, states) if controller else []
            action_by_id = {item["vehicle_id"]: item["applied_action"] for item in applied}
            controller_errors += sum(bool(item["error"]) for item in applied)
            for item in applied:
                ef.write(json.dumps({"time": time, "type": "action", **item}) + "\n")
            for collision in conn.simulation.getCollisions():
                collisions += 1
                ef.write(json.dumps({"time": time, "type": "collision", "detail": str(collision)}) + "\n")
            for kind, vehicles in (("teleport_start", conn.simulation.getStartingTeleportIDList()),
                                   ("teleport_end", conn.simulation.getEndingTeleportIDList())):
                for vid in vehicles:
                    teleports += int(kind == "teleport_start")
                    ef.write(json.dumps({"time": time, "type": kind, "vehicle_id": vid}) + "\n")
            if snapshot.diagnostics:
                ef.write(json.dumps({"time": time, "type": "detection", **snapshot.diagnostics}) + "\n")
            for state in states.values():
                row = asdict(state)
                row.update(detected_state=snapshot.traffic_state.value, action=action_by_id.get(state.vehicle_id, "KEEP"),
                           method=method, scenario=scenario, seed=seed)
                trajectory_writer.writerow(row)
            step_writer.writerow({"time": time, "active": len(states), "mean_speed": snapshot.mean_speed,
                                   "stopped": snapshot.stopped_count, **{f"queue_{k}": v for k, v in snapshot.queue_lengths.items()},
                                   "mean_wait": snapshot.mean_waiting_time, "max_wait": snapshot.max_waiting_time,
                                   "state": snapshot.traffic_state.value, "departed": len(departed), "arrived": len(arrived),
                                   "completed": len(completed), "v2v_deliveries": bus.last_delivery_count})
    summary = {**metadata, "duration_s": config["simulation"]["duration"], "departed_count": len(departed_ids),
               "completed_trip_count": len(completed), "collision_count": collisions, "teleport_count": teleports,
               "controller_error_count": controller_errors, "output_dir": str(output)}
    (output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary
