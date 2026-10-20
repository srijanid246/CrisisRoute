import random

from crisisroute.risk import assess_scenario_risk
from crisisroute.routing import build_cost_matrix

from .config import GAConfig
from .needs import zone_type_needs
from .scoring import AllocationResult, GenerationStats, compute_fitness, compute_metrics


def _random_gene(num_zones: int, rng: random.Random) -> int:
    return rng.randint(-1, num_zones - 1)


def _random_chromosome(num_resources: int, num_zones: int, rng: random.Random) -> list[int]:
    return [_random_gene(num_zones, rng) for _ in range(num_resources)]


def _repair(chromosome: list[int], unavailable_indices: set[int]) -> list[int]:
    for index in unavailable_indices:
        chromosome[index] = -1
    return chromosome


def _tournament_select(
    scored: list[tuple[float, list[int]]], tournament_size: int, rng: random.Random
) -> list[int]:
    contenders = rng.choices(scored, k=tournament_size)
    winner = max(contenders, key=lambda item: item[0])
    return list(winner[1])


def _uniform_crossover(
    parent_a: list[int], parent_b: list[int], rng: random.Random
) -> tuple[list[int], list[int]]:
    child_a: list[int] = []
    child_b: list[int] = []
    for gene_a, gene_b in zip(parent_a, parent_b):
        if rng.random() < 0.5:
            child_a.append(gene_a)
            child_b.append(gene_b)
        else:
            child_a.append(gene_b)
            child_b.append(gene_a)
    return child_a, child_b


def _mutate(chromosome: list[int], num_zones: int, mutation_rate: float, rng: random.Random) -> list[int]:
    mutated = list(chromosome)
    for i in range(len(mutated)):
        if rng.random() < mutation_rate:
            mutated[i] = _random_gene(num_zones, rng)
    return mutated


def run_ga(
    scenario,
    cost_matrix: dict[str, dict[str, float]] | None = None,
    risk_assessments: dict | None = None,
    config: GAConfig | None = None,
    unavailable_resource_ids: set[str] | None = None,
    seed_chromosomes: list[list[int]] | None = None,
) -> AllocationResult:
    config = config or GAConfig()
    if config.population_size < 1:
        raise ValueError("population_size must be >= 1")
    if config.generations < 1:
        raise ValueError("generations must be >= 1")

    cost_matrix = cost_matrix or build_cost_matrix(scenario)
    if risk_assessments is None:
        risk_assessments = {result.zone_id: result for result in assess_scenario_risk(scenario)}

    rng = random.Random(config.seed)
    resources = scenario.resources
    zones = scenario.zones
    num_zones = len(zones)
    num_resources = len(resources)

    unavailable_resource_ids = unavailable_resource_ids or set()
    unavailable_indices = {i for i, r in enumerate(resources) if r.id in unavailable_resource_ids}

    zone_needs = {zone.id: zone_type_needs(zone, risk_assessments[zone.id].category) for zone in zones}

    def fitness_of(chromosome: list[int]) -> float:
        return compute_fitness(scenario, chromosome, cost_matrix, risk_assessments, zone_needs)

    population: list[list[int]] = [
        _repair(list(seed_chromosome[:num_resources]), unavailable_indices)
        for seed_chromosome in (seed_chromosomes or [])
    ]
    while len(population) < config.population_size:
        population.append(_repair(_random_chromosome(num_resources, num_zones, rng), unavailable_indices))

    history: list[GenerationStats] = []
    best_chromosome: list[int] = list(population[0])
    best_fitness = float("-inf")

    for generation in range(config.generations):
        scored = sorted(
            ((fitness_of(individual), individual) for individual in population),
            key=lambda item: item[0],
            reverse=True,
        )

        generation_best_fitness, generation_best_individual = scored[0]
        generation_average_fitness = sum(f for f, _ in scored) / len(scored)
        history.append(
            GenerationStats(
                generation=generation,
                best_fitness=generation_best_fitness,
                average_fitness=generation_average_fitness,
            )
        )

        if generation_best_fitness > best_fitness:
            best_fitness = generation_best_fitness
            best_chromosome = list(generation_best_individual)

        next_population = [list(individual) for _, individual in scored[: config.elitism_count]]

        while len(next_population) < config.population_size:
            parent_a = _tournament_select(scored, config.tournament_size, rng)
            parent_b = _tournament_select(scored, config.tournament_size, rng)

            if rng.random() < config.crossover_rate:
                child_a, child_b = _uniform_crossover(parent_a, parent_b, rng)
            else:
                child_a, child_b = list(parent_a), list(parent_b)

            child_a = _repair(_mutate(child_a, num_zones, config.mutation_rate, rng), unavailable_indices)
            child_b = _repair(_mutate(child_b, num_zones, config.mutation_rate, rng), unavailable_indices)

            next_population.append(child_a)
            if len(next_population) < config.population_size:
                next_population.append(child_b)

        population = next_population

    metrics = compute_metrics(scenario, best_chromosome, cost_matrix, unavailable_resource_ids)

    return AllocationResult(
        algorithm="genetic_algorithm",
        chromosome=best_chromosome,
        fitness=best_fitness,
        history=history,
        metrics=metrics,
    )
