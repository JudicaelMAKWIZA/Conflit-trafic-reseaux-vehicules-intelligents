"""FCFS non préemptif, priorité à l'entrée en zone puis à l'identifiant."""
from traffic_conflict.resolution.base import ResolverStrategy, in_control_zone, cleared


class FCFSResolver(ResolverStrategy):
    def __init__(self, config):
        super().__init__(config)
        self.entered = {}
        self.active = None

    def resolve(self, snapshot, v2v_views, context):
        states = self.vehicles(snapshot, v2v_views)
        candidates = {vid: state for vid, state in states.items() if in_control_zone(state, self.config)}
        for vid in candidates:
            self.entered.setdefault(vid, snapshot.time)
        if self.active and cleared(states.get(self.active), self.config):
            self.active = None
        if self.active is None and candidates:
            self.active = min(candidates, key=lambda vid: (self.entered[vid], vid))
        return self.commands(states, {self.active}, "fcfs_non_preemptive")
