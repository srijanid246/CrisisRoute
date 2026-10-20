from flask import Blueprint, current_app, g, jsonify, request

from crisisroute.agents import Simulation
from crisisroute.agents.presets import flood_demo_dynamic
from crisisroute.allocation import GAConfig, run_ga, run_greedy
from crisisroute.replanning import Plan, Planner, static_outcome
from crisisroute.routing import ALGORITHMS, build_graph, search
from crisisroute.scenario import Scenario, generate_scenario, load_preset

from .db import EventRecord, PlanRecord, ScenarioRecord
from .event_codec import build_event, deserialize_hidden_event, serialize_hidden_event

api_bp = Blueprint("api", __name__, url_prefix="/api")


def get_session():
    if "db_session" not in g:
        g.db_session = current_app.config["SESSION_FACTORY"]()
    return g.db_session


@api_bp.teardown_request
def close_session(exception=None):
    session = g.pop("db_session", None)
    if session is not None:
        if exception is not None:
            session.rollback()
        session.close()


def _latest_plan_record(session, scenario_id: int):
    return (
        session.query(PlanRecord)
        .filter_by(scenario_id=scenario_id)
        .order_by(PlanRecord.version.desc())
        .first()
    )


@api_bp.route("/scenarios", methods=["POST"])
def create_scenario():
    body = request.get_json(silent=True) or {}
    preset = body.get("preset")
    seed = body.get("seed")
    hidden_events_payload = []

    if preset == "flood_demo_dynamic":
        scenario, hidden_events = flood_demo_dynamic()
        hidden_events_payload = [serialize_hidden_event(h) for h in hidden_events]
    elif preset:
        try:
            scenario = load_preset(preset)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
    elif seed is not None:
        scenario = generate_scenario(seed=int(seed))
    else:
        return jsonify({"error": "either seed or preset is required"}), 400

    session = get_session()
    record = ScenarioRecord(
        seed=scenario.seed,
        preset=preset,
        data=scenario.to_dict(),
        hidden_events=hidden_events_payload,
    )
    session.add(record)
    session.commit()

    return jsonify({"id": record.id, "seed": record.seed, "preset": record.preset}), 201


@api_bp.route("/scenarios/<int:scenario_id>", methods=["GET"])
def get_scenario(scenario_id: int):
    session = get_session()
    record = session.get(ScenarioRecord, scenario_id)
    if record is None:
        return jsonify({"error": "scenario not found"}), 404

    data = record.data
    return jsonify(
        {
            "id": record.id,
            "seed": record.seed,
            "preset": record.preset,
            "graph": {"nodes": data["nodes"], "edges": data["edges"]},
            "zones": data["zones"],
            "resources": data["resources"],
            "hospitals": data["hospitals"],
            "depots": data["depots"],
        }
    )


@api_bp.route("/scenarios/<int:scenario_id>/plan", methods=["POST"])
def create_plan(scenario_id: int):
    session = get_session()
    record = session.get(ScenarioRecord, scenario_id)
    if record is None:
        return jsonify({"error": "scenario not found"}), 404

    if _latest_plan_record(session, scenario_id) is not None:
        return jsonify({"error": "a plan already exists for this scenario; use /events to evolve it"}), 409

    scenario = Scenario.from_dict(record.data)
    planner = Planner()
    plan = planner.create_plan(scenario)

    plan_record = PlanRecord(scenario_id=scenario_id, version=1, data=plan.to_dict())
    record.data = scenario.to_dict()
    session.add(plan_record)
    session.commit()

    return jsonify({"version": plan_record.version, "plan": plan.to_dict()}), 201


@api_bp.route("/scenarios/<int:scenario_id>/events", methods=["POST"])
def apply_event(scenario_id: int):
    session = get_session()
    record = session.get(ScenarioRecord, scenario_id)
    if record is None:
        return jsonify({"error": "scenario not found"}), 404

    body = request.get_json(silent=True) or {}
    event_type = body.get("type")
    payload = body.get("payload") or {}
    if not event_type:
        return jsonify({"error": "type is required"}), 400

    latest_plan_record = _latest_plan_record(session, scenario_id)
    if latest_plan_record is None:
        return jsonify({"error": "no plan exists yet; call /plan first"}), 409

    try:
        event = build_event(event_type, payload)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    scenario = Scenario.from_dict(record.data)
    old_plan = Plan.from_dict(latest_plan_record.data)

    try:
        outcome = static_outcome(scenario, old_plan, event)
        planner = Planner()
        new_plan, diff = planner.apply_event(scenario, old_plan, event)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    new_version = latest_plan_record.version + 1
    plan_record = PlanRecord(scenario_id=scenario_id, version=new_version, data=new_plan.to_dict())
    event_record = EventRecord(
        scenario_id=scenario_id,
        resulting_plan_version=new_version,
        type=event_type,
        payload=payload,
        diff=diff.to_dict(),
        static_outcome=outcome.to_dict(),
    )
    record.data = scenario.to_dict()
    session.add(plan_record)
    session.add(event_record)
    session.commit()

    return (
        jsonify(
            {
                "version": new_version,
                "plan": new_plan.to_dict(),
                "diff": diff.to_dict(),
                "static_outcome": outcome.to_dict(),
            }
        ),
        201,
    )


