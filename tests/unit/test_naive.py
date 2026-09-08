from dataclasses import replace

from traffic_conflict.communication.v2v_bus import V2VBus
from traffic_conflict.config import load_config
from traffic_conflict.domain.enums import ActionType
from traffic_conflict.domain.models import TrafficSnapshot, VehicleState
from traffic_conflict.resolution.naive_yield import NaiveYield


def test_naive_yields_mutually_and_avoids_duplicate_commands():
    a = VehicleState("a", 1, 0, 0, 0, "N_in_0", "N_in", "r_N_LEFT", approach="N", distance_to_junction=20)
    b = replace(a, vehicle_id="b", approach="E")
    states = {"a": a, "b": b}
    resolver = NaiveYield(load_config("S1"))
    snapshot = TrafficSnapshot(1, states)
    views = V2VBus().broadcast(states)
    assert [a.action_type for a in resolver.resolve(snapshot, views, {})] == [ActionType.STOP, ActionType.STOP]
    assert resolver.resolve(snapshot, views, {}) == []
