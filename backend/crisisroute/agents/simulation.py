from dataclasses import dataclass
from typing import Any

from crisisroute.replanning.events import apply_physical_effect

from .ambulance import AmbulanceAgent
from .command_center import CommandCenterAgent
from .messages import Message, MessageBus
from .rescue_team import RescueTeamAgent
from .supply_vehicle import SupplyVehicleAgent
from .uav import UAVAgent
from .world import World

AGENT_CLASS_BY_RESOURCE_TYPE = {
    "ambulance": AmbulanceAgent,
    "rescue_team": RescueTeamAgent,
    "relief_vehicle": SupplyVehicleAgent,
}


@dataclass
class TickSnapshot:
    tick: int
    agent_positions: dict[str, tuple[float, float]]
    agent_states: dict[str, str]
    zone_remaining_population: dict[str, int]
    hospital_occupancy: dict[str, int]
    messages: list[Message]

    def to_dict(self) -> dict[str, Any]:
        return {
            "tick": self.tick,
            "agent_positions": {k: list(v) for k, v in self.agent_positions.items()},
            "agent_states": dict(self.agent_states),
            "zone_remaining_population": dict(self.zone_remaining_population),
            "hospital_occupancy": dict(self.hospital_occupancy),
            "messages": [m.to_dict() for m in self.messages],
        }


@dataclass
class SimulationMetrics:
    people_rescued: int
    people_delivered_to_hospital: int
    average_rescue_completion_time_ticks: float
    tasks_completed: int
    replans_triggered: int
    idle_ticks_per_agent: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "people_rescued": self.people_rescued,
            "people_delivered_to_hospital": self.people_delivered_to_hospital,
            "average_rescue_completion_time_ticks": self.average_rescue_completion_time_ticks,
            "tasks_completed": self.tasks_completed,
            "replans_triggered": self.replans_triggered,
            "idle_ticks_per_agent": dict(self.idle_ticks_per_agent),
        }


@dataclass
class SimulationResult:
    snapshots: list[TickSnapshot]
    metrics: SimulationMetrics


class Simulation:
    def __init__(self, hidden_events=None, ga_config=None, num_uavs: int = 1, uav_survey_radius_km: float | None = None):
        self.hidden_events = sorted(hidden_events or [], key=lambda h: h.tick)
        self.ga_config = ga_config
        self.num_uavs = num_uavs
        self.uav_survey_radius_km = uav_survey_radius_km
        self.world: World | None = None
        self.bus: MessageBus | None = None
        self.command_center: CommandCenterAgent | None = None
        self.ground_agents: dict[str, Any] = {}
        self.uav_agents: dict[str, UAVAgent] = {}
        self.snapshots: list[TickSnapshot] = []
        self.tick = 0
        self._pending_hidden_events: list = []

    def _setup(self, scenario) -> None:
        self.world = World(scenario)
        self.bus = MessageBus()
        self.bus.register("COMMAND")
        self.command_center = CommandCenterAgent(scenario, ga_config=self.ga_config)

        self.ground_agents = {}
        for resource in scenario.resources:
            agent_class = AGENT_CLASS_BY_RESOURCE_TYPE[resource.type]
            agent = agent_class(resource, resource.current_node)
            self.ground_agents[agent.agent_id] = agent
            self.bus.register(agent.agent_id)

        waypoints = [(self.world.node_by_id[z.node_id].lat, self.world.node_by_id[z.node_id].lng) for z in scenario.zones]
        if not waypoints:
            waypoints = [(self.world.node_by_id[d.node_id].lat, self.world.node_by_id[d.node_id].lng) for d in scenario.depots]

        self.uav_agents = {}
        for i in range(self.num_uavs):
            uav_id = f"UAV-{i + 1}"
            kwargs = {}
            if self.uav_survey_radius_km is not None:
                kwargs["survey_radius_km"] = self.uav_survey_radius_km
            agent = UAVAgent(uav_id, waypoints, **kwargs)
            self.uav_agents[uav_id] = agent
            self.bus.register(uav_id)

        self.snapshots = []
        self.tick = 0
        self._pending_hidden_events = list(self.hidden_events)

        self.command_center.send_initial_assignments(self.bus, self.tick)

    def step(self) -> TickSnapshot:
        tick = self.tick

        while self._pending_hidden_events and self._pending_hidden_events[0].tick == tick:
            hidden_event = self._pending_hidden_events.pop(0)
            apply_physical_effect(self.world.scenario, hidden_event.event)
            if hasattr(hidden_event.event, "zone"):
                self.world.register_zone(hidden_event.event.zone)

        for agent in self.ground_agents.values():
            agent.step(tick, self.world, self.bus)
        for agent in self.uav_agents.values():
            agent.step(tick, self.world, self.bus)
        self.command_center.step(tick, self.world, self.bus)

        agent_positions: dict[str, tuple[float, float]] = {}
        agent_states: dict[str, str] = {}
        for agent in list(self.ground_agents.values()) + list(self.uav_agents.values()):
            agent_positions[agent.agent_id] = agent.position(self.world)
            agent_states[agent.agent_id] = agent.state

        snapshot = TickSnapshot(
            tick=tick,
            agent_positions=agent_positions,
            agent_states=agent_states,
            zone_remaining_population=dict(self.world.zone_remaining_population),
            hospital_occupancy=dict(self.world.hospital_occupancy),
            messages=self.bus.log_for_tick(tick),
        )
        self.snapshots.append(snapshot)
        self.tick += 1
        return snapshot

    def run(self, scenario, max_ticks: int) -> SimulationResult:
        self._setup(scenario)
        for _ in range(max_ticks):
            self.step()
        return SimulationResult(snapshots=list(self.snapshots), metrics=self._compute_metrics())

    def _compute_metrics(self) -> SimulationMetrics:
        people_rescued = sum(getattr(a, "people_rescued", 0) for a in self.ground_agents.values())
        people_delivered = sum(getattr(a, "patients_delivered", 0) for a in self.ground_agents.values())

        completion_times: list[int] = []
        for agent in self.ground_agents.values():
            completion_times.extend(getattr(agent, "completion_times", []))
        average_completion = sum(completion_times) / len(completion_times) if completion_times else 0.0

        tasks_completed = sum(getattr(a, "tasks_completed", 0) for a in self.ground_agents.values())

        idle_ticks = {agent_id: agent.idle_ticks for agent_id, agent in self.ground_agents.items()}
        idle_ticks.update({agent_id: agent.idle_ticks for agent_id, agent in self.uav_agents.items()})

        return SimulationMetrics(
            people_rescued=people_rescued,
            people_delivered_to_hospital=people_delivered,
            average_rescue_completion_time_ticks=average_completion,
            tasks_completed=tasks_completed,
            replans_triggered=self.command_center.replans_triggered,
            idle_ticks_per_agent=idle_ticks,
        )
