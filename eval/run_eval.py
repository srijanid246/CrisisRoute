import csv
import math
import os
import random
import statistics
import sys
import time
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from crisisroute.allocation import GAConfig, run_ga, run_greedy
from crisisroute.replanning import NewZoneEvent, Planner, ResourceUnavailableEvent, RoadBlockedEvent, static_outcome
from crisisroute.risk import assess_scenario_risk
from crisisroute.routing import ALGORITHMS, build_cost_matrix, build_graph, search
from crisisroute.scenario import Zone, generate_scenario
from crisisroute.scenario.presets import (
    LARGE_SCENARIO_NUM_ZONES,
    LARGE_SCENARIO_RESOURCE_COUNTS,
    LARGE_SCENARIO_TARGET_NODES,
    flood_demo,
)

SEEDS = list(range(30))
PAIRS_PER_SEED = 10
SCENARIO_TYPES = ["no_change", "road_blockage", "new_zone", "resource_shortage"]
SCALES = {
    "small": {"target_nodes": 80, "num_zones": None, "resource_counts": None},
    "large": {
        "target_nodes": LARGE_SCENARIO_TARGET_NODES,
        "num_zones": LARGE_SCENARIO_NUM_ZONES,
        "resource_counts": LARGE_SCENARIO_RESOURCE_COUNTS,
    },
}
CONVERGENCE_GENERATION_ALERT_THRESHOLD = 10

EVAL_DIR = Path(__file__).resolve().parent
RESULTS_DIR = EVAL_DIR / "results"
FIGURES_DIR = EVAL_DIR / "figures"

NEW_ZONE_TEMPLATE = {
    "name": "Zone EVAL",
    "population": 12000,
    "vulnerable_pct": 20.0,
    "water_level_m": 1.5,
    "rainfall_mm": 150.0,
    "infrastructure_condition": "damaged",
    "road_accessibility": "limited",
}


