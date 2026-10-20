from crisisroute.routing import search

from .messages import Message
from .movement import RouteProgress

SUPPLY_VEHICLE_STATES = {"IDLE", "EN_ROUTE_TO_ZONE", "DELIVERING", "EN_ROUTE_TO_DEPOT", "RELOADING"}
DELIVERY_RATE_PER_TICK = 10
RELOAD_TICKS = 2


class SupplyVehicleAgent:
    def __init__(self, resource, start_node: int):
        self.agent_id = resource.id
        self.resource_type = resource.type
        self.capacity = resource.capacity
        self.depot_node = start_node
        self.current_node = start_node
        self.state = "IDLE"
        self.assigned_zone_id = None
        self.route = None
        self.reported_block = False
        self.idle_ticks = 0
        self.units_carried = resource.capacity
        self.units_delivered_total = 0
        self.tasks_completed = 0
        self.reload_remaining = 0

    def _go_idle(self) -> None:
        self.state = "IDLE"
        self.assigned_zone_id = None
        self.route = None
        self.reported_block = False

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
        self.state = "EN_ROUTE_TO_ZONE"
        self.reported_block = False

    def _route_to_depot(self, world) -> list[int]:
        result = search(world.graph, self.current_node, self.depot_node, algorithm="astar")
        return result.path if result.path else [self.current_node]

    def step(self, tick: int, world, bus) -> None:
        for message in bus.drain(self.agent_id):
            self.receive(message)

        if self.state == "IDLE":
            self.idle_ticks += 1

        elif self.state == "EN_ROUTE_TO_ZONE":
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
                self.state = "DELIVERING"

        elif self.state == "DELIVERING":
            needed = world.zone_relief_needed.get(self.assigned_zone_id, 0)
            deliverable = min(DELIVERY_RATE_PER_TICK, needed, self.units_carried)
            if deliverable > 0:
                world.zone_relief_needed[self.assigned_zone_id] = needed - deliverable
                self.units_carried -= deliverable
                self.units_delivered_total += deliverable
            if world.zone_relief_needed.get(self.assigned_zone_id, 0) <= 0 or self.units_carried <= 0:
                self.tasks_completed += 1
                bus.send(
                    Message(
                        type="TASK_COMPLETE",
                        sender=self.agent_id,
                        tick=tick,
                        payload={"task": "relief_delivered", "zone_id": self.assigned_zone_id},
                        recipient="COMMAND",
                    )
                )
                self.route = RouteProgress(self._route_to_depot(world))
                self.state = "EN_ROUTE_TO_DEPOT"
                self.reported_block = False

        elif self.state == "EN_ROUTE_TO_DEPOT":
            status = self.route.advance(world.graph, world.tick_duration_hours)
            if status == "blocked":
                if not self.reported_block:
                    bus.send(
                        Message(
                            type="ROUTE_BLOCKED",
                            sender=self.agent_id,
                            tick=tick,
                            payload={"source": self.route.current_node, "target": self.route.next_node, "zone_id": None},
                            recipient="COMMAND",
                        )
                    )
                    self.reported_block = True
                self.route = RouteProgress(self._route_to_depot(world))
            elif status == "arrived":
                self.current_node = self.route.current_node
                self.state = "RELOADING"
                self.reload_remaining = RELOAD_TICKS

        elif self.state == "RELOADING":
            self.reload_remaining -= 1
            if self.reload_remaining <= 0:
                self.units_carried = self.capacity
                self._go_idle()
                bus.send(
                    Message(
                        type="REQUEST_HELP",
                        sender=self.agent_id,
                        tick=tick,
                        payload={"need": "assignment"},
                        recipient="COMMAND",
                    )
                )

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
        if self.route is not None and self.state in ("EN_ROUTE_TO_ZONE", "EN_ROUTE_TO_DEPOT"):
            return self.route.interpolated_position(world.graph)
        node = world.node_by_id[self.current_node]
        return node.lat, node.lng
