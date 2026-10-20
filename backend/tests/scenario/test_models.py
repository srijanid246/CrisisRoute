from crisisroute.scenario import generate_scenario
from crisisroute.scenario.models import Scenario


def test_round_trip_preserves_content():
    original = generate_scenario(seed=7)
    restored = Scenario.from_dict(original.to_dict())
    assert restored.to_dict() == original.to_dict()


def test_round_trip_produces_equal_dataclass_instances():
    original = generate_scenario(seed=7)
    restored = Scenario.from_dict(original.to_dict())
    assert restored.nodes == original.nodes
    assert restored.edges == original.edges
    assert restored.zones == original.zones
    assert restored.resources == original.resources
    assert restored.hospitals == original.hospitals
    assert restored.depots == original.depots


def test_edge_travel_time_blocked_is_infinite():
    from crisisroute.scenario.models import Edge

    edge = Edge(source=0, target=1, length_km=10.0, speed_kmph=50.0, condition="good", blocked=True)
    assert edge.travel_time_hours() == float("inf")


def test_edge_travel_time_matches_formula():
    from crisisroute.scenario.models import Edge

    edge = Edge(source=0, target=1, length_km=10.0, speed_kmph=50.0, condition="damaged", blocked=False)
    assert edge.travel_time_hours() == (10.0 / 50.0) * 1.6