def ensure_dirs() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    with open(path, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def mean_std(values: list[float]) -> tuple[float, float]:
    clean = [v for v in values if v is not None and math.isfinite(v)]
    if not clean:
        return float("nan"), float("nan")
    if len(clean) == 1:
        return clean[0], 0.0
    return statistics.mean(clean), statistics.stdev(clean)


def run_routing_eval() -> list[dict]:
    rows = []
    for seed in SEEDS:
        scenario = generate_scenario(seed)
        graph = build_graph(scenario)
        node_ids = [n.id for n in scenario.nodes]
        rng = random.Random(seed * 1000 + 7)
        pairs = [tuple(rng.sample(node_ids, 2)) for _ in range(PAIRS_PER_SEED)]
        for pair_index, (start, goal) in enumerate(pairs):
            for algorithm in ALGORITHMS:
                result = search(graph, start, goal, algorithm=algorithm)
                rows.append(
                    {
                        "seed": seed,
                        "pair_index": pair_index,
                        "start": start,
                        "goal": goal,
                        "algorithm": algorithm,
                        "cost": result.cost,
                        "nodes_explored": result.nodes_explored,
                        "exec_time_ms": result.exec_time_ms,
                    }
                )
    write_csv(
        RESULTS_DIR / "routing_comparison.csv",
        ["seed", "pair_index", "start", "goal", "algorithm", "cost", "nodes_explored", "exec_time_ms"],
        rows,
    )
    return rows


def run_allocation_eval() -> tuple[list[dict], list[dict]]:
    rows = []
    convergence_rows = []
    for scale_name, params in SCALES.items():
        for seed in SEEDS:
            scenario = generate_scenario(seed, **params)
            risk_assessments = {r.zone_id: r for r in assess_scenario_risk(scenario)}
            cost_matrix = build_cost_matrix(scenario)

            greedy_result = run_greedy(scenario, cost_matrix, risk_assessments)
            ga_result = run_ga(scenario, cost_matrix, risk_assessments, GAConfig(seed=seed))

            for algorithm, result in (("genetic_algorithm", ga_result), ("greedy", greedy_result)):
                rows.append(
                    {
                        "scale": scale_name,
                        "seed": seed,
                        "algorithm": algorithm,
                        "fitness": result.fitness,
                        "population_covered": result.metrics.population_covered,
                        "average_response_time_hours": result.metrics.average_response_time_hours,
                        "resource_utilisation": result.metrics.resource_utilisation,
                        "total_travel_cost_hours": result.metrics.total_travel_cost_hours,
                        "num_zones": len(scenario.zones),
                        "num_resources": len(scenario.resources),
                    }
                )

            for stats in ga_result.history:
                convergence_rows.append(
                    {
                        "scale": scale_name,
                        "seed": seed,
                        "generation": stats.generation,
                        "best_fitness": stats.best_fitness,
                        "average_fitness": stats.average_fitness,
                    }
                )

    write_csv(
        RESULTS_DIR / "allocation_comparison.csv",
        [
            "scale",
            "seed",
            "algorithm",
            "fitness",
            "population_covered",
            "average_response_time_hours",
            "resource_utilisation",
            "total_travel_cost_hours",
            "num_zones",
            "num_resources",
        ],
        rows,
    )
    write_csv(
        RESULTS_DIR / "ga_convergence_by_scale.csv",
        ["scale", "seed", "generation", "best_fitness", "average_fitness"],
        convergence_rows,
    )
    return rows, convergence_rows


def _road_blocked_event(plan):
    if not plan.routes:
        return None
    _, route = next(iter(plan.routes.items()))
    if len(route.path) < 2:
        return None
    return RoadBlockedEvent(source=route.path[0], target=route.path[1])


def _new_zone_event(scenario):
    reserved = (
        {d.node_id for d in scenario.depots}
        | {h.node_id for h in scenario.hospitals}
        | {z.node_id for z in scenario.zones}
    )
    candidates = [n.id for n in scenario.nodes if n.id not in reserved]
    if not candidates:
        return None
    zone = Zone(id="EVAL", node_id=candidates[0], **NEW_ZONE_TEMPLATE)
    return NewZoneEvent(zone=zone)


def _resource_unavailable_event(scenario):
    if not scenario.resources:
        return None
    return ResourceUnavailableEvent(resource_id=scenario.resources[0].id)


def run_replanning_eval() -> list[dict]:
    rows = []
    for seed in SEEDS:
        for scenario_type in SCENARIO_TYPES:
            scenario = generate_scenario(seed)
            planner = Planner(ga_config=GAConfig(seed=seed))
            plan = planner.create_plan(scenario)

            if scenario_type == "no_change":
                for mode in ("static", "dynamic"):
                    rows.append(
                        {
                            "seed": seed,
                            "scenario_type": scenario_type,
                            "mode": mode,
                            "population_covered": plan.metrics.population_covered,
                            "failed_deliveries": 0,
                            "average_response_time_hours": plan.metrics.average_response_time_hours,
                            "replan_time_ms": 0.0,
                            "assignments_changed": 0,
                            "routes_changed": 0,
                            "replan_mode": "no_event",
                        }
                    )
                continue

            if scenario_type == "road_blockage":
                event = _road_blocked_event(plan)
            elif scenario_type == "new_zone":
                event = _new_zone_event(scenario)
            else:
                event = _resource_unavailable_event(scenario)

            if event is None:
                continue

            static = static_outcome(scenario, plan, event)

            start_time = time.perf_counter()
            _, diff = planner.apply_event(scenario, plan, event)
            replan_time_ms = (time.perf_counter() - start_time) * 1000.0

            replan_mode = "full_rerun" if diff.ga_rerun else "reroute_only"

            rows.append(
                {
                    "seed": seed,
                    "scenario_type": scenario_type,
                    "mode": "static",
                    "population_covered": static.metrics.population_covered,
                    "failed_deliveries": len(static.failed_resource_ids),
                    "average_response_time_hours": static.metrics.average_response_time_hours,
                    "replan_time_ms": 0.0,
                    "assignments_changed": 0,
                    "routes_changed": 0,
                    "replan_mode": "static_no_replan",
                }
            )
            rows.append(
                {
                    "seed": seed,
                    "scenario_type": scenario_type,
                    "mode": "dynamic",
                    "population_covered": diff.metrics_after.population_covered,
                    "failed_deliveries": 0,
                    "average_response_time_hours": diff.metrics_after.average_response_time_hours,
                    "replan_time_ms": replan_time_ms,
                    "assignments_changed": len(diff.assignment_changes),
                    "routes_changed": len(diff.route_changes),
                    "replan_mode": replan_mode,
                }
            )
    write_csv(
        RESULTS_DIR / "replanning_comparison.csv",
        [
            "seed",
            "scenario_type",
            "mode",
            "population_covered",
            "failed_deliveries",
            "average_response_time_hours",
            "replan_time_ms",
            "assignments_changed",
            "routes_changed",
            "replan_mode",
        ],
        rows,
    )
    return rows


def run_ga_convergence_eval():
    scenario = flood_demo()
    risk_assessments = {r.zone_id: r for r in assess_scenario_risk(scenario)}
    cost_matrix = build_cost_matrix(scenario)
    result = run_ga(scenario, cost_matrix, risk_assessments, GAConfig(seed=42))

    rows = [
        {"generation": g.generation, "best_fitness": g.best_fitness, "average_fitness": g.average_fitness}
        for g in result.history
    ]
    write_csv(RESULTS_DIR / "ga_convergence.csv", ["generation", "best_fitness", "average_fitness"], rows)
    return result, rows


def plot_routing(rows: list[dict]) -> None:
    by_algorithm = {alg: {"cost": [], "nodes_explored": [], "exec_time_ms": []} for alg in ALGORITHMS}
    for row in rows:
        by_algorithm[row["algorithm"]]["cost"].append(row["cost"])
        by_algorithm[row["algorithm"]]["nodes_explored"].append(row["nodes_explored"])
        by_algorithm[row["algorithm"]]["exec_time_ms"].append(row["exec_time_ms"])

    metrics = [("cost", "Path cost (h)"), ("nodes_explored", "Nodes explored"), ("exec_time_ms", "Exec time (ms)")]
    colors = {"astar": "#1565c0", "bfs": "#2e7d32", "dfs": "#ef6c00"}

    fig, axes = plt.subplots(1, 3, figsize=(13, 4.5))
    for ax, (key, label) in zip(axes, metrics):
        means_stds = [mean_std(by_algorithm[alg][key]) for alg in ALGORITHMS]
        means = [m for m, _ in means_stds]
        stds = [s for _, s in means_stds]
        ax.bar(ALGORITHMS, means, yerr=stds, capsize=4, color=[colors[a] for a in ALGORITHMS])
        ax.set_title(label)
        ax.set_ylabel(label)
    fig.suptitle(f"BFS vs DFS vs A* across {len(SEEDS)} seeds ({PAIRS_PER_SEED} pairs/seed)")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "routing_comparison.png", dpi=150)
    plt.close(fig)


