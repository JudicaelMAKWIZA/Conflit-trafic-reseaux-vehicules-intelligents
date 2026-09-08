import pytest

from traffic_conflict.simulation.runner import run_experiment


@pytest.mark.integration
@pytest.mark.parametrize("method", ["naive", "fcfs", "cooperative"])
def test_s1_baselines_and_censored_metrics(tmp_path, method):
    result = run_experiment("S1", method, 1, tmp_path)
    assert result["valid_run"]
    if method == "naive":
        assert result["completed_trip_count"] == 0
        assert result["deadlock_detected"]
        assert result["recovery_censored"]
        assert result["recovery_time_s"] is None
        assert result["mean_waiting_time_s"] is None
        assert result["unfinished_mean_waiting_time_s"] > 50
        assert result["detection_latency_s"] == pytest.approx(5)
    elif method == "fcfs":
        assert result["completed_trip_count"] == 4
        assert result["resolution_success"]
        assert not result["deadlock_detected"]
        assert result["recovery_time_s"] is None
        assert result["throughput_veh_per_hour"] == 144
        assert result["mean_waiting_time_s"] > 0
    else:
        assert result["completed_trip_count"] == 4
        assert result["resolution_success"] and result["deadlock_detected"]
        assert result["recovery_time_s"] > 0
        assert not result["recovery_censored"]
