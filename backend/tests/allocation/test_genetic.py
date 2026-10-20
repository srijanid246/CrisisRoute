from crisisroute.allocation import GAConfig, run_ga, run_greedy
from crisisroute.risk import assess_scenario_risk
from crisisroute.routing import build_cost_matrix
from crisisroute.scenario.presets import flood_demo


def _flood_demo_setup():
    scenario = flood_demo()
    cost_matrix = build_cost_matrix(scenario)
    risk_assessments = {r.zone_id: r for r in assess_scenario_risk(scenario)}
    return scenario, cost_matrix, risk_assessments


def test_same_seed_produces_identical_result():
    scenario, cost_matrix, risk_assessments = _flood_demo_setup()
    config = GAConfig(population_size=30, generations=20, seed=7)

    first = run_ga(scenario, cost_matrix, risk_assessments, config)
    second = run_ga(scenario, cost_matrix, risk_assessments, config)

    assert first == second


def test_different_seeds_can_produce_different_results():
    scenario, cost_matrix, risk_assessments = _flood_demo_setup()

    result_a = run_ga(scenario, cost_matrix, risk_assessments, GAConfig(population_size=20, generations=10, seed=1))
    result_b = run_ga(scenario, cost_matrix, risk_assessments, GAConfig(population_size=20, generations=10, seed=2))

    assert result_a.history != result_b.history or result_a.chromosome != result_b.chromosome


def test_best_fitness_never_decreases_across_generations():
    scenario, cost_matrix, risk_assessments = _flood_demo_setup()
    config = GAConfig(population_size=30, generations=40, seed=42)

    result = run_ga(scenario, cost_matrix, risk_assessments, config)

    best_so_far = float("-inf")
    for stats in result.history:
        best_so_far = max(best_so_far, stats.best_fitness)
        assert stats.best_fitness <= best_so_far + 1e-9
    assert result.fitness == best_so_far


def test_ga_fitness_is_at_least_greedy_on_flood_demo():
    scenario, cost_matrix, risk_assessments = _flood_demo_setup()

    greedy_result = run_greedy(scenario, cost_matrix, risk_assessments)
    ga_result = run_ga(scenario, cost_matrix, risk_assessments, GAConfig(seed=42))

    assert ga_result.fitness >= greedy_result.fitness


def test_unavailable_resources_are_never_assigned_by_ga():
    scenario, cost_matrix, risk_assessments = _flood_demo_setup()
    unavailable = {scenario.resources[0].id, scenario.resources[2].id}
    unavailable_indices = {0, 2}

    for seed in (1, 2, 3, 42):
        config = GAConfig(population_size=20, generations=15, seed=seed)
        result = run_ga(scenario, cost_matrix, risk_assessments, config, unavailable_resource_ids=unavailable)
        for index in unavailable_indices:
            assert result.chromosome[index] == -1


def test_ga_only_assigns_known_zone_indices_or_idle():
    scenario, cost_matrix, risk_assessments = _flood_demo_setup()
    config = GAConfig(population_size=20, generations=15, seed=99)
    result = run_ga(scenario, cost_matrix, risk_assessments, config)
    valid_values = set(range(len(scenario.zones))) | {-1}
    assert set(result.chromosome) <= valid_values


def test_seed_chromosomes_set_a_fitness_floor():
    from crisisroute.allocation.needs import zone_type_needs
    from crisisroute.allocation.scoring import compute_fitness

    scenario, cost_matrix, risk_assessments = _flood_demo_setup()
    zone_needs = {z.id: zone_type_needs(z, risk_assessments[z.id].category) for z in scenario.zones}

    all_idle = [-1] * len(scenario.resources)
    idle_fitness = compute_fitness(scenario, all_idle, cost_matrix, risk_assessments, zone_needs)

    config = GAConfig(population_size=10, generations=3, seed=123)
    result = run_ga(
        scenario, cost_matrix, risk_assessments, config, seed_chromosomes=[all_idle]
    )

    assert result.fitness >= idle_fitness


def test_seed_chromosomes_are_repaired_for_unavailable_resources():
    scenario, cost_matrix, risk_assessments = _flood_demo_setup()
    seed = [0] * len(scenario.resources)
    unavailable = {scenario.resources[0].id}

    config = GAConfig(population_size=1, generations=1, elitism_count=1, tournament_size=1, seed=5)
    result = run_ga(
        scenario,
        cost_matrix,
        risk_assessments,
        config,
        unavailable_resource_ids=unavailable,
        seed_chromosomes=[seed],
    )

    assert result.chromosome[0] == -1
    assert result.chromosome[1:] == seed[1:]


def test_result_round_trip():
    from crisisroute.allocation import AllocationResult

    scenario, cost_matrix, risk_assessments = _flood_demo_setup()
    config = GAConfig(population_size=15, generations=5, seed=5)
    result = run_ga(scenario, cost_matrix, risk_assessments, config)
    restored = AllocationResult.from_dict(result.to_dict())
    assert restored == result
