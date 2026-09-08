from dataclasses import replace

from traffic_conflict.config import load_config
from traffic_conflict.detection.deadlock import DeadlockDetector
from traffic_conflict.domain.conflicts import COMPATIBILITY, incompatible
from traffic_conflict.domain.models import VehicleState


def pair():
    a = VehicleState("a", 0, 0, 0, 0, "N_in_0", "N_in", "r_N_LEFT", approach="N",
                     movement="LEFT", is_stopped=True, distance_to_junction=7)
    return {"a": a, "b": replace(a, vehicle_id="b", approach="E")}


def test_complete_symmetric_conflict_table():
    assert len(COMPATIBILITY) == 144
    assert all(value == COMPATIBILITY[b, a] for (a, b), value in COMPATIBILITY.items())
    states = pair()
    assert incompatible(states["a"], states["b"])
    assert not incompatible(replace(states["a"], movement="STRAIGHT"),
                            replace(states["b"], movement="STRAIGHT", approach="S"))


def test_cycle_requires_continuous_persistence_and_resets_after_progress():
    detector = DeadlockDetector(load_config("S1"))
    states = pair()
    assert not detector.update(states, 0)["is_deadlock"]
    assert not detector.update(states, 4.9)["is_deadlock"]
    result = detector.update(states, 5)
    assert result["is_deadlock"] and result["cycles"]
    assert result["wait_for_graph"] == {"a": ["b"], "b": ["a"]}
    moving = {**states, "b": replace(states["b"], speed=1, is_stopped=False)}
    assert not detector.update(moving, 6)["is_deadlock"]
    assert not detector.update(states, 7)["is_deadlock"]
    assert detector.update(states, 12)["is_deadlock"]


def test_single_queue_or_a_crossing_vehicle_is_not_deadlock():
    detector = DeadlockDetector(load_config("S1"))
    states = pair()
    same = {**states, "b": replace(states["b"], approach="N")}
    assert not detector.update(same, 0)["is_deadlock"]
    assert not detector.update(same, 100)["is_deadlock"]
    crossing = replace(states["a"], vehicle_id="c", road_id=":J_0", speed=2, is_stopped=False)
    assert not detector.update({**states, "c": crossing}, 200)["is_deadlock"]
