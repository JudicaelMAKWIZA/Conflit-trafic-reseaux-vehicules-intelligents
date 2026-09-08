"""Estimation agrégée indépendante des commandes TraCI et des stratégies."""
from collections import deque
from statistics import mean

from traffic_conflict.domain.models import TrafficSnapshot
from traffic_conflict.domain.enums import TrafficState
from traffic_conflict.detection.deadlock import DeadlockDetector
from traffic_conflict.detection.congestion import CongestionDetector
from traffic_conflict.communication.v2v_bus import communicated_states


class TrafficStateEstimator:
    def __init__(self, config):
        self.config = config
        self.flows = deque()
        self.deadlock = DeadlockDetector(config)
        self.congestion = CongestionDetector(config)

    def update(self, states, v2v_views, time, departed=(), arrived=()):
        self.flows.append((time, len(departed), len(arrived)))
        while self.flows and self.flows[0][0] <= time - self.config["detection"]["flow_window"]:
            self.flows.popleft()
        queues = {approach: 0 for approach in ("N", "E", "S", "W")}
        for state in states.values():
            if state.road_id.endswith("_in") and state.speed < self.config["detection"]["queue_speed"]:
                queues[state.approach] += 1
        snapshot = TrafficSnapshot(
            time=time, vehicles=states, mean_speed=mean([s.speed for s in states.values()]) if states else 0.0,
            stopped_count=sum(s.is_stopped for s in states.values()), queue_lengths=queues,
            mean_waiting_time=mean([s.waiting_time for s in states.values()]) if states else 0.0,
            max_waiting_time=max([s.waiting_time for s in states.values()], default=0.0),
            entries_in_window=sum(item[1] for item in self.flows),
            exits_in_window=sum(item[2] for item in self.flows))
        diagnostic = self.deadlock.update(communicated_states(states, v2v_views), time)
        congestion = self.congestion.update(snapshot)
        snapshot.diagnostics = {"deadlock": diagnostic, "congestion": congestion}
        if diagnostic["is_deadlock"]:
            snapshot.traffic_state = TrafficState.DEADLOCK
        elif congestion["is_congested"]:
            snapshot.traffic_state = TrafficState.CONGESTED
        return snapshot
