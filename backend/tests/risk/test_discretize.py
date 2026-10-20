import pytest

from crisisroute.risk.discretize import (
    discretize_infrastructure_condition,
    discretize_population,
    discretize_rainfall,
    discretize_road_accessibility,
    discretize_vulnerable_pct,
    discretize_water_level,
    partial_evidence,
    zone_to_evidence,
)


@pytest.mark.parametrize(
    "mm,expected",
    [(0.0, "Low"), (79.9, "Low"), (80.0, "Medium"), (149.9, "Medium"), (150.0, "High"), (220.0, "High")],
)
def test_discretize_rainfall_thresholds(mm, expected):
    assert discretize_rainfall(mm) == expected


@pytest.mark.parametrize(
    "m,expected",
    [(0.0, "Low"), (0.49, "Low"), (0.5, "Medium"), (1.49, "Medium"), (1.5, "High"), (2.5, "High")],
)
def test_discretize_water_level_thresholds(m, expected):
    assert discretize_water_level(m) == expected


@pytest.mark.parametrize(
    "population,expected",
    [(0, "Low"), (4999, "Low"), (5000, "Medium"), (11999, "Medium"), (12000, "High"), (20000, "High")],
)
def test_discretize_population_thresholds(population, expected):
    assert discretize_population(population) == expected


@pytest.mark.parametrize(
    "pct,expected",
    [(0.0, "Low"), (14.9, "Low"), (15.0, "Medium"), (24.9, "Medium"), (25.0, "High"), (35.0, "High")],
)
def test_discretize_vulnerable_pct_thresholds(pct, expected):
    assert discretize_vulnerable_pct(pct) == expected


def test_discretize_road_accessibility_passes_through_known_states():
    for state in ("accessible", "limited", "cutoff"):
        assert discretize_road_accessibility(state) == state


def test_discretize_road_accessibility_rejects_unknown_state():
    with pytest.raises(ValueError):
        discretize_road_accessibility("partially_open")


def test_discretize_infrastructure_condition_passes_through_known_states():
    for state in ("good", "damaged", "critical"):
        assert discretize_infrastructure_condition(state) == state


def test_discretize_infrastructure_condition_rejects_unknown_state():
    with pytest.raises(ValueError):
        discretize_infrastructure_condition("destroyed")


def test_zone_to_evidence_covers_all_bn_inputs():
    from crisisroute.scenario import generate_scenario

    scenario = generate_scenario(seed=42)
    zone = scenario.zones[0]
    evidence = zone_to_evidence(zone)
    assert set(evidence.keys()) == {
        "Rainfall",
        "WaterLevel",
        "PopulationDensity",
        "VulnerablePopulation",
        "RoadAccessibility",
        "InfrastructureCondition",
    }


def test_partial_evidence_includes_only_provided_fields():
    evidence = partial_evidence(water_level_m=2.0)
    assert evidence == {"WaterLevel": "High"}


def test_partial_evidence_empty_when_nothing_provided():
    assert partial_evidence() == {}


def test_partial_evidence_combines_multiple_fields():
    evidence = partial_evidence(water_level_m=2.0, population=18000)
    assert evidence == {"WaterLevel": "High", "PopulationDensity": "High"}
