import copy
from dataclasses import dataclass
from typing import Any

from crisisroute.allocation import AllocationMetrics
from crisisroute.allocation.scoring import compute_metrics

from .events import ResourceUnavailableEvent, RoadBlockedEvent, apply_physical_effect
from .plan import Plan


@dataclass
class StaticOutcome:
    metrics: AllocationMetrics
    failed_resource_ids: list[str]
    uncovered_zone_ids: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "metrics": self.metrics.to_dict(),
            "failed_resource_ids": list(self.failed_resource_ids),
            "uncovered_zone_ids": list(self.uncovered_zone_ids),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StaticOutcome":
        return cls(
            metrics=AllocationMetrics.from_dict(data["metrics"]),
            failed_resource_ids=list(data["failed_resource_ids"]),
            uncovered_zone_ids=list(data["uncovered_zone_ids"]),
        )


def static_outcome(scenario, old_plan: Plan, event) -> StaticOutcome:
    scenario_copy = copy.deepcopy(scenario)
    apply_physical_effect(scenario_copy, event)

    resources = scenario_copy.resources
    resource_index_by_id = {r.id: i for i, r in enumerate(resources)}
    zone_by_index = {i: z for i, z in enumerate(scenario_copy.zones)}

    chromosome = list(old_plan.allocation.chromosome)
    failed_resource_ids: list[str] = []
    extra_unavailable: set[str] = set()

    if isinstance(event, RoadBlockedEvent):
        blocked_pairs = {(event.source, event.target), (event.target, event.source)}
        for resource_id, route in old_plan.routes.items():
            route_pairs = set(zip(route.path, route.path[1:]))
            if route_pairs & blocked_pairs:
                failed_resource_ids.append(resource_id)
    elif isinstance(event, ResourceUnavailableEvent):
        index = resource_index_by_id.get(event.resource_id)
        if index is not None and chromosome[index] != -1:
            failed_resource_ids.append(event.resource_id)
        extra_unavailable.add(event.resource_id)

    effective_chromosome = list(chromosome)
    for resource_id in failed_resource_ids:
        effective_chromosome[resource_index_by_id[resource_id]] = -1

    cost_matrix: dict[str, dict[str, float]] = {}
    for resource_id, route in old_plan.routes.items():
        index = resource_index_by_id.get(resource_id)
        if index is None:
            continue
        gene = chromosome[index]
        if gene == -1:
            continue
        zone_id = zone_by_index[gene].id
        cost_matrix[resource_id] = {zone_id: route.cost}

    unavailable_for_metrics = old_plan.unavailable_resource_ids | extra_unavailable
    metrics = compute_metrics(scenario_copy, effective_chromosome, cost_matrix, unavailable_for_metrics)

    assigned_zone_indices = {gene for gene in effective_chromosome if gene != -1}
    uncovered_zone_ids = [
        zone.id for index, zone in enumerate(scenario_copy.zones) if index not in assigned_zone_indices
    ]

    return StaticOutcome(
        metrics=metrics,
        failed_resource_ids=failed_resource_ids,
        uncovered_zone_ids=uncovered_zone_ids,
    )
