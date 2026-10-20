from crisisroute.allocation import GAConfig
from crisisroute.allocation.scoring import compute_fitness
from crisisroute.allocation.needs import zone_type_needs
from crisisroute.replanning import NewZoneEvent, Planner, ResourceUnavailableEvent, RiskChangeEvent, RoadBlockedEvent
from crisisroute.scenario import Depot, Edge, Node, Resource, Scenario, Zone
from crisisroute.scenario.presets import flood_demo


def _flood_demo_plan():
    scenario = flood_demo()
    planner = Planner()
    plan = planner.create_plan(scenario)
    return scenario, planner, plan


def _tiny_single_edge_scenario():
    nodes = [Node(id=0, lat=13.0, lng=80.0), Node(id=1, lat=13.0, lng=80.01)]
    edges = [Edge(source=0, target=1, length_km=1.0, speed_kmph=60.0, condition="good", blocked=False)]
    zones = [
        Zone(
            id="Z0",
            name="Z0",
            node_id=1,
            population=5000,
            vulnerable_pct=10.0,
            water_level_m=0.3,
            rainfall_mm=50.0,
            infrastructure_condition="good",
            road_accessibility="accessible",
        )
    ]
    resources = [Resource(id="R0", type="ambulance", capacity=2, current_node=0)]
    depots = [Depot(id="D0", name="D0", node_id=0)]
    return Scenario(seed=0, nodes=nodes, edges=edges, zones=zones, resources=resources, hospitals=[], depots=depots)


def test_create_plan_covers_every_zone_with_a_risk_assessment():
    scenario, _, plan = _flood_demo_plan()
    assert set(plan.risk_assessments.keys()) == {z.id for z in scenario.zones}


def test_create_plan_chromosome_length_matches_resource_count():
    scenario, _, plan = _flood_demo_plan()
    assert len(plan.allocation.chromosome) == len(scenario.resources)


def test_create_plan_has_a_route_for_every_deployed_resource():
    scenario, _, plan = _flood_demo_plan()
    deployed_ids = {r.id for gene, r in zip(plan.allocation.chromosome, scenario.resources) if gene != -1}
    assert set(plan.routes.keys()) == deployed_ids


def test_road_blocked_on_unused_edge_changes_nothing():
    scenario, planner, plan = _flood_demo_plan()
    used_pairs = set()
    for route in plan.routes.values():
        used_pairs |= set(zip(route.path, route.path[1:]))
        used_pairs |= set(zip(route.path[1:], route.path))

    unused_edge = next(
        e for e in scenario.edges if not e.blocked and (e.source, e.target) not in used_pairs
    )

    new_plan, diff = planner.apply_event(scenario, plan, RoadBlockedEvent(source=unused_edge.source, target=unused_edge.target))

    assert diff.ga_rerun is False
    assert diff.assignment_changes == []
    assert diff.route_changes == []
    assert new_plan.allocation.chromosome == plan.allocation.chromosome
    assert unused_edge.blocked is True


def test_road_blocked_small_increase_reroutes_without_ga_rerun():
    scenario, planner, plan = _flood_demo_plan()
    resource_id, route = next(iter(plan.routes.items()))
    source, target = route.path[0], route.path[1]

    new_plan, diff = planner.apply_event(scenario, plan, RoadBlockedEvent(source=source, target=target))

    assert diff.ga_rerun is False
    assert diff.assignment_changes == []
    assert len(diff.route_changes) == 1
    assert diff.route_changes[0].resource_id == resource_id
    assert new_plan.routes[resource_id].path != route.path
    for other_id, other_route in plan.routes.items():
        if other_id != resource_id:
            assert new_plan.routes[other_id].path == other_route.path
            assert new_plan.routes[other_id].cost == other_route.cost


def test_road_blocked_large_increase_triggers_ga_rerun():
    scenario, planner, plan = _flood_demo_plan()
    new_plan, diff = planner.apply_event(scenario, plan, RoadBlockedEvent(source=36, target=45))

    assert diff.ga_rerun is True
    assert "GA rerun" in diff.trigger_reason


def test_road_blocked_unreachable_route_idles_the_resource():
    scenario = _tiny_single_edge_scenario()
    planner = Planner()
    plan = planner.create_plan(scenario)
    assert plan.allocation.chromosome == [0]

    new_plan, diff = planner.apply_event(scenario, plan, RoadBlockedEvent(source=0, target=1))

    assert diff.ga_rerun is True
    assert new_plan.allocation.chromosome == [-1]
    assert "R0" not in new_plan.routes


def test_road_blocked_marks_the_edge_blocked_on_the_scenario():
    scenario, planner, plan = _flood_demo_plan()
    edge = next(e for e in scenario.edges if not e.blocked)
    planner.apply_event(scenario, plan, RoadBlockedEvent(source=edge.source, target=edge.target))
    assert edge.blocked is True