def plot_allocation(rows: list[dict]) -> None:
    keys = ["population_covered", "average_response_time_hours", "resource_utilisation", "total_travel_cost_hours"]
    labels = ["Population covered", "Avg response (h)", "Utilisation", "Travel cost (h)"]
    algorithms = ["genetic_algorithm", "greedy"]
    display = ["GA", "Greedy"]
    scale_names = list(SCALES.keys())

    fig, axes = plt.subplots(len(scale_names), 4, figsize=(16, 4.5 * len(scale_names)))
    for row_index, scale_name in enumerate(scale_names):
        scale_rows = [r for r in rows if r["scale"] == scale_name]
        for col_index, (key, label) in enumerate(zip(keys, labels)):
            ax = axes[row_index][col_index]
            means_stds = [
                mean_std([r[key] for r in scale_rows if r["algorithm"] == alg]) for alg in algorithms
            ]
            means = [m for m, _ in means_stds]
            stds = [s for _, s in means_stds]
            ax.bar(display, means, yerr=stds, capsize=4, color=["#1565c0", "#ef6c00"])
            ax.set_title(f"{label}\n({scale_name} scale)")
    fig.suptitle(f"GA vs Greedy across {len(SEEDS)} seeds, small vs large scale")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "allocation_comparison.png", dpi=150)
    plt.close(fig)


