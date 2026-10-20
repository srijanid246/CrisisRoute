import L from "leaflet";
import { useMemo } from "react";
import { CircleMarker, MapContainer, Marker, Polyline, TileLayer, Tooltip, useMapEvents } from "react-leaflet";

import { resourceColor, resourceLabel, riskColor, routeColor } from "../constants.js";

const CHENNAI_CENTER = [13.0827, 80.2707];

function zoneRadius(population) {
  const radius = 6 + Math.sqrt(population) / 20;
  return Math.max(8, Math.min(30, radius));
}

function makeResourceIcon(type) {
  const color = resourceColor(type);
  const label = resourceLabel(type);
  return L.divIcon({
    className: "resource-icon",
    html: `<div class="resource-icon-inner" style="background:${color}">${label}</div>`,
    iconSize: [22, 22],
    iconAnchor: [11, 11],
  });
}

function ClickCapture({ onMapClick }) {
  useMapEvents({
    click(event) {
      onMapClick(event.latlng);
    },
  });
  return null;
}

export default function MapView({ scenario, plan, interactionMode, onEdgeClick, onMapClick }) {
  const nodesById = useMemo(() => {
    const map = {};
    for (const node of scenario.graph.nodes) {
      map[node.id] = node;
    }
    return map;
  }, [scenario]);

  const resourceIcons = useMemo(() => {
    const icons = {};
    for (const resource of scenario.resources) {
      if (!icons[resource.type]) {
        icons[resource.type] = makeResourceIcon(resource.type);
      }
    }
    return icons;
  }, [scenario]);

  const zoneById = useMemo(() => {
    const map = {};
    for (const zone of scenario.zones) {
      map[zone.id] = zone;
    }
    return map;
  }, [scenario]);

  const assignments = useMemo(() => {
    if (!plan) return {};
    const map = {};
    scenario.resources.forEach((resource, index) => {
      const gene = plan.allocation.chromosome[index];
      map[resource.id] = gene === -1 ? null : scenario.zones[gene];
    });
    return map;
  }, [plan, scenario]);

  const resourceOffsets = useMemo(() => {
    const groups = {};
    for (const resource of scenario.resources) {
      if (!groups[resource.current_node]) groups[resource.current_node] = [];
      groups[resource.current_node].push(resource.id);
    }
    const offsets = {};
    const RADIUS_DEG = 0.0018;
    for (const ids of Object.values(groups)) {
      const count = ids.length;
      ids.forEach((id, i) => {
        if (count === 1) {
          offsets[id] = [0, 0];
          return;
        }
        const angle = (2 * Math.PI * i) / count;
        offsets[id] = [Math.sin(angle) * RADIUS_DEG, Math.cos(angle) * RADIUS_DEG];
      });
    }
    return offsets;
  }, [scenario]);

  return (
    <MapContainer center={CHENNAI_CENTER} zoom={12} className="map-container">
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <ClickCapture onMapClick={onMapClick} />

      {scenario.graph.edges.map((edge, index) => {
        const source = nodesById[edge.source];
        const target = nodesById[edge.target];
        if (!source || !target) return null;
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
              opacity: edge.blocked ? 0.9 : 0.5,
            }}
            eventHandlers={{
              click: () => onEdgeClick(edge),
            }}
          >
            <Tooltip sticky>
              {edge.condition} / {edge.blocked ? "blocked" : "open"} / {edge.length_km.toFixed(2)} km
            </Tooltip>
          </Polyline>
        );
      })}

      {plan &&
        scenario.resources.map((resource, index) => {
          const route = plan.routes[resource.id];
          if (!route || route.path.length < 2) return null;
          const positions = route.path
            .map((nodeId) => nodesById[nodeId])
            .filter(Boolean)
            .map((node) => [node.lat, node.lng]);
          return (
            <Polyline
              key={`route-${resource.id}`}
              positions={positions}
              pathOptions={{ color: routeColor(index), weight: 4, opacity: 0.85 }}
            />
          );
        })}

      {scenario.zones.map((zone) => {
        const node = nodesById[zone.node_id];
        if (!node) return null;
        const assessment = plan?.risk_assessments?.[zone.id];
        const category = assessment?.category;
        const color = category ? riskColor(category) : "#9e9e9e";
        return (
          <CircleMarker
            key={`zone-${zone.id}`}
            center={[node.lat, node.lng]}
            radius={zoneRadius(zone.population)}
            pathOptions={{
              color,
              fillColor: color,
              fillOpacity: 0.45,
              weight: 2,
            }}
          >
            <Tooltip sticky>
              <div>
                <strong>{zone.name}</strong>
                <br />
                risk: {category ? `${category} (${assessment.score.toFixed(2)})` : "not yet assessed"}
                <br />
                population: {zone.population}
              </div>
            </Tooltip>
          </CircleMarker>
        );
      })}

      {scenario.resources.map((resource) => {
        const node = nodesById[resource.current_node];
        if (!node) return null;
        const zone = assignments[resource.id];
        const [dLat, dLng] = resourceOffsets[resource.id] || [0, 0];
        return (
          <Marker
            key={`resource-${resource.id}`}
            position={[node.lat + dLat, node.lng + dLng]}
            icon={resourceIcons[resource.type]}
          >
            <Tooltip sticky>
              <div>
                <strong>{resource.id}</strong> ({resource.type})
                <br />
                {zone ? `-> ${zone.name}` : "idle"}
              </div>
            </Tooltip>
          </Marker>
        );
      })}
    </MapContainer>
  );
}
