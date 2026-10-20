from crisisroute.risk import RISK_STATES, assess_risk, assess_scenario_risk, assess_zone_risk
from crisisroute.scenario.presets import flood_demo

BASELINE_EVIDENCE = {
    "Rainfall": "Low",
    "WaterLevel": "Low",
    "PopulationDensity": "Low",
    "VulnerablePopulation": "Low",
    "RoadAccessibility": "accessible",
    "InfrastructureCondition": "good",
}


def test_posterior_sums_to_one_with_full_evidence():
    result = assess_risk(BASELINE_EVIDENCE)
    assert abs(sum(result.posterior.values()) - 1.0) < 1e-9


def test_posterior_covers_all_risk_states():
    result = assess_risk(BASELINE_EVIDENCE)
    assert set(result.posterior.keys()) == set(RISK_STATES)


def test_category_is_argmax_of_posterior():
    result = assess_risk(BASELINE_EVIDENCE)
    assert result.category == max(result.posterior, key=result.posterior.get)


def test_score_is_within_unit_interval():
    result = assess_risk(BASELINE_EVIDENCE)
    assert 0.0 <= result.score <= 1.0


def test_higher_water_level_increases_risk():
    low_water = dict(BASELINE_EVIDENCE, WaterLevel="Low")
    high_water = dict(BASELINE_EVIDENCE, WaterLevel="High")

    low_result = assess_risk(low_water)
    high_result = assess_risk(high_water)

    assert high_result.score > low_result.score
    assert high_result.posterior["VeryHigh"] > low_result.posterior["VeryHigh"]


def test_higher_population_increases_risk():
    low_population = dict(BASELINE_EVIDENCE, PopulationDensity="Low")
    high_population = dict(BASELINE_EVIDENCE, PopulationDensity="High")

    low_result = assess_risk(low_population)
    high_result = assess_risk(high_population)

    assert high_result.score > low_result.score
    assert high_result.posterior["VeryHigh"] > low_result.posterior["VeryHigh"]


def test_worst_case_evidence_is_highest_risk_category():
    worst = {
        "Rainfall": "High",
        "WaterLevel": "High",
        "PopulationDensity": "High",
        "VulnerablePopulation": "High",
        "RoadAccessibility": "cutoff",
        "InfrastructureCondition": "critical",
    }
    result = assess_risk(worst)
    assert result.category == "VeryHigh"


def test_best_case_evidence_is_lowest_risk_category():
    result = assess_risk(BASELINE_EVIDENCE)
    assert result.category == "Low"


def test_missing_evidence_still_returns_valid_result():
    partial = {"WaterLevel": "High"}
    result = assess_risk(partial)
    assert abs(sum(result.posterior.values()) - 1.0) < 1e-9
    assert result.category in RISK_STATES
    assert 0.0 <= result.score <= 1.0


def test_empty_evidence_falls_back_to_priors():
    result = assess_risk({})
    assert abs(sum(result.posterior.values()) - 1.0) < 1e-9
    assert result.category in RISK_STATES
    assert 0.0 <= result.score <= 1.0


def test_missing_evidence_moves_risk_in_the_expected_direction():
    no_evidence_result = assess_risk({})
    high_water_only = assess_risk({"WaterLevel": "High"})
    assert high_water_only.score > no_evidence_result.score


def test_assess_zone_risk_uses_full_zone_evidence():
    scenario = flood_demo()
    zone = next(z for z in scenario.zones if z.id == "C")
    result = assess_zone_risk(zone)
    assert result.zone_id == "C"
    assert result.category in RISK_STATES


def test_assess_scenario_risk_returns_one_result_per_zone():
    scenario = flood_demo()
    results = assess_scenario_risk(scenario)
    assert [r.zone_id for r in results] == [z.id for z in scenario.zones]
    for result in results:
        assert abs(sum(result.posterior.values()) - 1.0) < 1e-9


def test_flood_demo_zone_c_is_higher_risk_than_zone_b():
    scenario = flood_demo()
    results = {r.zone_id: r for r in assess_scenario_risk(scenario)}
    assert results["C"].score > results["B"].score