def plot_replanning(rows: list[dict]) -> None:
    scenario_types = [s for s in SCENARIO_TYPES if s != "no_change"]
    metrics = [
        ("population_covered", "Population covered"),
        ("failed_deliveries", "Failed deliveries"),
        ("average_response_time_hours", "Avg response (h)"),
    ]
    x = list(range(len(scenario_types)))
    width = 0.35

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    for ax, (key, label) in zip(axes, metrics):
        static_means = []
        dynamic_means = []
        for scenario_type in scenario_types:
            static_vals = [r[key] for r in rows if r["scenario_type"] == scenario_type and r["mode"] == "static"]
            dynamic_vals = [r[key] for r in rows if r["scenario_type"] == scenario_type and r["mode"] == "dynamic"]
            static_means.append(mean_std(static_vals)[0])
            dynamic_means.append(mean_std(dynamic_vals)[0])
        ax.bar([i - width / 2 for i in x], static_means, width, label="static", color="#c62828")
        ax.bar([i + width / 2 for i in x], dynamic_means, width, label="dynamic", color="#1565c0")
        ax.set_xticks(x)
        ax.set_xticklabels(scenario_types, rotation=20, ha="right")
        ax.set_title(label)
        ax.legend()
    fig.suptitle(f"Static vs dynamic replanning across {len(SEEDS)} seeds")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "replanning_comparison.png", dpi=150)
    plt.close(fig)


def plot_replanning_cost(rows: list[dict]) -> None:
    scenario_types = [s for s in SCENARIO_TYPES if s != "no_change"]
    dynamic_rows = [r for r in rows if r["mode"] == "dynamic"]
    metrics = [
        ("replan_time_ms", "Replan time (ms)"),
        ("assignments_changed", "Assignments changed"),
        ("routes_changed", "Routes changed"),
    ]

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    for ax, (key, label) in zip(axes, metrics):
        means_stds = [
            mean_std([r[key] for r in dynamic_rows if r["scenario_type"] == st]) for st in scenario_types
        ]
        means = [m for m, _ in means_stds]
        stds = [s for _, s in means_stds]
        ax.bar(scenario_types, means, yerr=stds, capsize=4, color="#1565c0")
        ax.set_xticklabels(scenario_types, rotation=20, ha="right")
        ax.set_title(label)
    fig.suptitle(f"Dynamic replanning cost across {len(SEEDS)} seeds")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "replanning_cost.png", dpi=150)
    plt.close(fig)