def test_new_zone_is_added_and_assessed():
    scenario, planner, plan = _flood_demo_plan()
    new_zone = Zone(
        id="E",
        name="Zone E",
        node_id=scenario.nodes[70].id,
        population=14000,
        vulnerable_pct=20.0,
        water_level_m=1.6,
        rainfall_mm=170.0,
        infrastructure_condition="damaged",
        road_accessibility="limited",
    )

    new_plan, diff = planner.apply_event(scenario, plan, NewZoneEvent(zone=new_zone))

    assert new_zone in scenario.zones
    assert "E" in new_plan.risk_assessments
    assert diff.ga_rerun is True
    assert diff.event_type == "NEW_ZONE"
    assert len(new_plan.allocation.chromosome) == len(scenario.resources)


def test_new_zone_ga_rerun_is_at_least_as_good_as_the_seeded_allocation():
    scenario, planner, plan = _flood_demo_plan()
    old_chromosome = list(plan.allocation.chromosome)
    new_zone = Zone(
        id="E",
        name="Zone E",
        node_id=scenario.nodes[70].id,
        population=14000,
        vulnerable_pct=20.0,
        water_level_m=1.6,
        rainfall_mm=170.0,
        infrastructure_condition="damaged",
        road_accessibility="limited",
    )

    new_plan, diff = planner.apply_event(scenario, plan, NewZoneEvent(zone=new_zone))

    zone_needs = {
        z.id: zone_type_needs(z, new_plan.risk_assessments[z.id].category) for z in scenario.zones
    }
    seeded_fitness = compute_fitness(
        scenario, old_chromosome, new_plan.cost_matrix, new_plan.risk_assessments, zone_needs
    )
    assert new_plan.allocation.fitness >= seeded_fitness


def test_resource_unavailable_idles_the_resource_and_reruns_ga():
    scenario, planner, plan = _flood_demo_plan()
    resource_id = scenario.resources[0].id
    index = 0

    new_plan, diff = planner.apply_event(scenario, plan, ResourceUnavailableEvent(resource_id=resource_id))

    assert diff.ga_rerun is True
    assert new_plan.allocation.chromosome[index] == -1
    assert resource_id not in new_plan.routes
    assert resource_id in new_plan.unavailable_resource_ids


def test_resource_unavailable_accumulates_across_events():
    scenario, planner, plan = _flood_demo_plan()
    id_a, id_b = scenario.resources[0].id, scenario.resources[1].id

    plan_after_a, _ = planner.apply_event(scenario, plan, ResourceUnavailableEvent(resource_id=id_a))
    plan_after_b, _ = planner.apply_event(scenario, plan_after_a, ResourceUnavailableEvent(resource_id=id_b))

    assert plan_after_b.unavailable_resource_ids == {id_a, id_b}
    assert plan_after_b.allocation.chromosome[0] == -1
    assert plan_after_b.allocation.chromosome[1] == -1


def test_risk_change_without_category_change_skips_ga_rerun():
    scenario, planner, plan = _flood_demo_plan()
    zone = next(z for z in scenario.zones if z.id == "B")
    old_category = plan.risk_assessments["B"].category

    new_plan, diff = planner.apply_event(
        scenario, plan, RiskChangeEvent(zone_id="B", attributes={"rainfall_mm": zone.rainfall_mm + 1.0})
    )

    assert new_plan.risk_assessments["B"].category == old_category
    assert diff.ga_rerun is False
    assert new_plan.allocation is plan.allocation
    assert new_plan.allocation.chromosome == plan.allocation.chromosome


def test_risk_change_with_category_change_triggers_ga_rerun():
    scenario, planner, plan = _flood_demo_plan()
    old_category = plan.risk_assessments["B"].category

    new_plan, diff = planner.apply_event(
        scenario,
        plan,
        RiskChangeEvent(zone_id="B", attributes={"water_level_m": 2.5, "rainfall_mm": 220.0}),
    )

    assert new_plan.risk_assessments["B"].category != old_category
    assert diff.ga_rerun is True


def test_risk_change_updates_the_zone_attributes_on_the_scenario():
    scenario, planner, plan = _flood_demo_plan()
    zone = next(z for z in scenario.zones if z.id == "B")

    planner.apply_event(scenario, plan, RiskChangeEvent(zone_id="B", attributes={"water_level_m": 2.1}))

    assert zone.water_level_m == 2.1


def test_plan_round_trip():
    from crisisroute.replanning import Plan

    _, _, plan = _flood_demo_plan()
    restored = Plan.from_dict(plan.to_dict())
    assert restored == plan


def test_diff_round_trip():
    from crisisroute.replanning import PlanDiff

    scenario, planner, plan = _flood_demo_plan()
    _, diff = planner.apply_event(scenario, plan, RoadBlockedEvent(source=36, target=45))
    restored = PlanDiff.from_dict(diff.to_dict())
    assert restored == diff
