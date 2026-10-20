from crisisroute.replanning import NewZoneEvent, Planner, RoadBlockedEvent
from crisisroute.scenario import Zone
from crisisroute.scenario.presets import flood_demo

from .hidden_events import HiddenEvent

NEW_ZONE_ATTRS = {
    "name": "Zone E - Guindy",
    "population": 11000,
    "vulnerable_pct": 19.0,
    "water_level_m": 1.4,
    "rainfall_mm": 155.0,
    "infrastructure_condition": "damaged",
    "road_accessibility": "limited",
}

ROAD_BLOCKED_TICK = 15
NEW_ZONE_TICK = 30


def flood_demo_dynamic():
    scenario = flood_demo()

    planner = Planner()
    throwaway_plan = planner.create_plan(scenario)
    longest_resource_id, longest_route = max(
        throwaway_plan.routes.items(), key=lambda item: len(item[1].path)
    )
    blocked_source, blocked_target = longest_route.path[-2], longest_route.path[-1]

    zone_a = next(z for z in scenario.zones if z.id == "A")
    zone_a_node = next(n for n in scenario.nodes if n.id == zone_a.node_id)
    reserved = (
        {d.node_id for d in scenario.depots}
        | {h.node_id for h in scenario.hospitals}
        | {z.node_id for z in scenario.zones}
    )
    candidates = sorted(
        (n for n in scenario.nodes if n.id not in reserved),
        key=lambda n: (n.lat - zone_a_node.lat) ** 2 + (n.lng - zone_a_node.lng) ** 2,
    )
    new_zone_node_id = candidates[0].id

    hidden_events = [
        HiddenEvent(tick=ROAD_BLOCKED_TICK, event=RoadBlockedEvent(source=blocked_source, target=blocked_target)),
        HiddenEvent(
            tick=NEW_ZONE_TICK,
            event=NewZoneEvent(zone=Zone(id="E", node_id=new_zone_node_id, **NEW_ZONE_ATTRS)),
        ),
    ]
    return scenario, hidden_events
