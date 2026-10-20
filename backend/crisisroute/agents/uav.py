from crisisroute.scenario.network import haversine_km

from .messages import Message
from .movement import StraightLineProgress

UAV_SPEED_KMPH = 150.0
UAV_SURVEY_RADIUS_KM = 5.0


class UAVAgent:
    def __init__(
        self,
        agent_id: str,
        waypoints: list[tuple[float, float]],
        speed_kmph: float = UAV_SPEED_KMPH,
        survey_radius_km: float = UAV_SURVEY_RADIUS_KM,
    ):
        self.agent_id = agent_id
        self.resource_type = "uav"
        self.state = "PATROLLING"
        self.progress = StraightLineProgress(waypoints, speed_kmph)
        self.survey_radius_km = survey_radius_km
        self.idle_ticks = 0

    def step(self, tick: int, world, bus) -> None:
        bus.drain(self.agent_id)

        self.progress.advance(world.tick_duration_hours)
        lat, lng = self.progress.interpolated_position()

        for zone in world.scenario.zones:
            node = world.node_by_id[zone.node_id]
            if haversine_km(lat, lng, node.lat, node.lng) <= self.survey_radius_km:
                bus.send(
                    Message(
                        type="ZONE_REPORT",
                        sender=self.agent_id,
                        tick=tick,
                        payload={"zone": zone.to_dict()},
                        recipient="COMMAND",
                    )
                )

        for edge in world.scenario.edges:
            if not edge.blocked:
                continue
            source = world.node_by_id[edge.source]
            target = world.node_by_id[edge.target]
            mid_lat = (source.lat + target.lat) / 2
            mid_lng = (source.lng + target.lng) / 2
            if haversine_km(lat, lng, mid_lat, mid_lng) <= self.survey_radius_km:
                bus.send(
                    Message(
                        type="ROUTE_BLOCKED",
                        sender=self.agent_id,
                        tick=tick,
                        payload={"source": edge.source, "target": edge.target, "zone_id": None},
                        recipient="COMMAND",
                    )
                )

        bus.send(
            Message(
                type="STATUS_UPDATE",
                sender=self.agent_id,
                tick=tick,
                payload={"state": self.state, "position": [lat, lng]},
                recipient="COMMAND",
            )
        )

    def position(self, world) -> tuple[float, float]:
        return self.progress.interpolated_position()
