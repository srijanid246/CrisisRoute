RESOURCE_TYPES = ("ambulance", "rescue_team", "relief_vehicle")

BASE_NEEDS_BY_RISK_CATEGORY = {
    "Low": {"ambulance": 0, "rescue_team": 0, "relief_vehicle": 0},
    "Medium": {"ambulance": 1, "rescue_team": 0, "relief_vehicle": 1},
    "High": {"ambulance": 1, "rescue_team": 1, "relief_vehicle": 1},
    "VeryHigh": {"ambulance": 2, "rescue_team": 1, "relief_vehicle": 1},
}

POPULATION_EXTRA_AMBULANCE_THRESHOLD = 10000
POPULATION_EXTRA_RELIEF_THRESHOLD = 15000


def zone_type_needs(zone, risk_category: str) -> dict[str, int]:
    needs = dict(BASE_NEEDS_BY_RISK_CATEGORY[risk_category])
    if zone.population >= POPULATION_EXTRA_AMBULANCE_THRESHOLD:
        needs["ambulance"] += 1
    if zone.population >= POPULATION_EXTRA_RELIEF_THRESHOLD:
        needs["relief_vehicle"] += 1
    return needs
