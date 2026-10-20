import pytest

from crisisroute.allocation.scoring import (
    LAMBDA_TRAVEL,
    PENALTY_PER_UNMET_UNIT,
    compute_fitness,
    compute_metrics,
    coverage_fraction,
)
from crisisroute.risk import RiskAssessment
from crisisroute.scenario import Resource, Scenario, Zone


def _zone(zone_id: str, population: int) -> Zone:
    return Zone(
        id=zone_id,
        name=zone_id,
        node_id=0,
        population=population,
        vulnerable_pct=10.0,
        water_level_m=0.3,
        rainfall_mm=50.0,
        infrastructure_condition="good",
        road_accessibility="accessible",
    )


def _resource(resource_id: str, resource_type: str) -> Resource:
    return Resource(id=resource_id, type=resource_type, capacity=1, current_node=0)


def _risk(zone_id: str, score: float, category: str) -> RiskAssessment:
    return RiskAssessment(zone_id=zone_id, evidence={}, posterior={}, category=category, score=score)


def _tiny_scenario() -> Scenario:
    return Scenario(
        seed=0,
        nodes=[],
        edges=[],
        zones=[_zone("Z0", 1000), _zone("Z1", 2000)],
        resources=[
            _resource("R0", "ambulance"),
            _resource("R1", "ambulance"),
            _resource("R2", "rescue_team"),
        ],
        hospitals=[],
        depots=[],
    )


def test_coverage_fraction_has_diminishing_returns():
    assert coverage_fraction(0) == 0.0
    assert coverage_fraction(1) == pytest.approx(0.5)
    assert coverage_fraction(2) == pytest.approx(0.75)
    assert coverage_fraction(3) == pytest.approx(0.875)
    assert coverage_fraction(2) - coverage_fraction(1) < coverage_fraction(1) - coverage_fraction(0)


def test_coverage_fraction_is_monotonically_increasing():
    values = [coverage_fraction(n) for n in range(6)]
    assert values == sorted(values)


def test_fitness_with_no_assignment_equals_full_penalty():
    scenario = _tiny_scenario()
    risk_assessments = {"Z0": _risk("Z0", 0.8, "High"), "Z1": _risk("Z1", 0.2, "Low")}
    zone_needs = {"Z0": {"ambulance": 1, "rescue_team": 1, "relief_vehicle": 0}, "Z1": {"ambulance": 0, "rescue_team": 0, "relief_vehicle": 0}}
    cost_matrix = {r.id: {z.id: 0.0 for z in scenario.zones} for r in scenario.resources}

    chromosome = [-1, -1, -1]
    fitness = compute_fitness(scenario, chromosome, cost_matrix, risk_assessments, zone_needs)

    expected_penalty = 2 * PENALTY_PER_UNMET_UNIT
    assert fitness == pytest.approx(-expected_penalty)


def test_fitness_improves_when_needs_are_met():
    scenario = _tiny_scenario()
    risk_assessments = {"Z0": _risk("Z0", 0.8, "High"), "Z1": _risk("Z1", 0.2, "Low")}
    zone_needs = {"Z0": {"ambulance": 1, "rescue_team": 1, "relief_vehicle": 0}, "Z1": {"ambulance": 0, "rescue_team": 0, "relief_vehicle": 0}}
    cost_matrix = {r.id: {z.id: 0.0 for z in scenario.zones} for r in scenario.resources}

    unmet = compute_fitness(scenario, [-1, -1, -1], cost_matrix, risk_assessments, zone_needs)
    met = compute_fitness(scenario, [0, -1, 0], cost_matrix, risk_assessments, zone_needs)

    assert met > unmet


def test_fitness_decreases_with_more_travel_time():
    scenario = _tiny_scenario()
    risk_assessments = {"Z0": _risk("Z0", 0.8, "High"), "Z1": _risk("Z1", 0.2, "Low")}
    zone_needs = {"Z0": {"ambulance": 0, "rescue_team": 0, "relief_vehicle": 0}, "Z1": {"ambulance": 0, "rescue_team": 0, "relief_vehicle": 0}}

    near_matrix = {r.id: {z.id: 0.1 for z in scenario.zones} for r in scenario.resources}
    far_matrix = {r.id: {z.id: 1.0 for z in scenario.zones} for r in scenario.resources}

    chromosome = [0, -1, -1]
    near_fitness = compute_fitness(scenario, chromosome, near_matrix, risk_assessments, zone_needs)
    far_fitness = compute_fitness(scenario, chromosome, far_matrix, risk_assessments, zone_needs)

    assert near_fitness > far_fitness
    assert near_fitness - far_fitness == pytest.approx(LAMBDA_TRAVEL * (1.0 - 0.1))


def test_compute_metrics_on_known_assignment():
    scenario = _tiny_scenario()
    cost_matrix = {
        "R0": {"Z0": 0.5, "Z1": 2.0},
        "R1": {"Z0": 1.5, "Z1": 0.5},
        "R2": {"Z0": 0.2, "Z1": 0.8},
    }
    chromosome = [0, -1, 1]

    metrics = compute_metrics(scenario, chromosome, cost_matrix)

    assert metrics.total_travel_cost_hours == pytest.approx(0.5 + 0.8)
    assert metrics.average_response_time_hours == pytest.approx((0.5 + 0.8) / 2)
    assert metrics.resource_utilisation == pytest.approx(2 / 3)
    expected_population_covered = 1000 * coverage_fraction(1) + 2000 * coverage_fraction(1)
    assert metrics.population_covered == pytest.approx(expected_population_covered)


def test_compute_metrics_excludes_unavailable_from_utilisation_denominator():
    scenario = _tiny_scenario()
    cost_matrix = {r.id: {z.id: 0.5 for z in scenario.zones} for r in scenario.resources}
    chromosome = [0, -1, -1]

    metrics = compute_metrics(scenario, chromosome, cost_matrix, unavailable_resource_ids={"R1"})

    assert metrics.resource_utilisation == pytest.approx(1 / 2)
