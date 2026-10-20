from crisisroute.allocation.needs import zone_type_needs
from crisisroute.scenario import Zone


def _zone(population: int) -> Zone:
    return Zone(
        id="Z",
        name="Z",
        node_id=0,
        population=population,
        vulnerable_pct=10.0,
        water_level_m=0.3,
        rainfall_mm=50.0,
        infrastructure_condition="good",
        road_accessibility="accessible",
    )


def test_low_risk_zone_needs_nothing():
    assert zone_type_needs(_zone(1000), "Low") == {"ambulance": 0, "rescue_team": 0, "relief_vehicle": 0}


def test_high_risk_zone_needs_one_of_each_critical_type():
    needs = zone_type_needs(_zone(1000), "High")
    assert needs["ambulance"] >= 1
    assert needs["rescue_team"] >= 1


def test_very_high_risk_needs_more_than_high():
    low_pop = _zone(1000)
    very_high = zone_type_needs(low_pop, "VeryHigh")
    high = zone_type_needs(low_pop, "High")
    assert very_high["ambulance"] >= high["ambulance"]
    assert very_high["rescue_team"] >= high["rescue_team"]


def test_large_population_adds_extra_ambulance_need():
    small = zone_type_needs(_zone(5000), "Medium")
    large = zone_type_needs(_zone(12000), "Medium")
    assert large["ambulance"] == small["ambulance"] + 1


def test_very_large_population_adds_extra_relief_vehicle_need():
    small = zone_type_needs(_zone(5000), "Medium")
    large = zone_type_needs(_zone(16000), "Medium")
    assert large["relief_vehicle"] == small["relief_vehicle"] + 1
