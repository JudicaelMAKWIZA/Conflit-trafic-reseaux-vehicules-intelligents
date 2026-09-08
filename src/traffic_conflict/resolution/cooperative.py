"""Coordination déterministe V2V : récupération de cycles d'attente."""
from traffic_conflict.resolution.base import in_control_zone, cleared
from traffic_conflict.resolution.fcfs import FCFSResolver
from traffic_conflict.resolution.naive_yield import NaiveYield


class CooperativeV2VResolver(FCFSResolver):
    def __init__(self, config):
        super().__init__(config)
        self.initial = NaiveYield(config)
        self.recovery_started = False
        self.next_review = 0.0

    def recovery_score(self, state):
        # Le cumul d'attente fournit l'aging; la distance restante approxime le coût.
        cost = (max(state.distance_to_junction, 0.0) + state.length) / self.config["network"]["speed_limit"]
        return (-state.cumulative_waiting_time, cost, state.vehicle_id)

    def resolve(self, snapshot, v2v_views, context):
        if self.config["control"]["initial_policy"] != "naive_until_deadlock":
            return super().resolve(snapshot, v2v_views, context)
        if not self.recovery_started:
            if not snapshot.diagnostics.get("deadlock", {}).get("is_deadlock"):
                return self.initial.resolve(snapshot, v2v_views, context)
            self.recovery_started = True
            self.last_intent = self.initial.last_intent.copy()
        states = self.vehicles(snapshot, v2v_views)
        candidates = {vid: state for vid, state in states.items() if in_control_zone(state, self.config)}
        if self.active and cleared(states.get(self.active), self.config):
            self.active = None
        if self.active is None and candidates and snapshot.time >= self.next_review:
            winner = min(candidates.values(), key=self.recovery_score)
            self.active = winner.vehicle_id
            self.next_review = snapshot.time + self.config["control"]["release_window"]
            context["decision"] = {"mode": "deadlock_recovery", "selected": self.active,
                                   "scores": {vid: list(self.recovery_score(state)) for vid, state in candidates.items()}}
        return self.commands(states, {self.active}, "cooperative_recovery_wait_then_cost_then_id")
