export function agentTypeById(initialScenario) {
  const map = {};
  for (const resource of initialScenario.resources) {
    map[resource.id] = resource.type;
  }
  return map;
}

export function worldAtTick(initialScenario, hiddenEvents, tick) {
  const blockedKeys = new Set();
  const extraZones = [];

  for (const hidden of hiddenEvents) {
    if (hidden.tick > tick) continue;
    if (hidden.type === "ROAD_BLOCKED") {
      blockedKeys.add(`${hidden.payload.source}-${hidden.payload.target}`);
      blockedKeys.add(`${hidden.payload.target}-${hidden.payload.source}`);
    } else if (hidden.type === "NEW_ZONE") {
      extraZones.push(hidden.payload.zone);
    }
  }

  const edges = initialScenario.graph.edges.map((edge) => ({
    ...edge,
    wasAlwaysKnown: edge.blocked,
    blocked: edge.blocked || blockedKeys.has(`${edge.source}-${edge.target}`),
  }));

  const zones = [...initialScenario.zones, ...extraZones];

  return { nodes: initialScenario.graph.nodes, edges, zones };
}

export function pendingHiddenEvents(hiddenEvents, tick) {
  return hiddenEvents.filter((hidden) => hidden.tick > tick);
}

export function discoveredUpToTick(snapshots, tick) {
  const blockedKeys = new Set();
  const zoneIds = new Set();

  for (let i = 0; i <= tick && i < snapshots.length; i += 1) {
    for (const message of snapshots[i].messages) {
      if (message.type === "ROUTE_BLOCKED") {
        blockedKeys.add(`${message.payload.source}-${message.payload.target}`);
        blockedKeys.add(`${message.payload.target}-${message.payload.source}`);
      } else if (message.type === "ZONE_REPORT" && message.payload.zone) {
        zoneIds.add(message.payload.zone.id);
      }
    }
  }

  return { blockedKeys, zoneIds };
}

export function latestAssignmentsUpToTick(snapshots, tick) {
  const assignments = {};
  for (let i = 0; i <= tick && i < snapshots.length; i += 1) {
    for (const message of snapshots[i].messages) {
      if (message.type !== "ASSIGNMENT") continue;
      const recipient = message.recipient;
      if (!recipient) continue;
      assignments[recipient] = {
        route: message.payload.route,
        reason: message.payload.reason,
        tick: message.tick,
        zoneId: message.payload.zone_id,
      };
    }
  }
  return assignments;
}

export function isReplanHighlighted(assignment, tick, highlightTicks = 15) {
  if (!assignment || assignment.reason !== "replan") return false;
  return tick - assignment.tick <= highlightTicks;
}
