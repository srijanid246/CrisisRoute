from dataclasses import dataclass
from typing import Any

from crisisroute.scenario import Zone


@dataclass
class RoadBlockedEvent:
    source: int
    target: int


@dataclass
class NewZoneEvent:
    zone: Zone


@dataclass
class ResourceUnavailableEvent:
    resource_id: str


@dataclass
class RiskChangeEvent:
    zone_id: str
    attributes: dict[str, Any]


def find_edge(scenario, source: int, target: int):
    for edge in scenario.edges:
        if (edge.source, edge.target) in ((source, target), (target, source)):
            return edge
    return None


def apply_physical_effect(scenario, event):
    if isinstance(event, RoadBlockedEvent):
        edge = find_edge(scenario, event.source, event.target)
        if edge is None:
            raise ValueError(f"no edge between nodes {event.source} and {event.target}")
        edge.blocked = True
        return edge

    if isinstance(event, NewZoneEvent):
        scenario.zones.append(event.zone)
        return event.zone

    if isinstance(event, ResourceUnavailableEvent):
        return None

    if isinstance(event, RiskChangeEvent):
        zone = next((z for z in scenario.zones if z.id == event.zone_id), None)
        if zone is None:
            raise ValueError(f"unknown zone id: {event.zone_id!r}")
        for key, value in event.attributes.items():
            setattr(zone, key, value)
        return zone

    raise TypeError(f"unknown event type: {type(event)!r}")
