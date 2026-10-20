from .messages import Message
from .movement import RouteProgress

AMBULANCE_STATES = {"IDLE", "EN_ROUTE", "AT_ZONE", "TO_HOSPITAL", "UNLOADING"}
LOADING_TICKS = 2
UNLOADING_TICKS = 2


class AmbulanceAgent:
    def __init__(self, resource, start_node: int):
        self.agent_id = resource.id
        self.resource_type = resource.type
        self.capacity = resource.capacity
        self.current_node = start_node
        self.state = "IDLE"
        self.assigned_zone_id = None
        self.assigned_hospital_id = None
        self.route = None
        self.loading_remaining = 0
        self.unloading_remaining = 0
        self.reported_block = False
        self.idle_ticks = 0
        self.patients_delivered = 0
        self.tasks_completed = 0

    def _go_idle(self) -> None:
        self.state = "IDLE"
        self.assigned_zone_id = None
        self.assigned_hospital_id = None
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
        self.state = "EN_ROUTE"
        self.reported_block = False

    def _report_block(self, tick: int, bus, zone_id) -> None:
        if self.reported_block:
            return
        bus.send(
            Message(
                type="ROUTE_BLOCKED",
                sender=self.agent_id,
                tick=tick,
                payload={"source": self.route.current_node, "target": self.route.next_node, "zone_id": zone_id},
                recipient="COMMAND",
            )
        )
        self.reported_block = True

    def step(self, tick: int, world, bus) -> None:
        for message in bus.drain(self.agent_id):
            self.receive(message)

        if self.state == "IDLE":
            self.idle_ticks += 1

        elif self.state == "EN_ROUTE":
            status = self.route.advance(world.graph, world.tick_duration_hours)
            if status == "blocked":
                self._report_block(tick, bus, self.assigned_zone_id)
            elif status == "arrived":
                self.current_node = self.route.current_node
                self.state = "AT_ZONE"
                self.loading_remaining = LOADING_TICKS

        elif self.state == "AT_ZONE":
            self.loading_remaining -= 1
            if self.loading_remaining <= 0:
                self.state = "TO_HOSPITAL"
                self.route = None

        elif self.state == "TO_HOSPITAL":
            if self.route is None:
                nearest = world.nearest_available_hospital(self.current_node)
                if nearest is None:
                    bus.send(
                        Message(
                            type="STATUS_UPDATE",
                            sender=self.agent_id,
                            tick=tick,
                            payload={"state": self.state, "current_node": self.current_node, "waiting_for": "hospital_capacity"},
                            recipient="COMMAND",
                        )
                    )
                    return
                hospital_id, path, _ = nearest
                self.assigned_hospital_id = hospital_id
                world.reserve_hospital_slot(hospital_id)
                self.route = RouteProgress(path)
                self.reported_block = False
            status = self.route.advance(world.graph, world.tick_duration_hours)
            if status == "blocked":
                self._report_block(tick, bus, None)
                world.release_hospital_slot(self.assigned_hospital_id)
                self.assigned_hospital_id = None
                self.route = None
            elif status == "arrived":
                self.current_node = self.route.current_node
                self.state = "UNLOADING"
                self.unloading_remaining = UNLOADING_TICKS

        elif self.state == "UNLOADING":
            self.unloading_remaining -= 1
            if self.unloading_remaining <= 0:
                world.release_hospital_slot(self.assigned_hospital_id)
                self.patients_delivered += self.capacity
                self.tasks_completed += 1
                bus.send(
                    Message(
                        type="TASK_COMPLETE",
                        sender=self.agent_id,
                        tick=tick,
                        payload={"task": "hospital_delivery", "patients": self.capacity},
                        recipient="COMMAND",
                    )
                )
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
        if self.route is not None and self.state in ("EN_ROUTE", "TO_HOSPITAL"):
            return self.route.interpolated_position(world.graph)
        node = world.node_by_id[self.current_node]
        return node.lat, node.lng
