"""Estimation agrégée indépendante des commandes TraCI et des stratégies."""
from collections import deque
from statistics import mean

from traffic_conflict.domain.models import TrafficSnapshot


class TrafficStateEstimator:
    def __init__(self, config):
        self.config = config
        self.flows = deque()

    def update(self, states, v2v_views, time, departed=(), arrived=()):
        self.flows.append((time, len(departed), len(arrived)))
        while self.flows and self.flows[0][0] <= time - self.config["detection"]["flow_window"]:
            self.flows.popleft()
        queues = {approach: 0 for approach in ("N", "E", "S", "W")}
        for state in states.values():
            if state.road_id.endswith("_in") and state.speed < self.config["detection"]["queue_speed"]:
                queues[state.approach] += 1
        return TrafficSnapshot(
            time=time, vehicles=states, mean_speed=mean([s.speed for s in states.values()]) if states else 0.0,
            stopped_count=sum(s.is_stopped for s in states.values()), queue_lengths=queues,
            mean_waiting_time=mean([s.waiting_time for s in states.values()]) if states else 0.0,
            max_waiting_time=max([s.waiting_time for s in states.values()], default=0.0),
            entries_in_window=sum(item[1] for item in self.flows),
            exits_in_window=sum(item[2] for item in self.flows))
