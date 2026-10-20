import heapq
import math
import random

import pytest

from crisisroute.routing import ALGORITHMS, build_graph, other_endpoint, path_cost_hours, search
from crisisroute.routing.graph import RoutingGraph
from crisisroute.scenario import Edge, Node, generate_scenario


def _build_graph_with_blocked_edge() -> RoutingGraph:
    nodes = {
        0: Node(id=0, lat=13.00, lng=80.00),
        1: Node(id=1, lat=13.00, lng=80.01),
        2: Node(id=2, lat=13.00, lng=80.02),
        3: Node(id=3, lat=13.01, lng=80.01),
        4: Node(id=4, lat=14.00, lng=81.00),
    }
    edges = [
        Edge(source=0, target=1, length_km=1.0, speed_kmph=60.0, condition="good", blocked=False),
        Edge(source=1, target=2, length_km=1.0, speed_kmph=60.0, condition="good", blocked=True),
        Edge(source=0, target=3, length_km=2.0, speed_kmph=40.0, condition="good", blocked=False),
        Edge(source=3, target=2, length_km=2.0, speed_kmph=40.0, condition="good", blocked=False),
    ]
    adjacency: dict[int, list[Edge]] = {node_id: [] for node_id in nodes}
    for edge in edges:
        adjacency[edge.source].append(edge)
        adjacency[edge.target].append(edge)
    max_speed = max(edge.speed_kmph for edge in edges)
    return RoutingGraph(nodes=nodes, adjacency=adjacency, max_speed_kmph=max_speed)


def _dijkstra_reference(graph: RoutingGraph, start: int, goal: int) -> float:
    if start not in graph.nodes or goal not in graph.nodes:
        return math.inf
    distances = {start: 0.0}
    visited: set[int] = set()
    heap = [(0.0, start)]
    while heap:
        dist, current = heapq.heappop(heap)
        if current in visited:
            continue
        visited.add(current)
        if current == goal:
            return dist
        for edge in graph.adjacency.get(current, []):
            if edge.blocked:
                continue
            neighbor = other_endpoint(edge, current)
            new_dist = dist + edge.travel_time_hours()
            if new_dist < distances.get(neighbor, math.inf):
                distances[neighbor] = new_dist
                heapq.heappush(heap, (new_dist, neighbor))
    return math.inf


@pytest.mark.parametrize("algorithm", ALGORITHMS)
def test_blocked_edge_is_avoided(algorithm):
    graph = _build_graph_with_blocked_edge()
    result = search(graph, 0, 2, algorithm=algorithm)
    assert result.path
    pairs = list(zip(result.path, result.path[1:]))
    assert (1, 2) not in pairs
    assert (2, 1) not in pairs
    assert 3 in result.path


@pytest.mark.parametrize("algorithm", ALGORITHMS)
def test_unreachable_goal_returns_empty_path_and_inf_cost(algorithm):
    graph = _build_graph_with_blocked_edge()
    result = search(graph, 0, 4, algorithm=algorithm)
    assert result.path == []
    assert result.cost == math.inf


@pytest.mark.parametrize("algorithm", ALGORITHMS)
def test_start_equals_goal(algorithm):
    graph = _build_graph_with_blocked_edge()
    result = search(graph, 0, 0, algorithm=algorithm)
    assert result.path == [0]
    assert result.cost == 0.0


@pytest.mark.parametrize("algorithm", ALGORITHMS)
def test_unknown_start_or_goal_is_unreachable(algorithm):
    graph = _build_graph_with_blocked_edge()
    result = search(graph, 0, 999, algorithm=algorithm)
    assert result.path == []
    assert result.cost == math.inf


def test_search_rejects_unknown_algorithm():
    graph = _build_graph_with_blocked_edge()
    with pytest.raises(ValueError):
        search(graph, 0, 2, algorithm="dijkstra")


def test_astar_matches_dijkstra_on_random_pairs():
    rng = random.Random(123)
    for seed in (1, 2, 3, 42, 999):
        scenario = generate_scenario(seed=seed)
        graph = build_graph(scenario)
        node_ids = list(graph.nodes.keys())
        for _ in range(10):
            start, goal = rng.sample(node_ids, 2)
            astar_cost = search(graph, start, goal, algorithm="astar").cost
            dijkstra_cost = _dijkstra_reference(graph, start, goal)
            if math.isinf(dijkstra_cost):
                assert math.isinf(astar_cost)
            else:
                assert math.isclose(astar_cost, dijkstra_cost, rel_tol=1e-9, abs_tol=1e-9)


def test_astar_cost_is_never_worse_than_bfs_or_dfs():
    rng = random.Random(7)
    scenario = generate_scenario(seed=42)
    graph = build_graph(scenario)
    node_ids = list(graph.nodes.keys())
    for _ in range(15):
        start, goal = rng.sample(node_ids, 2)
        astar_cost = search(graph, start, goal, algorithm="astar").cost
        bfs_cost = search(graph, start, goal, algorithm="bfs").cost
        dfs_cost = search(graph, start, goal, algorithm="dfs").cost
        if math.isfinite(bfs_cost):
            assert astar_cost <= bfs_cost + 1e-9
        if math.isfinite(dfs_cost):
            assert astar_cost <= dfs_cost + 1e-9


def test_bfs_and_dfs_cost_matches_path_cost_hours():
    scenario = generate_scenario(seed=42)
    graph = build_graph(scenario)
    start, goal = scenario.nodes[0].id, scenario.nodes[-1].id
    for algorithm in ("bfs", "dfs"):
        result = search(graph, start, goal, algorithm=algorithm)
        assert math.isclose(result.cost, path_cost_hours(graph, result.path), rel_tol=1e-9)


def test_nodes_explored_is_positive_for_successful_search():
    scenario = generate_scenario(seed=42)
    graph = build_graph(scenario)
    start, goal = scenario.nodes[0].id, scenario.nodes[-1].id
    for algorithm in ALGORITHMS:
        result = search(graph, start, goal, algorithm=algorithm)
        assert result.nodes_explored > 0


def test_exec_time_ms_is_non_negative():
    scenario = generate_scenario(seed=42)
    graph = build_graph(scenario)
    start, goal = scenario.nodes[0].id, scenario.nodes[-1].id
    for algorithm in ALGORITHMS:
        result = search(graph, start, goal, algorithm=algorithm)
        assert result.exec_time_ms >= 0.0


def test_search_result_round_trip():
    from crisisroute.routing import SearchResult

    scenario = generate_scenario(seed=42)
    graph = build_graph(scenario)
    result = search(graph, scenario.nodes[0].id, scenario.nodes[-1].id, algorithm="astar")
    restored = SearchResult.from_dict(result.to_dict())
    assert restored == result
