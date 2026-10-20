from crisisroute.agents.presets import flood_demo_dynamic
from crisisroute.replanning import NewZoneEvent, RoadBlockedEvent


def test_flood_demo_dynamic_has_two_hidden_events():
    scenario, hidden_events = flood_demo_dynamic()
    assert len(hidden_events) == 2


def test_flood_demo_dynamic_event_types_and_order():
    scenario, hidden_events = flood_demo_dynamic()
    ticks = [h.tick for h in hidden_events]
    assert ticks == sorted(ticks)
    assert isinstance(hidden_events[0].event, RoadBlockedEvent)
    assert isinstance(hidden_events[1].event, NewZoneEvent)


def test_flood_demo_dynamic_road_blocked_edge_exists_in_scenario():
    scenario, hidden_events = flood_demo_dynamic()
    block = hidden_events[0].event
    assert any(
        {e.source, e.target} == {block.source, block.target} for e in scenario.edges
    )


def test_flood_demo_dynamic_new_zone_targets_an_unreserved_node():
    scenario, hidden_events = flood_demo_dynamic()
    new_zone_event = hidden_events[1].event
    reserved = (
        {d.node_id for d in scenario.depots}
        | {h.node_id for h in scenario.hospitals}
        | {z.node_id for z in scenario.zones}
    )
    assert new_zone_event.zone.node_id not in reserved
    assert new_zone_event.zone.id not in {z.id for z in scenario.zones}


def test_flood_demo_dynamic_is_deterministic():
    scenario_a, events_a = flood_demo_dynamic()
    scenario_b, events_b = flood_demo_dynamic()
    assert scenario_a.to_dict() == scenario_b.to_dict()
    assert [(e.tick, e.event) for e in events_a] == [(e.tick, e.event) for e in events_b]
