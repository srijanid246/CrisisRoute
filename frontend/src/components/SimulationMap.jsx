import L from "leaflet";
import { useMemo } from "react";
import { Circle, CircleMarker, MapContainer, Marker, Polyline, TileLayer, Tooltip } from "react-leaflet";

import { UAV_SURVEY_RADIUS_KM, agentStateColor, resourceLabel } from "../constants.js";
import {
  agentTypeById,
  discoveredUpToTick,
  latestAssignmentsUpToTick,
  isReplanHighlighted,
  worldAtTick,
} from "../simulationDerive.js";

const CHENNAI_CENTER = [13.0827, 80.2707];

function makeAgentIcon(type, state) {
  const color = agentStateColor(state);
  const label = resourceLabel(type);
  return L.divIcon({
    className: "sim-agent-icon",
    html: `<div class="sim-agent-icon-inner" style="background:${color}">${label}</div>`,
    iconSize: [24, 24],
    iconAnchor: [12, 12],
  });
}

export default function SimulationMap({ initialScenario, hiddenEvents, snapshots, tick }) {
  const snapshot = snapshots[tick];

  const typeById = useMemo(() => agentTypeById(initialScenario), [initialScenario]);
  const world = useMemo(() => worldAtTick(initialScenario, hiddenEvents, tick), [initialScenario, hiddenEvents, tick]);
  const discovered = useMemo(() => discoveredUpToTick(snapshots, tick), [snapshots, tick]);
  const assignments = useMemo(() => latestAssignmentsUpToTick(snapshots, tick), [snapshots, tick]);

  const nodesById = useMemo(() => {
    const map = {};
    for (const node of world.nodes) map[node.id] = node;
    return map;
  }, [world]);

  if (!snapshot) return null;

  return (
    <MapContainer center={CHENNAI_CENTER} zoom={12} className="map-container">
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />

      {world.edges.map((edge, index) => {
        const source = nodesById[edge.source];
        const target = nodesById[edge.target];
        if (!source || !target) return null;
        const isDiscovered =
          !edge.blocked || edge.wasAlwaysKnown || discovered.blockedKeys.has(`${edge.source}-${edge.target}`);
        return (
          <Polyline
            key={`edge-${index}`}
            positions={[
              [source.lat, source.lng],
              [target.lat, target.lng],
            ]}
            pathOptions={{
              color: edge.blocked ? "#c62828" : "#90a4ae",
              weight: edge.blocked ? 3 : 1.5,
              dashArray: edge.blocked ? "6 6" : null,
              opacity: edge.blocked ? (isDiscovered ? 0.9 : 0.25) : 0.5,
            }}
          >
            <Tooltip sticky>
              {edge.blocked ? (isDiscovered ? "blocked (known)" : "blocked (not yet discovered)") : "open"}
            </Tooltip>
          </Polyline>
        );
      })}

      {Object.entries(assignments).map(([agentId, assignment]) => {
        if (!assignment.route || assignment.route.length < 2) return null;
        const positions = assignment.route.map((nodeId) => nodesById[nodeId]).filter(Boolean).map((n) => [n.lat, n.lng]);
        const highlighted = isReplanHighlighted(assignment, tick);
        return (
          <Polyline
            key={`route-${agentId}`}
            positions={positions}
            pathOptions={{
              color: highlighted ? "#ff1744" : "#1565c0",
              weight: highlighted ? 5 : 3,
              opacity: highlighted ? 0.95 : 0.55,
              dashArray: highlighted ? "2 6" : null,
            }}
          />
        );
      })}

      {world.zones.map((zone) => {
        const node = nodesById[zone.node_id];
        if (!node) return null;
        const isDiscovered = discovered.zoneIds.has(zone.id);
        const remaining = snapshot.zone_remaining_population[zone.id];
        const radius = 8 + Math.sqrt(zone.population) / 20;
        const color = remaining === 0 ? "#2e7d32" : "#ef6c00";
        return (
          <CircleMarker
            key={`zone-${zone.id}`}
            center={[node.lat, node.lng]}
            radius={Math.max(8, Math.min(30, radius))}
            pathOptions={{
              color,
              fillColor: color,
              fillOpacity: isDiscovered ? 0.45 : 0.12,
              opacity: isDiscovered ? 1 : 0.3,
              dashArray: isDiscovered ? null : "4 4",
            }}
          >
            <Tooltip sticky>
              <div>
                <strong>{zone.name}</strong>
                <br />
                {isDiscovered ? "known to command" : "not yet discovered"}
                <br />
                remaining trapped: {remaining ?? "n/a"}
              </div>
            </Tooltip>
          </CircleMarker>
        );
      })}

      {Object.entries(snapshot.agent_positions).map(([agentId, position]) => {
        const type = typeById[agentId] || "uav";
        const state = snapshot.agent_states[agentId];
        return (
          <Marker key={`agent-${agentId}`} position={position} icon={makeAgentIcon(type, state)}>
            <Tooltip sticky>
              <div>
                <strong>{agentId}</strong> ({type})
                <br />
                state: {state}
              </div>
            </Tooltip>
          </Marker>
        );
      })}

      {Object.entries(snapshot.agent_positions)
        .filter(([agentId]) => (typeById[agentId] || "uav") === "uav")
        .map(([agentId, position]) => (
          <Circle
            key={`survey-${agentId}`}
            center={position}
            radius={UAV_SURVEY_RADIUS_KM * 1000}
            pathOptions={{ color: "#37474f", fillColor: "#37474f", fillOpacity: 0.07, weight: 1, dashArray: "3 5" }}
          />
        ))}
    </MapContainer>
  );
}
