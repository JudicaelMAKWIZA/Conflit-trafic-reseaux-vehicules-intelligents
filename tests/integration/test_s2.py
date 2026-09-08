import pytest

from traffic_conflict.simulation.runner import run_experiment


@pytest.mark.integration
def test_s2_detects_real_congestion_and_drains_fcfs(tmp_path):
    result = run_experiment("S2", "fcfs", 1, tmp_path)
    assert result["valid_run"]
    assert result["time_in_congestion_s"] > 0
    assert result["completed_trip_count"] == result["expected_trip_count"]
    assert result["fairness_complete"]
    assert not result["deadlock_detected"]
