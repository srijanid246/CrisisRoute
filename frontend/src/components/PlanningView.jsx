import { useCallback, useState } from "react";

import {
  applyEvent,
  compareAllocation,
  compareRouting,
  createPlan,
  createScenario,
  getScenario,
} from "../api.js";
import AllocationChart from "./AllocationChart.jsx";
import LeftPanel from "./LeftPanel.jsx";
import MapView from "./MapView.jsx";
import RightPanel from "./RightPanel.jsx";
import RoutingChart from "./RoutingChart.jsx";

function nearestNodeId(nodes, latlng) {
  let best = nodes[0];
  let bestDistance = Infinity;
  for (const node of nodes) {
    const distance = (node.lat - latlng.lat) ** 2 + (node.lng - latlng.lng) ** 2;
    if (distance < bestDistance) {
      bestDistance = distance;
      best = node;
    }
  }
  return best.id;
}

function nextZoneId(zones) {
  const letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
  const used = new Set(zones.map((zone) => zone.id));
  for (const letter of letters) {
    if (!used.has(letter)) return letter;
  }
  return `Z${zones.length}`;
}

export default function PlanningView() {
  const [scenarioId, setScenarioId] = useState(null);
  const [scenario, setScenario] = useState(null);
  const [plan, setPlan] = useState(null);
  const [lastEvent, setLastEvent] = useState(null);
  const [routingComparison, setRoutingComparison] = useState(null);
  const [allocationComparison, setAllocationComparison] = useState(null);
  const [interactionMode, setInteractionMode] = useState("idle");
  const [busy, setBusy] = useState(false);
  const [statusMessage, setStatusMessage] = useState("");

  const refreshComparisons = useCallback(async (id) => {
    const [routing, allocation] = await Promise.all([compareRouting(id), compareAllocation(id)]);
    setRoutingComparison(routing);
    setAllocationComparison(allocation);
  }, []);

  const handleLoadDemo = useCallback(async () => {
    setBusy(true);
    setStatusMessage("Loading flood demo scenario...");
    try {
      const created = await createScenario({ preset: "flood_demo" });
      const fullScenario = await getScenario(created.id);
      setScenarioId(created.id);
      setScenario(fullScenario);
      setPlan(null);
      setLastEvent(null);
      setRoutingComparison(null);
      setAllocationComparison(null);
      setInteractionMode("idle");
      setStatusMessage(`Loaded scenario #${created.id} (flood_demo).`);
    } catch (error) {
      setStatusMessage(`Error: ${error.message}`);
    } finally {
      setBusy(false);
    }
  }, []);

  const handleGeneratePlan = useCallback(async () => {
    if (!scenarioId) return;
    setBusy(true);
    setStatusMessage("Running Bayesian risk, GA allocation and A* routing...");
    try {
      const result = await createPlan(scenarioId);
      setPlan(result.plan);
      await refreshComparisons(scenarioId);
      setStatusMessage(`Plan created (version ${result.version}).`);
    } catch (error) {
      setStatusMessage(`Error: ${error.message}`);
    } finally {
      setBusy(false);
    }
  }, [scenarioId, refreshComparisons]);

  const runEvent = useCallback(
    async (type, payload) => {
      if (!scenarioId) return;
      setBusy(true);
      setStatusMessage(`Applying ${type}...`);
      try {
        const result = await applyEvent(scenarioId, type, payload);
        const refreshedScenario = await getScenario(scenarioId);
        setScenario(refreshedScenario);
        setPlan(result.plan);
        setLastEvent(result);
        await refreshComparisons(scenarioId);
        setStatusMessage(
          `${type} applied (version ${result.version}). GA rerun: ${result.diff.ga_rerun ? "yes" : "no"}.`
        );
      } catch (error) {
        setStatusMessage(`Error: ${error.message}`);
      } finally {
        setBusy(false);
        setInteractionMode("idle");
      }
    },
    [scenarioId, refreshComparisons]
  );

  const handleEdgeClick = useCallback(
    (edge) => {
      if (interactionMode !== "block-road") return;
      runEvent("ROAD_BLOCKED", { source: edge.source, target: edge.target });
    },
    [interactionMode, runEvent]
  );

  const handleMapClick = useCallback(
    (latlng) => {
      if (interactionMode !== "add-zone" || !scenario) return;
      const populationInput = window.prompt("Population of the new zone?", "10000");
      if (populationInput === null) {
        setInteractionMode("idle");
        return;
      }
      const population = Math.max(100, parseInt(populationInput, 10) || 10000);
      const nodeId = nearestNodeId(scenario.graph.nodes, latlng);
      const zoneId = nextZoneId(scenario.zones);
      runEvent("NEW_ZONE", {
        zone: {
          id: zoneId,
          name: `Zone ${zoneId}`,
          node_id: nodeId,
          population,
          vulnerable_pct: 15.0,
          water_level_m: 1.0,
          rainfall_mm: 100.0,
          infrastructure_condition: "damaged",
          road_accessibility: "limited",
        },
      });
    },
    [interactionMode, scenario, runEvent]
  );

  const handleMarkUnavailable = useCallback(
    (resourceId) => {
      runEvent("RESOURCE_UNAVAILABLE", { resource_id: resourceId });
    },
    [runEvent]
  );

  const handleRaiseWaterLevel = useCallback(
    (zoneId) => {
      const zone = scenario.zones.find((z) => z.id === zoneId);
      const newLevel = Math.round((zone.water_level_m + 0.5) * 100) / 100;
      runEvent("RISK_CHANGE", { zone_id: zoneId, attributes: { water_level_m: newLevel } });
    },
    [scenario, runEvent]
  );

  return (
    <>
      <div className="app-top">
        <LeftPanel
          scenario={scenario}
          plan={plan}
          interactionMode={interactionMode}
          onSetInteractionMode={setInteractionMode}
          onLoadDemo={handleLoadDemo}
          onGeneratePlan={handleGeneratePlan}
          onMarkUnavailable={handleMarkUnavailable}
          onRaiseWaterLevel={handleRaiseWaterLevel}
          busy={busy}
          statusMessage={statusMessage}
        />

        <div className="map-panel">
          {scenario ? (
            <MapView
              scenario={scenario}
              plan={plan}
              interactionMode={interactionMode}
              onEdgeClick={handleEdgeClick}
              onMapClick={handleMapClick}
            />
          ) : (
            <div className="map-placeholder">Load a scenario to see the map.</div>
          )}
        </div>

        <RightPanel scenario={scenario} plan={plan} lastEvent={lastEvent} />
      </div>

      <div className="app-bottom">
        <RoutingChart routingComparison={routingComparison} />
        <AllocationChart allocationComparison={allocationComparison} />
      </div>
    </>
  );
}
