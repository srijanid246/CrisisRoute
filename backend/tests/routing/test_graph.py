from crisisroute.routing import build_graph, other_endpoint
from crisisroute.scenario import generate_scenario


def test_every_edge_appears_in_both_endpoints_adjacency():
    scenario = generate_scenario(seed=42)
    graph = build_graph(scenario)
    for edge in scenario.edges:
        assert edge in graph.adjacency[edge.source]
        assert edge in graph.adjacency[edge.target]


def test_max_speed_kmph_matches_fastest_edge():
    scenario = generate_scenario(seed=42)
    graph = build_graph(scenario)
    assert graph.max_speed_kmph == max(edge.speed_kmph for edge in scenario.edges)


def test_other_endpoint_returns_the_opposite_node():
    scenario = generate_scenario(seed=42)
    edge = scenario.edges[0]
    assert other_endpoint(edge, edge.source) == edge.target
    assert other_endpoint(edge, edge.target) == edge.source


def test_every_node_has_an_adjacency_entry():
    scenario = generate_scenario(seed=42)
    graph = build_graph(scenario)
    for node in scenario.nodes:
        assert node.id in graph.adjacency
