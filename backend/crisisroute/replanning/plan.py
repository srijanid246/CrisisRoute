from dataclasses import dataclass
from typing import Any

from crisisroute.allocation import AllocationMetrics, AllocationResult
from crisisroute.risk import RiskAssessment
from crisisroute.routing import SearchResult


@dataclass
class Plan:
    risk_assessments: dict[str, RiskAssessment]
    allocation: AllocationResult
    routes: dict[str, SearchResult]
    cost_matrix: dict[str, dict[str, float]]
    unavailable_resource_ids: set[str]
    metrics: AllocationMetrics

    def to_dict(self) -> dict[str, Any]:
        return {
            "risk_assessments": {zone_id: r.to_dict() for zone_id, r in self.risk_assessments.items()},
            "allocation": self.allocation.to_dict(),
            "routes": {resource_id: route.to_dict() for resource_id, route in self.routes.items()},
            "cost_matrix": {r: dict(z) for r, z in self.cost_matrix.items()},
            "unavailable_resource_ids": sorted(self.unavailable_resource_ids),
            "metrics": self.metrics.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Plan":
        return cls(
            risk_assessments={k: RiskAssessment.from_dict(v) for k, v in data["risk_assessments"].items()},
            allocation=AllocationResult.from_dict(data["allocation"]),
            routes={k: SearchResult.from_dict(v) for k, v in data["routes"].items()},
            cost_matrix={k: dict(v) for k, v in data["cost_matrix"].items()},
            unavailable_resource_ids=set(data["unavailable_resource_ids"]),
            metrics=AllocationMetrics.from_dict(data["metrics"]),
        )


@dataclass
class AssignmentChange:
    resource_id: str
    old_zone_id: str | None
    new_zone_id: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "resource_id": self.resource_id,
            "old_zone_id": self.old_zone_id,
            "new_zone_id": self.new_zone_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AssignmentChange":
        return cls(**data)


@dataclass
class RouteChange:
    resource_id: str
    old_cost: float | None
    new_cost: float | None
    old_path: list[int]
    new_path: list[int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "resource_id": self.resource_id,
            "old_cost": self.old_cost,
            "new_cost": self.new_cost,
            "old_path": list(self.old_path),
            "new_path": list(self.new_path),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RouteChange":
        return cls(
            resource_id=data["resource_id"],
            old_cost=data["old_cost"],
            new_cost=data["new_cost"],
            old_path=list(data["old_path"]),
            new_path=list(data["new_path"]),
        )


@dataclass
class PlanDiff:
    event_type: str
    trigger_reason: str
    ga_rerun: bool
    assignment_changes: list[AssignmentChange]
    route_changes: list[RouteChange]
    metrics_before: AllocationMetrics
    metrics_after: AllocationMetrics

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "trigger_reason": self.trigger_reason,
            "ga_rerun": self.ga_rerun,
            "assignment_changes": [c.to_dict() for c in self.assignment_changes],
            "route_changes": [c.to_dict() for c in self.route_changes],
            "metrics_before": self.metrics_before.to_dict(),
            "metrics_after": self.metrics_after.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PlanDiff":
        return cls(
            event_type=data["event_type"],
            trigger_reason=data["trigger_reason"],
            ga_rerun=data["ga_rerun"],
            assignment_changes=[AssignmentChange.from_dict(c) for c in data["assignment_changes"]],
            route_changes=[RouteChange.from_dict(c) for c in data["route_changes"]],
            metrics_before=AllocationMetrics.from_dict(data["metrics_before"]),
            metrics_after=AllocationMetrics.from_dict(data["metrics_after"]),
        )
