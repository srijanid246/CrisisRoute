import math

from crisisroute.allocation import GAConfig, run_ga
from crisisroute.allocation.scoring import compute_metrics
from crisisroute.risk import assess_scenario_risk, assess_zone_risk, get_inference_engine
from crisisroute.routing import SearchResult, build_cost_matrix, build_graph, search

from .events import NewZoneEvent, ResourceUnavailableEvent, RiskChangeEvent, RoadBlockedEvent, apply_physical_effect
from .plan import AssignmentChange, Plan, PlanDiff, RouteChange

ROUTE_COST_INCREASE_THRESHOLD = 1.3


def _build_routes(scenario, graph, allocation) -> dict[str, SearchResult]:
    routes = {}
    for gene, resource in zip(allocation.chromosome, scenario.resources):
        if gene == -1:
            continue
        zone = scenario.zones[gene]
        routes[resource.id] = search(graph, resource.current_node, zone.node_id, algorithm="astar")
    return routes


def _diff_assignments(old_allocation, new_allocation, scenario) -> list[AssignmentChange]:
    changes = []
    for index, resource in enumerate(scenario.resources):
        old_gene = old_allocation.chromosome[index]
        new_gene = new_allocation.chromosome[index]
        if old_gene == new_gene:
            continue
        old_zone_id = scenario.zones[old_gene].id if old_gene != -1 else None
        new_zone_id = scenario.zones[new_gene].id if new_gene != -1 else None
        changes.append(AssignmentChange(resource_id=resource.id, old_zone_id=old_zone_id, new_zone_id=new_zone_id))
    return changes


def _diff_routes(old_routes: dict[str, SearchResult], new_routes: dict[str, SearchResult]) -> list[RouteChange]:
    changes = []
    for resource_id in sorted(set(old_routes) | set(new_routes)):
        old_route = old_routes.get(resource_id)
        new_route = new_routes.get(resource_id)
        if old_route is not None and new_route is not None:
            if old_route.path == new_route.path and old_route.cost == new_route.cost:
                continue
        changes.append(
            RouteChange(
                resource_id=resource_id,
                old_cost=old_route.cost if old_route else None,
                new_cost=new_route.cost if new_route else None,
                old_path=list(old_route.path) if old_route else [],
                new_path=list(new_route.path) if new_route else [],
            )
        )
    return changes


def _route_degraded(old_cost: float, new_cost: float) -> bool:
    if math.isinf(new_cost):
        return True
    if old_cost == 0:
        return new_cost > 0
    return new_cost > old_cost * ROUTE_COST_INCREASE_THRESHOLD


