from dataclasses import replace

from traffic_conflict.config import load_config
from traffic_conflict.domain.models import VehicleState
from traffic_conflict.resolution.cooperative import CooperativeV2VResolver


def test_recovery_priority_wait_then_distance_then_id():
    resolver = CooperativeV2VResolver(load_config("S1"))
    a = VehicleState("a", 0, 0, 0, 0, "N_in_0", "N_in", "r_N_LEFT", length=5,
                     cumulative_waiting_time=10, distance_to_junction=20)
    older = replace(a, vehicle_id="z", cumulative_waiting_time=11, distance_to_junction=40)
    cheaper = replace(a, vehicle_id="z", distance_to_junction=10)
    tied = replace(a, vehicle_id="b")
    assert min([a, older], key=resolver.recovery_score) is older
    assert min([a, cheaper], key=resolver.recovery_score) is cheaper
    assert min([a, tied], key=resolver.recovery_score) is a
