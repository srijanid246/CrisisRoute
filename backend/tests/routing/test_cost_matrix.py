import math

from crisisroute.routing import build_cost_matrix, build_graph, search
from crisisroute.scenario.presets import flood_demo


def test_cost_matrix_covers_every_resource_and_zone():
    scenario = flood_demo()
    matrix = build_cost_matrix(scenario)
    assert set(matrix.keys()) == {r.id for r in scenario.resources}
    for resource_id, row in matrix.items():
        assert set(row.keys()) == {z.id for z in scenario.zones}


def test_cost_matrix_is_finite_on_connected_flood_demo():
    scenario = flood_demo()
    matrix = build_cost_matrix(scenario)
    for row in matrix.values():
        for cost in row.values():
            assert math.isfinite(cost)
            assert cost >= 0.0


def test_cost_matrix_matches_direct_astar_search():
    scenario = flood_demo()
    graph = build_graph(scenario)
    matrix = build_cost_matrix(scenario, graph=graph)
    resource = scenario.resources[0]
    zone = scenario.zones[0]
    expected = search(graph, resource.current_node, zone.node_id, algorithm="astar").cost
    assert matrix[resource.id][zone.id] == expected
