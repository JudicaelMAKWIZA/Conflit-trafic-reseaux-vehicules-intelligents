"""Baseline volontairement fragile : céder à toute approche adverse présente."""
from traffic_conflict.resolution.base import ResolverStrategy, in_control_zone


class NaiveYield(ResolverStrategy):
    def resolve(self, snapshot, v2v_views, context):
        states = self.vehicles(snapshot, v2v_views)
        candidates = {vid: state for vid, state in states.items() if in_control_zone(state, self.config)}
        allowed = {vid for vid, state in candidates.items()
                   if not any(other.approach != state.approach for oid, other in candidates.items() if oid != vid)}
        return self.commands(states, allowed, "naive_yield_conflicting_approach")
