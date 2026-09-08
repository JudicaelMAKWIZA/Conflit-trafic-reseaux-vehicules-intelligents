"""Re-run a complete measured recovery, including seeded SUMO inputs."""
import json

import pytest

from traffic_conflict.simulation.runner import run_experiment


@pytest.mark.integration
def test_s1_cooperative_same_seed_reproduces_routes_trajectories_and_metrics(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    for output in (first, second):
        result = run_experiment("S1", "cooperative", 3, output)
        assert result["valid_run"]
        assert result["deadlock_detected"] and result["resolution_success"]
        assert result["completed_trip_count"] == 4

    for relative in ("scenario/routes.rou.xml", "trajectories.csv", "steps.csv"):
        first_bytes = (first / relative).read_bytes()
        assert first_bytes, f"Missing measured content: {relative}"
        assert first_bytes == (second / relative).read_bytes(), relative

    summaries = []
    for output in (first, second):
        metadata = json.loads((output / "metadata.json").read_text(encoding="utf-8"))
        summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
        # Provenance can differ between executions (timestamp, Git worktree,
        # paths, input hashes). All computed metrics must remain identical.
        provenance = set(metadata) - {"scenario", "method", "seed"}
        provenance.add("output_dir")
        summaries.append({key: value for key, value in summary.items() if key not in provenance})
    assert summaries[0] == summaries[1]
    assert summaries[0]["seed"] == 3
