import pytest

from crisisroute.api import create_app


@pytest.fixture
def client():
    app = create_app(database_url="sqlite:///:memory:")
    return app.test_client()


def _create_flood_demo_scenario(client):
    response = client.post("/api/scenarios", json={"preset": "flood_demo"})
    assert response.status_code == 201
    return response.get_json()["id"]


def _create_plan(client, scenario_id):
    response = client.post(f"/api/scenarios/{scenario_id}/plan")
    assert response.status_code == 201
    return response.get_json()


def test_create_scenario_with_preset(client):
    response = client.post("/api/scenarios", json={"preset": "flood_demo"})
    assert response.status_code == 201
    data = response.get_json()
    assert data["preset"] == "flood_demo"
    assert data["seed"] == 20261008
    assert isinstance(data["id"], int)


def test_create_scenario_with_seed(client):
    response = client.post("/api/scenarios", json={"seed": 42})
    assert response.status_code == 201
    data = response.get_json()
    assert data["seed"] == 42
    assert data["preset"] is None


def test_create_scenario_requires_seed_or_preset(client):
    response = client.post("/api/scenarios", json={})
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_create_scenario_rejects_unknown_preset(client):
    response = client.post("/api/scenarios", json={"preset": "not_a_real_preset"})
    assert response.status_code == 400


def test_get_scenario_not_found(client):
    response = client.get("/api/scenarios/999")
    assert response.status_code == 404


def test_get_scenario_returns_graph_zones_resources(client):
    scenario_id = _create_flood_demo_scenario(client)
    response = client.get(f"/api/scenarios/{scenario_id}")
    assert response.status_code == 200
    data = response.get_json()
    assert set(data.keys()) >= {"id", "seed", "preset", "graph", "zones", "resources", "hospitals", "depots"}
    assert "nodes" in data["graph"]
    assert "edges" in data["graph"]
    assert len(data["zones"]) == 4
    assert len(data["resources"]) == 5


def test_create_plan(client):
    scenario_id = _create_flood_demo_scenario(client)
    data = _create_plan(client, scenario_id)
    assert data["version"] == 1
    assert "allocation" in data["plan"]
    assert "routes" in data["plan"]
    assert "risk_assessments" in data["plan"]


def test_create_plan_without_scenario_returns_404(client):
    response = client.post("/api/scenarios/999/plan")
    assert response.status_code == 404


def test_create_plan_twice_conflicts(client):
    scenario_id = _create_flood_demo_scenario(client)
    _create_plan(client, scenario_id)
    response = client.post(f"/api/scenarios/{scenario_id}/plan")
    assert response.status_code == 409


def test_apply_event_without_plan_conflicts(client):
    scenario_id = _create_flood_demo_scenario(client)
    response = client.post(
        f"/api/scenarios/{scenario_id}/events",
        json={"type": "RESOURCE_UNAVAILABLE", "payload": {"resource_id": "AMB-1"}},
    )
    assert response.status_code == 409


def test_apply_event_unknown_type_returns_400(client):
    scenario_id = _create_flood_demo_scenario(client)
    _create_plan(client, scenario_id)
    response = client.post(
        f"/api/scenarios/{scenario_id}/events", json={"type": "NOT_A_REAL_EVENT", "payload": {}}
    )
    assert response.status_code == 400


def test_apply_event_requires_type(client):
    scenario_id = _create_flood_demo_scenario(client)
    _create_plan(client, scenario_id)
    response = client.post(f"/api/scenarios/{scenario_id}/events", json={"payload": {}})
    assert response.status_code == 400


def test_full_flow_create_scenario_plan_event(client):
    scenario_id = _create_flood_demo_scenario(client)
    plan_data = _create_plan(client, scenario_id)

    resource_id, route = next(iter(plan_data["plan"]["routes"].items()))
    source, target = route["path"][0], route["path"][1]

    response = client.post(
        f"/api/scenarios/{scenario_id}/events",
        json={"type": "ROAD_BLOCKED", "payload": {"source": source, "target": target}},
    )
    assert response.status_code == 201
    data = response.get_json()

    assert data["version"] == 2
    assert set(data.keys()) == {"version", "plan", "diff", "static_outcome"}
    assert data["diff"]["event_type"] == "ROAD_BLOCKED"
    assert resource_id in data["static_outcome"]["failed_resource_ids"]

    scenario_response = client.get(f"/api/scenarios/{scenario_id}")
    edges = scenario_response.get_json()["graph"]["edges"]
    matching = [
        e for e in edges if {e["source"], e["target"]} == {source, target}
    ]
    assert matching and matching[0]["blocked"] is True


