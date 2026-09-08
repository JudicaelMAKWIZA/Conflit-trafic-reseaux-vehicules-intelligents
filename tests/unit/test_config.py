import pytest

from traffic_conflict.config import load_config, merge, validate_config


def test_merge_is_recursive_and_does_not_mutate():
    original = {"nested": {"x": 1, "y": 2}}
    result = merge(original, {"nested": {"x": 3}})
    assert result == {"nested": {"x": 3, "y": 2}}
    assert original["nested"]["x"] == 1


@pytest.mark.parametrize("scenario", ["S0", "S1", "S2"])
def test_configs_disable_teleport_and_contain_ten_seeds(scenario):
    config = load_config(scenario)
    assert config["simulation"]["time_to_teleport"] == -1
    assert len(set(config["experiment"]["seeds"])) >= 10


def test_reject_teleport_enabled():
    config = load_config("S1")
    config["simulation"]["time_to_teleport"] = 30
    with pytest.raises(ValueError, match="téléportations"):
        validate_config(config)


def test_unknown_scenario():
    with pytest.raises(ValueError, match="inconnu"):
        load_config("S99")
