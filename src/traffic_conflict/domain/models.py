"""Small data contracts, independent of SUMO and of any resolver strategy.

Times are simulation seconds, positions and lengths metres, speeds metres per
second. Detection thresholds belong in YAML; these classes do not classify
observations or calculate traffic metrics.
"""

from dataclasses import dataclass, field, replace
from typing import Any

from .enums import ActionType, TrafficState


@dataclass(frozen=True, slots=True)
class VehicleState:
    """One immutable vehicle observation.

    ``waiting_time`` counts consecutive stopped time observed by Python,
    including controller stops. ``cumulative_waiting_time`` accumulates those
    stopped intervals since departure. ``sumo_waiting_time`` preserves the
    native TraCI value, which excludes scheduled stops. Unknown optional
    geometry has no implied detector threshold; the collector fills geometry
    from SUMO before a controller uses it.
    """

    vehicle_id: str
    time: float
    x: float
    y: float
    speed: float
    lane_id: str
    road_id: str
    route_id: str
    waiting_time: float = 0.0
    heading: float | None = None
    distance_to_junction: float | None = None
    is_stopped: bool = False
    approach: str = ""
    movement: str = "STRAIGHT"
    length: float = 0.0
    lane_position: float = 0.0
    sumo_waiting_time: float = 0.0
    cumulative_waiting_time: float = 0.0


@dataclass(frozen=True, slots=True)
class V2VMessage:
    """An immutable, detached observation sent through the perfect V2V bus."""

    sender_id: str
    timestamp: float
    state: VehicleState
    intent: str | None = None

    def __post_init__(self) -> None:
        if self.sender_id != self.state.vehicle_id:
            raise ValueError("V2V sender_id must identify the supplied state")
        object.__setattr__(self, "state", replace(self.state))


@dataclass(slots=True)
class TrafficSnapshot:
    """Observed traffic and aggregate values supplied by the estimator.

    Empty aggregate values are defaults for constructing an observation, not
    substitutes for measured results. Queue lengths are vehicle counts indexed
    by approach. Entry/exit counts refer to the configured sliding window.
    """

    time: float
    vehicles: dict[str, VehicleState] = field(default_factory=dict)
    mean_speed: float = 0.0
    stopped_count: int = 0
    queue_lengths: dict[str, int] = field(default_factory=dict)
    mean_waiting_time: float = 0.0
    max_waiting_time: float = 0.0
    entries_in_window: int = 0
    exits_in_window: int = 0
    traffic_state: TrafficState = TrafficState.NORMAL
    diagnostics: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # VehicleState values are immutable; copy the collection so an update
        # to the collector's dictionary cannot change a past observation.
        self.vehicles = dict(self.vehicles)
        self.queue_lengths = dict(self.queue_lengths)
        self.diagnostics = dict(self.diagnostics)

    @property
    def total_vehicles(self) -> int:
        return len(self.vehicles)


@dataclass(frozen=True, slots=True)
class VehicleAction:
    """A requested command; the ActionController reports its actual outcome."""

    vehicle_id: str
    action_type: ActionType
    duration: float | None = None
    target_speed: float | None = None
    reason: str = ""