def plot_ga_convergence(rows: list[dict]) -> None:
    generations = [r["generation"] for r in rows]
    best = [r["best_fitness"] for r in rows]
    average = [r["average_fitness"] for r in rows]

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(generations, best, label="best fitness", color="#1565c0")
    ax.plot(generations, average, label="average fitness", color="#ef6c00")
    ax.set_xlabel("Generation")
    ax.set_ylabel("Fitness")
    ax.set_title("GA convergence on flood_demo (seed=42)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "ga_convergence.png", dpi=150)
    plt.close(fig)


def plot_ga_convergence_by_scale(rows: list[dict]) -> None:
    scale_names = list(SCALES.keys())
    fig, axes = plt.subplots(1, len(scale_names), figsize=(8 * len(scale_names), 5))
    if len(scale_names) == 1:
        axes = [axes]

    for ax, scale_name in zip(axes, scale_names):
        scale_rows = [r for r in rows if r["scale"] == scale_name]
        generations = sorted({r["generation"] for r in scale_rows})
        best_mean, best_std, avg_mean, avg_std = [], [], [], []
        for generation in generations:
            at_gen = [r for r in scale_rows if r["generation"] == generation]
            bm, bs = mean_std([r["best_fitness"] for r in at_gen])
            am, a_s = mean_std([r["average_fitness"] for r in at_gen])
            best_mean.append(bm)
            best_std.append(bs)
            avg_mean.append(am)
            avg_std.append(a_s)

        best_mean_arr = best_mean
        best_upper = [m + s for m, s in zip(best_mean, best_std)]
        best_lower = [m - s for m, s in zip(best_mean, best_std)]
        avg_upper = [m + s for m, s in zip(avg_mean, avg_std)]
        avg_lower = [m - s for m, s in zip(avg_mean, avg_std)]

        ax.plot(generations, best_mean_arr, label="best fitness (mean)", color="#1565c0")
        ax.fill_between(generations, best_lower, best_upper, color="#1565c0", alpha=0.2)
        ax.plot(generations, avg_mean, label="average fitness (mean)", color="#ef6c00")
        ax.fill_between(generations, avg_lower, avg_upper, color="#ef6c00", alpha=0.2)
        ax.set_xlabel("Generation")
        ax.set_ylabel("Fitness")
        ax.set_title(f"{scale_name} scale ({len(SEEDS)} seeds, mean +/- std)")
        ax.legend()

    fig.suptitle("GA convergence by scale")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "ga_convergence_by_scale.png", dpi=150)
    plt.close(fig)


def print_routing_summary(rows: list[dict]) -> None:
    print("=" * 78)
    print(f"ROUTING: BFS vs DFS vs A*  ({len(SEEDS)} seeds x {PAIRS_PER_SEED} pairs/seed)")
    print("=" * 78)
    print(f"{'algorithm':10} {'cost mean':>10} {'cost std':>10} {'nodes mean':>11} {'nodes std':>10} {'ms mean':>9} {'ms std':>9}")
    for algorithm in ALGORITHMS:
        costs = [r["cost"] for r in rows if r["algorithm"] == algorithm]
        nodes = [r["nodes_explored"] for r in rows if r["algorithm"] == algorithm]
        times = [r["exec_time_ms"] for r in rows if r["algorithm"] == algorithm]
        unreachable = sum(1 for c in costs if not math.isfinite(c))
        cm, cs = mean_std(costs)
        nm, ns = mean_std(nodes)
        tm, ts = mean_std(times)
        print(
            f"{algorithm:10} {cm:10.4f} {cs:10.4f} {nm:11.2f} {ns:10.2f} {tm:9.4f} {ts:9.4f}"
            + (f"   ({unreachable} unreachable excluded from cost)" if unreachable else "")
        )


def print_allocation_summary(rows: list[dict]) -> None:
    print()
    print("=" * 78)
    print(f"ALLOCATION: GA vs Greedy  ({len(SEEDS)} seeds x {len(SCALES)} scales)")
    print("=" * 78)
    for scale_name in SCALES:
        scale_rows = [r for r in rows if r["scale"] == scale_name]
        print(f"-- {scale_name} scale --")
        print(
            f"{'algorithm':18} {'pop_cov mean':>12} {'pop_cov std':>11} {'resp mean':>9} {'resp std':>8} "
            f"{'util mean':>9} {'util std':>8} {'travel mean':>11} {'travel std':>10}"
        )
        for algorithm in ("genetic_algorithm", "greedy"):
            pop = [r["population_covered"] for r in scale_rows if r["algorithm"] == algorithm]
            resp = [r["average_response_time_hours"] for r in scale_rows if r["algorithm"] == algorithm]
            util = [r["resource_utilisation"] for r in scale_rows if r["algorithm"] == algorithm]
            travel = [r["total_travel_cost_hours"] for r in scale_rows if r["algorithm"] == algorithm]
            pm, ps = mean_std(pop)
            rm, rs = mean_std(resp)
            um, us = mean_std(util)
            tm, ts = mean_std(travel)
            print(f"{algorithm:18} {pm:12.1f} {ps:11.1f} {rm:9.4f} {rs:8.4f} {um:9.3f} {us:8.3f} {tm:11.3f} {ts:10.3f}")

        ga_by_seed = {r["seed"]: r["fitness"] for r in scale_rows if r["algorithm"] == "genetic_algorithm"}
        greedy_by_seed = {r["seed"]: r["fitness"] for r in scale_rows if r["algorithm"] == "greedy"}
        ga_wins = sum(1 for seed in SEEDS if ga_by_seed[seed] >= greedy_by_seed[seed])
        print(f"GA fitness >= greedy fitness in {ga_wins}/{len(SEEDS)} seeds")
        print()


