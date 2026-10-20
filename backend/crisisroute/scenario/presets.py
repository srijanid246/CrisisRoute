import random

from .generator import generate_scenario
from .models import Hospital, Resource, Scenario, Zone

FLOOD_DEMO_SEED = 20261008


def flood_demo() -> Scenario:
    base = generate_scenario(FLOOD_DEMO_SEED)
    depot_1, depot_2 = base.depots[0], base.depots[1]

    reserved = {d.node_id for d in base.depots} | {h.node_id for h in base.hospitals}
    candidates = [n.id for n in base.nodes if n.id not in reserved]
    zone_rng = random.Random(FLOOD_DEMO_SEED + 1)
    zone_node_ids = zone_rng.sample(candidates, 4)

    zones = [
        Zone(
            id="A",
            name="Zone A - Velachery",
            node_id=zone_node_ids[0],
            population=18000,
            vulnerable_pct=22.5,
            water_level_m=1.8,
            rainfall_mm=180.0,
            infrastructure_condition="damaged",
            road_accessibility="limited",
        ),
        Zone(
            id="B",
            name="Zone B - Saidapet",
            node_id=zone_node_ids[1],
            population=12000,
            vulnerable_pct=15.0,
            water_level_m=1.2,
            rainfall_mm=140.0,
            infrastructure_condition="damaged",
            road_accessibility="accessible",
        ),
        Zone(
            id="C",
            name="Zone C - Kotturpuram",
            node_id=zone_node_ids[2],
            population=9000,
            vulnerable_pct=28.0,
            water_level_m=2.4,
            rainfall_mm=210.0,
            infrastructure_condition="critical",
            road_accessibility="cutoff",
        ),
        Zone(
            id="D",
            name="Zone D - Adyar",
            node_id=zone_node_ids[3],
            population=15000,
            vulnerable_pct=18.5,
            water_level_m=1.5,
            rainfall_mm=160.0,
            infrastructure_condition="damaged",
            road_accessibility="limited",
        ),
    ]

    resources = [
        Resource(id="AMB-1", type="ambulance", capacity=2, current_node=depot_1.node_id),
        Resource(id="AMB-2", type="ambulance", capacity=2, current_node=depot_1.node_id),
        Resource(id="RESCUE-1", type="rescue_team", capacity=6, current_node=depot_1.node_id),
        Resource(id="RESCUE-2", type="rescue_team", capacity=6, current_node=depot_2.node_id),
        Resource(id="RELIEF-1", type="relief_vehicle", capacity=40, current_node=depot_2.node_id),
    ]

    hospitals = [
        Hospital(
            id="HOSPITAL-1",
            name="City General Hospital",
            node_id=base.hospitals[0].node_id,
            capacity=150,
        ),
        Hospital(
            id="HOSPITAL-2",
            name="Riverside Hospital",
            node_id=base.hospitals[1].node_id,
            capacity=100,
        ),
    ]

    return Scenario(
        seed=FLOOD_DEMO_SEED,
        nodes=base.nodes,
        edges=base.edges,
        zones=zones,
        resources=resources,
        hospitals=hospitals,
        depots=base.depots,
    )


LARGE_SCENARIO_SEED = 20261100
LARGE_SCENARIO_TARGET_NODES = 300
LARGE_SCENARIO_NUM_ZONES = 15
LARGE_SCENARIO_RESOURCE_COUNTS = {"ambulance": 10, "rescue_team": 8, "relief_vehicle": 7}


def large_scenario() -> Scenario:
    return generate_scenario(
        LARGE_SCENARIO_SEED,
        target_nodes=LARGE_SCENARIO_TARGET_NODES,
        num_zones=LARGE_SCENARIO_NUM_ZONES,
        resource_counts=LARGE_SCENARIO_RESOURCE_COUNTS,
    )


PRESETS = {"flood_demo": flood_demo, "large": large_scenario}


def load_preset(name: str) -> Scenario:
    try:
        builder = PRESETS[name]
    except KeyError as exc:
        raise ValueError(f"unknown preset: {name}") from exc
    return builder()