def test_resource_unavailable_event_idles_the_resource(client):
    scenario_id = _create_flood_demo_scenario(client)
    plan_data = _create_plan(client, scenario_id)
    chromosome = plan_data["plan"]["allocation"]["chromosome"]

    response = client.post(
        f"/api/scenarios/{scenario_id}/events",
        json={"type": "RESOURCE_UNAVAILABLE", "payload": {"resource_id": "AMB-1"}},
    )
    assert response.status_code == 201
    data = response.get_json()
    assert "AMB-1" not in data["plan"]["routes"]


def test_new_zone_event_adds_exactly_one_zone(client):
    scenario_id = _create_flood_demo_scenario(client)
    _create_plan(client, scenario_id)

    scenario_data = client.get(f"/api/scenarios/{scenario_id}").get_json()
    node_id = scenario_data["graph"]["nodes"][70]["id"]

    new_zone = {
        "id": "E",
        "name": "Zone E",
        "node_id": node_id,
        "population": 14000,
        "vulnerable_pct": 20.0,
        "water_level_m": 1.6,
        "rainfall_mm": 170.0,
        "infrastructure_condition": "damaged",
        "road_accessibility": "limited",
    }
    response = client.post(
        f"/api/scenarios/{scenario_id}/events", json={"type": "NEW_ZONE", "payload": {"zone": new_zone}}
    )
    assert response.status_code == 201

    updated = client.get(f"/api/scenarios/{scenario_id}").get_json()
    assert len(updated["zones"]) == 5
    assert [z["id"] for z in updated["zones"]] == ["A", "B", "C", "D", "E"]


def test_risk_change_event(client):
    scenario_id = _create_flood_demo_scenario(client)
    _create_plan(client, scenario_id)

    response = client.post(
        f"/api/scenarios/{scenario_id}/events",
        json={
            "type": "RISK_CHANGE",
            "payload": {"zone_id": "B", "attributes": {"water_level_m": 2.5, "rainfall_mm": 220.0}},
        },
    )
    assert response.status_code == 201
    data = response.get_json()
    assert data["plan"]["risk_assessments"]["B"]["category"] in {"High", "VeryHigh"}


def test_list_plans_returns_versions_in_order(client):
    scenario_id = _create_flood_demo_scenario(client)
    _create_plan(client, scenario_id)
    client.post(
        f"/api/scenarios/{scenario_id}/events",
        json={"type": "RESOURCE_UNAVAILABLE", "payload": {"resource_id": "AMB-1"}},
    )
    client.post(
        f"/api/scenarios/{scenario_id}/events",
        json={"type": "RESOURCE_UNAVAILABLE", "payload": {"resource_id": "AMB-2"}},
    )

    response = client.get(f"/api/scenarios/{scenario_id}/plans")
    assert response.status_code == 200
    plans = response.get_json()["plans"]
    assert [p["version"] for p in plans] == [1, 2, 3]


def test_compare_routing_returns_three_algorithms_per_resource(client):
    scenario_id = _create_flood_demo_scenario(client)
    plan_data = _create_plan(client, scenario_id)
    deployed_resource_ids = set(plan_data["plan"]["routes"].keys())

    response = client.get(f"/api/scenarios/{scenario_id}/compare/routing")
    assert response.status_code == 200
    data = response.get_json()
    assert set(data["routes"].keys()) == deployed_resource_ids
    for algorithms in data["routes"].values():
        assert set(algorithms.keys()) == {"astar", "bfs", "dfs"}
        for result in algorithms.values():
            assert "cost" in result and "path" in result and "nodes_explored" in result


