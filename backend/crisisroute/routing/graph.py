from dataclasses import dataclass

from crisisroute.scenario import Edge, Node, Scenario


@dataclass
class RoutingGraph:
    nodes: dict[int, Node]
    adjacency: dict[int, list[Edge]]
    max_speed_kmph: float


def other_endpoint(edge: Edge, node_id: int) -> int:
    return edge.target if edge.source == node_id else edge.source


def build_graph(scenario: Scenario) -> RoutingGraph:
    nodes = {node.id: node for node in scenario.nodes}
    adjacency: dict[int, list[Edge]] = {node_id: [] for node_id in nodes}
    max_speed_kmph = 0.0

    for edge in scenario.edges:
        adjacency[edge.source].append(edge)
        adjacency[edge.target].append(edge)
        if edge.speed_kmph > max_speed_kmph:
            max_speed_kmph = edge.speed_kmph

    return RoutingGraph(nodes=nodes, adjacency=adjacency, max_speed_kmph=max_speed_kmph)
