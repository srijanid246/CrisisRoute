from typing import Any

from crisisroute.agents import HiddenEvent
from crisisroute.replanning import NewZoneEvent, ResourceUnavailableEvent, RiskChangeEvent, RoadBlockedEvent
from crisisroute.scenario import Zone


def _build_road_blocked(payload: dict[str, Any]) -> RoadBlockedEvent:
    return RoadBlockedEvent(source=int(payload["source"]), target=int(payload["target"]))


def _build_new_zone(payload: dict[str, Any]) -> NewZoneEvent:
    return NewZoneEvent(zone=Zone.from_dict(payload["zone"]))


def _build_resource_unavailable(payload: dict[str, Any]) -> ResourceUnavailableEvent:
    return ResourceUnavailableEvent(resource_id=str(payload["resource_id"]))


def _build_risk_change(payload: dict[str, Any]) -> RiskChangeEvent:
    return RiskChangeEvent(zone_id=str(payload["zone_id"]), attributes=dict(payload["attributes"]))


EVENT_BUILDERS = {
    "ROAD_BLOCKED": _build_road_blocked,
    "NEW_ZONE": _build_new_zone,
    "RESOURCE_UNAVAILABLE": _build_resource_unavailable,
    "RISK_CHANGE": _build_risk_change,
}


def build_event(event_type: str, payload: dict[str, Any]):
    try:
        builder = EVENT_BUILDERS[event_type]
    except KeyError as exc:
        raise ValueError(f"unknown event type: {event_type!r}") from exc
    try:
        return builder(payload)
    except KeyError as exc:
        raise ValueError(f"missing field {exc.args[0]!r} in payload for {event_type}") from exc


def serialize_event(event) -> dict[str, Any]:
    if isinstance(event, RoadBlockedEvent):
        return {"type": "ROAD_BLOCKED", "payload": {"source": event.source, "target": event.target}}
    if isinstance(event, NewZoneEvent):
        return {"type": "NEW_ZONE", "payload": {"zone": event.zone.to_dict()}}
    if isinstance(event, ResourceUnavailableEvent):
        return {"type": "RESOURCE_UNAVAILABLE", "payload": {"resource_id": event.resource_id}}
    if isinstance(event, RiskChangeEvent):
        return {"type": "RISK_CHANGE", "payload": {"zone_id": event.zone_id, "attributes": dict(event.attributes)}}
    raise TypeError(f"unknown event object: {event!r}")


def serialize_hidden_event(hidden_event: HiddenEvent) -> dict[str, Any]:
    return {"tick": hidden_event.tick, **serialize_event(hidden_event.event)}


def deserialize_hidden_event(data: dict[str, Any]) -> HiddenEvent:
    return HiddenEvent(tick=int(data["tick"]), event=build_event(data["type"], data["payload"]))
