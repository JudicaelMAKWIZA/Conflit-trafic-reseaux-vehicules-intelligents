from traffic_conflict.resolution.naive_yield import NaiveYield
from traffic_conflict.resolution.fcfs import FCFSResolver

STRATEGIES = {"naive": NaiveYield, "fcfs": FCFSResolver}


def make_resolver(method, config):
    if method == "observe":
        return None
    if method not in STRATEGIES:
        raise ValueError(f"Méthode inconnue : {method}")
    return STRATEGIES[method](config)
