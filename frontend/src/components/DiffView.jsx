function MetricsComparison({ before, after }) {
  const rows = [
    ["Population covered", "population_covered", 1],
    ["Avg response (h)", "average_response_time_hours", 3],
    ["Utilisation", "resource_utilisation", 2],
    ["Total travel (h)", "total_travel_cost_hours", 3],
  ];
  return (
    <table className="data-table">
      <thead>
        <tr>
          <th>Metric</th>
          <th>Before</th>
          <th>After</th>
        </tr>
      </thead>
      <tbody>
        {rows.map(([label, key, digits]) => (
          <tr key={key}>
            <td>{label}</td>
            <td>{before[key].toFixed(digits)}</td>
            <td>{after[key].toFixed(digits)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default function DiffView({ event }) {
  if (!event) return null;
  const { diff, static_outcome: staticOutcome } = event;

  return (
    <section className="panel-section diff-view">
      <h3>Last event: {diff.event_type}</h3>
      <p className="trigger-reason">{diff.trigger_reason}</p>
      <p>GA rerun: <strong>{diff.ga_rerun ? "yes" : "no"}</strong></p>

      <h4>Assignment changes</h4>
      {diff.assignment_changes.length === 0 ? (
        <p className="empty-note">(none)</p>
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>Resource</th>
              <th>Old zone</th>
              <th>New zone</th>
            </tr>
          </thead>
          <tbody>
            {diff.assignment_changes.map((change) => (
              <tr key={change.resource_id}>
                <td>{change.resource_id}</td>
                <td>{change.old_zone_id || "idle"}</td>
                <td>{change.new_zone_id || "idle"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <h4>Route changes</h4>
      {diff.route_changes.length === 0 ? (
        <p className="empty-note">(none)</p>
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>Resource</th>
              <th>Old cost (h)</th>
              <th>New cost (h)</th>
            </tr>
          </thead>
          <tbody>
            {diff.route_changes.map((change) => (
              <tr key={change.resource_id}>
                <td>{change.resource_id}</td>
                <td>{change.old_cost === null ? "-" : change.old_cost.toFixed(3)}</td>
                <td>{change.new_cost === null || !Number.isFinite(change.new_cost) ? "unreachable" : change.new_cost.toFixed(3)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <h4>Metrics before / after replanning</h4>
      <MetricsComparison before={diff.metrics_before} after={diff.metrics_after} />

      <h4>Static baseline (no replanning)</h4>
      <p>
        Failed deliveries: {staticOutcome.failed_resource_ids.length === 0 ? "none" : staticOutcome.failed_resource_ids.join(", ")}
      </p>
      <p>
        Uncovered zones: {staticOutcome.uncovered_zone_ids.length === 0 ? "none" : staticOutcome.uncovered_zone_ids.join(", ")}
      </p>
      <MetricsComparison before={diff.metrics_before} after={staticOutcome.metrics} />
    </section>
  );
}
