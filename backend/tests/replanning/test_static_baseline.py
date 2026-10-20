import math

from crisisroute.replanning import (
    NewZoneEvent,
    Planner,
    ResourceUnavailableEvent,
    RiskChangeEvent,
    RoadBlockedEvent,
    static_outcome,
)
from crisisroute.scenario import Zone
from crisisroute.scenario.presets import flood_demo


def _flood_demo_plan():
    scenario = flood_demo()
    planner = Planner()
    plan = planner.create_plan(scenario)
    return scenario, planner, plan


def test_static_outcome_does_not_mutate_the_caller_scenario():
    scenario, planner, plan = _flood_demo_plan()
    resource_id, route = next(iter(plan.routes.items()))
    source, target = route.path[0], route.path[1]
    event = RoadBlockedEvent(source=source, target=target)

    static_outcome(scenario, plan, event)

    edge = next(e for e in scenario.edges if (e.source, e.target) in ((source, target), (target, source)))
    assert edge.blocked is False


def test_static_outcome_road_blocked_counts_affected_route_as_failed():
    scenario, planner, plan = _flood_demo_plan()
    resource_id, route = next(iter(plan.routes.items()))
    source, target = route.path[0], route.path[1]

    outcome = static_outcome(scenario, plan, RoadBlockedEvent(source=source, target=target))

    assert resource_id in outcome.failed_resource_ids


def test_static_outcome_road_blocked_covers_less_population_than_replanning():
    scenario, planner, plan = _flood_demo_plan()
    resource_id, route = next(iter(plan.routes.items()))
    source, target = route.path[0], route.path[1]
    event = RoadBlockedEvent(source=source, target=target)

    outcome = static_outcome(scenario, plan, event)
    _, diff = planner.apply_event(scenario, plan, event)

    assert outcome.metrics.population_covered <= diff.metrics_after.population_covered


def test_static_outcome_road_blocked_unused_edge_has_no_failures():
    scenario, planner, plan = _flood_demo_plan()
    used_pairs = set()
    for route in plan.routes.values():
        used_pairs |= set(zip(route.path, route.path[1:]))
        used_pairs |= set(zip(route.path[1:], route.path))
    unused_edge = next(e for e in scenario.edges if not e.blocked and (e.source, e.target) not in used_pairs)

    outcome = static_outcome(scenario, plan, RoadBlockedEvent(source=unused_edge.source, target=unused_edge.target))

    assert outcome.failed_resource_ids == []
    assert outcome.metrics.population_covered == plan.metrics.population_covered


def test_static_outcome_resource_unavailable_counts_as_failed_when_assigned():
    scenario, planner, plan = _flood_demo_plan()
    resource_id = next(rid for rid in plan.routes)

    outcome = static_outcome(scenario, plan, ResourceUnavailableEvent(resource_id=resource_id))

    assert resource_id in outcome.failed_resource_ids


def test_static_outcome_resource_unavailable_does_not_mutate_scenario():
    scenario, planner, plan = _flood_demo_plan()
    resource_id = next(rid for rid in plan.routes)
    original_resource_ids = {r.id for r in scenario.resources}

    static_outcome(scenario, plan, ResourceUnavailableEvent(resource_id=resource_id))

    assert {r.id for r in scenario.resources} == original_resource_ids


def test_static_outcome_new_zone_leaves_it_uncovered():
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

    outcome = static_outcome(scenario, plan, NewZoneEvent(zone=new_zone))

    assert "E" in outcome.uncovered_zone_ids
    assert new_zone not in scenario.zones


def test_static_outcome_risk_change_does_not_fail_any_delivery():
    scenario, planner, plan = _flood_demo_plan()

    outcome = static_outcome(
        scenario, plan, RiskChangeEvent(zone_id="B", attributes={"water_level_m": 2.5, "rainfall_mm": 220.0})
    )

    assert outcome.failed_resource_ids == []
    assert outcome.metrics.population_covered == plan.metrics.population_covered


def test_static_outcome_metrics_are_finite():
    scenario, planner, plan = _flood_demo_plan()
    resource_id, route = next(iter(plan.routes.items()))
    outcome = static_outcome(scenario, plan, RoadBlockedEvent(source=route.path[0], target=route.path[1]))

    assert math.isfinite(outcome.metrics.population_covered)
    assert math.isfinite(outcome.metrics.average_response_time_hours)
    assert math.isfinite(outcome.metrics.resource_utilisation)
    assert math.isfinite(outcome.metrics.total_travel_cost_hours)
