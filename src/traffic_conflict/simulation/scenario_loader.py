"""Build the shared physical intersection and seeded SUMO scenario inputs."""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import random
import subprocess
import xml.etree.ElementTree as ET

from traffic_conflict.config import ROOT, load_config, validate_config
from traffic_conflict.simulation.sumo_client import find_binary


APPROACHES = ("N", "E", "S", "W")
MOVEMENTS = ("STRAIGHT", "LEFT", "RIGHT")


def outgoing_approach(approach: str, movement: str) -> str:
    """Exit branch for right-hand traffic, viewed from the incoming branch."""
    if approach not in APPROACHES or movement not in MOVEMENTS:
        raise ValueError(f"Mouvement inconnu : {approach}/{movement}")
    offset = {"STRAIGHT": 2, "LEFT": 1, "RIGHT": -1}[movement]
    return APPROACHES[(APPROACHES.index(approach) + offset) % len(APPROACHES)]


def _write_xml(root: ET.Element, path: Path) -> None:
    ET.indent(root, space="  ")
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)


def _number(value: float) -> str:
    return format(float(value), ".9g")


def build_network(config: dict, output_dir: Path) -> Path:
    """Generate one lane per direction and branch, retaining internal links.

    The priority junction retains SUMO junction safety and collision detection.
    Every left/right/straight movement is explicit; no U-turn is permitted.
    Source XML inputs are retained beside the built network.
    """
    network = config["network"]
    arm_length = float(network["arm_length"])
    speed_limit = float(network["speed_limit"])
    lane_width = float(network["lane_width"])
    if min(arm_length, speed_limit, lane_width) <= 0:
        raise ValueError("La géométrie et la vitesse du réseau doivent être positives")
    folder = Path(output_dir).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    nodes = ET.Element("nodes")
    ET.SubElement(nodes, "node", id="J", x="0", y="0", type="priority")
    positions = {"N": (0, arm_length), "E": (arm_length, 0),
                 "S": (0, -arm_length), "W": (-arm_length, 0)}
    for approach in APPROACHES:
        x, y = positions[approach]
        ET.SubElement(nodes, "node", id=approach, x=_number(x), y=_number(y))
    edges = ET.Element("edges")
    connections = ET.Element("connections")
    for approach in APPROACHES:
        common = {"numLanes": "1", "speed": _number(speed_limit),
                  "width": _number(lane_width), "priority": "1"}
        ET.SubElement(edges, "edge", {"id": f"{approach}_in", "from": approach,
                                      "to": "J", **common})
        ET.SubElement(edges, "edge", {"id": f"{approach}_out", "from": "J",
                                      "to": approach, **common})
        for movement in MOVEMENTS:
            exit_branch = outgoing_approach(approach, movement)
            ET.SubElement(connections, "connection", {
                "from": f"{approach}_in", "to": f"{exit_branch}_out",
                "fromLane": "0", "toLane": "0",
            })
    nodes_path = folder / "nodes.nod.xml"
    edges_path = folder / "edges.edg.xml"
    connections_path = folder / "connections.con.xml"
    _write_xml(nodes, nodes_path)
    _write_xml(edges, edges_path)
    _write_xml(connections, connections_path)
    net_path = folder / "network.net.xml"
    command = [
        find_binary("netconvert"), "--node-files", str(nodes_path),
        "--edge-files", str(edges_path), "--connection-files", str(connections_path),
        "--output-file", str(net_path), "--no-turnarounds", "true",
        "--offset.disable-normalization", "true", "--no-internal-links", "false",
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    (folder / "netconvert.log").write_text(result.stdout + result.stderr, encoding="utf-8")
    if result.returncode:
        raise RuntimeError(f"netconvert a échoué : {result.stderr.strip()}")
    return net_path


def _normal_demand(config: dict, seed: int) -> list[dict]:
    demand = config["demand"]
    count = int(demand["vehicle_count"])
    start = float(demand["start"])
    headway = float(demand["headway"])
    jitter = float(demand["arrival_jitter"])
    approaches = list(demand["approaches"])
    movement = demand["movement"]
    if count < 1 or start < 0 or headway <= 0 or jitter < 0 or not approaches:
        raise ValueError("Paramètres de demande S0 invalides")
    for approach in approaches:
        outgoing_approach(approach, movement)
    rng = random.Random(seed)
    vehicles = []
    for index in range(count):
        approach = approaches[index % len(approaches)]
        depart = round(max(0.0, start + index * headway + rng.uniform(-jitter, jitter)), 6)
        if depart >= float(config["simulation"]["duration"]):
            raise ValueError("Une arrivée S0 dépasse l'horizon configuré")
        vehicles.append({"vehicle_id": f"S0_{approach}_{index:03d}",
                         "approach": approach, "movement": movement,
                         "route_id": f"r_{approach}_{movement}", "depart": depart})
    return sorted(vehicles, key=lambda item: (item["depart"], item["vehicle_id"]))


def build_scenario(scenario: str = "S0", seed: int = 1,
                   output_dir: Path | None = None, config: dict | None = None) -> Path:
    """Write reproducible scenario inputs and return the absolute .sumocfg path."""
    if scenario not in ("S0", "S1"):
        raise ValueError("Seuls S0 et S1 sont disponibles à cette phase du pilote")
    settings = deepcopy(config) if config is not None else load_config(scenario)
    validate_config(settings)
    if settings.get("scenario", scenario) != scenario:
        raise ValueError("La configuration ne correspond pas au scénario demandé")
    folder = (Path(output_dir) if output_dir is not None else
              ROOT / "scenarios" / settings["name"] / f"seed_{seed:03d}").resolve()
    if scenario == "S0":
        vehicles = _normal_demand(settings, seed)
    else:
        rng = random.Random(seed)
        demand = settings["demand"]
        vehicles = [{"vehicle_id": f"S1_{approach}_{index:03d}", "approach": approach,
                     "movement": demand["movement"], "route_id": f"r_{approach}_{demand['movement']}",
                     "depart": round(demand["start"] + rng.uniform(0, demand["arrival_jitter"]), 6)}
                    for index, approach in enumerate(demand["approaches"])]
        vehicles.sort(key=lambda item: (item["depart"], item["vehicle_id"]))
    net_path = build_network(settings, folder)
    routes = ET.Element("routes")
    vehicle_config = settings["vehicle"]
    ET.SubElement(routes, "vType", {
        "id": "pilot_vehicle", "vClass": "passenger",
        "length": _number(vehicle_config["length"]),
        "minGap": _number(vehicle_config["min_gap"]),
        "accel": _number(vehicle_config["accel"]),
        "decel": _number(vehicle_config["decel"]),
        "tau": _number(vehicle_config["tau"]),
        "sigma": _number(vehicle_config["sigma"]),
        "speedFactor": _number(vehicle_config["speed_factor"]),
        "maxSpeed": _number(settings["network"]["speed_limit"]),
    })
    for approach in APPROACHES:
        for movement in MOVEMENTS:
            exit_branch = outgoing_approach(approach, movement)
            ET.SubElement(routes, "route", id=f"r_{approach}_{movement}",
                          edges=f"{approach}_in {exit_branch}_out")
    for vehicle in vehicles:
        ET.SubElement(routes, "vehicle", id=vehicle["vehicle_id"], type="pilot_vehicle",
                      route=vehicle["route_id"], depart=_number(vehicle["depart"]),
                      departLane="0", departSpeed="0")
    route_path = folder / "routes.rou.xml"
    _write_xml(routes, route_path)
    sim = settings["simulation"]
    sumocfg = ET.Element("configuration")
    inputs = ET.SubElement(sumocfg, "input")
    ET.SubElement(inputs, "net-file", value=net_path.name)
    ET.SubElement(inputs, "route-files", value=route_path.name)
    time = ET.SubElement(sumocfg, "time")
    ET.SubElement(time, "begin", value="0")
    ET.SubElement(time, "end", value=_number(sim["duration"]))
    ET.SubElement(time, "step-length", value=_number(sim["step_length"]))
    processing = ET.SubElement(sumocfg, "processing")
    ET.SubElement(processing, "time-to-teleport", value=str(sim["time_to_teleport"]))
    ET.SubElement(processing, "collision.action", value=sim["collision_action"])
    ET.SubElement(processing, "collision.check-junctions",
                  value=str(sim["collision_check_junctions"]).lower())
    ET.SubElement(processing, "ignore-junction-blocker", value="-1")
    randomness = ET.SubElement(sumocfg, "random_number")
    ET.SubElement(randomness, "seed", value=str(seed))
    config_path = folder / "scenario.sumocfg"
    _write_xml(sumocfg, config_path)
    manifest = {"scenario": scenario, "seed": seed, "vehicle_count": len(vehicles),
                "duration": sim["duration"], "vehicles": vehicles, "config": settings}
    (folder / "demand_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return config_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Construire les entrées du scénario SUMO S0")
    parser.add_argument("--scenario", choices=["S0", "S1"], default="S0")
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--config", type=Path, help="YAML de surcharges du scénario")
    args = parser.parse_args()
    settings = load_config(args.scenario, args.config)
    print(build_scenario(args.scenario, args.seed, args.output_dir, settings))


if __name__ == "__main__":
    main()
