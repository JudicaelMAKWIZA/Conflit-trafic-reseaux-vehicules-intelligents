from unittest.mock import Mock

from traffic_conflict.config import load_config
from traffic_conflict.control.action_controller import ActionController
from traffic_conflict.domain.enums import ActionType
from traffic_conflict.domain.models import VehicleAction, VehicleState


def test_controller_cancels_pending_stop_without_invalid_resume():
    conn = Mock()
    conn.vehicle.getStopState.return_value = 0
    controller = ActionController(conn, load_config("S1"))
    state = VehicleState("a", 0, 0, 0, 2, "N_in_0", "N_in", "r_N_LEFT", lane_position=100, distance_to_junction=40)
    assert controller.apply([VehicleAction("a", ActionType.STOP)], {"a": state})[0]["error"] is None
    controller.apply([VehicleAction("a", ActionType.RESUME)], {"a": state})
    conn.vehicle.resume.assert_not_called()
    assert conn.vehicle.setStop.call_args.kwargs["duration"] == 0


def test_controller_resumes_reached_stop():
    conn = Mock()
    conn.vehicle.getStopState.return_value = 1
    controller = ActionController(conn, load_config("S1"))
    controller.held["a"] = ("N_in", 130)
    state = VehicleState("a", 0, 0, 0, 0, "N_in_0", "N_in", "r_N_LEFT")
    assert controller.apply([VehicleAction("a", ActionType.RESUME)], {"a": state})[0]["applied_action"] == "RESUME"
    conn.vehicle.resume.assert_called_once_with("a")
