from crisisroute.agents.command_center import CommandCenterAgent
from crisisroute.agents.messages import Message, MessageBus
from crisisroute.scenario.presets import flood_demo


def _bus_with_command():
    bus = MessageBus()
    bus.register("COMMAND")
    return bus


def test_command_center_builds_an_initial_plan_from_belief():
    scenario = flood_demo()
    command = CommandCenterAgent(scenario)
    assert len(command.plan.allocation.chromosome) == len(scenario.resources)
    assert command.replans_triggered == 0


def test_hidden_blocked_road_is_unknown_until_reported():
    scenario = flood_demo()
    command = CommandCenterAgent(scenario)
    bus = _bus_with_command()

    edge = next(e for e in scenario.edges if not e.blocked)

    assert command.knows_edge_blocked(edge.source, edge.target) is False

    edge.blocked = True
    assert command.knows_edge_blocked(edge.source, edge.target) is False

    bus.send(
        Message(
            type="ROUTE_BLOCKED",
            sender="AMB-1",
            tick=5,
            payload={"source": edge.source, "target": edge.target, "zone_id": "A"},
            recipient="COMMAND",
        )
    )
    command.step(5, world=None, bus=bus)

    assert command.knows_edge_blocked(edge.source, edge.target) is True
    assert command.replans_triggered == 1


def test_duplicate_route_blocked_reports_do_not_trigger_a_second_replan():
    scenario = flood_demo()
    command = CommandCenterAgent(scenario)
    bus = _bus_with_command()
    edge = next(e for e in scenario.edges if not e.blocked)
    edge.blocked = True

    for tick in (5, 6):
        bus.send(
            Message(
                type="ROUTE_BLOCKED",
                sender="AMB-1",
                tick=tick,
                payload={"source": edge.source, "target": edge.target, "zone_id": "A"},
                recipient="COMMAND",
            )
        )
        command.step(tick, world=None, bus=bus)

    assert command.replans_triggered == 1


def test_hidden_new_zone_is_unknown_until_reported():
    scenario = flood_demo()
    command = CommandCenterAgent(scenario)
    bus = _bus_with_command()

    assert command.knows_zone("E") is False

    new_zone_data = {
        "id": "E",
        "name": "Zone E",
        "node_id": scenario.nodes[50].id,
        "population": 9000,
        "vulnerable_pct": 15.0,
        "water_level_m": 1.0,
        "rainfall_mm": 90.0,
        "infrastructure_condition": "damaged",
        "road_accessibility": "limited",
    }
    bus.send(Message(type="ZONE_REPORT", sender="UAV-1", tick=10, payload={"zone": new_zone_data}, recipient="COMMAND"))
    command.step(10, world=None, bus=bus)

    assert command.knows_zone("E") is True
    assert "E" in {z.id for z in command.belief_scenario.zones}
    assert command.replans_triggered == 1


def test_request_help_from_assigned_resource_returns_an_assignment():
    scenario = flood_demo()
    command = CommandCenterAgent(scenario)
    bus = _bus_with_command()

    resource_id = scenario.resources[0].id
    index = next(i for i, r in enumerate(scenario.resources) if r.id == resource_id)
    zone_index = command.plan.allocation.chromosome[index]
    if zone_index == -1:
        return

    bus.register(resource_id)
    bus.send(Message(type="REQUEST_HELP", sender=resource_id, tick=3, payload={"need": "assignment"}, recipient="COMMAND"))
    command.step(3, world=None, bus=bus)

    assignments = bus.drain(resource_id)
    assert len(assignments) == 1
    assert assignments[0].type == "ASSIGNMENT"
    assert assignments[0].payload["zone_id"] == scenario.zones[zone_index].id


def test_task_complete_is_counted():
    scenario = flood_demo()
    command = CommandCenterAgent(scenario)
    bus = _bus_with_command()

    bus.send(Message(type="TASK_COMPLETE", sender="AMB-1", tick=2, payload={"task": "hospital_delivery"}, recipient="COMMAND"))
    command.step(2, world=None, bus=bus)

    assert command.tasks_completed == 1
