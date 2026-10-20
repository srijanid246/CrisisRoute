import copy

from crisisroute.replanning import NewZoneEvent, Planner, RoadBlockedEvent
from crisisroute.routing import build_graph, search
from crisisroute.scenario import Zone

from .messages import Message


class CommandCenterAgent:
    agent_id = "COMMAND"

    def __init__(self, true_scenario, ga_config=None):
        self.belief_scenario = copy.deepcopy(true_scenario)
        self.belief_graph = build_graph(self.belief_scenario)
        self.planner = Planner(ga_config=ga_config)
        self.plan = self.planner.create_plan(self.belief_scenario)
        self.replans_triggered = 0
        self.reports_received = 0
        self.tasks_completed = 0
        self.idle_ticks = 0
        self._known_blocked_edges = {
            (edge.source, edge.target) for edge in self.belief_scenario.edges if edge.blocked
        }
        self._known_zone_ids = {zone.id for zone in self.belief_scenario.zones}

    def _resource_index(self, resource_id: str):
        for index, resource in enumerate(self.belief_scenario.resources):
            if resource.id == resource_id:
                return index
        return None

    def _route_for(self, resource_id: str, target_node: int):
        index = self._resource_index(resource_id)
        if index is None:
            return None
        resource = self.belief_scenario.resources[index]
        result = search(self.belief_graph, resource.current_node, target_node, algorithm="astar")
        return result.path if result.path else None

    def _send_assignment(self, bus, tick: int, resource_id: str, zone_id, reason: str = "assignment") -> None:
        if zone_id is None:
            bus.send(
                Message(
                    type="ASSIGNMENT",
                    sender=self.agent_id,
                    tick=tick,
                    payload={"zone_id": None, "route": None, "reason": reason},
                    recipient=resource_id,
                )
            )
            return
        zone = next((z for z in self.belief_scenario.zones if z.id == zone_id), None)
        if zone is None:
            return
        route = self._route_for(resource_id, zone.node_id)
        if not route:
            return
        bus.send(
            Message(
                type="ASSIGNMENT",
                sender=self.agent_id,
                tick=tick,
                payload={"zone_id": zone_id, "route": route, "reason": reason},
                recipient=resource_id,
            )
        )

    def send_initial_assignments(self, bus, tick: int) -> None:
        for index, resource in enumerate(self.belief_scenario.resources):
            gene = self.plan.allocation.chromosome[index]
            if gene == -1:
                continue
            zone = self.belief_scenario.zones[gene]
            self._send_assignment(bus, tick, resource.id, zone.id, reason="initial")

    def _apply_belief_event(self, bus, tick: int, event) -> None:
        new_plan, diff = self.planner.apply_event(self.belief_scenario, self.plan, event)
        self.replans_triggered += 1
        self.plan = new_plan
        for change in diff.assignment_changes:
            self._send_assignment(bus, tick, change.resource_id, change.new_zone_id, reason="replan")

    def _handle_route_blocked(self, bus, tick: int, payload) -> None:
        source, target = payload.get("source"), payload.get("target")
        if source is None or target is None:
            return
        if (source, target) in self._known_blocked_edges or (target, source) in self._known_blocked_edges:
            return
        self._known_blocked_edges.add((source, target))
        self._apply_belief_event(bus, tick, RoadBlockedEvent(source=source, target=target))

    def _handle_zone_report(self, bus, tick: int, payload) -> None:
        zone_data = payload.get("zone")
        if zone_data is None or zone_data["id"] in self._known_zone_ids:
            return
        self._known_zone_ids.add(zone_data["id"])
        self._apply_belief_event(bus, tick, NewZoneEvent(zone=Zone.from_dict(zone_data)))

    def _handle_request_help(self, bus, tick: int, sender: str) -> None:
        index = self._resource_index(sender)
        if index is None:
            return
        gene = self.plan.allocation.chromosome[index]
        if gene == -1:
            return
        zone = self.belief_scenario.zones[gene]
        self._send_assignment(bus, tick, sender, zone.id)

    def step(self, tick: int, world, bus) -> None:
        for message in bus.drain(self.agent_id):
            self.reports_received += 1
            if message.type == "ROUTE_BLOCKED":
                self._handle_route_blocked(bus, tick, message.payload)
            elif message.type == "ZONE_REPORT":
                self._handle_zone_report(bus, tick, message.payload)
            elif message.type == "REQUEST_HELP":
                self._handle_request_help(bus, tick, message.sender)
            elif message.type == "TASK_COMPLETE":
                self.tasks_completed += 1

    def knows_edge_blocked(self, source: int, target: int) -> bool:
        return (source, target) in self._known_blocked_edges or (target, source) in self._known_blocked_edges

    def knows_zone(self, zone_id: str) -> bool:
        return zone_id in self._known_zone_ids
