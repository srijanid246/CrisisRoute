from .messages import Message
from .movement import RouteProgress

RESCUE_TEAM_STATES = {"IDLE", "EN_ROUTE", "RESCUING"}
RESCUE_RATE_PER_TICK = 40


class RescueTeamAgent:
    def __init__(self, resource, start_node: int):
        self.agent_id = resource.id
        self.resource_type = resource.type
        self.current_node = start_node
        self.state = "IDLE"
        self.assigned_zone_id = None
        self.route = None
        self.reported_block = False
        self.idle_ticks = 0
        self.people_rescued = 0
        self.tasks_completed = 0
        self.rescue_start_tick = None
        self.completion_times: list[int] = []

    def _go_idle(self) -> None:
        self.state = "IDLE"
        self.assigned_zone_id = None
        self.route = None
        self.reported_block = False
        self.rescue_start_tick = None

    def receive(self, message: Message) -> None:
        if message.type != "ASSIGNMENT":
            return
        zone_id = message.payload.get("zone_id")
        route = message.payload.get("route")
        if zone_id is None or not route:
            self._go_idle()
            return
        self.assigned_zone_id = zone_id
        self.route = RouteProgress(route)
        self.current_node = route[0]
        self.state = "EN_ROUTE"
        self.reported_block = False

    def _finish(self, tick: int, bus) -> None:
        if self.rescue_start_tick is not None:
            self.completion_times.append(tick - self.rescue_start_tick)
        self.tasks_completed += 1
        bus.send(
            Message(
                type="TASK_COMPLETE",
                sender=self.agent_id,
                tick=tick,
                payload={"task": "zone_cleared", "zone_id": self.assigned_zone_id},
                recipient="COMMAND",
            )
        )
        self._go_idle()
        bus.send(
            Message(type="REQUEST_HELP", sender=self.agent_id, tick=tick, payload={"need": "assignment"}, recipient="COMMAND")
        )

    def step(self, tick: int, world, bus) -> None:
        for message in bus.drain(self.agent_id):
            self.receive(message)

        if self.state == "IDLE":
            self.idle_ticks += 1

        elif self.state == "EN_ROUTE":
            status = self.route.advance(world.graph, world.tick_duration_hours)
            if status == "blocked":
                if not self.reported_block:
                    bus.send(
                        Message(
                            type="ROUTE_BLOCKED",
                            sender=self.agent_id,
                            tick=tick,
                            payload={
                                "source": self.route.current_node,
                                "target": self.route.next_node,
                                "zone_id": self.assigned_zone_id,
                            },
                            recipient="COMMAND",
                        )
                    )
                    self.reported_block = True
            elif status == "arrived":
                self.current_node = self.route.current_node
                self.state = "RESCUING"
                self.rescue_start_tick = tick

        elif self.state == "RESCUING":
            remaining = world.zone_remaining_population.get(self.assigned_zone_id, 0)
            if remaining <= 0:
                self._finish(tick, bus)
                return
            rescued_now = min(RESCUE_RATE_PER_TICK, remaining)
            world.zone_remaining_population[self.assigned_zone_id] = remaining - rescued_now
            self.people_rescued += rescued_now
            if world.zone_remaining_population[self.assigned_zone_id] <= 0:
                self._finish(tick, bus)
                return

        bus.send(
            Message(
                type="STATUS_UPDATE",
                sender=self.agent_id,
                tick=tick,
                payload={"state": self.state, "current_node": self.current_node, "zone_id": self.assigned_zone_id},
                recipient="COMMAND",
            )
        )

    def position(self, world) -> tuple[float, float]:
        if self.route is not None and self.state == "EN_ROUTE":
            return self.route.interpolated_position(world.graph)
        node = world.node_by_id[self.current_node]
        return node.lat, node.lng
