from dataclasses import replace

from traffic_conflict.communication.v2v_bus import V2VBus, communicated_states
from traffic_conflict.domain.models import VehicleState


def test_perfect_bus_delivers_each_other_vehicle_once_and_no_stale_state():
    a = VehicleState("a", 1, 0, 0, 5, "N_in_0", "N_in", "r_N_STRAIGHT")
    b = replace(a, vehicle_id="b", approach="E")
    states = {"a": a, "b": b}
    bus = V2VBus()
    views = bus.broadcast(states)
    assert set(views["a"]) == {"b"}
    assert views["a"]["b"].state == b
    assert views["a"]["b"].state is not b
    assert bus.last_delivery_count == 2
    assert communicated_states(states, views) == states
    assert bus.broadcast({"a": a}) == {"a": {}}
    assert bus.last_delivery_count == 0


def test_empty_bus():
    assert V2VBus().broadcast({}) == {}
