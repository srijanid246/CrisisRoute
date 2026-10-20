const API_BASE = "http://localhost:5000/api";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.error || `request failed: ${response.status}`);
  }
  return data;
}

export function createScenario(body) {
  return request("/scenarios", { method: "POST", body: JSON.stringify(body) });
}

export function getScenario(scenarioId) {
  return request(`/scenarios/${scenarioId}`);
}

export function createPlan(scenarioId) {
  return request(`/scenarios/${scenarioId}/plan`, { method: "POST" });
}

export function applyEvent(scenarioId, type, payload) {
  return request(`/scenarios/${scenarioId}/events`, {
    method: "POST",
    body: JSON.stringify({ type, payload }),
  });
}

export function listPlans(scenarioId) {
  return request(`/scenarios/${scenarioId}/plans`);
}

export function compareRouting(scenarioId) {
  return request(`/scenarios/${scenarioId}/compare/routing`);
}

export function compareAllocation(scenarioId) {
  return request(`/scenarios/${scenarioId}/compare/allocation`);
}

export function simulateScenario(scenarioId, body = {}) {
  return request(`/scenarios/${scenarioId}/simulate`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}