class Planner:
    def __init__(self, ga_config: GAConfig | None = None):
        self.ga_config = ga_config or GAConfig()

    def create_plan(self, scenario) -> Plan:
        risk_assessments = {result.zone_id: result for result in assess_scenario_risk(scenario)}
        graph = build_graph(scenario)
        cost_matrix = build_cost_matrix(scenario, graph)
        allocation = run_ga(scenario, cost_matrix, risk_assessments, self.ga_config)
        routes = _build_routes(scenario, graph, allocation)

        return Plan(
            risk_assessments=risk_assessments,
            allocation=allocation,
            routes=routes,
            cost_matrix=cost_matrix,
            unavailable_resource_ids=set(),
            metrics=allocation.metrics,
        )

    def apply_event(self, scenario, plan: Plan, event) -> tuple[Plan, PlanDiff]:
        if isinstance(event, RoadBlockedEvent):
            return self._apply_road_blocked(scenario, plan, event)
        if isinstance(event, NewZoneEvent):
            return self._apply_new_zone(scenario, plan, event)
        if isinstance(event, ResourceUnavailableEvent):
            return self._apply_resource_unavailable(scenario, plan, event)
        if isinstance(event, RiskChangeEvent):
            return self._apply_risk_change(scenario, plan, event)
        raise TypeError(f"unknown event type: {type(event)!r}")

    def _apply_road_blocked(self, scenario, plan: Plan, event: RoadBlockedEvent) -> tuple[Plan, PlanDiff]:
        apply_physical_effect(scenario, event)
        graph = build_graph(scenario)
        blocked_pairs = {(event.source, event.target), (event.target, event.source)}

        resource_by_id = {r.id: r for r in scenario.resources}
        resource_index_by_id = {r.id: i for i, r in enumerate(scenario.resources)}
        zone_by_index = {i: z for i, z in enumerate(scenario.zones)}

        affected_resource_ids = [
            resource_id
            for resource_id, route in plan.routes.items()
            if set(zip(route.path, route.path[1:])) & blocked_pairs
        ]

        new_routes = dict(plan.routes)
        new_cost_matrix = {rid: dict(row) for rid, row in plan.cost_matrix.items()}
        needs_ga_rerun = False

        for resource_id in affected_resource_ids:
            old_route = plan.routes[resource_id]
            resource = resource_by_id[resource_id]
            gene = plan.allocation.chromosome[resource_index_by_id[resource_id]]
            zone = zone_by_index[gene]

            new_route = search(graph, resource.current_node, zone.node_id, algorithm="astar")
            new_routes[resource_id] = new_route
            new_cost_matrix.setdefault(resource_id, {})[zone.id] = new_route.cost

            if _route_degraded(old_route.cost, new_route.cost):
                needs_ga_rerun = True

        old_allocation = plan.allocation
        metrics_before = plan.metrics

        if needs_ga_rerun:
            full_cost_matrix = build_cost_matrix(scenario, graph)
            new_allocation = run_ga(
                scenario,
                full_cost_matrix,
                plan.risk_assessments,
                self.ga_config,
                unavailable_resource_ids=plan.unavailable_resource_ids,
            )
            new_routes = _build_routes(scenario, graph, new_allocation)
            new_cost_matrix = full_cost_matrix
            new_metrics = new_allocation.metrics
            reason = (
                f"edge ({event.source},{event.target}) blocked; {len(affected_resource_ids)} "
                "active route(s) affected and at least one became unreachable or its cost rose "
                "more than 30%; GA rerun"
            )
        elif affected_resource_ids:
            new_allocation = old_allocation
            new_metrics = compute_metrics(
                scenario, old_allocation.chromosome, new_cost_matrix, plan.unavailable_resource_ids
            )
            reason = (
                f"edge ({event.source},{event.target}) blocked; {len(affected_resource_ids)} "
                "active route(s) rerouted in place, no threshold breach, allocation unchanged"
            )
        else:
            new_allocation = old_allocation
            new_metrics = plan.metrics
            reason = f"edge ({event.source},{event.target}) blocked; no active route used it"

        new_plan = Plan(
            risk_assessments=plan.risk_assessments,
            allocation=new_allocation,
            routes=new_routes,
            cost_matrix=new_cost_matrix,
            unavailable_resource_ids=plan.unavailable_resource_ids,
            metrics=new_metrics,
        )

        diff = PlanDiff(
            event_type="ROAD_BLOCKED",
            trigger_reason=reason,
            ga_rerun=needs_ga_rerun,
            assignment_changes=_diff_assignments(old_allocation, new_allocation, scenario),
            route_changes=_diff_routes(plan.routes, new_routes),
            metrics_before=metrics_before,
            metrics_after=new_metrics,
        )
        return new_plan, diff

    def _apply_new_zone(self, scenario, plan: Plan, event: NewZoneEvent) -> tuple[Plan, PlanDiff]:
        zone = apply_physical_effect(scenario, event)

        engine = get_inference_engine()
        new_assessment = assess_zone_risk(zone, engine=engine)
        new_risk_assessments = dict(plan.risk_assessments)
        new_risk_assessments[zone.id] = new_assessment

        graph = build_graph(scenario)
        new_cost_matrix = build_cost_matrix(scenario, graph)

        old_allocation = plan.allocation
        metrics_before = plan.metrics

        new_allocation = run_ga(
            scenario,
            new_cost_matrix,
            new_risk_assessments,
            self.ga_config,
            unavailable_resource_ids=plan.unavailable_resource_ids,
            seed_chromosomes=[list(old_allocation.chromosome)],
        )
        new_routes = _build_routes(scenario, graph, new_allocation)
        new_metrics = new_allocation.metrics

        new_plan = Plan(
            risk_assessments=new_risk_assessments,
            allocation=new_allocation,
            routes=new_routes,
            cost_matrix=new_cost_matrix,
            unavailable_resource_ids=plan.unavailable_resource_ids,
            metrics=new_metrics,
        )

        diff = PlanDiff(
            event_type="NEW_ZONE",
            trigger_reason=(
                f"zone {zone.id} added; risk assessed as {new_assessment.category} "
                f"(score={new_assessment.score:.3f}); GA rerun seeded with current allocation"
            ),
            ga_rerun=True,
            assignment_changes=_diff_assignments(old_allocation, new_allocation, scenario),
            route_changes=_diff_routes(plan.routes, new_routes),
            metrics_before=metrics_before,
            metrics_after=new_metrics,
        )
        return new_plan, diff

    def _apply_resource_unavailable(
        self, scenario, plan: Plan, event: ResourceUnavailableEvent
    ) -> tuple[Plan, PlanDiff]:
        apply_physical_effect(scenario, event)

        new_unavailable = set(plan.unavailable_resource_ids)
        new_unavailable.add(event.resource_id)

        graph = build_graph(scenario)
        old_allocation = plan.allocation
        metrics_before = plan.metrics

        new_allocation = run_ga(
            scenario,
            plan.cost_matrix,
            plan.risk_assessments,
            self.ga_config,
            unavailable_resource_ids=new_unavailable,
        )
        new_routes = _build_routes(scenario, graph, new_allocation)
        new_metrics = new_allocation.metrics

        new_plan = Plan(
            risk_assessments=plan.risk_assessments,
            allocation=new_allocation,
            routes=new_routes,
            cost_matrix=plan.cost_matrix,
            unavailable_resource_ids=new_unavailable,
            metrics=new_metrics,
        )

        diff = PlanDiff(
            event_type="RESOURCE_UNAVAILABLE",
            trigger_reason=f"resource {event.resource_id} marked unavailable; GA rerun",
            ga_rerun=True,
            assignment_changes=_diff_assignments(old_allocation, new_allocation, scenario),
            route_changes=_diff_routes(plan.routes, new_routes),
            metrics_before=metrics_before,
            metrics_after=new_metrics,
        )
        return new_plan, diff

    def _apply_risk_change(self, scenario, plan: Plan, event: RiskChangeEvent) -> tuple[Plan, PlanDiff]:
        old_assessment = plan.risk_assessments[event.zone_id]
        zone = apply_physical_effect(scenario, event)

        engine = get_inference_engine()
        new_assessment = assess_zone_risk(zone, engine=engine)
        new_risk_assessments = dict(plan.risk_assessments)
        new_risk_assessments[event.zone_id] = new_assessment

        category_changed = new_assessment.category != old_assessment.category
        old_allocation = plan.allocation
        metrics_before = plan.metrics

        if category_changed:
            graph = build_graph(scenario)
            new_allocation = run_ga(
                scenario,
                plan.cost_matrix,
                new_risk_assessments,
                self.ga_config,
                unavailable_resource_ids=plan.unavailable_resource_ids,
            )
            new_routes = _build_routes(scenario, graph, new_allocation)
            new_metrics = new_allocation.metrics
            reason = (
                f"zone {event.zone_id} risk category changed "
                f"{old_assessment.category} -> {new_assessment.category}; GA rerun"
            )
        else:
            new_allocation = old_allocation
            new_routes = plan.routes
            new_metrics = plan.metrics
            reason = (
                f"zone {event.zone_id} risk score changed "
                f"({old_assessment.score:.3f} -> {new_assessment.score:.3f}) but category stayed "
                f"{new_assessment.category}; GA not rerun"
            )

        new_plan = Plan(
            risk_assessments=new_risk_assessments,
            allocation=new_allocation,
            routes=new_routes,
            cost_matrix=plan.cost_matrix,
            unavailable_resource_ids=plan.unavailable_resource_ids,
            metrics=new_metrics,
        )

        diff = PlanDiff(
            event_type="RISK_CHANGE",
            trigger_reason=reason,
            ga_rerun=category_changed,
            assignment_changes=_diff_assignments(old_allocation, new_allocation, scenario),
            route_changes=_diff_routes(plan.routes, new_routes),
            metrics_before=metrics_before,
            metrics_after=new_metrics,
        )
        return new_plan, diff
