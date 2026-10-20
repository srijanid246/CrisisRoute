import math
import random

from .models import Edge, Node

CHENNAI_LAT = 13.0827
CHENNAI_LNG = 80.2707
GRID_SPACING_DEG = 0.03
JITTER_FRACTION = 0.4
CONDITION_WEIGHTS = {"good": 0.65, "damaged": 0.25, "flooded": 0.10}
DIAGONAL_EDGE_PROBABILITY = 0.3
FLOODED_BLOCK_PROBABILITY = 0.5
DAMAGED_BLOCK_PROBABILITY = 0.08
EARTH_RADIUS_KM = 6371.0


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def _grid_dimensions(target_nodes: int) -> tuple[int, int]:
    side = round(math.sqrt(target_nodes))
    return side, side


def build_network(rng: random.Random, target_nodes: int = 80) -> tuple[list[Node], list[Edge]]:
    rows, cols = _grid_dimensions(target_nodes)
    nodes: list[Node] = []
    index_of: dict[tuple[int, int], int] = {}

    for r in range(rows):
        for c in range(cols):
            lat = CHENNAI_LAT + (r - rows / 2) * GRID_SPACING_DEG
            lng = CHENNAI_LNG + (c - cols / 2) * GRID_SPACING_DEG
            lat += rng.uniform(-JITTER_FRACTION, JITTER_FRACTION) * GRID_SPACING_DEG
            lng += rng.uniform(-JITTER_FRACTION, JITTER_FRACTION) * GRID_SPACING_DEG
            node_id = len(nodes)
            index_of[(r, c)] = node_id
            nodes.append(Node(id=node_id, lat=lat, lng=lng))

    edges: list[Edge] = []

    def add_edge(a: int, b: int) -> None:
        node_a, node_b = nodes[a], nodes[b]
        straight_km = haversine_km(node_a.lat, node_a.lng, node_b.lat, node_b.lng)
        length_km = round(straight_km * rng.uniform(1.0, 1.25), 3)
        speed_kmph = round(rng.uniform(30.0, 70.0), 1)
        condition = rng.choices(
            list(CONDITION_WEIGHTS.keys()), weights=list(CONDITION_WEIGHTS.values())
        )[0]
        if condition == "flooded":
            blocked = rng.random() < FLOODED_BLOCK_PROBABILITY
        elif condition == "damaged":
            blocked = rng.random() < DAMAGED_BLOCK_PROBABILITY
        else:
            blocked = False
        edges.append(
            Edge(
                source=a,
                target=b,
                length_km=length_km,
                speed_kmph=speed_kmph,
                condition=condition,
                blocked=blocked,
            )
        )

    for r in range(rows):
        for c in range(cols):
            a = index_of[(r, c)]
            if c + 1 < cols:
                add_edge(a, index_of[(r, c + 1)])
            if r + 1 < rows:
                add_edge(a, index_of[(r + 1, c)])
            if r + 1 < rows and c + 1 < cols and rng.random() < DIAGONAL_EDGE_PROBABILITY:
                add_edge(a, index_of[(r + 1, c + 1)])

    return nodes, edges
