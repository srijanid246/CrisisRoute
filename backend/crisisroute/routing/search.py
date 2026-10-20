import heapq
import math
import time
from collections import deque
from dataclasses import dataclass
from typing import Any

from crisisroute.scenario import Edge
from crisisroute.scenario.network import haversine_km

from .graph import RoutingGraph, other_endpoint

ALGORITHMS = ("astar", "bfs", "dfs")


@dataclass
class SearchResult:
    algorithm: str
    path: list[int]
    cost: float
    nodes_explored: int
    exec_time_ms: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "algorithm": self.algorithm,
            "path": list(self.path),
            "cost": self.cost,
            "nodes_explored": self.nodes_explored,
            "exec_time_ms": self.exec_time_ms,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SearchResult":
        return cls(
            algorithm=data["algorithm"],
            path=list(data["path"]),
            cost=data["cost"],
            nodes_explored=data["nodes_explored"],
            exec_time_ms=data["exec_time_ms"],
        )


def _reconstruct_path(parent: dict[int, int | None], goal: int) -> list[int]:
    path: list[int] = []
    node: int | None = goal
    while node is not None:
        path.append(node)
        node = parent[node]
    path.reverse()
    return path


def _bfs(graph: RoutingGraph, start: int, goal: int) -> tuple[list[int], int]:
    visited = {start}
    queue = deque([start])
    parent: dict[int, int | None] = {start: None}
    nodes_explored = 0

    while queue:
        current = queue.popleft()
        nodes_explored += 1
        if current == goal:
            return _reconstruct_path(parent, goal), nodes_explored
        for edge in graph.adjacency.get(current, []):
            if edge.blocked:
                continue
            neighbor = other_endpoint(edge, current)
            if neighbor not in visited:
                visited.add(neighbor)
                parent[neighbor] = current
                queue.append(neighbor)

    return [], nodes_explored


def _dfs(graph: RoutingGraph, start: int, goal: int) -> tuple[list[int], int]:
    visited = {start}
    stack = [start]
    parent: dict[int, int | None] = {start: None}
    nodes_explored = 0

    while stack:
        current = stack.pop()
        nodes_explored += 1
        if current == goal:
            return _reconstruct_path(parent, goal), nodes_explored
        for edge in graph.adjacency.get(current, []):
            if edge.blocked:
                continue
            neighbor = other_endpoint(edge, current)
            if neighbor not in visited:
                visited.add(neighbor)
                parent[neighbor] = current
                stack.append(neighbor)

    return [], nodes_explored


def _astar(graph: RoutingGraph, start: int, goal: int) -> tuple[list[int], float, int]:
    goal_node = graph.nodes[goal]
    max_speed = graph.max_speed_kmph if graph.max_speed_kmph > 0 else 1.0

    def heuristic(node_id: int) -> float:
        node = graph.nodes[node_id]
        distance_km = haversine_km(node.lat, node.lng, goal_node.lat, goal_node.lng)
        return distance_km / max_speed

    open_heap: list[tuple[float, float, int]] = [(heuristic(start), 0.0, start)]
    best_g = {start: 0.0}
    parent: dict[int, int | None] = {start: None}
    closed: set[int] = set()
    nodes_explored = 0

    while open_heap:
        _, g, current = heapq.heappop(open_heap)
        if current in closed:
            continue
        closed.add(current)
        nodes_explored += 1
        if current == goal:
            return _reconstruct_path(parent, goal), g, nodes_explored
        for edge in graph.adjacency.get(current, []):
            if edge.blocked:
                continue
            neighbor = other_endpoint(edge, current)
            tentative_g = g + edge.travel_time_hours()
            if tentative_g < best_g.get(neighbor, math.inf):
                best_g[neighbor] = tentative_g
                parent[neighbor] = current
                heapq.heappush(open_heap, (tentative_g + heuristic(neighbor), tentative_g, neighbor))

    return [], math.inf, nodes_explored


def _edge_between(graph: RoutingGraph, a: int, b: int) -> Edge | None:
    for edge in graph.adjacency.get(a, []):
        if edge.blocked:
            continue
        if other_endpoint(edge, a) == b:
            return edge
    return None


def path_cost_hours(graph: RoutingGraph, path: list[int]) -> float:
    if len(path) < 2:
        return 0.0
    total = 0.0
    for a, b in zip(path, path[1:]):
        edge = _edge_between(graph, a, b)
        if edge is None:
            return math.inf
        total += edge.travel_time_hours()
    return total


def search(graph: RoutingGraph, start: int, goal: int, algorithm: str = "astar") -> SearchResult:
    if algorithm not in ALGORITHMS:
        raise ValueError(f"unknown routing algorithm: {algorithm!r}")

    start_time = time.perf_counter()

    if start not in graph.nodes or goal not in graph.nodes:
        path, cost, nodes_explored = [], math.inf, 0
    elif algorithm == "astar":
        path, cost, nodes_explored = _astar(graph, start, goal)
    elif algorithm == "bfs":
        path, nodes_explored = _bfs(graph, start, goal)
        cost = path_cost_hours(graph, path) if path else math.inf
    else:
        path, nodes_explored = _dfs(graph, start, goal)
        cost = path_cost_hours(graph, path) if path else math.inf

    exec_time_ms = (time.perf_counter() - start_time) * 1000.0

    return SearchResult(
        algorithm=algorithm,
        path=path,
        cost=cost,
        nodes_explored=nodes_explored,
        exec_time_ms=exec_time_ms,
    )
