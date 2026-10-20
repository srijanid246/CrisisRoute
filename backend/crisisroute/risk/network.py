from itertools import product

from pgmpy.factors.discrete import TabularCPD
from pgmpy.models import DiscreteBayesianNetwork

RAINFALL_STATES = ["Low", "Medium", "High"]
WATER_LEVEL_STATES = ["Low", "Medium", "High"]
POPULATION_DENSITY_STATES = ["Low", "Medium", "High"]
VULNERABLE_POPULATION_STATES = ["Low", "Medium", "High"]
ROAD_ACCESSIBILITY_STATES = ["accessible", "limited", "cutoff"]
INFRASTRUCTURE_CONDITION_STATES = ["good", "damaged", "critical"]
HAZARD_STATES = ["Low", "Medium", "High"]
EXPOSURE_STATES = ["Low", "Medium", "High"]
VULNERABILITY_STATES = ["Low", "Medium", "High"]
RISK_STATES = ["Low", "Medium", "High", "VeryHigh"]

THREE_LEVEL_SEVERITY = {"Low": 0, "Medium": 1, "High": 2}
ROAD_ACCESSIBILITY_SEVERITY = {"accessible": 0, "limited": 1, "cutoff": 2}
INFRASTRUCTURE_CONDITION_SEVERITY = {"good": 0, "damaged": 1, "critical": 2}

RAINFALL_PRIOR = [0.22, 0.39, 0.39]
WATER_LEVEL_PRIOR = [0.13, 0.44, 0.43]
POPULATION_DENSITY_PRIOR = [0.21, 0.37, 0.42]
VULNERABLE_POPULATION_PRIOR = [0.333, 0.333, 0.334]
ROAD_ACCESSIBILITY_PRIOR = [0.5, 0.35, 0.15]
INFRASTRUCTURE_CONDITION_PRIOR = [0.4, 0.4, 0.2]

TWO_FACTOR_BASE_DISTRIBUTION = {
    0: [0.85, 0.12, 0.03],
    1: [0.65, 0.28, 0.07],
    2: [0.45, 0.35, 0.20],
    3: [0.20, 0.40, 0.40],
    4: [0.05, 0.20, 0.75],
}

THREE_FACTOR_BASE_DISTRIBUTION = {
    0: [0.90, 0.08, 0.02, 0.00],
    1: [0.70, 0.22, 0.07, 0.01],
    2: [0.45, 0.35, 0.15, 0.05],
    3: [0.22, 0.33, 0.30, 0.15],
    4: [0.08, 0.22, 0.40, 0.30],
    5: [0.02, 0.10, 0.33, 0.55],
    6: [0.00, 0.03, 0.17, 0.80],
}


def _root_cpd(variable: str, states: list[str], prior: list[float]) -> TabularCPD:
    return TabularCPD(
        variable=variable,
        variable_card=len(states),
        values=[[p] for p in prior],
        state_names={variable: states},
    )


def _combine_two(
    variable: str,
    child_states: list[str],
    parent_a: str,
    states_a: list[str],
    severity_a: dict[str, int],
    parent_b: str,
    states_b: list[str],
    severity_b: dict[str, int],
    base_distribution: dict[int, list[float]],
) -> TabularCPD:
    columns = []
    for state_a, state_b in product(states_a, states_b):
        index = severity_a[state_a] + severity_b[state_b]
        columns.append(base_distribution[index])
    values = [[column[i] for column in columns] for i in range(len(child_states))]
    return TabularCPD(
        variable=variable,
        variable_card=len(child_states),
        values=values,
        evidence=[parent_a, parent_b],
        evidence_card=[len(states_a), len(states_b)],
        state_names={
            variable: child_states,
            parent_a: states_a,
            parent_b: states_b,
        },
    )


