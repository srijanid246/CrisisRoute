from crisisroute.routing import build_graph, search

TICK_DURATION_HOURS = 0.05
VULNERABLE_RESCUE_FRACTION = 1.0
RELIEF_UNITS_PER_CAPITA = 0.01


def initial_trapped_population(zone) -> int:
    return max(0, round(zone.population * zone.vulnerable_pct / 100.0 * VULNERABLE_RESCUE_FRACTION))


def initial_relief_units_needed(zone) -> int:
    return max(0, round(zone.population * RELIEF_UNITS_PER_CAPITA))


class World:
    def __init__(self, scenario, tick_duration_hours: float = TICK_DURATION_HOURS):
        self.scenario = scenario
        self.graph = build_graph(scenario)
        self.tick_duration_hours = tick_duration_hours
        self.hospital_capacity = {h.id: h.capacity for h in scenario.hospitals}
        self.hospital_occupancy = {h.id: 0 for h in scenario.hospitals}
        self.node_by_id = {n.id: n for n in scenario.nodes}
        self.zone_remaining_population: dict[str, int] = {}
        self.zone_relief_needed: dict[str, int] = {}
        for zone in scenario.zones:
            self.register_zone(zone)

    def register_zone(self, zone) -> None:
        self.zone_remaining_population.setdefault(zone.id, initial_trapped_population(zone))
        self.zone_relief_needed.setdefault(zone.id, initial_relief_units_needed(zone))

    def hospital_has_capacity(self, hospital_id: str) -> bool:
        return self.hospital_occupancy[hospital_id] < self.hospital_capacity[hospital_id]

    def reserve_hospital_slot(self, hospital_id: str) -> None:
        self.hospital_occupancy[hospital_id] += 1

    def release_hospital_slot(self, hospital_id: str) -> None:
        self.hospital_occupancy[hospital_id] = max(0, self.hospital_occupancy[hospital_id] - 1)

    def nearest_available_hospital(self, from_node: int):
        best = None
        for hospital in self.scenario.hospitals:
            if not self.hospital_has_capacity(hospital.id):
                continue
            result = search(self.graph, from_node, hospital.node_id, algorithm="astar")
            if not result.path:
                continue
            if best is None or result.cost < best[2]:
                best = (hospital.id, result.path, result.cost)
        return best
