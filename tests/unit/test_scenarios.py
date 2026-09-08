"""Validate demand and movement contracts without starting a simulator."""
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest

from traffic_conflict.config import load_config
from traffic_conflict.simulation import scenario_loader


@pytest.fixture
def stub_network(monkeypatch):
    def build(config: dict, output_dir: Path) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        net_path = output_dir / "network.net.xml"
        net_path.write_text("<net/>", encoding="utf-8")
        return net_path
    monkeypatch.setattr(scenario_loader, "build_network", build)


@pytest.mark.parametrize("approach, expected", [
    ("N", ("S", "E", "W")), ("E", ("W", "S", "N")),
    ("S", ("N", "W", "E")), ("W", ("E", "N", "S")),
])
def test_routes_respect_right_hand_traffic_without_uturns(approach, expected):
    destinations = tuple(scenario_loader.outgoing_approach(approach, movement)
                         for movement in ("STRAIGHT", "LEFT", "RIGHT"))
    assert destinations == expected
    assert approach not in destinations


def test_seeded_routes_match_manifest_and_are_reproducible(tmp_path, stub_network):
    first = scenario_loader.build_scenario(seed=3, output_dir=tmp_path / "first")
    second = scenario_loader.build_scenario(seed=3, output_dir=tmp_path / "second")
    other = scenario_loader.build_scenario(seed=4, output_dir=tmp_path / "other")
    first_routes = (first.parent / "routes.rou.xml").read_bytes()
    assert first_routes == (second.parent / "routes.rou.xml").read_bytes()
    assert first_routes != (other.parent / "routes.rou.xml").read_bytes()
    manifest = json.loads((first.parent / "demand_manifest.json").read_text())
    vehicle_xml = ET.fromstring(first_routes).findall("vehicle")
    assert len(vehicle_xml) == manifest["vehicle_count"] == 12
    assert {v["approach"] for v in manifest["vehicles"]} == {"N", "E", "S", "W"}
    assert [float(v.attrib["depart"]) for v in vehicle_xml] == sorted(
        v["depart"] for v in manifest["vehicles"]
    )
    assert {v.attrib["id"] for v in vehicle_xml} == {
        v["vehicle_id"] for v in manifest["vehicles"]
    }
    cfg = ET.parse(first)
    assert cfg.find("processing/time-to-teleport").attrib["value"] == "-1"
    assert cfg.find("processing/collision.action").attrib["value"] == "warn"
    assert cfg.find("processing/collision.check-junctions").attrib["value"] == "true"


def test_build_does_not_mutate_configuration(tmp_path, stub_network):
    config = load_config("S0")
    before = json.dumps(config, sort_keys=True)
    scenario_loader.build_scenario(config=config, output_dir=tmp_path)
    assert json.dumps(config, sort_keys=True) == before


def test_demand_past_horizon_is_rejected(tmp_path, stub_network):
    config = load_config("S0")
    config["simulation"]["duration"] = 5.0
    with pytest.raises(ValueError, match="horizon"):
        scenario_loader.build_scenario(config=config, output_dir=tmp_path)


@pytest.mark.parametrize("scenario", ["S99"])
def test_unimplemented_scenarios_are_rejected(scenario, tmp_path):
    with pytest.raises(ValueError, match="disponibles"):
        scenario_loader.build_scenario(scenario, output_dir=tmp_path)
