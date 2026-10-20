from crisisroute.agents.messages import Message, MessageBus
from crisisroute.agents.rescue_team import RescueTeamAgent
from crisisroute.agents.world import World
from crisisroute.scenario import Depot, Edge, Node, Resource, Scenario, Zone


def _two_zone_scenario() -> Scenario:
    nodes = [
        Node(id=0, lat=13.00, lng=80.00),
        Node(id=1, lat=13.00, lng=80.03),
        Node(id=2, lat=13.00, lng=80.06),
        Node(id=3, lat=13.03, lng=80.00),
    ]
    edges = [
        Edge(source=0, target=1, length_km=3.0, speed_kmph=60.0, condition="good", blocked=False),
        Edge(source=1, target=2, length_km=3.0, speed_kmph=60.0, condition="good", blocked=False),
        Edge(source=0, target=3, length_km=3.0, speed_kmph=60.0, condition="good", blocked=False),
    ]
    zones = [
        Zone(
            id="Z1", name="Z1", node_id=2, population=100, vulnerable_pct=20.0,
            water_level_m=1.0, rainfall_mm=100.0, infrastructure_condition="damaged", road_accessibility="limited",
        ),
        Zone(
            id="Z2", name="Z2", node_id=3, population=1000, vulnerable_pct=80.0,
            water_level_m=1.0, rainfall_mm=100.0, infrastructure_condition="damaged", road_accessibility="limited",
        ),
    ]
    resources = [Resource(id="RESCUE-1", type="rescue_team", capacity=6, current_node=0)]
    depots = [Depot(id="D0", name="D0", node_id=0)]
    return Scenario(seed=0, nodes=nodes, edges=edges, zones=zones, resources=resources, hospitals=[], depots=depots)


def _assign(agent, bus, tick, zone_id, route):
    bus.send(Message(type="ASSIGNMENT", sender="COMMAND", tick=tick, payload={"zone_id": zone_id, "route": route}, recipient=agent.agent_id))


def test_rescue_team_starts_idle():
    scenario = _two_zone_scenario()
    agent = RescueTeamAgent(scenario.resources[0], scenario.resources[0].current_node)
    assert agent.state == "IDLE"


def test_rescue_team_clears_a_small_zone_and_returns_to_idle():
    scenario = _two_zone_scenario()
    world = World(scenario)
    bus = MessageBus()
    bus.register("COMMAND")
    agent = RescueTeamAgent(scenario.resources[0], scenario.resources[0].current_node)
    bus.register(agent.agent_id)

    _assign(agent, bus, 0, "Z1", [0, 1, 2])

    states_seen = set()
    for tick in range(10):
        agent.step(tick, world, bus)
        states_seen.add(agent.state)
        if tick > 0 and agent.state == "IDLE":
            break

    assert {"EN_ROUTE", "RESCUING", "IDLE"} <= states_seen
    assert agent.state == "IDLE"
    assert world.zone_remaining_population["Z1"] == 0
    assert agent.people_rescued == 20
    assert agent.tasks_completed == 1
    assert len(agent.completion_times) == 1


def test_rescue_team_decrements_zone_population_gradually():
    scenario = _two_zone_scenario()
    world = World(scenario)
    bus = MessageBus()
    bus.register("COMMAND")
    agent = RescueTeamAgent(scenario.resources[0], scenario.resources[0].current_node)
    bus.register(agent.agent_id)

    _assign(agent, bus, 0, "Z2", [0, 3])
    agent.step(0, world, bus)
    assert agent.state == "RESCUING"

    before = world.zone_remaining_population["Z2"]
    agent.step(1, world, bus)
    after = world.zone_remaining_population["Z2"]

    assert after < before
    assert after == before - min(40, before)


def test_rescue_team_can_be_reassigned_mid_rescue():
    scenario = _two_zone_scenario()
    world = World(scenario)
    bus = MessageBus()
    bus.register("COMMAND")
    agent = RescueTeamAgent(scenario.resources[0], scenario.resources[0].current_node)
    bus.register(agent.agent_id)

    _assign(agent, bus, 0, "Z2", [0, 3])
    agent.step(0, world, bus)
    assert agent.state == "RESCUING"
    assert agent.assigned_zone_id == "Z2"

    _assign(agent, bus, 1, "Z1", [3, 0, 1, 2])
    agent.step(1, world, bus)

    assert agent.assigned_zone_id == "Z1"
    assert agent.state == "EN_ROUTE"


def test_rescue_team_sends_task_complete_and_request_help():
    scenario = _two_zone_scenario()
    world = World(scenario)
    bus = MessageBus()
    bus.register("COMMAND")
    agent = RescueTeamAgent(scenario.resources[0], scenario.resources[0].current_node)
    bus.register(agent.agent_id)

    _assign(agent, bus, 0, "Z1", [0, 1, 2])
    for tick in range(10):
        agent.step(tick, world, bus)
        if agent.state == "IDLE" and tick > 0:
            break

    sent_types = [m.type for m in bus.log if m.sender == agent.agent_id]
    assert "TASK_COMPLETE" in sent_types
    assert "REQUEST_HELP" in sent_types


def test_rescue_team_reports_blocked_route_exactly_once():
    scenario = _two_zone_scenario()
    scenario.edges[0].blocked = True
    world = World(scenario)
    bus = MessageBus()
    bus.register("COMMAND")
    agent = RescueTeamAgent(scenario.resources[0], scenario.resources[0].current_node)
    bus.register(agent.agent_id)

    _assign(agent, bus, 0, "Z1", [0, 1, 2])
    for tick in range(5):
        agent.step(tick, world, bus)

    blocked_reports = [m for m in bus.log if m.sender == agent.agent_id and m.type == "ROUTE_BLOCKED"]
    assert len(blocked_reports) == 1
    assert agent.state == "EN_ROUTE"
