from crisisroute.scenario import Scenario

from .graph import RoutingGraph, build_graph
from .search import search


def build_cost_matrix(
    scenario: Scenario, graph: RoutingGraph | None = None
) -> dict[str, dict[str, float]]:
    graph = graph or build_graph(scenario)
    matrix: dict[str, dict[str, float]] = {}

    for resource in scenario.resources:
        row: dict[str, float] = {}
        for zone in scenario.zones:
            result = search(graph, resource.current_node, zone.node_id, algorithm="astar")
            row[zone.id] = result.cost
        matrix[resource.id] = row

    return matrix
