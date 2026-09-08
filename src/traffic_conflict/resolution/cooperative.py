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
        self.granted = set()
        self.phase_approach = None
        self.phase_until = 0.0
        self.last_service = {}

    def recovery_score(self, state):
        # Le cumul d'attente fournit l'aging; la distance restante approxime le coût.
        cost = (max(state.distance_to_junction, 0.0) + state.length) / self.config["network"]["speed_limit"]
        return (-state.cumulative_waiting_time, cost, state.vehicle_id)

    def resolve(self, snapshot, v2v_views, context):
        if self.config["control"]["congestion_regulation"]:
            return self.regulate(snapshot, v2v_views, context)
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

    def regulate(self, snapshot, v2v_views, context):
        states = self.vehicles(snapshot, v2v_views)
        candidates = {vid: s for vid, s in states.items() if in_control_zone(s, self.config)}
        self.granted = {vid for vid in self.granted if not cleared(states.get(vid), self.config)}
        approaches = sorted({s.approach for s in candidates.values()})
        for approach in approaches:
            self.last_service.setdefault(approach, snapshot.time)
        phase_empty = not any(s.approach == self.phase_approach for s in candidates.values())
        if not self.granted and (self.phase_approach is None or snapshot.time >= self.phase_until or phase_empty):
            self.phase_approach = None
            if approaches:
                pressure, age = {}, {}
                for approach in approaches:
                    group = [s for s in states.values() if s.approach == approach and s.road_id.endswith("_in")]
                    queue = sum(s.speed < self.config["detection"]["queue_speed"] for s in group)
                    max_wait = max(s.waiting_time for s in group)
                    age[approach] = snapshot.time - self.last_service[approach]
                    pressure[approach] = (queue + self.config["control"]["pressure_alpha"] *
                                          max_wait / self.config["control"]["wait_normalization"] +
                                          self.config["control"]["aging_weight"] * age[approach])
                starved = [a for a in approaches if age[a] >= self.config["control"]["max_approach_wait"]]
                winner = min(starved, key=lambda a: (-age[a], -pressure[a], a)) if starved else min(approaches, key=lambda a: (-pressure[a], a))
                self.phase_approach = winner
                self.phase_until = snapshot.time + self.config["control"]["control_interval"]
                self.last_service[winner] = snapshot.time
                context["decision"] = {"mode": "congestion_pressure", "selected_approach": winner,
                                       "pressure": pressure, "age_s": age, "phase_until": self.phase_until}
        if self.phase_approach and snapshot.time < self.phase_until:
            self.granted.update(vid for vid, s in candidates.items() if s.approach == self.phase_approach)
        # Les véhicules autorisés gardent leur réservation jusqu'au dégagement arrière.
        return self.commands(states, self.granted, "cooperative_pressure_with_aging")
