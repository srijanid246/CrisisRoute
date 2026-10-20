const SPEEDS = [1, 2, 5, 10, 20];

export default function SimulationControls({
  hasData,
  busy,
  onLoad,
  playing,
  onTogglePlay,
  speed,
  onSpeedChange,
  tick,
  maxTick,
  onScrub,
  metrics,
  hiddenEvents,
}) {
  return (
    <div className="panel left-panel">
      <h2>CrisisRoute</h2>
      <p className="sim-subtitle">Simulation</p>

      <section className="panel-section">
        <button className="btn btn-primary" onClick={onLoad} disabled={busy}>
          Load flood_demo_dynamic
        </button>
      </section>

      {hasData && (
        <section className="panel-section">
          <h3>Playback</h3>
          <div className="control-block">
            <button className="btn" onClick={onTogglePlay}>
              {playing ? "Pause" : "Play"}
            </button>
            <label>Speed: {speed}x</label>
            <select value={speed} onChange={(e) => onSpeedChange(Number(e.target.value))}>
              {SPEEDS.map((s) => (
                <option key={s} value={s}>
                  {s}x
                </option>
              ))}
            </select>
            <label>
              Tick {tick} / {maxTick}
            </label>
            <input
              type="range"
              min={0}
              max={maxTick}
              value={tick}
              onChange={(e) => onScrub(Number(e.target.value))}
            />
          </div>
        </section>
      )}

      {hasData && hiddenEvents.length > 0 && (
        <section className="panel-section">
          <h3>Hidden events</h3>
          {hiddenEvents.map((h, i) => (
            <div key={i} className="hidden-event-row">
              tick {h.tick}: {h.type}
              {h.type === "ROAD_BLOCKED" && ` (${h.payload.source}, ${h.payload.target})`}
              {h.type === "NEW_ZONE" && ` (${h.payload.zone.id})`}
            </div>
          ))}
        </section>
      )}

      {hasData && metrics && (
        <section className="panel-section">
          <h3>Final metrics (full run)</h3>
          <div className="metrics-row sim-metrics">
            <span>Rescued: {metrics.people_rescued}</span>
            <span>Delivered: {metrics.people_delivered_to_hospital}</span>
            <span>Avg rescue time: {metrics.average_rescue_completion_time_ticks.toFixed(1)} ticks</span>
            <span>Tasks done: {metrics.tasks_completed}</span>
            <span>Replans: {metrics.replans_triggered}</span>
          </div>
        </section>
      )}
    </div>
  );
}