@api_bp.route("/scenarios/<int:scenario_id>/plans", methods=["GET"])
def list_plans(scenario_id: int):
    session = get_session()
    record = session.get(ScenarioRecord, scenario_id)
    if record is None:
        return jsonify({"error": "scenario not found"}), 404

    plan_records = (
        session.query(PlanRecord)
        .filter_by(scenario_id=scenario_id)
        .order_by(PlanRecord.version.asc())
        .all()
    )
    return jsonify(
        {
            "plans": [
                {"version": p.version, "created_at": p.created_at.isoformat(), "plan": p.data}
                for p in plan_records
            ]
        }
    )


@api_bp.route("/scenarios/<int:scenario_id>/compare/routing", methods=["GET"])
def compare_routing(scenario_id: int):
    session = get_session()
    record = session.get(ScenarioRecord, scenario_id)
    if record is None:
        return jsonify({"error": "scenario not found"}), 404

    latest_plan_record = _latest_plan_record(session, scenario_id)
    if latest_plan_record is None:
        return jsonify({"error": "no plan exists yet; call /plan first"}), 409

    scenario = Scenario.from_dict(record.data)
    plan = Plan.from_dict(latest_plan_record.data)
    graph = build_graph(scenario)
    resource_index_by_id = {r.id: i for i, r in enumerate(scenario.resources)}

    results = {}
    for resource in scenario.resources:
        if resource.id not in plan.routes:
            continue
        gene = plan.allocation.chromosome[resource_index_by_id[resource.id]]
        zone = scenario.zones[gene]
        results[resource.id] = {
            algorithm: search(graph, resource.current_node, zone.node_id, algorithm=algorithm).to_dict()
            for algorithm in ALGORITHMS
        }

    return jsonify({"version": latest_plan_record.version, "routes": results})


@api_bp.route("/scenarios/<int:scenario_id>/compare/allocation", methods=["GET"])
def compare_allocation(scenario_id: int):
    session = get_session()
    record = session.get(ScenarioRecord, scenario_id)
    if record is None:
        return jsonify({"error": "scenario not found"}), 404

    latest_plan_record = _latest_plan_record(session, scenario_id)
    if latest_plan_record is None:
        return jsonify({"error": "no plan exists yet; call /plan first"}), 409

    scenario = Scenario.from_dict(record.data)
    plan = Plan.from_dict(latest_plan_record.data)

    greedy_result = run_greedy(
        scenario,
        plan.cost_matrix,
        plan.risk_assessments,
        unavailable_resource_ids=plan.unavailable_resource_ids,
    )
    ga_result = run_ga(
        scenario,
        plan.cost_matrix,
        plan.risk_assessments,
        GAConfig(),
        unavailable_resource_ids=plan.unavailable_resource_ids,
    )

    return jsonify(
        {
            "version": latest_plan_record.version,
            "greedy": greedy_result.to_dict(),
            "genetic_algorithm": ga_result.to_dict(),
        }
    )


@api_bp.route("/scenarios/<int:scenario_id>/simulate", methods=["POST"])
def simulate_scenario(scenario_id: int):
    session = get_session()
    record = session.get(ScenarioRecord, scenario_id)
    if record is None:
        return jsonify({"error": "scenario not found"}), 404

    body = request.get_json(silent=True) or {}
    try:
        max_ticks = int(body.get("max_ticks", 150))
        num_uavs = int(body.get("num_uavs", 1))
    except (TypeError, ValueError):
        return jsonify({"error": "max_ticks and num_uavs must be integers"}), 400

    scenario = Scenario.from_dict(record.data)
    initial_scenario_payload = {
        "graph": {
            "nodes": [n.to_dict() for n in scenario.nodes],
            "edges": [e.to_dict() for e in scenario.edges],
        },
        "zones": [z.to_dict() for z in scenario.zones],
        "resources": [r.to_dict() for r in scenario.resources],
        "hospitals": [h.to_dict() for h in scenario.hospitals],
        "depots": [d.to_dict() for d in scenario.depots],
    }

    hidden_events_payload = body.get("hidden_events")
    if hidden_events_payload is None:
        hidden_events_payload = record.hidden_events or []
    try:
        hidden_events = [deserialize_hidden_event(h) for h in hidden_events_payload]
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    simulation = Simulation(hidden_events=hidden_events, num_uavs=num_uavs)
    result = simulation.run(scenario, max_ticks)

    record.data = scenario.to_dict()
    session.commit()

    return jsonify(
        {
            "initial_scenario": initial_scenario_payload,
            "hidden_events": hidden_events_payload,
            "snapshots": [s.to_dict() for s in result.snapshots],
            "metrics": result.metrics.to_dict(),
        }
    )
