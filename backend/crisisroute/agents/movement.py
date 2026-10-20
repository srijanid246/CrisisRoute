from crisisroute.routing import other_endpoint
from crisisroute.scenario.network import haversine_km


def edge_between(graph, a: int, b: int):
    for edge in graph.adjacency.get(a, []):
        if other_endpoint(edge, a) == b:
            return edge
    return None


class RouteProgress:
    def __init__(self, path: list[int]):
        self.path = list(path)
        self.index = 0
        self.edge_hours_elapsed = 0.0

    @property
    def finished(self) -> bool:
        return self.index >= len(self.path) - 1

    @property
    def current_node(self) -> int:
        return self.path[self.index]

    @property
    def next_node(self) -> int | None:
        if self.finished:
            return None
        return self.path[self.index + 1]

    def advance(self, graph, hours: float) -> str:
        if self.finished:
            return "arrived"
        edge = edge_between(graph, self.current_node, self.next_node)
        if edge is None:
            return "no_edge"
        if edge.blocked:
            return "blocked"
        self.edge_hours_elapsed += hours
        travel_time = edge.travel_time_hours()
        if self.edge_hours_elapsed >= travel_time:
            self.edge_hours_elapsed = 0.0
            self.index += 1
            return "arrived" if self.finished else "advanced"
        return "moving"

    def interpolated_position(self, graph) -> tuple[float, float]:
        node_a = graph.nodes[self.current_node]
        if self.finished:
            return node_a.lat, node_a.lng
        node_b = graph.nodes[self.next_node]
        edge = edge_between(graph, self.current_node, self.next_node)
        travel_time = edge.travel_time_hours() if edge is not None else 0.0
        fraction = 0.0 if travel_time <= 0 else min(1.0, self.edge_hours_elapsed / travel_time)
        lat = node_a.lat + (node_b.lat - node_a.lat) * fraction
        lng = node_a.lng + (node_b.lng - node_a.lng) * fraction
        return lat, lng


class StraightLineProgress:
    def __init__(self, waypoints: list[tuple[float, float]], speed_kmph: float):
        self.waypoints = list(waypoints)
        self.speed_kmph = speed_kmph
        self.index = 0
        self.leg_hours_elapsed = 0.0

    @property
    def current_waypoint(self) -> tuple[float, float]:
        return self.waypoints[self.index % len(self.waypoints)]

    @property
    def next_waypoint(self) -> tuple[float, float]:
        return self.waypoints[(self.index + 1) % len(self.waypoints)]

    def leg_hours(self) -> float:
        lat1, lng1 = self.current_waypoint
        lat2, lng2 = self.next_waypoint
        distance_km = haversine_km(lat1, lng1, lat2, lng2)
        return distance_km / self.speed_kmph if self.speed_kmph > 0 else 0.0

    def advance(self, hours: float) -> None:
        leg_duration = self.leg_hours()
        self.leg_hours_elapsed += hours
        if leg_duration <= 0 or self.leg_hours_elapsed >= leg_duration:
            self.leg_hours_elapsed = 0.0
            self.index += 1

    def interpolated_position(self) -> tuple[float, float]:
        lat1, lng1 = self.current_waypoint
        lat2, lng2 = self.next_waypoint
        leg_duration = self.leg_hours()
        fraction = 0.0 if leg_duration <= 0 else min(1.0, self.leg_hours_elapsed / leg_duration)
        lat = lat1 + (lat2 - lat1) * fraction
        lng = lng1 + (lng2 - lng1) * fraction
        return lat, lng
