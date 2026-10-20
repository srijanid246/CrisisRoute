export const RISK_COLORS = {
  Low: "#2e7d32",
  Medium: "#f9a825",
  High: "#ef6c00",
  VeryHigh: "#c62828",
};

export const RESOURCE_TYPE_COLORS = {
  ambulance: "#1565c0",
  rescue_team: "#6a1b9a",
  relief_vehicle: "#00897b",
  uav: "#37474f",
};

export const RESOURCE_TYPE_LABELS = {
  ambulance: "A",
  rescue_team: "R",
  relief_vehicle: "V",
  uav: "U",
};

export const AGENT_STATE_COLORS = {
  IDLE: "#9e9e9e",
  EN_ROUTE: "#1565c0",
  EN_ROUTE_TO_ZONE: "#1565c0",
  AT_ZONE: "#ef6c00",
  RESCUING: "#ef6c00",
  DELIVERING: "#ef6c00",
  TO_HOSPITAL: "#8e24aa",
  EN_ROUTE_TO_DEPOT: "#8e24aa",
  UNLOADING: "#2e7d32",
  RELOADING: "#2e7d32",
  PATROLLING: "#00897b",
};

export const UAV_SURVEY_RADIUS_KM = 5.0;
export const REPLAN_ROUTE_COLOR = "#ff1744";

export const ROUTE_COLOR_PALETTE = [
  "#e53935",
  "#8e24aa",
  "#3949ab",
  "#00897b",
  "#fb8c00",
  "#6d4c41",
  "#039be5",
  "#43a047",
  "#ad1457",
  "#5d4037",
];

export function riskColor(category) {
  return RISK_COLORS[category] || "#9e9e9e";
}

export function resourceColor(type) {
  return RESOURCE_TYPE_COLORS[type] || "#546e7a";
}

export function resourceLabel(type) {
  return RESOURCE_TYPE_LABELS[type] || "?";
}

export function routeColor(index) {
  return ROUTE_COLOR_PALETTE[index % ROUTE_COLOR_PALETTE.length];
}

export function agentStateColor(state) {
  return AGENT_STATE_COLORS[state] || "#9e9e9e";
}
