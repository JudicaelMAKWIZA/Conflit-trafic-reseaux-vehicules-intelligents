import json

import pandas as pd
import pytest

from traffic_conflict.metrics.compute import summarize_approach_fairness


def final_states(*observations):
    return pd.DataFrame(observations, columns=["vehicle_id", "cumulative_waiting_time"])


def test_starved_and_not_departed_approaches_remain_visible():
    demand = [{"vehicle_id": vid, "approach": approach}
              for vid, approach in [("n", "N"), ("e", "E"), ("w", "W")]]
    result = summarize_approach_fairness(demand, final_states(("n", 2), ("e", 80)), {"n"})

    assert result["expected_by_approach"] == {"E": 1, "N": 1, "W": 1}
    assert result["departed_by_approach"] == {"E": 1, "N": 1, "W": 0}
    assert result["completed_by_approach"] == {"E": 0, "N": 1, "W": 0}
    assert result["unfinished_by_approach"] == {"E": 1, "N": 0, "W": 1}
    assert result["waiting_by_approach_s"] == {"E": None, "N": 2, "W": None}
    assert result["unfinished_observed_waiting_by_approach_s"] == {"E": 80, "N": None, "W": None}
    assert result["fairness_observed_std_wait_s"] == 0
    assert not result["fairness_complete"]
    assert result["fairness_std_wait_s"] is None
    json.dumps(result, allow_nan=False)


def test_complete_demand_uses_mean_wait_per_approach():
    demand = [{"vehicle_id": "n1", "approach": "N"},
              {"vehicle_id": "n2", "approach": "N"},
              {"vehicle_id": "e", "approach": "E"}]
    states = final_states(("n1", 4), ("n2", 8), ("e", 18))
    result = summarize_approach_fairness(demand, states, {"n1", "n2", "e"})

    assert result["fairness_complete"]
    assert result["waiting_by_approach_s"] == {"E": 18, "N": 6}
    assert result["fairness_std_wait_s"] == pytest.approx(6)
    assert result["unfinished_by_approach"] == {"E": 0, "N": 0}
    assert result["unfinished_observed_waiting_by_approach_s"] == {"E": None, "N": None}


def test_partial_completion_is_censored_even_if_each_approach_completed_a_trip():
    demand = [{"vehicle_id": "n", "approach": "N"},
              {"vehicle_id": "e1", "approach": "E"},
              {"vehicle_id": "e2", "approach": "E"}]
    result = summarize_approach_fairness(demand, final_states(("n", 1), ("e1", 1), ("e2", 30)), {"n", "e1"})

    assert result["fairness_observed_std_wait_s"] == 0
    assert not result["fairness_complete"]
    assert result["fairness_std_wait_s"] is None
    assert result["unfinished_observed_waiting_by_approach_s"]["E"] == 30


def test_no_completed_trip_produces_no_fabricated_fairness():
    demand = [{"vehicle_id": "n", "approach": "N"}]
    result = summarize_approach_fairness(demand, final_states(), set())

    assert result["fairness_std_wait_s"] is None
    assert result["fairness_observed_std_wait_s"] is None
    assert not result["fairness_complete"]
    assert result["waiting_by_approach_s"] == {"N": None}
    assert result["unfinished_observed_waiting_by_approach_s"] == {"N": None}
    json.dumps(result, allow_nan=False)
