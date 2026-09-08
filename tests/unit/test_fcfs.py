from dataclasses import replace

from traffic_conflict.communication.v2v_bus import V2VBus
from traffic_conflict.config import load_config
from traffic_conflict.domain.enums import ActionType
from traffic_conflict.domain.models import TrafficSnapshot, VehicleState
from traffic_conflict.resolution.fcfs import FCFSResolver


def test_fcfs_tie_break_and_keeps_reservation_until_rear_clears():
    a = VehicleState("a", 0, 0, 0, 0, "N_in_0", "N_in", "r_N_LEFT", approach="N", distance_to_junction=20, length=5)
    b = replace(a, vehicle_id="b", approach="E")
    states = {"b": b, "a": a}
    resolver = FCFSResolver(load_config("S1"))
    bus = V2VBus()
    actions = resolver.resolve(TrafficSnapshot(1, states), bus.broadcast(states), {})
    assert resolver.active == "a"
    assert next(x for x in actions if x.vehicle_id == "b").action_type == ActionType.STOP
    states["a"] = replace(a, road_id="W_out", lane_position=10)
    resolver.resolve(TrafficSnapshot(2, states), bus.broadcast(states), {})
    assert resolver.active == "a"
    states["a"] = replace(a, road_id="W_out", lane_position=14)
    resolver.resolve(TrafficSnapshot(3, states), bus.broadcast(states), {})
    assert resolver.active == "b"
