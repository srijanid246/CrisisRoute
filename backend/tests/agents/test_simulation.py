import math

from crisisroute.agents import HiddenEvent, Simulation
from crisisroute.agents.presets import flood_demo_dynamic
from crisisroute.replanning import RoadBlockedEvent
from crisisroute.scenario.presets import flood_demo


def test_simulation_run_returns_one_snapshot_per_tick():
    scenario = flood_demo()
    sim = Simulation(num_uavs=1)
    result = sim.run(scenario, max_ticks=10)
    assert len(result.snapshots) == 10
    assert [s.tick for s in result.snapshots] == list(range(10))


def test_snapshot_contains_every_agent():
    scenario = flood_demo()
    sim = Simulation(num_uavs=2)
    result = sim.run(scenario, max_ticks=3)
    snapshot = result.snapshots[0]
    expected_ids = {r.id for r in scenario.resources} | {"UAV-1", "UAV-2"}
    assert set(snapshot.agent_positions.keys()) == expected_ids
    assert set(snapshot.agent_states.keys()) == expected_ids


def test_zone_population_decreases_over_time():
    scenario = flood_demo()
    sim = Simulation(num_uavs=1)
    result = sim.run(scenario, max_ticks=40)
    first = result.snapshots[0].zone_remaining_population
    last = result.snapshots[-1].zone_remaining_population
    assert sum(last.values()) < sum(first.values())


def test_hospital_occupancy_is_tracked_in_snapshots():
    scenario = flood_demo()
    sim = Simulation(num_uavs=1)
    result = sim.run(scenario, max_ticks=40)
    for snapshot in result.snapshots:
        for hospital in scenario.hospitals:
            assert snapshot.hospital_occupancy[hospital.id] >= 0
            assert snapshot.hospital_occupancy[hospital.id] <= hospital.capacity


def test_messages_are_logged_every_tick():
    scenario = flood_demo()
    sim = Simulation(num_uavs=1)
    result = sim.run(scenario, max_ticks=5)
    assert all(len(snapshot.messages) > 0 for snapshot in result.snapshots)


def test_hidden_road_block_stays_hidden_from_command_center_until_discovered():
    scenario, hidden_events = flood_demo_dynamic()
    block_event = next(h for h in hidden_events if isinstance(h.event, RoadBlockedEvent))

    sim = Simulation(hidden_events=hidden_events, num_uavs=1)
    sim._setup(scenario)

    for _ in range(block_event.tick):
        sim.step()
    assert sim.command_center.knows_edge_blocked(block_event.event.source, block_event.event.target) is False

    discovered = False
    for _ in range(100):
        sim.step()
        if sim.command_center.knows_edge_blocked(block_event.event.source, block_event.event.target):
            discovered = True
            break
    assert discovered
    assert sim.command_center.replans_triggered >= 1


def test_simulation_metrics_are_well_formed():
    scenario = flood_demo()
    sim = Simulation(num_uavs=1)
    result = sim.run(scenario, max_ticks=60)
    metrics = result.metrics
    assert metrics.people_rescued >= 0
    assert metrics.people_delivered_to_hospital >= 0
    assert metrics.tasks_completed >= 0
    assert metrics.replans_triggered >= 0
    assert set(metrics.idle_ticks_per_agent.keys()) == {r.id for r in scenario.resources} | {"UAV-1"}


def test_simulation_is_deterministic_for_a_fixed_scenario_and_config():
    scenario_a = flood_demo()
    scenario_b = flood_demo()
    sim_a = Simulation(num_uavs=1)
    sim_b = Simulation(num_uavs=1)
    result_a = sim_a.run(scenario_a, max_ticks=20)
    result_b = sim_b.run(scenario_b, max_ticks=20)
    assert [s.agent_states for s in result_a.snapshots] == [s.agent_states for s in result_b.snapshots]
    assert [s.zone_remaining_population for s in result_a.snapshots] == [s.zone_remaining_population for s in result_b.snapshots]


def test_agents_never_mutate_each_other_directly():
    scenario = flood_demo()
    sim = Simulation(num_uavs=1)
    sim._setup(scenario)
    resource_id = scenario.resources[0].id
    agent = sim.ground_agents[resource_id]
    assert not hasattr(agent, "command_center")
    assert not any(
        isinstance(getattr(agent, attribute_name, None), type(sim.command_center))
        for attribute_name in vars(agent)
    )
