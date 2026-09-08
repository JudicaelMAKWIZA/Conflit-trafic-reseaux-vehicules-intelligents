import csv

import pytest

from traffic_conflict.simulation.runner import run_experiment


@pytest.mark.integration
def test_real_collector_and_v2v_logs(tmp_path):
    summary = run_experiment(output_dir=tmp_path)
    assert summary["completed_trip_count"] == 12
    assert summary["collision_count"] == summary["teleport_count"] == 0
    with (tmp_path / "trajectories.csv").open() as stream:
        rows = list(csv.DictReader(stream))
    assert rows
    assert all(float(row["speed"]) >= 0 and row["lane_id"] for row in rows)
    with (tmp_path / "steps.csv").open() as stream:
        steps = list(csv.DictReader(stream))
    assert all(int(row["v2v_deliveries"]) == int(row["active"]) * (int(row["active"]) - 1) for row in steps)
    assert int(steps[-1]["completed"]) == 12