def print_search_space_summary(rows: list[dict]) -> None:
    print("=" * 78)
    print("SEARCH SPACE SIZE: (num_zones + 1) ^ num_resources")
    print("=" * 78)
    for scale_name in SCALES:
        scale_rows = [r for r in rows if r["scale"] == scale_name and r["algorithm"] == "genetic_algorithm"]
        sizes = [(r["num_zones"] + 1) ** r["num_resources"] for r in scale_rows]
        zones = sorted({r["num_zones"] for r in scale_rows})
        resources = sorted({r["num_resources"] for r in scale_rows})
        print(f"{scale_name:6} zones={zones} resources={resources}")
        print(f"       min={min(sizes):.3e}  max={max(sizes):.3e}  mean={sum(sizes) / len(sizes):.3e}")
    print(f"{'flood_demo (4 zones, 5 resources)':38} = {5 ** 5:,}")
    large_zones = LARGE_SCENARIO_NUM_ZONES
    large_resources = sum(LARGE_SCENARIO_RESOURCE_COUNTS.values())
    print(
        f"{'large preset (' + str(large_zones) + ' zones, ' + str(large_resources) + ' resources)':38} "
        f"= {(large_zones + 1) ** large_resources:.3e}"
    )


def print_replanning_summary(rows: list[dict]) -> None:
    print()
    print("=" * 78)
    print(f"REPLANNING: static vs dynamic  ({len(SEEDS)} seeds x {len(SCENARIO_TYPES)} scenario types)")
    print("=" * 78)
    print(
        f"{'scenario_type':18} {'mode':8} {'pop_cov mean':>12} {'pop_cov std':>11} "
        f"{'failed mean':>11} {'failed std':>10} {'resp mean':>9} {'resp std':>8}"
    )
    for scenario_type in SCENARIO_TYPES:
        for mode in ("static", "dynamic"):
            matching = [r for r in rows if r["scenario_type"] == scenario_type and r["mode"] == mode]
            pop = [r["population_covered"] for r in matching]
            failed = [r["failed_deliveries"] for r in matching]
            resp = [r["average_response_time_hours"] for r in matching]
            pm, ps = mean_std(pop)
            fm, fs = mean_std(failed)
            rm, rs = mean_std(resp)
            print(f"{scenario_type:18} {mode:8} {pm:12.1f} {ps:11.1f} {fm:11.2f} {fs:10.2f} {rm:9.4f} {rs:8.4f}")

    print()
    print(f"{'scenario_type':18} {'time_ms mean':>12} {'time_ms std':>11} {'assign mean':>11} {'assign std':>10} "
          f"{'routes mean':>11} {'routes std':>10}")
    for scenario_type in SCENARIO_TYPES:
        dynamic_rows = [r for r in rows if r["scenario_type"] == scenario_type and r["mode"] == "dynamic"]
        tm, ts = mean_std([r["replan_time_ms"] for r in dynamic_rows])
        am, a_s = mean_std([r["assignments_changed"] for r in dynamic_rows])
        rm, rs = mean_std([r["routes_changed"] for r in dynamic_rows])
        modes = [r["replan_mode"] for r in dynamic_rows]
        full_rerun_count = modes.count("full_rerun")
        reroute_only_count = modes.count("reroute_only")
        print(
            f"{scenario_type:18} {tm:12.3f} {ts:11.3f} {am:11.2f} {a_s:10.2f} {rm:11.2f} {rs:10.2f}"
            f"   (full_rerun={full_rerun_count}, reroute_only={reroute_only_count})"
        )


