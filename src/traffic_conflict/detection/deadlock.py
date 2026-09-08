"""Cycles d'attente persistants, sans connaissance de la stratégie de résolution."""
import networkx as nx

from traffic_conflict.domain.conflicts import incompatible
from traffic_conflict.domain.geometry import in_control_zone, cleared


class DeadlockDetector:
    def __init__(self, config):
        self.config = config
        self.since = None
        self.signature = None

    def update(self, states, time):
        near = {vid: state for vid, state in states.items()
                if in_control_zone(state, self.config) or state.road_id.startswith(":") or
                (state.road_id.endswith("_out") and not cleared(state, self.config))}
        stopped = {vid: state for vid, state in near.items() if state.is_stopped}
        graph = nx.DiGraph()
        graph.add_nodes_from(stopped)
        for aid, a in stopped.items():
            for bid, b in stopped.items():
                if aid != bid and incompatible(a, b):
                    graph.add_edge(aid, bid)
        components = sorted([sorted(part) for part in nx.strongly_connected_components(graph) if len(part) > 1])
        involved = sorted({vid for part in components for vid in part})
        # Une file pendant qu'un véhicule franchit n'est pas une attente mutuelle.
        eligible = (len(involved) >= self.config["detection"]["deadlock_min_vehicles"] and
                    len(stopped) == len(near))
        signature = tuple(involved)
        if not eligible:
            self.since, self.signature = None, None
        elif signature != self.signature:
            self.signature, self.since = signature, time
        detected = bool(eligible and time - self.since + 1e-9 >= self.config["detection"]["deadlock_persistence"])
        cycles = [[edge[0] for edge in nx.find_cycle(graph.subgraph(part))] for part in components]
        return {"is_deadlock": detected, "vehicles": involved,
                "wait_for_graph": {vid: sorted(graph.successors(vid)) for vid in sorted(graph)},
                "cycles": cycles, "onset_time": self.since,
                "detection_latency_s": time - self.since if detected else None}
