"""Seul module autorisé à transformer les décisions en commandes véhicule."""
import traci

from traffic_conflict.domain.enums import ActionType


class ActionController:
    def __init__(self, connection, config):
        self.connection = connection
        self.config = config
        self.held = {}
        self.configured = set()

    def apply(self, actions, states):
        conn = self.connection
        for vid in sorted(set(states) - self.configured):
            conn.vehicle.setSpeedMode(vid, self.config["vehicle"]["speed_mode"])
            self.configured.add(vid)
        results = []
        for action in actions:
            result = {"vehicle_id": action.vehicle_id, "requested_action": action.action_type.value,
                      "applied_action": "KEEP", "reason": action.reason, "error": None}
            try:
                state = states[action.vehicle_id]
                vid = action.vehicle_id
                if action.action_type == ActionType.STOP and vid not in self.held:
                    position = state.lane_position + state.distance_to_junction - self.config["control"]["stop_margin"]
                    conn.vehicle.setStop(vid, state.road_id, pos=position, laneIndex=0,
                                         duration=action.duration or self.config["control"]["stop_duration"])
                    self.held[vid] = (state.road_id, position)
                    result["applied_action"] = "STOP"
                elif action.action_type == ActionType.RESUME and vid in self.held:
                    edge, position = self.held[vid]
                    if conn.vehicle.getStopState(vid) & 1:
                        conn.vehicle.resume(vid)
                    else:
                        conn.vehicle.setStop(vid, edge, pos=position, laneIndex=0, duration=0)
                    del self.held[vid]
                    result["applied_action"] = "RESUME"
                elif action.action_type == ActionType.SLOW_DOWN:
                    conn.vehicle.slowDown(vid, action.target_speed, action.duration)
                    result["applied_action"] = "SLOW_DOWN"
            except (traci.TraCIException, KeyError, TypeError) as exc:
                result["error"] = str(exc)
            results.append(result)
        return results
