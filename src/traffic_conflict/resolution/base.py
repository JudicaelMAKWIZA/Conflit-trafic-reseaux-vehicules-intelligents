"""Interface de stratégie et helpers géométriques partagés."""
from abc import ABC, abstractmethod

from traffic_conflict.communication.v2v_bus import communicated_states
from traffic_conflict.domain.enums import ActionType
from traffic_conflict.domain.models import VehicleAction


def in_control_zone(state, config):
    return state.road_id.endswith("_in") and state.distance_to_junction <= config["control"]["zone_distance"]


def cleared(state, config):
    return state is None or (state.road_id.endswith("_out") and
                             state.lane_position >= state.length + config["control"]["clearance_distance"])


class ResolverStrategy(ABC):
    def __init__(self, config):
        self.config = config
        self.last_intent = {}

    @abstractmethod
    def resolve(self, snapshot, v2v_views, context):
        """Retourner les commandes ; aucun accès TraCI n'est autorisé ici."""

    def vehicles(self, snapshot, views):
        return communicated_states(snapshot.vehicles, views)

    def commands(self, states, allowed, reason):
        actions = []
        for vid, state in states.items():
            if not in_control_zone(state, self.config):
                continue
            action = ActionType.RESUME if vid in allowed else ActionType.STOP
            if self.last_intent.get(vid) == action:
                continue
            self.last_intent[vid] = action
            actions.append(VehicleAction(vid, action, self.config["control"]["stop_duration"], reason=reason))
        return actions
