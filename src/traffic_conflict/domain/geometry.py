"""Prédicats géométriques communs, sans dépendance aux détecteurs/résolveurs."""


def in_control_zone(state, config):
    return state.road_id.endswith("_in") and state.distance_to_junction <= config["control"]["zone_distance"]


def cleared(state, config):
    return state is None or (state.road_id.endswith("_out") and
                             state.lane_position >= state.length + config["control"]["clearance_distance"])
