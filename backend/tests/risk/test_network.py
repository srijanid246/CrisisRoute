import pytest

from crisisroute.risk.network import RISK_STATES, build_network


def test_build_network_passes_pgmpy_validation():
    network = build_network()
    assert network.check_model()


def test_all_cpds_sum_to_one_per_column():
    network = build_network()
    for cpd in network.get_cpds():
        totals = cpd.get_values().sum(axis=0)
        for total in totals:
            assert pytest.approx(1.0, abs=1e-9) == total


def test_network_has_expected_edges():
    network = build_network()
    edges = set(network.edges())
    assert edges == {
        ("Rainfall", "Hazard"),
        ("WaterLevel", "Hazard"),
        ("PopulationDensity", "Exposure"),
        ("VulnerablePopulation", "Exposure"),
        ("RoadAccessibility", "Vulnerability"),
        ("InfrastructureCondition", "Vulnerability"),
        ("Hazard", "Risk"),
        ("Exposure", "Risk"),
        ("Vulnerability", "Risk"),
    }


def test_risk_node_has_four_states():
    assert RISK_STATES == ["Low", "Medium", "High", "VeryHigh"]