def _combine_three(
    variable: str,
    child_states: list[str],
    parent_a: str,
    states_a: list[str],
    severity_a: dict[str, int],
    parent_b: str,
    states_b: list[str],
    severity_b: dict[str, int],
    parent_c: str,
    states_c: list[str],
    severity_c: dict[str, int],
    base_distribution: dict[int, list[float]],
) -> TabularCPD:
    columns = []
    for state_a, state_b, state_c in product(states_a, states_b, states_c):
        index = severity_a[state_a] + severity_b[state_b] + severity_c[state_c]
        columns.append(base_distribution[index])
    values = [[column[i] for column in columns] for i in range(len(child_states))]
    return TabularCPD(
        variable=variable,
        variable_card=len(child_states),
        values=values,
        evidence=[parent_a, parent_b, parent_c],
        evidence_card=[len(states_a), len(states_b), len(states_c)],
        state_names={
            variable: child_states,
            parent_a: states_a,
            parent_b: states_b,
            parent_c: states_c,
        },
    )


def build_network() -> DiscreteBayesianNetwork:
    network = DiscreteBayesianNetwork(
        [
            ("Rainfall", "Hazard"),
            ("WaterLevel", "Hazard"),
            ("PopulationDensity", "Exposure"),
            ("VulnerablePopulation", "Exposure"),
            ("RoadAccessibility", "Vulnerability"),
            ("InfrastructureCondition", "Vulnerability"),
            ("Hazard", "Risk"),
            ("Exposure", "Risk"),
            ("Vulnerability", "Risk"),
        ]
    )

    rainfall_cpd = _root_cpd("Rainfall", RAINFALL_STATES, RAINFALL_PRIOR)
    water_level_cpd = _root_cpd("WaterLevel", WATER_LEVEL_STATES, WATER_LEVEL_PRIOR)
    population_density_cpd = _root_cpd(
        "PopulationDensity", POPULATION_DENSITY_STATES, POPULATION_DENSITY_PRIOR
    )
    vulnerable_population_cpd = _root_cpd(
        "VulnerablePopulation", VULNERABLE_POPULATION_STATES, VULNERABLE_POPULATION_PRIOR
    )
    road_accessibility_cpd = _root_cpd(
        "RoadAccessibility", ROAD_ACCESSIBILITY_STATES, ROAD_ACCESSIBILITY_PRIOR
    )
    infrastructure_condition_cpd = _root_cpd(
        "InfrastructureCondition", INFRASTRUCTURE_CONDITION_STATES, INFRASTRUCTURE_CONDITION_PRIOR
    )

    hazard_cpd = _combine_two(
        "Hazard",
        HAZARD_STATES,
        "Rainfall",
        RAINFALL_STATES,
        THREE_LEVEL_SEVERITY,
        "WaterLevel",
        WATER_LEVEL_STATES,
        THREE_LEVEL_SEVERITY,
        TWO_FACTOR_BASE_DISTRIBUTION,
    )
    exposure_cpd = _combine_two(
        "Exposure",
        EXPOSURE_STATES,
        "PopulationDensity",
        POPULATION_DENSITY_STATES,
        THREE_LEVEL_SEVERITY,
        "VulnerablePopulation",
        VULNERABLE_POPULATION_STATES,
        THREE_LEVEL_SEVERITY,
        TWO_FACTOR_BASE_DISTRIBUTION,
    )
    vulnerability_cpd = _combine_two(
        "Vulnerability",
        VULNERABILITY_STATES,
        "RoadAccessibility",
        ROAD_ACCESSIBILITY_STATES,
        ROAD_ACCESSIBILITY_SEVERITY,
        "InfrastructureCondition",
        INFRASTRUCTURE_CONDITION_STATES,
        INFRASTRUCTURE_CONDITION_SEVERITY,
        TWO_FACTOR_BASE_DISTRIBUTION,
    )
    risk_cpd = _combine_three(
        "Risk",
        RISK_STATES,
        "Hazard",
        HAZARD_STATES,
        THREE_LEVEL_SEVERITY,
        "Exposure",
        EXPOSURE_STATES,
        THREE_LEVEL_SEVERITY,
        "Vulnerability",
        VULNERABILITY_STATES,
        THREE_LEVEL_SEVERITY,
        THREE_FACTOR_BASE_DISTRIBUTION,
    )

    network.add_cpds(
        rainfall_cpd,
        water_level_cpd,
        population_density_cpd,
        vulnerable_population_cpd,
        road_accessibility_cpd,
        infrastructure_condition_cpd,
        hazard_cpd,
        exposure_cpd,
        vulnerability_cpd,
        risk_cpd,
    )

    if not network.check_model():
        raise ValueError("invalid bayesian network definition")

    return network
