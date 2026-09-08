"""Persistent congestion by incoming approach, independent of TraCI/control.

All classification thresholds are pilot hypotheses supplied by YAML. A queue
must remain slow and sufficiently long, or its maximum waiting time must stay
above the configured threshold while increasing, for the configured duration.
"""
from collections import defaultdict
from statistics import mean

from traffic_conflict.domain.models import TrafficSnapshot


class CongestionDetector:
    def __init__(self, config: dict):
        self.config = config
        self.since: dict[str, float] = {}
        self.previous_waits: dict[str, dict[str, float]] = {}
        self.previous_time: float | None = None

    def update(self, snapshot: TrafficSnapshot) -> dict:
        if self.previous_time is not None and snapshot.time < self.previous_time:
            raise ValueError("Congestion observations must have increasing simulation time")

        thresholds = self.config["detection"]
        incoming = defaultdict(list)
        for state in snapshot.vehicles.values():
            if state.road_id.endswith("_in"):
                incoming[state.approach].append(state)

        diagnostics = {}
        detected = []
        next_waits = {}
        for approach, states in sorted(incoming.items()):
            speed = mean(state.speed for state in states)
            queue = sum(state.speed < thresholds["queue_speed"] for state in states)
            max_wait = max(state.waiting_time for state in states)
            previous = self.previous_waits.get(approach, {})
            # Compare the current maximum-wait vehicle to its own prior wait.
            # A departing leader can lower the aggregate maximum even though
            # its successor is still waiting longer; that is not recovery.
            waiting_increasing = any(
                state.waiting_time == max_wait
                and state.vehicle_id in previous
                and state.waiting_time > previous[state.vehicle_id]
                for state in states
            )
            slow_queue = (
                speed < thresholds["congestion_speed"]
                and queue >= thresholds["congestion_queue"]
            )
            growing_wait = max_wait >= thresholds["congestion_wait"] and waiting_increasing
            candidate = slow_queue or growing_wait
            if candidate:
                self.since.setdefault(approach, snapshot.time)
            else:
                self.since.pop(approach, None)
            onset = self.since.get(approach)
            duration = snapshot.time - onset if onset is not None else 0.0
            congested = candidate and duration + 1e-9 >= thresholds["congestion_persistence"]
            if congested:
                detected.append(approach)
            diagnostics[approach] = {
                "mean_speed_mps": speed,
                "queue_length_veh": queue,
                "max_waiting_time_s": max_wait,
                "waiting_increasing": waiting_increasing,
                "slow_queue": slow_queue,
                "growing_wait": growing_wait,
                "candidate": candidate,
                "onset_time": onset,
                "persistence_s": duration,
                "is_congested": congested,
            }
            next_waits[approach] = {state.vehicle_id: state.waiting_time for state in states}

        # Empty/disappeared approaches have recovered and must start a new
        # persistence interval if traffic later returns.
        self.since = {approach: onset for approach, onset in self.since.items() if approach in incoming}
        self.previous_waits = next_waits
        self.previous_time = snapshot.time
        return {"is_congested": bool(detected), "approaches": detected, "diagnostics": diagnostics}
