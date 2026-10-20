from dataclasses import dataclass
from typing import Any

COVERAGE_PER_RESOURCE = 0.5
LAMBDA_TRAVEL = 5000.0
PENALTY_PER_UNMET_UNIT = 8000.0


def coverage_fraction(assigned_count: int) -> float:
    if assigned_count <= 0:
        return 0.0
    return 1.0 - (1.0 - COVERAGE_PER_RESOURCE) ** assigned_count


def assignment_by_zone_index(chromosome: list[int], resources: list) -> dict[int, list]:
    assignment: dict[int, list] = {}
    for gene, resource in zip(chromosome, resources):
        if gene == -1:
            continue
        assignment.setdefault(gene, []).append(resource)
    return assignment


def compute_fitness(
    scenario,
    chromosome: list[int],
    cost_matrix: dict[str, dict[str, float]],
    risk_assessments: dict[str, Any],
    zone_needs: dict[str, dict[str, int]],
) -> float:
    resources = scenario.resources
    assignment = assignment_by_zone_index(chromosome, resources)
    coverage_term = 0.0
    penalty = 0.0

    for zone_index, zone in enumerate(scenario.zones):
        assigned = assignment.get(zone_index, [])
        coverage = coverage_fraction(len(assigned))
        risk_score = risk_assessments[zone.id].score
        coverage_term += risk_score * zone.population * coverage

        type_counts: dict[str, int] = {}
        for resource in assigned:
            type_counts[resource.type] = type_counts.get(resource.type, 0) + 1
        for resource_type, needed in zone_needs[zone.id].items():
            shortfall = max(0, needed - type_counts.get(resource_type, 0))
            penalty += shortfall * PENALTY_PER_UNMET_UNIT

    travel_time = 0.0
    for gene, resource in zip(chromosome, resources):
        if gene == -1:
            continue
        zone = scenario.zones[gene]
        travel_time += cost_matrix[resource.id][zone.id]

    return coverage_term - LAMBDA_TRAVEL * travel_time - penalty


@dataclass
class AllocationMetrics:
    population_covered: float
    average_response_time_hours: float
    resource_utilisation: float
    total_travel_cost_hours: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "population_covered": self.population_covered,
            "average_response_time_hours": self.average_response_time_hours,
            "resource_utilisation": self.resource_utilisation,
            "total_travel_cost_hours": self.total_travel_cost_hours,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AllocationMetrics":
        return cls(**data)


def compute_metrics(
    scenario,
    chromosome: list[int],
    cost_matrix: dict[str, dict[str, float]],
    unavailable_resource_ids: set[str] | None = None,
) -> AllocationMetrics:
    resources = scenario.resources
    unavailable_resource_ids = unavailable_resource_ids or set()
    assignment = assignment_by_zone_index(chromosome, resources)

    population_covered = 0.0
    for zone_index, zone in enumerate(scenario.zones):
        assigned = assignment.get(zone_index, [])
        population_covered += zone.population * coverage_fraction(len(assigned))

    deployed = [(gene, resource) for gene, resource in zip(chromosome, resources) if gene != -1]
    travel_times = [cost_matrix[resource.id][scenario.zones[gene].id] for gene, resource in deployed]
    total_travel_cost = sum(travel_times)
    average_response_time = total_travel_cost / len(travel_times) if travel_times else 0.0

    available_count = sum(1 for r in resources if r.id not in unavailable_resource_ids)
    resource_utilisation = len(deployed) / available_count if available_count > 0 else 0.0

    return AllocationMetrics(
        population_covered=population_covered,
        average_response_time_hours=average_response_time,
        resource_utilisation=resource_utilisation,
        total_travel_cost_hours=total_travel_cost,
    )


@dataclass
class GenerationStats:
    generation: int
    best_fitness: float
    average_fitness: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "generation": self.generation,
            "best_fitness": self.best_fitness,
            "average_fitness": self.average_fitness,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GenerationStats":
        return cls(**data)


@dataclass
class AllocationResult:
    algorithm: str
    chromosome: list[int]
    fitness: float
    history: list[GenerationStats]
    metrics: AllocationMetrics

    def to_dict(self) -> dict[str, Any]:
        return {
            "algorithm": self.algorithm,
            "chromosome": list(self.chromosome),
            "fitness": self.fitness,
            "history": [g.to_dict() for g in self.history],
            "metrics": self.metrics.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AllocationResult":
        return cls(
            algorithm=data["algorithm"],
            chromosome=list(data["chromosome"]),
            fitness=data["fitness"],
            history=[GenerationStats.from_dict(g) for g in data["history"]],
            metrics=AllocationMetrics.from_dict(data["metrics"]),
        )
