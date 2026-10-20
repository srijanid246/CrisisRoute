RAINFALL_LOW_MAX = 80.0
RAINFALL_MEDIUM_MAX = 150.0

WATER_LEVEL_LOW_MAX = 0.5
WATER_LEVEL_MEDIUM_MAX = 1.5

POPULATION_LOW_MAX = 5000
POPULATION_MEDIUM_MAX = 12000

VULNERABLE_PCT_LOW_MAX = 15.0
VULNERABLE_PCT_MEDIUM_MAX = 25.0

ROAD_ACCESSIBILITY_STATES = {"accessible", "limited", "cutoff"}
INFRASTRUCTURE_CONDITION_STATES = {"good", "damaged", "critical"}


def discretize_rainfall(rainfall_mm: float) -> str:
    if rainfall_mm < RAINFALL_LOW_MAX:
        return "Low"
    if rainfall_mm < RAINFALL_MEDIUM_MAX:
        return "Medium"
    return "High"


def discretize_water_level(water_level_m: float) -> str:
    if water_level_m < WATER_LEVEL_LOW_MAX:
        return "Low"
    if water_level_m < WATER_LEVEL_MEDIUM_MAX:
        return "Medium"
    return "High"


def discretize_population(population: int) -> str:
    if population < POPULATION_LOW_MAX:
        return "Low"
    if population < POPULATION_MEDIUM_MAX:
        return "Medium"
    return "High"


def discretize_vulnerable_pct(vulnerable_pct: float) -> str:
    if vulnerable_pct < VULNERABLE_PCT_LOW_MAX:
        return "Low"
    if vulnerable_pct < VULNERABLE_PCT_MEDIUM_MAX:
        return "Medium"
    return "High"


def discretize_road_accessibility(road_accessibility: str) -> str:
    if road_accessibility not in ROAD_ACCESSIBILITY_STATES:
        raise ValueError(f"unknown road_accessibility state: {road_accessibility!r}")
    return road_accessibility


def discretize_infrastructure_condition(infrastructure_condition: str) -> str:
    if infrastructure_condition not in INFRASTRUCTURE_CONDITION_STATES:
        raise ValueError(f"unknown infrastructure_condition state: {infrastructure_condition!r}")
    return infrastructure_condition


def zone_to_evidence(zone) -> dict[str, str]:
    return {
        "Rainfall": discretize_rainfall(zone.rainfall_mm),
        "WaterLevel": discretize_water_level(zone.water_level_m),
        "PopulationDensity": discretize_population(zone.population),
        "VulnerablePopulation": discretize_vulnerable_pct(zone.vulnerable_pct),
        "RoadAccessibility": discretize_road_accessibility(zone.road_accessibility),
        "InfrastructureCondition": discretize_infrastructure_condition(zone.infrastructure_condition),
    }


def partial_evidence(
    *,
    rainfall_mm: float | None = None,
    water_level_m: float | None = None,
    population: int | None = None,
    vulnerable_pct: float | None = None,
    road_accessibility: str | None = None,
    infrastructure_condition: str | None = None,
) -> dict[str, str]:
    evidence: dict[str, str] = {}
    if rainfall_mm is not None:
        evidence["Rainfall"] = discretize_rainfall(rainfall_mm)
    if water_level_m is not None:
        evidence["WaterLevel"] = discretize_water_level(water_level_m)
    if population is not None:
        evidence["PopulationDensity"] = discretize_population(population)
    if vulnerable_pct is not None:
        evidence["VulnerablePopulation"] = discretize_vulnerable_pct(vulnerable_pct)
    if road_accessibility is not None:
        evidence["RoadAccessibility"] = discretize_road_accessibility(road_accessibility)
    if infrastructure_condition is not None:
        evidence["InfrastructureCondition"] = discretize_infrastructure_condition(infrastructure_condition)
    return evidence
