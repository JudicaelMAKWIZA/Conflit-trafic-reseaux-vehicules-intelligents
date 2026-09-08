"""Métriques calculées uniquement à partir des traces d'une simulation réelle."""
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd
import yaml


def finite_stat(values, statistic):
    return float(statistic(values)) if len(values) else None


def summarize_approach_fairness(manifest_vehicles, last_states, completed_ids):
    """Conserver chaque approche demandée, y compris les véhicules non insérés.

    L'attente des trajets inachevés est une observation censurée, séparée de
    l'attente des trajets terminés. Un véhicule jamais observé n'a pas une
    attente nulle. L'écart-type principal n'est interprétable qu'une fois toute
    la demande terminée ; sa variante ``observed`` porte sur les seuls terminés.
    """
    expected = {}
    for vehicle in manifest_vehicles:
        expected.setdefault(str(vehicle["approach"]), set()).add(vehicle["vehicle_id"])
    observed_ids = set(last_states.vehicle_id)
    completed_ids = set(completed_ids)
    summary = {key: {} for key in (
        "expected_by_approach", "departed_by_approach", "completed_by_approach",
        "unfinished_by_approach", "waiting_by_approach_s",
        "unfinished_observed_waiting_by_approach_s")}
    for approach, expected_ids in sorted(expected.items()):
        completed = expected_ids & completed_ids
        unfinished = expected_ids - completed_ids
        finished_wait = last_states.loc[last_states.vehicle_id.isin(completed), "cumulative_waiting_time"]
        censored_wait = last_states.loc[last_states.vehicle_id.isin(unfinished), "cumulative_waiting_time"]
        summary["expected_by_approach"][approach] = len(expected_ids)
        summary["departed_by_approach"][approach] = len(expected_ids & (observed_ids | completed_ids))
        summary["completed_by_approach"][approach] = len(completed)
        summary["unfinished_by_approach"][approach] = len(unfinished)
        summary["waiting_by_approach_s"][approach] = finite_stat(finished_wait.to_numpy(), np.mean)
        summary["unfinished_observed_waiting_by_approach_s"][approach] = finite_stat(censored_wait.to_numpy(), np.mean)
    all_means = list(summary["waiting_by_approach_s"].values())
    observed_means = np.array([value for value in all_means if value is not None])
    complete = all(count == 0 for count in summary["unfinished_by_approach"].values())
    observed_std = finite_stat(observed_means, np.std)
    summary["fairness_complete"] = complete
    summary["fairness_observed_std_wait_s"] = observed_std
    summary["fairness_std_wait_s"] = observed_std if complete and len(observed_means) == len(all_means) else None
    return summary


