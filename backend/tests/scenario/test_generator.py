from collections import deque

from crisisroute.scenario import generate_scenario


def _connected_component_sizes(nodes, edges):
    adjacency = {node.id: set() for node in nodes}
    for edge in edges:
        adjacency[edge.source].add(edge.target)
        adjacency[edge.target].add(edge.source)

    visited = set()
    sizes = []
    for start in adjacency:
        if start in visited:
            continue
        queue = deque([start])
        visited.add(start)
        size = 0
        while queue:
            current = queue.popleft()
            size += 1
            for neighbor in adjacency[current]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        sizes.append(size)
    return sizes


def test_same_seed_produces_identical_scenario():
    first = generate_scenario(seed=42)
    second = generate_scenario(seed=42)
    assert first.to_dict() == second.to_dict()


def test_different_seeds_produce_different_scenarios():
    first = generate_scenario(seed=1)
    second = generate_scenario(seed=2)
    assert first.to_dict() != second.to_dict()


def test_graph_is_fully_connected_for_several_seeds():
    for seed in (0, 1, 42, 1234, 999999):
        scenario = generate_scenario(seed=seed)
        sizes = _connected_component_sizes(scenario.nodes, scenario.edges)
        assert sizes == [len(scenario.nodes)]


def test_node_count_is_about_eighty():
    scenario = generate_scenario(seed=42)
    assert 75 <= len(scenario.nodes) <= 85


def test_zone_count_within_spec():
    for seed in range(20):
        scenario = generate_scenario(seed=seed)
        assert 4 <= len(scenario.zones) <= 8
        assert len({zone.id for zone in scenario.zones}) == len(scenario.zones)


def test_zones_reference_valid_nodes():
    scenario = generate_scenario(seed=42)
    node_ids = {node.id for node in scenario.nodes}
    for zone in scenario.zones:
        assert zone.node_id in node_ids


def test_exactly_two_depots_and_two_hospitals():
    scenario = generate_scenario(seed=42)
    assert len(scenario.depots) == 2
    assert len(scenario.hospitals) == 2


def test_resources_start_at_a_depot_node():
    scenario = generate_scenario(seed=42)
    depot_nodes = {depot.node_id for depot in scenario.depots}
    assert len(scenario.resources) > 0
    for resource in scenario.resources:
        assert resource.current_node in depot_nodes
        assert resource.type in {"ambulance", "rescue_team", "relief_vehicle"}


def test_edge_travel_time_formula_is_consistent():
    scenario = generate_scenario(seed=42)
    for edge in scenario.edges:
        if edge.blocked:
            assert edge.travel_time_hours() == float("inf")
        else:
            expected = edge.length_km / edge.speed_kmph
            multiplier = {"good": 1.0, "damaged": 1.6, "flooded": 3.0}[edge.condition]
            assert edge.travel_time_hours() == expected * multiplier


def test_explicit_num_zones_overrides_random_range():
    scenario = generate_scenario(seed=42, num_zones=15)
    assert len(scenario.zones) == 15
    assert len({zone.id for zone in scenario.zones}) == 15


def test_explicit_resource_counts_override_random_range():
    scenario = generate_scenario(
        seed=42,
        resource_counts={"ambulance": 10, "rescue_team": 8, "relief_vehicle": 7},
    )
    by_type = {}
    for resource in scenario.resources:
        by_type[resource.type] = by_type.get(resource.type, 0) + 1
    assert by_type == {"ambulance": 10, "rescue_team": 8, "relief_vehicle": 7}


def test_partial_resource_counts_override_only_given_types():
    scenario = generate_scenario(seed=42, resource_counts={"ambulance": 9})
    by_type = {}
    for resource in scenario.resources:
        by_type[resource.type] = by_type.get(resource.type, 0) + 1
    assert by_type["ambulance"] == 9
    assert 2 <= by_type["rescue_team"] <= 5
    assert 1 <= by_type["relief_vehicle"] <= 4


def test_default_behaviour_unchanged_when_overrides_omitted():
    default_call = generate_scenario(seed=42)
    explicit_none = generate_scenario(seed=42, num_zones=None, resource_counts=None)
    assert default_call.to_dict() == explicit_none.to_dict()


def test_large_target_node_count_and_zone_count_work_together():
    scenario = generate_scenario(
        seed=1,
        target_nodes=300,
        num_zones=15,
        resource_counts={"ambulance": 10, "rescue_team": 8, "relief_vehicle": 7},
    )
    assert 280 <= len(scenario.nodes) <= 320
    assert len(scenario.zones) == 15
    assert len(scenario.resources) == 25
