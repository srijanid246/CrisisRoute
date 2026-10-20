import { useState } from "react";

export default function LeftPanel({
  scenario,
  plan,
  interactionMode,
  onSetInteractionMode,
  onLoadDemo,
  onGeneratePlan,
  onMarkUnavailable,
  onRaiseWaterLevel,
  busy,
  statusMessage,
}) {
  const [selectedResourceId, setSelectedResourceId] = useState("");
  const [selectedZoneId, setSelectedZoneId] = useState("");

  const resources = scenario?.resources || [];
  const zones = scenario?.zones || [];

  return (
    <div className="panel left-panel">
      <h2>CrisisRoute</h2>

      <section className="panel-section">
        <button className="btn btn-primary" onClick={onLoadDemo} disabled={busy}>
          Load flood demo
        </button>
        <button className="btn btn-primary" onClick={onGeneratePlan} disabled={busy || !scenario}>
          Generate plan
        </button>
      </section>

      <section className="panel-section">
        <h3>Events</h3>

        <div className="control-block">
          <button
            className={`btn ${interactionMode === "block-road" ? "btn-active" : ""}`}
            disabled={busy || !plan}
            onClick={() =>
              onSetInteractionMode(interactionMode === "block-road" ? "idle" : "block-road")
            }
          >
            {interactionMode === "block-road" ? "Click an edge to block it..." : "Block a road"}
          </button>
        </div>

        <div className="control-block">
          <label>Mark resource unavailable</label>
          <select
            value={selectedResourceId}
            onChange={(event) => setSelectedResourceId(event.target.value)}
            disabled={busy || !plan}
          >
            <option value="">select a resource</option>
            {resources.map((resource) => (
              <option key={resource.id} value={resource.id}>
                {resource.id} ({resource.type})
              </option>
            ))}
          </select>
          <button
            className="btn"
            disabled={busy || !plan || !selectedResourceId}
            onClick={() => onMarkUnavailable(selectedResourceId)}
          >
            Mark unavailable
          </button>
        </div>

        <div className="control-block">
          <button
            className={`btn ${interactionMode === "add-zone" ? "btn-active" : ""}`}
            disabled={busy || !plan}
            onClick={() => onSetInteractionMode(interactionMode === "add-zone" ? "idle" : "add-zone")}
          >
            {interactionMode === "add-zone" ? "Click the map to place a zone..." : "Add a new zone"}
          </button>
        </div>

        <div className="control-block">
          <label>Raise a zone's water level</label>
          <select
            value={selectedZoneId}
            onChange={(event) => setSelectedZoneId(event.target.value)}
            disabled={busy || !plan}
          >
            <option value="">select a zone</option>
            {zones.map((zone) => (
              <option key={zone.id} value={zone.id}>
                {zone.name}
              </option>
            ))}
          </select>
          <button
            className="btn"
            disabled={busy || !plan || !selectedZoneId}
            onClick={() => onRaiseWaterLevel(selectedZoneId)}
          >
            +0.5m water level
          </button>
        </div>
      </section>

      {statusMessage && <div className="status-message">{statusMessage}</div>}
    </div>
  );
}
