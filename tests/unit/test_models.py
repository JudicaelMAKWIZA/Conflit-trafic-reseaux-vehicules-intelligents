"""Protect observation immutability and the contracts used by logging/V2V."""

from dataclasses import FrozenInstanceError, asdict, replace
import json

import pytest

from traffic_conflict.domain import (
    ActionType,
    TrafficSnapshot,
    TrafficState,
    V2VMessage,
    VehicleAction,
    VehicleState,
)


def make_state(**changes: object) -> VehicleState:
    state = VehicleState(
        vehicle_id="north_0",
        time=12.0,
        x=100.0,
        y=150.0,
        speed=0.0,
        lane_id="N_in_0",
        road_id="N_in",
        route_id="N_straight",
        waiting_time=6.0,
        is_stopped=True,
        approach="N",
        length=5.0,
        lane_position=45.0,
        cumulative_waiting_time=8.0,
    )
    return replace(state, **changes)


def test_v2v_message_retains_immutable_observation_after_next_step() -> None:
    state = make_state()
    message = V2VMessage(state.vehicle_id, state.time, state, "STRAIGHT")
    next_state = replace(state, time=13.0, speed=2.0, waiting_time=0.0)

    assert message.state == state
    assert message.state is not state
    assert message.state.time == 12.0
    assert next_state.time == 13.0
    with pytest.raises(FrozenInstanceError):
        message.state.speed = 1.0
    with pytest.raises(FrozenInstanceError):
        message.timestamp = 13.0


def test_v2v_message_rejects_misattributed_vehicle_state() -> None:
    with pytest.raises(ValueError, match="sender_id"):
        V2VMessage("south_0", 12.0, make_state())


def test_controller_waiting_is_preserved_when_sumo_excludes_scheduled_stop() -> None:
    row = asdict(make_state(sumo_waiting_time=0.0))
    assert row["waiting_time"] == 6.0
    assert row["cumulative_waiting_time"] == 8.0
    assert row["sumo_waiting_time"] == 0.0


def test_snapshot_detaches_mutable_source_collections() -> None:
    vehicles = {"north_0": make_state()}
    queues = {"N": 1}
    diagnostics = {"cycle_found": True}
    snapshot = TrafficSnapshot(
        time=12.0, vehicles=vehicles, queue_lengths=queues,
        diagnostics=diagnostics,
    )
    vehicles.clear()
    queues["N"] = 0
    diagnostics.clear()

    assert snapshot.total_vehicles == 1
    assert snapshot.queue_lengths == {"N": 1}
    assert snapshot.diagnostics == {"cycle_found": True}
    assert TrafficSnapshot(time=13.0).vehicles == {}
    assert TrafficSnapshot(time=13.0).queue_lengths == {}


def test_commands_and_traffic_states_export_as_stable_json_labels() -> None:
    action = VehicleAction(
        "north_0", ActionType.SLOW_DOWN, duration=2.0,
        target_speed=1.0, reason="congestion regulation",
    )
    exported = json.loads(json.dumps(asdict(action)))
    assert exported["action_type"] == "SLOW_DOWN"
    assert exported["target_speed"] == 1.0
    snapshot = TrafficSnapshot(time=12.0, traffic_state=TrafficState.DEADLOCK)
    assert json.loads(json.dumps(asdict(snapshot)))["traffic_state"] == "DEADLOCK"
    with pytest.raises(FrozenInstanceError):
        action.target_speed = 9.0
