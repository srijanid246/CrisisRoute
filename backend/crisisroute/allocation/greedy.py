from crisisroute.risk import assess_scenario_risk
from crisisroute.routing import build_cost_matrix

from .needs import zone_type_needs
from .scoring import AllocationResult, compute_fitness, compute_metrics


def run_greedy(
    scenario,
    cost_matrix: dict[str, dict[str, float]] | None = None,
    risk_assessments: dict | None = None,
    unavailable_resource_ids: set[str] | None = None,
) -> AllocationResult:
    cost_matrix = cost_matrix or build_cost_matrix(scenario)
    if risk_assessments is None:
        risk_assessments = {result.zone_id: result for result in assess_scenario_risk(scenario)}

    resources = scenario.resources
    zones = scenario.zones
    unavailable_resource_ids = unavailable_resource_ids or set()

    zone_index_by_id = {zone.id: index for index, zone in enumerate(zones)}
    zone_needs = {zone.id: zone_type_needs(zone, risk_assessments[zone.id].category) for zone in zones}

    chromosome = [-1] * len(resources)
    available_indices = [i for i, r in enumerate(resources) if r.id not in unavailable_resource_ids]

    zones_by_risk = sorted(zones, key=lambda zone: risk_assessments[zone.id].score, reverse=True)

    for zone in zones_by_risk:
        zone_index = zone_index_by_id[zone.id]
        for resource_type, needed_count in zone_needs[zone.id].items():
            for _ in range(needed_count):
                candidates = [
                    i
                    for i in available_indices
                    if chromosome[i] == -1 and resources[i].type == resource_type
                ]
                if not candidates:
                    break
                chosen = min(candidates, key=lambda i: cost_matrix[resources[i].id][zone.id])
                chromosome[chosen] = zone_index

    fitness = compute_fitness(scenario, chromosome, cost_matrix, risk_assessments, zone_needs)
    metrics = compute_metrics(scenario, chromosome, cost_matrix, unavailable_resource_ids)

    return AllocationResult(
        algorithm="greedy",
        chromosome=chromosome,
        fitness=fitness,
        history=[],
        metrics=metrics,
    )
