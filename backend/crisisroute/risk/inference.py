from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from pgmpy.inference import VariableElimination

from .discretize import zone_to_evidence
from .network import RISK_STATES, build_network

RISK_SCORE_VALUES = {
    "Low": 0.0,
    "Medium": 1 / 3,
    "High": 2 / 3,
    "VeryHigh": 1.0,
}


@dataclass
class RiskAssessment:
    zone_id: str | None
    evidence: dict[str, str]
    posterior: dict[str, float]
    category: str
    score: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "zone_id": self.zone_id,
            "evidence": dict(self.evidence),
            "posterior": dict(self.posterior),
            "category": self.category,
            "score": self.score,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RiskAssessment":
        return cls(
            zone_id=data["zone_id"],
            evidence=dict(data["evidence"]),
            posterior=dict(data["posterior"]),
            category=data["category"],
            score=data["score"],
        )


@lru_cache(maxsize=1)
def get_inference_engine() -> VariableElimination:
    return VariableElimination(build_network())


def assess_risk(
    evidence: dict[str, str],
    zone_id: str | None = None,
    engine: VariableElimination | None = None,
) -> RiskAssessment:
    engine = engine or get_inference_engine()
    result = engine.query(variables=["Risk"], evidence=evidence, show_progress=False)
    states = result.state_names["Risk"]
    posterior = {state: float(prob) for state, prob in zip(states, result.values)}
    category = max(posterior, key=posterior.get)
    score = sum(posterior[state] * RISK_SCORE_VALUES[state] for state in RISK_STATES)
    return RiskAssessment(
        zone_id=zone_id,
        evidence=dict(evidence),
        posterior=posterior,
        category=category,
        score=score,
    )


def assess_zone_risk(zone, engine: VariableElimination | None = None) -> RiskAssessment:
    evidence = zone_to_evidence(zone)
    return assess_risk(evidence, zone_id=zone.id, engine=engine)


def assess_scenario_risk(scenario) -> list[RiskAssessment]:
    engine = get_inference_engine()
    return [assess_zone_risk(zone, engine=engine) for zone in scenario.zones]