def print_convergence_summary(result, rows: list[dict]) -> None:
    print()
    print("=" * 78)
    print("GA CONVERGENCE: flood_demo (seed=42)")
    print("=" * 78)
    print(f"generations run: {len(rows)}")
    print(f"final best fitness: {result.fitness:.1f}")
    first_gen = next(r["generation"] for r in rows if r["best_fitness"] == result.fitness)
    print(f"best fitness first reached at generation: {first_gen}")
    print(f"generation 0 best/average fitness: {rows[0]['best_fitness']:.1f} / {rows[0]['average_fitness']:.1f}")
    print(f"final generation average fitness: {rows[-1]['average_fitness']:.1f}")


def print_convergence_by_scale_summary(rows: list[dict]) -> list[str]:
    print()
    print("=" * 78)
    print(f"GA CONVERGENCE BY SCALE  ({len(SEEDS)} seeds per scale, default GAConfig)")
    print("=" * 78)
    warnings = []
    for scale_name in SCALES:
        scale_rows = [r for r in rows if r["scale"] == scale_name]
        first_gens = []
        final_gaps = []
        for seed in SEEDS:
            seed_rows = sorted((r for r in scale_rows if r["seed"] == seed), key=lambda r: r["generation"])
            if not seed_rows:
                continue
            final_best = seed_rows[-1]["best_fitness"]
            first_gen = next(r["generation"] for r in seed_rows if r["best_fitness"] == final_best)
            first_gens.append(first_gen)
            final_gaps.append(final_best - seed_rows[-1]["average_fitness"])
        fg_mean, fg_std = mean_std(first_gens)
        gap_mean, gap_std = mean_std(final_gaps)
        print(
            f"{scale_name:6} best-fitness-plateau generation: mean={fg_mean:.1f} std={fg_std:.1f} "
            f"min={min(first_gens)} max={max(first_gens)}"
        )
        print(f"       final best-minus-average fitness gap: mean={gap_mean:.1f} std={gap_std:.1f}")
        if fg_mean < CONVERGENCE_GENERATION_ALERT_THRESHOLD:
            warnings.append(
                f"{scale_name} scale: mean plateau generation {fg_mean:.1f} is under "
                f"{CONVERGENCE_GENERATION_ALERT_THRESHOLD} (final gap mean {gap_mean:.1f}, std {gap_std:.1f})"
            )
    return warnings


def main() -> None:
    ensure_dirs()
    print(f"Running CrisisRoute evaluation across {len(SEEDS)} seeds...")

    print("[1/4] routing: BFS vs DFS vs A*...")
    routing_rows = run_routing_eval()

    print("[2/4] allocation: GA vs greedy (small + large scale)...")
    allocation_rows, convergence_by_scale_rows = run_allocation_eval()

    print("[3/4] replanning: static vs dynamic...")
    replanning_rows = run_replanning_eval()

    print("[4/4] GA convergence on flood_demo...")
    convergence_result, convergence_rows = run_ga_convergence_eval()

    plot_routing(routing_rows)
    plot_allocation(allocation_rows)
    plot_replanning(replanning_rows)
    plot_replanning_cost(replanning_rows)
    plot_ga_convergence(convergence_rows)
    plot_ga_convergence_by_scale(convergence_by_scale_rows)

    print()
    print_routing_summary(routing_rows)
    print_allocation_summary(allocation_rows)
    print_search_space_summary(allocation_rows)
    print_replanning_summary(replanning_rows)
    print_convergence_summary(convergence_result, convergence_rows)
    warnings = print_convergence_by_scale_summary(convergence_by_scale_rows)

    print()
    print(f"CSVs written to {RESULTS_DIR}")
    print(f"Figures written to {FIGURES_DIR}")

    if warnings:
        print()
        print("=" * 78)
        print("CONVERGENCE ALERT")
        print("=" * 78)
        for warning in warnings:
            print(warning)


if __name__ == "__main__":
    main()
