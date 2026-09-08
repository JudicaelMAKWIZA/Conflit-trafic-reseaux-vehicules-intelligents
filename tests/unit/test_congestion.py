from dataclasses import replace

import pytest

from traffic_conflict.config import load_config
from traffic_conflict.detection.congestion import CongestionDetector
from traffic_conflict.domain.models import TrafficSnapshot, VehicleState


def observations(time, count=4, approach="N", speed=0.0, wait=0.0):
    return {
        f"{approach}{index}": VehicleState(
            f"{approach}{index}", time, 0, 0, speed,
            f"{approach}_in_0", f"{approach}_in", f"r_{approach}_STRAIGHT",
            waiting_time=wait, approach=approach, is_stopped=speed < 0.1,
        )
        for index in range(count)
    }


def sample(time, **kwargs):
    return TrafficSnapshot(time, vehicles=observations(time, **kwargs))


def test_slow_queue_requires_continuous_simulated_time_and_includes_threshold():
    detector = CongestionDetector(load_config("S2"))
    assert not detector.update(sample(0))["is_congested"]
    assert not detector.update(sample(7.9))["is_congested"]
    result = detector.update(sample(8))
    assert result["is_congested"]
    assert result["approaches"] == ["N"]
    assert result["diagnostics"]["N"]["persistence_s"] == 8
    assert result["diagnostics"]["N"]["queue_length_veh"] == 4


def test_recovery_resets_persistence_instead_of_accumulating_short_queues():
    detector = CongestionDetector(load_config("S2"))
    detector.update(sample(0))
    assert not detector.update(sample(7))["is_congested"]
    assert not detector.update(sample(8, speed=5))["is_congested"]
    assert not detector.update(sample(9))["is_congested"]
    assert not detector.update(sample(16.9))["is_congested"]
    assert detector.update(sample(17))["is_congested"]
    assert not detector.update(TrafficSnapshot(18))["is_congested"]
    assert not detector.update(sample(19))["is_congested"]


def test_speed_is_strict_and_queue_threshold_is_configurable():
    config = load_config("S2")
    config["detection"].update(queue_speed=3, congestion_queue=5, congestion_persistence=2)
    detector = CongestionDetector(config)
    detector.update(sample(0, count=5, speed=2))
    assert not detector.update(sample(10, count=5, speed=2))["is_congested"]
    detector.update(sample(11, count=4, speed=1))
    assert not detector.update(sample(20, count=4, speed=1))["is_congested"]
    assert not detector.update(sample(21, count=5, speed=1))["is_congested"]
    assert detector.update(sample(23, count=5, speed=1))["is_congested"]


def test_approaches_cannot_share_persistence_and_global_speed_does_not_mask_queue():
    detector = CongestionDetector(load_config("S2"))
    detector.update(sample(0))
    assert not detector.update(sample(7, approach="E"))["is_congested"]
    assert not detector.update(sample(8, approach="E"))["is_congested"]
    states = {**observations(15, approach="E"), **observations(15, count=20, speed=10)}
    result = detector.update(TrafficSnapshot(15, vehicles=states))
    assert result["approaches"] == ["E"]


def test_persistent_wait_can_detect_queue_below_vehicle_count_threshold():
    detector = CongestionDetector(load_config("S2"))
    assert not detector.update(sample(0, count=1, wait=29))["is_congested"]
    assert not detector.update(sample(1, count=1, wait=30))["is_congested"]
    result = detector.update(sample(9, count=1, wait=38))
    assert result["is_congested"]
    assert result["diagnostics"]["N"]["growing_wait"]
    assert not result["diagnostics"]["N"]["slow_queue"]
    assert not detector.update(sample(10, count=1, wait=0, speed=4))["is_congested"]


def test_waiting_successor_preserves_persistence_when_leader_leaves():
    detector = CongestionDetector(load_config("S2"))

    def snapshot(time, leader=True):
        states = observations(time, count=2, wait=30 + time)
        states["N0"] = replace(states["N0"], waiting_time=50 + time)
        if not leader:
            del states["N0"]
        return TrafficSnapshot(time, vehicles=states)

    detector.update(snapshot(0))
    detector.update(snapshot(1))
    assert not detector.update(snapshot(4, leader=False))["is_congested"]
    result = detector.update(snapshot(9, leader=False))
    assert result["is_congested"]
    assert result["diagnostics"]["N"]["onset_time"] == 1
    assert result["diagnostics"]["N"]["max_waiting_time_s"] == 39


def test_large_but_nonincreasing_wait_is_not_sufficient():
    detector = CongestionDetector(load_config("S2"))
    for time in (0, 1, 9, 100):
        result = detector.update(sample(time, count=1, wait=50))
        assert not result["is_congested"]
        assert not result["diagnostics"]["N"]["waiting_increasing"]


def test_outgoing_and_internal_vehicles_do_not_create_incoming_congestion():
    detector = CongestionDetector(load_config("S2"))
    states = observations(0, count=8, wait=100)
    states = {
        vid: replace(state, road_id="N_out" if index < 4 else ":J_0")
        for index, (vid, state) in enumerate(states.items())
    }
    detector.update(TrafficSnapshot(0, vehicles=states))
    result = detector.update(TrafficSnapshot(100, vehicles=states))
    assert result == {"is_congested": False, "approaches": [], "diagnostics": {}}


def test_time_reversal_is_rejected():
    detector = CongestionDetector(load_config("S2"))
    detector.update(sample(10))
    with pytest.raises(ValueError, match="simulation time"):
        detector.update(sample(9))
