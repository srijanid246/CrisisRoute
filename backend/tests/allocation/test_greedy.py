from crisisroute.allocation import run_greedy
from crisisroute.risk import RiskAssessment
from crisisroute.routing import build_cost_matrix
from crisisroute.scenario import Resource, Scenario, Zone
from crisisroute.scenario.presets import flood_demo


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


def test_greedy_assigns_nearest_suitable_resource_to_highest_risk_zone():
    scenario = Scenario(
        seed=0,
        nodes=[],
        edges=[],
        zones=[_zone("Z0", 1000), _zone("Z1", 1000)],
        resources=[_resource("R_FAR", "ambulance"), _resource("R_NEAR", "ambulance")],
        hospitals=[],
        depots=[],
    )
    cost_matrix = {
        "R_FAR": {"Z0": 5.0, "Z1": 5.0},
        "R_NEAR": {"Z0": 0.1, "Z1": 0.1},
    }
    risk_assessments = {
        "Z0": RiskAssessment(zone_id="Z0", evidence={}, posterior={}, category="High", score=0.9),
        "Z1": RiskAssessment(zone_id="Z1", evidence={}, posterior={}, category="Low", score=0.1),
    }

    result = run_greedy(scenario, cost_matrix, risk_assessments)

    near_index = scenario.resources.index(next(r for r in scenario.resources if r.id == "R_NEAR"))
    assert result.chromosome[near_index] == 0


def test_greedy_leaves_resources_idle_once_zone_needs_are_met():
    scenario = Scenario(
        seed=0,
        nodes=[],
        edges=[],
        zones=[_zone("Z0", 1000)],
        resources=[_resource("R0", "ambulance"), _resource("R1", "ambulance")],
        hospitals=[],
        depots=[],
    )
    cost_matrix = {"R0": {"Z0": 0.2}, "R1": {"Z0": 0.1}}
    risk_assessments = {"Z0": RiskAssessment(zone_id="Z0", evidence={}, posterior={}, category="Medium", score=0.4)}

    result = run_greedy(scenario, cost_matrix, risk_assessments)

    assert result.chromosome.count(-1) == 1


def test_greedy_is_deterministic():
    scenario = flood_demo()
    cost_matrix = build_cost_matrix(scenario)

    first = run_greedy(scenario, cost_matrix)
    second = run_greedy(scenario, cost_matrix)

    assert first == second


def test_unavailable_resources_are_never_assigned_by_greedy():
    scenario = flood_demo()
    cost_matrix = build_cost_matrix(scenario)
    unavailable = {scenario.resources[0].id, scenario.resources[2].id}

    result = run_greedy(scenario, cost_matrix, unavailable_resource_ids=unavailable)

    assert result.chromosome[0] == -1
    assert result.chromosome[2] == -1


def test_greedy_never_assigns_a_mismatched_resource_type():
    scenario = flood_demo()
    cost_matrix = build_cost_matrix(scenario)

    result = run_greedy(scenario, cost_matrix)

    from crisisroute.allocation.needs import zone_type_needs
    from crisisroute.risk import assess_scenario_risk

    risk_assessments = {r.zone_id: r for r in assess_scenario_risk(scenario)}
    zone_needs = {z.id: zone_type_needs(z, risk_assessments[z.id].category) for z in scenario.zones}

    for gene, resource in zip(result.chromosome, scenario.resources):
        if gene == -1:
            continue
        zone = scenario.zones[gene]
        assert zone_needs[zone.id].get(resource.type, 0) > 0
