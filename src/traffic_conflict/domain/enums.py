"""Labels shared by observation, decision, control and result exports."""

from enum import StrEnum


class TrafficState(StrEnum):
    NORMAL = "NORMAL"
    CONGESTED = "CONGESTED"
    DEADLOCK = "DEADLOCK"


class ActionType(StrEnum):
    KEEP = "KEEP"
    STOP = "STOP"
    SLOW_DOWN = "SLOW_DOWN"
    RESUME = "RESUME"
