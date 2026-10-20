export default function AllocationTable({ scenario, plan }) {
  if (!plan) return null;

  return (
    <section className="panel-section">
      <h3>Allocation</h3>
      <table className="data-table">
        <thead>
          <tr>
            <th>Resource</th>
            <th>Type</th>
            <th>Assigned zone</th>
            <th>Route cost (h)</th>
          </tr>
        </thead>
        <tbody>
          {scenario.resources.map((resource, index) => {
            const gene = plan.allocation.chromosome[index];
            const zone = gene === -1 ? null : scenario.zones[gene];
            const route = plan.routes[resource.id];
            return (
              <tr key={resource.id}>
                <td>{resource.id}</td>
                <td>{resource.type}</td>
                <td>{zone ? zone.name : "idle"}</td>
                <td>{route ? route.cost.toFixed(3) : "-"}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <div className="metrics-row">
        <span>Fitness: {plan.allocation.fitness.toFixed(1)}</span>
        <span>Population covered: {plan.metrics.population_covered.toFixed(1)}</span>
        <span>Avg response: {plan.metrics.average_response_time_hours.toFixed(3)}h</span>
        <span>Utilisation: {(plan.metrics.resource_utilisation * 100).toFixed(0)}%</span>
      </div>
    </section>
  );
}
