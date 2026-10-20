from collections import Counter

from crisisroute.scenario import load_preset
from crisisroute.scenario.presets import flood_demo, large_scenario


def test_flood_demo_is_deterministic():
    first = flood_demo()
    second = flood_demo()
    assert first.to_dict() == second.to_dict()


def test_flood_demo_has_zones_a_through_d():
    scenario = flood_demo()
    assert [zone.id for zone in scenario.zones] == ["A", "B", "C", "D"]


def test_flood_demo_zone_nodes_are_distinct_and_valid():
    scenario = flood_demo()
    node_ids = {node.id for node in scenario.nodes}
    zone_nodes = [zone.node_id for zone in scenario.zones]
    assert len(set(zone_nodes)) == 4
    for node_id in zone_nodes:
        assert node_id in node_ids


def test_flood_demo_resource_counts():
    scenario = flood_demo()
    by_type = {}
    for resource in scenario.resources:
        by_type[resource.type] = by_type.get(resource.type, 0) + 1
    assert by_type == {"ambulance": 2, "rescue_team": 2, "relief_vehicle": 1}


def test_flood_demo_resources_start_at_a_depot():
    scenario = flood_demo()
    depot_nodes = {depot.node_id for depot in scenario.depots}
    for resource in scenario.resources:
        assert resource.current_node in depot_nodes


def test_flood_demo_has_two_hospitals():
    scenario = flood_demo()
    assert len(scenario.hospitals) == 2
    assert {h.id for h in scenario.hospitals} == {"HOSPITAL-1", "HOSPITAL-2"}


def test_load_preset_returns_flood_demo():
    via_registry = load_preset("flood_demo")
    direct = flood_demo()
    assert via_registry.to_dict() == direct.to_dict()


def test_load_preset_rejects_unknown_name():
    import pytest

    with pytest.raises(ValueError):
        load_preset("not_a_real_preset")


def test_large_scenario_is_deterministic():
    first = large_scenario()
    second = large_scenario()
    assert first.to_dict() == second.to_dict()


def test_large_scenario_has_about_300_nodes():
    scenario = large_scenario()
    assert 280 <= len(scenario.nodes) <= 320


def test_large_scenario_has_fifteen_zones():
    scenario = large_scenario()
    assert len(scenario.zones) == 15
    assert len({z.id for z in scenario.zones}) == 15


def test_large_scenario_has_twenty_five_resources():
    scenario = large_scenario()
    assert len(scenario.resources) == 25
    assert Counter(r.type for r in scenario.resources) == {
        "ambulance": 10,
        "rescue_team": 8,
        "relief_vehicle": 7,
    }


def test_large_scenario_zone_and_depot_nodes_are_valid_and_distinct():
    scenario = large_scenario()
    node_ids = {n.id for n in scenario.nodes}
    zone_nodes = {z.node_id for z in scenario.zones}
    depot_nodes = {d.node_id for d in scenario.depots}
    hospital_nodes = {h.node_id for h in scenario.hospitals}
    assert zone_nodes <= node_ids
    assert depot_nodes <= node_ids
    assert hospital_nodes <= node_ids
    assert zone_nodes.isdisjoint(depot_nodes)
    assert zone_nodes.isdisjoint(hospital_nodes)
    assert depot_nodes.isdisjoint(hospital_nodes)


def test_load_preset_returns_large_scenario():
    via_registry = load_preset("large")
    direct = large_scenario()
    assert via_registry.to_dict() == direct.to_dict()
