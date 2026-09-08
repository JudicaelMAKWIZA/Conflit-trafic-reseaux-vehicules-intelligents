from dataclasses import replace

from traffic_conflict.config import load_config
from traffic_conflict.domain.models import VehicleState
from traffic_conflict.domain.models import TrafficSnapshot
from traffic_conflict.communication.v2v_bus import V2VBus
from traffic_conflict.resolution.cooperative import CooperativeV2VResolver


def test_recovery_priority_wait_then_distance_then_id():
    resolver = CooperativeV2VResolver(load_config("S1"))
    a = VehicleState("a", 0, 0, 0, 0, "N_in_0", "N_in", "r_N_LEFT", length=5,
                     cumulative_waiting_time=10, distance_to_junction=20)
    older = replace(a, vehicle_id="z", cumulative_waiting_time=11, distance_to_junction=40)
    cheaper = replace(a, vehicle_id="z", distance_to_junction=10)
    tied = replace(a, vehicle_id="b")
    assert min([a, older], key=resolver.recovery_score) is older
    assert min([a, cheaper], key=resolver.recovery_score) is cheaper
    assert min([a, tied], key=resolver.recovery_score) is a


def test_pressure_does_not_revoke_a_committed_crossing_on_phase_expiry():
    resolver = CooperativeV2VResolver(load_config("S2"))
    a = VehicleState("a", 0, 0, 0, 0, "N_in_0", "N_in", "r_N_STRAIGHT", length=5,
                     approach="N", distance_to_junction=7)
    b = replace(a, vehicle_id="b", approach="E")
    states = {"a": a, "b": b}
    bus = V2VBus()
    resolver.resolve(TrafficSnapshot(0, states), bus.broadcast(states), {})
    assert resolver.granted == {"b"}
    states["b"] = replace(b, road_id=":J_0", speed=5)
    resolver.resolve(TrafficSnapshot(20, states), bus.broadcast(states), {})
    assert resolver.granted == {"b"} and resolver.phase_approach == "E"
    states["b"] = replace(b, road_id="W_out", lane_position=14)
    resolver.resolve(TrafficSnapshot(21, states), bus.broadcast(states), {})
    assert resolver.granted == {"a"} and resolver.phase_approach == "N"
