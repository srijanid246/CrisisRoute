from dataclasses import asdict, dataclass
from typing import Any

CONDITION_MULTIPLIER = {"good": 1.0, "damaged": 1.6, "flooded": 3.0}


@dataclass
class Node:
    id: int
    lat: float
    lng: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Node":
        return cls(id=data["id"], lat=data["lat"], lng=data["lng"])


@dataclass
class Edge:
    source: int
    target: int
    length_km: float
    speed_kmph: float
    condition: str
    blocked: bool

    def travel_time_hours(self) -> float:
        if self.blocked:
            return float("inf")
        return self.length_km / self.speed_kmph * CONDITION_MULTIPLIER[self.condition]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Edge":
        return cls(
            source=data["source"],
            target=data["target"],
            length_km=data["length_km"],
            speed_kmph=data["speed_kmph"],
            condition=data["condition"],
            blocked=data["blocked"],
        )


@dataclass
class Zone:
    id: str
    name: str
    node_id: int
    population: int
    vulnerable_pct: float
    water_level_m: float
    rainfall_mm: float
    infrastructure_condition: str
    road_accessibility: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Zone":
        return cls(**data)


@dataclass
class Resource:
    id: str
    type: str
    capacity: int
    current_node: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Resource":
        return cls(**data)


@dataclass
class Hospital:
    id: str
    name: str
    node_id: int
    capacity: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Hospital":
        return cls(**data)


@dataclass
class Depot:
    id: str
    name: str
    node_id: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Depot":
        return cls(**data)


@dataclass
class Scenario:
    seed: int
    nodes: list[Node]
    edges: list[Edge]
    zones: list[Zone]
    resources: list[Resource]
    hospitals: list[Hospital]
    depots: list[Depot]

    def to_dict(self) -> dict[str, Any]:
        return {
            "seed": self.seed,
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "zones": [z.to_dict() for z in self.zones],
            "resources": [r.to_dict() for r in self.resources],
            "hospitals": [h.to_dict() for h in self.hospitals],
            "depots": [d.to_dict() for d in self.depots],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Scenario":
        return cls(
            seed=data["seed"],
            nodes=[Node.from_dict(n) for n in data["nodes"]],
            edges=[Edge.from_dict(e) for e in data["edges"]],
            zones=[Zone.from_dict(z) for z in data["zones"]],
            resources=[Resource.from_dict(r) for r in data["resources"]],
            hospitals=[Hospital.from_dict(h) for h in data["hospitals"]],
            depots=[Depot.from_dict(d) for d in data["depots"]],
        )
