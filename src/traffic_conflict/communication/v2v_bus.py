"""Bus logique parfait : une copie d'état, livrée immédiatement à chaque voisin."""
from traffic_conflict.domain.models import V2VMessage, VehicleState


class V2VBus:
    def __init__(self):
        self.last_delivery_count = 0

    def broadcast(self, states: dict[str, VehicleState]) -> dict[str, dict[str, V2VMessage]]:
        messages = {vid: V2VMessage(vid, state.time, state, state.movement)
                    for vid, state in sorted(states.items())}
        views = {vid: {sender: msg for sender, msg in messages.items() if sender != vid}
                 for vid in sorted(states)}
        self.last_delivery_count = sum(map(len, views.values()))
        return views


def communicated_states(own_states, views):
    """Vue logique de coordination assemblée depuis les messages reçus.

    Un véhicule seul ne possède que sa propre observation. La V0 émule en Python
    un arbitrage déterministe commun, sans prétendre à un consensus distribué.
    """
    if not own_states:
        return {}
    coordinator = min(own_states)
    return {coordinator: own_states[coordinator],
            **{vid: message.state for vid, message in views[coordinator].items()}}