def test_compare_routing_without_plan_conflicts(client):
    scenario_id = _create_flood_demo_scenario(client)
    response = client.get(f"/api/scenarios/{scenario_id}/compare/routing")
    assert response.status_code == 409


def test_compare_allocation_returns_ga_and_greedy(client):
    scenario_id = _create_flood_demo_scenario(client)
    _create_plan(client, scenario_id)

    response = client.get(f"/api/scenarios/{scenario_id}/compare/allocation")
    assert response.status_code == 200
    data = response.get_json()
    assert "fitness" in data["greedy"]
    assert "fitness" in data["genetic_algorithm"]
    assert data["genetic_algorithm"]["fitness"] >= data["greedy"]["fitness"]


def test_cors_headers_present(client):
    response = client.get(
        "/api/scenarios/999", headers={"Origin": "http://example.com"}
    )
    assert "Access-Control-Allow-Origin" in response.headers


def test_create_scenario_with_flood_demo_dynamic_preset(client):
    response = client.post("/api/scenarios", json={"preset": "flood_demo_dynamic"})
    assert response.status_code == 201
    data = response.get_json()
    assert data["preset"] == "flood_demo_dynamic"


def test_simulate_requires_existing_scenario(client):
    response = client.post("/api/scenarios/999/simulate", json={})
    assert response.status_code == 404


def test_simulate_returns_snapshots_metrics_and_hidden_events(client):
    scenario_id = _create_flood_demo_scenario(client)
    response = client.post(f"/api/scenarios/{scenario_id}/simulate", json={"max_ticks": 10, "num_uavs": 1})
    assert response.status_code == 200
    data = response.get_json()
    assert set(data.keys()) == {"initial_scenario", "hidden_events", "snapshots", "metrics"}
    assert len(data["snapshots"]) == 10
    assert data["hidden_events"] == []
    snapshot = data["snapshots"][0]
    assert set(snapshot.keys()) == {
        "tick",
        "agent_positions",
        "agent_states",
        "zone_remaining_population",
        "hospital_occupancy",
        "messages",
    }
    metrics = data["metrics"]
    assert set(metrics.keys()) == {
        "people_rescued",
        "people_delivered_to_hospital",
        "average_rescue_completion_time_ticks",
        "tasks_completed",
        "replans_triggered",
        "idle_ticks_per_agent",
    }


def test_simulate_uses_stored_hidden_events_for_flood_demo_dynamic(client):
    response = client.post("/api/scenarios", json={"preset": "flood_demo_dynamic"})
    scenario_id = response.get_json()["id"]

    simulate_response = client.post(f"/api/scenarios/{scenario_id}/simulate", json={"max_ticks": 40, "num_uavs": 1})
    assert simulate_response.status_code == 200
    data = simulate_response.get_json()

    assert len(data["hidden_events"]) == 2
    assert data["metrics"]["replans_triggered"] >= 1


def test_simulate_accepts_hidden_events_override(client):
    scenario_id = _create_flood_demo_scenario(client)
    response = client.post(
        f"/api/scenarios/{scenario_id}/simulate",
        json={"max_ticks": 10, "num_uavs": 1, "hidden_events": []},
    )
    assert response.status_code == 200
    assert response.get_json()["hidden_events"] == []


def test_simulate_rejects_malformed_hidden_events(client):
    scenario_id = _create_flood_demo_scenario(client)
    response = client.post(
        f"/api/scenarios/{scenario_id}/simulate",
        json={"max_ticks": 5, "hidden_events": [{"tick": 1, "type": "NOT_A_TYPE", "payload": {}}]},
    )
    assert response.status_code == 400


def test_simulate_initial_scenario_matches_pre_simulation_state(client):
    scenario_id = _create_flood_demo_scenario(client)
    before = client.get(f"/api/scenarios/{scenario_id}").get_json()

    response = client.post(f"/api/scenarios/{scenario_id}/simulate", json={"max_ticks": 5, "num_uavs": 1})
    data = response.get_json()

    assert data["initial_scenario"]["zones"] == before["zones"]
    assert len(data["initial_scenario"]["graph"]["edges"]) == len(before["graph"]["edges"])
