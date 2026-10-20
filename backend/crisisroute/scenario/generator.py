import random

from .models import Depot, Hospital, Resource, Scenario, Zone
from .network import build_network

ZONE_LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
INFRASTRUCTURE_LEVELS = ["good", "damaged", "critical"]
INFRASTRUCTURE_WEIGHTS = [0.4, 0.4, 0.2]
ACCESSIBILITY_LEVELS = ["accessible", "limited", "cutoff"]
ACCESSIBILITY_WEIGHTS = [0.5, 0.35, 0.15]
RESOURCE_CAPACITY = {"ambulance": 2, "rescue_team": 6, "relief_vehicle": 40}
RESOURCE_PREFIX = {"ambulance": "AMB", "rescue_team": "RESCUE", "relief_vehicle": "RELIEF"}
RESOURCE_COUNT_RANGE = {
    "ambulance": (2, 5),
    "rescue_team": (2, 5),
    "relief_vehicle": (1, 4),
}


def generate_scenario(
    seed: int,
    target_nodes: int = 80,
    num_zones: int | None = None,
    resource_counts: dict[str, int] | None = None,
) -> Scenario:
    rng = random.Random(seed)
    nodes, edges = build_network(rng, target_nodes)
    node_ids = [node.id for node in nodes]

    if num_zones is None:
        num_zones = rng.randint(4, 8)
    zone_nodes = rng.sample(node_ids, num_zones)
    remaining = [n for n in node_ids if n not in zone_nodes]
    depot_nodes = rng.sample(remaining, 2)
    remaining = [n for n in remaining if n not in depot_nodes]
    hospital_nodes = rng.sample(remaining, 2)

    zones = []
    for i, node_id in enumerate(zone_nodes):
        letter = ZONE_LETTERS[i]
        zones.append(
            Zone(
                id=letter,
                name=f"Zone {letter}",
                node_id=node_id,
                population=rng.randint(1000, 20000),
                vulnerable_pct=round(rng.uniform(5.0, 35.0), 1),
                water_level_m=round(rng.uniform(0.2, 2.5), 2),
                rainfall_mm=round(rng.uniform(40.0, 220.0), 1),
                infrastructure_condition=rng.choices(
                    INFRASTRUCTURE_LEVELS, weights=INFRASTRUCTURE_WEIGHTS
                )[0],
                road_accessibility=rng.choices(
                    ACCESSIBILITY_LEVELS, weights=ACCESSIBILITY_WEIGHTS
                )[0],
            )
        )

    depots = [
        Depot(id=f"DEPOT-{i + 1}", name=f"Depot {i + 1}", node_id=node_id)
        for i, node_id in enumerate(depot_nodes)
    ]
    hospitals = [
        Hospital(
            id=f"HOSPITAL-{i + 1}",
            name=f"Hospital {i + 1}",
            node_id=node_id,
            capacity=rng.randint(60, 200),
        )
        for i, node_id in enumerate(hospital_nodes)
    ]

    resources = []
    for resource_type, (low, high) in RESOURCE_COUNT_RANGE.items():
        if resource_counts is not None and resource_type in resource_counts:
            count = resource_counts[resource_type]
        else:
            count = rng.randint(low, high)
        prefix = RESOURCE_PREFIX[resource_type]
        for i in range(count):
            depot = depots[i % len(depots)]
            resources.append(
                Resource(
                    id=f"{prefix}-{i + 1}",
                    type=resource_type,
                    capacity=RESOURCE_CAPACITY[resource_type],
                    current_node=depot.node_id,
                )
            )

    return Scenario(
        seed=seed,
        nodes=nodes,
        edges=edges,
        zones=zones,
        resources=resources,
        hospitals=hospitals,
        depots=depots,
    )