def compute_metrics(output_dir):
    root = Path(output_dir)
    config = yaml.safe_load((root / "config.yaml").read_text(encoding="utf-8"))
    metadata = json.loads((root / "metadata.json").read_text(encoding="utf-8"))
    manifest = json.loads((root / "scenario/demand_manifest.json").read_text(encoding="utf-8"))
    states = pd.read_csv(root / "trajectories.csv")
    steps = pd.read_csv(root / "steps.csv")
    events = [json.loads(line) for line in (root / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    trips = [trip.attrib for trip in ET.parse(root / "tripinfo.xml").getroot().findall("tripinfo")]
    completed = [trip for trip in trips if float(trip["arrival"]) >= 0]
    completed_ids = {trip["id"] for trip in completed}
    last = states.sort_values("time").groupby("vehicle_id").tail(1)
    complete_states = last[last.vehicle_id.isin(completed_ids)]
    unfinished_states = last[~last.vehicle_id.isin(completed_ids)]
    wait = complete_states.cumulative_waiting_time.to_numpy()
    duration, dt = config["simulation"]["duration"], config["simulation"]["step_length"]
    detected = steps.state == "DEADLOCK"
    detections = [e for e in events if e["type"] == "detection" and e.get("deadlock", {}).get("is_deadlock")]
    first = detections[0] if detections else None
    recovery_time, clearance_time = None, None
    if first:
        clearance = []
        for vid in first["deadlock"]["vehicles"]:
            observations = states[(states.vehicle_id == vid) & (states.time >= first["time"])]
            cleared = observations[observations.road_id.str.endswith("_out") &
                                   (observations.lane_position >= observations.length + config["control"]["clearance_distance"])]
            if len(cleared):
                clearance.append(float(cleared.time.min()))
        if len(clearance) == len(first["deadlock"]["vehicles"]):
            clearance_time = max(clearance)
            recovery_time = clearance_time - first["time"]
    collisions = sum(e["type"] == "collision" for e in events)
    teleports = sum(e["type"] == "teleport_start" for e in events)
    actions = [e for e in events if e["type"] == "action"]
    errors = sum(bool(e["error"]) for e in actions)
    valid = collisions == teleports == errors == 0
    fairness = summarize_approach_fairness(manifest["vehicles"], last, completed_ids)
    queues = steps[["queue_N", "queue_E", "queue_S", "queue_W"]].to_numpy()
    congested = steps.loc[steps.state == "CONGESTED", "time"]
    normal_times = set(steps.loc[steps.state == "NORMAL", "time"])
    results = {**metadata,
        "duration_s": duration, "expected_trip_count": manifest["vehicle_count"],
        "departed_count": len(last), "completed_trip_count": len(completed),
        "unfinished_trip_count": manifest["vehicle_count"] - len(completed),
        "completion_rate": len(completed) / manifest["vehicle_count"],
        "valid_run": valid,
        "resolution_success": bool(valid and len(completed) == manifest["vehicle_count"]),
        "deadlock_detected": bool(first), "deadlock_event_count": int((detected & ~detected.shift(fill_value=False)).sum()),
        "false_deadlock_count": int((detected & ~detected.shift(fill_value=False)).sum()) if metadata["scenario"] == "S0" else None,
        "deadlock_onset_s": first["deadlock"]["onset_time"] if first else None,
        "first_deadlock_detection_s": first["time"] if first else None,
        "detection_latency_s": first["time"] - first["deadlock"]["onset_time"] if first else None,
        "recovery_time_s": recovery_time, "clearance_time_s": clearance_time,
        "recovery_censored": bool(first and recovery_time is None),
        "recovery_observation_limit_s": duration - first["time"] if first else None,
        "congestion_detection_time_s": float(congested.min()) if len(congested) else None,
        "time_in_congestion_s": len(congested) * dt,
        "time_in_deadlock_s": int(detected.sum()) * dt,
        "throughput_veh_per_hour": len(completed) * 3600 / duration,
        "mean_waiting_time_s": finite_stat(wait, np.mean),
        "p95_waiting_time_s": finite_stat(wait, lambda a: np.percentile(a, 95)),
        "max_waiting_time_s": float(last.cumulative_waiting_time.max()) if len(last) else None,
        "unfinished_mean_waiting_time_s": finite_stat(unfinished_states.cumulative_waiting_time.to_numpy(), np.mean),
        "mean_speed_mps": float(states.speed.mean()) if len(states) else None,
        "mean_queue_length_veh": float(queues.mean()), "max_queue_length_veh": int(queues.max()),
        "travel_time_s": finite_stat(np.array([float(t["duration"]) for t in completed]), np.mean),
        "depart_delay_mean_s": finite_stat(np.array([float(t["departDelay"]) for t in completed]), np.mean),
        **fairness,
        "collision_count": collisions, "teleport_count": teleports, "controller_error_count": errors,
        "action_count": sum(e["applied_action"] != "KEEP" and not e["error"] for e in actions),
        "stop_count": sum(e["applied_action"] == "STOP" for e in actions),
        "resume_count": sum(e["applied_action"] == "RESUME" for e in actions),
        "unnecessary_stop_count": None,
        "stops_while_normal_count": sum(e["applied_action"] == "STOP" and e["time"] in normal_times for e in actions),
        "output_dir": str(root)}
    # NORMAL n'implique pas qu'un STOP de prévention soit inutile : aucun oracle V0.
    (root / "summary.json").write_text(json.dumps(results, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    flat = {k: json.dumps(v, sort_keys=True) if isinstance(v, dict) else v for k, v in results.items()}
    pd.DataFrame([flat]).to_csv(root / "summary.csv", index=False)
    return results
