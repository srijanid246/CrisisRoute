from crisisroute.agents.ambulance import AmbulanceAgent
from crisisroute.agents.messages import Message, MessageBus
from crisisroute.agents.world import World
from crisisroute.scenario import Depot, Edge, Hospital, Node, Resource, Scenario, Zone


def _chain_scenario(hospital_capacity: int = 2) -> Scenario:
    nodes = [
        Node(id=0, lat=13.00, lng=80.00),
        Node(id=1, lat=13.00, lng=80.03),
        Node(id=2, lat=13.00, lng=80.06),
        Node(id=3, lat=13.00, lng=80.09),
    ]
    edges = [
        Edge(source=0, target=1, length_km=3.0, speed_kmph=60.0, condition="good", blocked=False),
        Edge(source=1, target=2, length_km=3.0, speed_kmph=60.0, condition="good", blocked=False),
        Edge(source=2, target=3, length_km=3.0, speed_kmph=60.0, condition="good", blocked=False),
    ]
    zones = [
        Zone(
            id="Z",
            name="Zone Z",
            node_id=2,
            population=100,
            vulnerable_pct=50.0,
            water_level_m=1.0,
            rainfall_mm=100.0,
            infrastructure_condition="damaged",
            road_accessibility="limited",
        )
    ]
    hospitals = [Hospital(id="H1", name="H1", node_id=3, capacity=hospital_capacity)]
    resources = [Resource(id="AMB-1", type="ambulance", capacity=2, current_node=0)]
    depots = [Depot(id="D0", name="D0", node_id=0)]
    return Scenario(seed=0, nodes=nodes, edges=edges, zones=zones, resources=resources, hospitals=hospitals, depots=depots)


def _assign(agent, bus, tick, zone_id, route):
    bus.send(Message(type="ASSIGNMENT", sender="COMMAND", tick=tick, payload={"zone_id": zone_id, "route": route}, recipient=agent.agent_id))


def test_ambulance_starts_idle():
    scenario = _chain_scenario()
    agent = AmbulanceAgent(scenario.resources[0], scenario.resources[0].current_node)
    assert agent.state == "IDLE"


def test_ambulance_full_state_cycle_returns_to_idle():
    scenario = _chain_scenario()
    world = World(scenario)
    bus = MessageBus()
    bus.register("COMMAND")
    agent = AmbulanceAgent(scenario.resources[0], scenario.resources[0].current_node)
    bus.register(agent.agent_id)

    _assign(agent, bus, 0, "Z", [0, 1, 2])

    states_seen = set()
    for tick in range(30):
        agent.step(tick, world, bus)
        states_seen.add(agent.state)
        if tick > 0 and agent.state == "IDLE":
            break

    assert {"EN_ROUTE", "AT_ZONE", "TO_HOSPITAL", "UNLOADING", "IDLE"} <= states_seen
    assert agent.state == "IDLE"
    assert agent.patients_delivered == agent.capacity
    assert agent.tasks_completed == 1


def test_ambulance_sends_task_complete_and_request_help_on_return_to_idle():
    scenario = _chain_scenario()
    world = World(scenario)
    bus = MessageBus()
    bus.register("COMMAND")
    agent = AmbulanceAgent(scenario.resources[0], scenario.resources[0].current_node)
    bus.register(agent.agent_id)

    _assign(agent, bus, 0, "Z", [0, 1, 2])
    for tick in range(30):
        agent.step(tick, world, bus)
        if agent.state == "IDLE" and tick > 0:
            break

    sent_types = [m.type for m in bus.log if m.sender == agent.agent_id]
    assert "TASK_COMPLETE" in sent_types
    assert "REQUEST_HELP" in sent_types


def test_ambulance_waits_when_hospital_is_full():
    scenario = _chain_scenario(hospital_capacity=1)
    world = World(scenario)
    world.reserve_hospital_slot("H1")
    bus = MessageBus()
    bus.register("COMMAND")
    agent = AmbulanceAgent(scenario.resources[0], scenario.resources[0].current_node)
    bus.register(agent.agent_id)

    _assign(agent, bus, 0, "Z", [0, 1, 2])
    for tick in range(10):
        agent.step(tick, world, bus)

    assert agent.state == "TO_HOSPITAL"
    assert agent.route is None


def test_ambulance_proceeds_once_hospital_capacity_frees_up():
    scenario = _chain_scenario(hospital_capacity=1)
    world = World(scenario)
    world.reserve_hospital_slot("H1")
    bus = MessageBus()
    bus.register("COMMAND")
    agent = AmbulanceAgent(scenario.resources[0], scenario.resources[0].current_node)
    bus.register(agent.agent_id)

    _assign(agent, bus, 0, "Z", [0, 1, 2])
    for tick in range(10):
        agent.step(tick, world, bus)
    assert agent.route is None

    world.release_hospital_slot("H1")
    agent.step(10, world, bus)

    assert agent.assigned_hospital_id == "H1"
    assert agent.state in ("TO_HOSPITAL", "UNLOADING")


def test_ambulance_reports_blocked_route_exactly_once():
    scenario = _chain_scenario()
    scenario.edges[0].blocked = True
    world = World(scenario)
    bus = MessageBus()
    bus.register("COMMAND")
    agent = AmbulanceAgent(scenario.resources[0], scenario.resources[0].current_node)
    bus.register(agent.agent_id)

    _assign(agent, bus, 0, "Z", [0, 1, 2])
    for tick in range(5):
        agent.step(tick, world, bus)

    blocked_reports = [m for m in bus.log if m.sender == agent.agent_id and m.type == "ROUTE_BLOCKED"]
    assert len(blocked_reports) == 1
    assert agent.state == "EN_ROUTE"


def test_ambulance_position_interpolates_along_route():
    scenario = _chain_scenario()
    world = World(scenario)
    bus = MessageBus()
    bus.register("COMMAND")
    agent = AmbulanceAgent(scenario.resources[0], scenario.resources[0].current_node)
    bus.register(agent.agent_id)

    _assign(agent, bus, 0, "Z", [0, 1, 2])
    lat0, lng0 = agent.position(world)
    agent.step(0, world, bus)
    lat1, lng1 = agent.position(world)

    assert (lat0, lng0) != (lat1, lng1)
