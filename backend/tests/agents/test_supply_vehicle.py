from crisisroute.agents.messages import Message, MessageBus
from crisisroute.agents.supply_vehicle import SupplyVehicleAgent
from crisisroute.agents.world import World
from crisisroute.scenario import Depot, Edge, Node, Resource, Scenario, Zone


def _depot_zone_scenario() -> Scenario:
    nodes = [
        Node(id=0, lat=13.00, lng=80.00),
        Node(id=1, lat=13.00, lng=80.03),
        Node(id=2, lat=13.00, lng=80.06),
    ]
    edges = [
        Edge(source=0, target=1, length_km=3.0, speed_kmph=60.0, condition="good", blocked=False),
        Edge(source=1, target=2, length_km=3.0, speed_kmph=60.0, condition="good", blocked=False),
    ]
    zones = [
        Zone(
            id="Z", name="Z", node_id=2, population=1000, vulnerable_pct=20.0,
            water_level_m=1.0, rainfall_mm=100.0, infrastructure_condition="damaged", road_accessibility="limited",
        )
    ]
    resources = [Resource(id="RELIEF-1", type="relief_vehicle", capacity=40, current_node=0)]
    depots = [Depot(id="D0", name="D0", node_id=0)]
    return Scenario(seed=0, nodes=nodes, edges=edges, zones=zones, resources=resources, hospitals=[], depots=depots)


def _assign(agent, bus, tick, zone_id, route):
    bus.send(Message(type="ASSIGNMENT", sender="COMMAND", tick=tick, payload={"zone_id": zone_id, "route": route}, recipient=agent.agent_id))


def test_supply_vehicle_starts_idle_and_fully_loaded():
    scenario = _depot_zone_scenario()
    resource = scenario.resources[0]
    agent = SupplyVehicleAgent(resource, resource.current_node)
    assert agent.state == "IDLE"
    assert agent.units_carried == resource.capacity


def test_supply_vehicle_full_cycle_returns_to_idle_and_reloads():
    scenario = _depot_zone_scenario()
    world = World(scenario)
    bus = MessageBus()
    bus.register("COMMAND")
    resource = scenario.resources[0]
    agent = SupplyVehicleAgent(resource, resource.current_node)
    bus.register(agent.agent_id)

    _assign(agent, bus, 0, "Z", [0, 1, 2])

    states_seen = set()
    for tick in range(30):
        agent.step(tick, world, bus)
        states_seen.add(agent.state)
        if tick > 0 and agent.state == "IDLE":
            break

    assert {"EN_ROUTE_TO_ZONE", "DELIVERING", "EN_ROUTE_TO_DEPOT", "RELOADING", "IDLE"} <= states_seen
    assert agent.state == "IDLE"
    assert agent.units_carried == agent.capacity
    assert agent.current_node == agent.depot_node


def test_supply_vehicle_decrements_zone_relief_needed():
    scenario = _depot_zone_scenario()
    world = World(scenario)
    bus = MessageBus()
    bus.register("COMMAND")
    resource = scenario.resources[0]
    agent = SupplyVehicleAgent(resource, resource.current_node)
    bus.register(agent.agent_id)

    before = world.zone_relief_needed["Z"]
    _assign(agent, bus, 0, "Z", [0, 1, 2])
    for tick in range(5):
        agent.step(tick, world, bus)
        if agent.state == "DELIVERING":
            break

    agent.step(5, world, bus)
    after = world.zone_relief_needed["Z"]
    assert after < before


def test_supply_vehicle_capped_by_capacity_when_delivering():
    scenario = _depot_zone_scenario()
    scenario.zones[0].population = 100000
    world = World(scenario)
    bus = MessageBus()
    bus.register("COMMAND")
    resource = scenario.resources[0]
    agent = SupplyVehicleAgent(resource, resource.current_node)
    bus.register(agent.agent_id)

    _assign(agent, bus, 0, "Z", [0, 1, 2])
    for tick in range(10):
        agent.step(tick, world, bus)
        if agent.state == "EN_ROUTE_TO_DEPOT":
            break

    assert agent.units_carried == 0
    assert agent.units_delivered_total == agent.capacity


def test_supply_vehicle_reports_blocked_route_exactly_once():
    scenario = _depot_zone_scenario()
    scenario.edges[0].blocked = True
    world = World(scenario)
    bus = MessageBus()
    bus.register("COMMAND")
    resource = scenario.resources[0]
    agent = SupplyVehicleAgent(resource, resource.current_node)
    bus.register(agent.agent_id)

    _assign(agent, bus, 0, "Z", [0, 1, 2])
    for tick in range(5):
        agent.step(tick, world, bus)

    blocked_reports = [m for m in bus.log if m.sender == agent.agent_id and m.type == "ROUTE_BLOCKED"]
    assert len(blocked_reports) == 1
    assert agent.state == "EN_ROUTE_TO_ZONE"
