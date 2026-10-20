from crisisroute.agents.messages import MessageBus
from crisisroute.agents.uav import UAVAgent
from crisisroute.agents.world import World
from crisisroute.scenario import Depot, Edge, Node, Resource, Scenario, Zone


def _survey_scenario(edge_blocked: bool = False) -> Scenario:
    nodes = [
        Node(id=0, lat=13.00, lng=80.00),
        Node(id=1, lat=13.00, lng=80.10),
        Node(id=2, lat=20.00, lng=90.00),
    ]
    edges = [
        Edge(source=0, target=1, length_km=11.0, speed_kmph=60.0, condition="good", blocked=edge_blocked),
    ]
    zones = [
        Zone(
            id="NEAR", name="NEAR", node_id=0, population=100, vulnerable_pct=10.0,
            water_level_m=1.0, rainfall_mm=100.0, infrastructure_condition="good", road_accessibility="accessible",
        ),
        Zone(
            id="FAR", name="FAR", node_id=2, population=100, vulnerable_pct=10.0,
            water_level_m=1.0, rainfall_mm=100.0, infrastructure_condition="good", road_accessibility="accessible",
        ),
    ]
    resources = [Resource(id="R0", type="ambulance", capacity=2, current_node=0)]
    depots = [Depot(id="D0", name="D0", node_id=0)]
    return Scenario(seed=0, nodes=nodes, edges=edges, zones=zones, resources=resources, hospitals=[], depots=depots)


def test_uav_starts_at_first_waypoint():
    scenario = _survey_scenario()
    uav = UAVAgent("UAV-1", [(13.00, 80.00), (13.00, 80.10)])
    assert uav.position(None) == (13.00, 80.00)


def test_uav_moves_in_a_straight_line_ignoring_blocked_roads():
    scenario = _survey_scenario(edge_blocked=True)
    world = World(scenario)
    bus = MessageBus()
    bus.register("COMMAND")
    uav = UAVAgent("UAV-1", [(13.00, 80.00), (13.00, 80.10)], speed_kmph=200.0)
    bus.register(uav.agent_id)

    lat0, lng0 = uav.position(world)
    uav.step(0, world, bus)
    lat1, lng1 = uav.position(world)

    assert (lat0, lng0) != (lat1, lng1)
    assert uav.state == "PATROLLING"


def test_uav_reports_zone_within_survey_radius():
    scenario = _survey_scenario()
    world = World(scenario)
    bus = MessageBus()
    bus.register("COMMAND")
    uav = UAVAgent("UAV-1", [(13.00, 80.00)], survey_radius_km=5.0)
    bus.register(uav.agent_id)

    uav.step(0, world, bus)

    reports = [m for m in bus.log if m.type == "ZONE_REPORT"]
    reported_ids = {m.payload["zone"]["id"] for m in reports}
    assert "NEAR" in reported_ids
    assert "FAR" not in reported_ids


def test_uav_does_not_report_zone_outside_survey_radius():
    scenario = _survey_scenario()
    world = World(scenario)
    bus = MessageBus()
    bus.register("COMMAND")
    uav = UAVAgent("UAV-1", [(20.00, 90.00)], survey_radius_km=5.0)
    bus.register(uav.agent_id)

    uav.step(0, world, bus)

    reports = [m for m in bus.log if m.type == "ZONE_REPORT"]
    reported_ids = {m.payload["zone"]["id"] for m in reports}
    assert "NEAR" not in reported_ids


def test_uav_reports_blocked_edge_within_survey_radius():
    scenario = _survey_scenario(edge_blocked=True)
    world = World(scenario)
    bus = MessageBus()
    bus.register("COMMAND")
    uav = UAVAgent("UAV-1", [(13.00, 80.05)], survey_radius_km=10.0)
    bus.register(uav.agent_id)

    uav.step(0, world, bus)

    reports = [m for m in bus.log if m.type == "ROUTE_BLOCKED"]
    assert len(reports) == 1
    assert reports[0].payload["source"] == 0
    assert reports[0].payload["target"] == 1


def test_uav_does_not_report_open_edges():
    scenario = _survey_scenario(edge_blocked=False)
    world = World(scenario)
    bus = MessageBus()
    bus.register("COMMAND")
    uav = UAVAgent("UAV-1", [(13.00, 80.05)], survey_radius_km=10.0)
    bus.register(uav.agent_id)

    uav.step(0, world, bus)

    reports = [m for m in bus.log if m.type == "ROUTE_BLOCKED"]
    assert reports == []
