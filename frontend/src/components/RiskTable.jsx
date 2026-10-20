export default function RiskTable({ scenario, plan }) {
  if (!plan) return null;

  return (
    <section className="panel-section">
      <h3>Risk</h3>
      <table className="data-table">
        <thead>
          <tr>
            <th>Zone</th>
            <th>Category</th>
            <th>Score</th>
            <th>Population</th>
            <th>Water (m)</th>
            <th>Rainfall (mm)</th>
          </tr>
        </thead>
        <tbody>
          {scenario.zones.map((zone) => {
            const assessment = plan.risk_assessments[zone.id];
            return (
              <tr key={zone.id}>
                <td>{zone.name}</td>
                <td className={`risk-cell risk-${assessment?.category || "Low"}`}>
                  {assessment?.category || "n/a"}
                </td>
                <td>{assessment ? assessment.score.toFixed(3) : "n/a"}</td>
                <td>{zone.population}</td>
                <td>{zone.water_level_m}</td>
                <td>{zone.rainfall_mm}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </section>
  );
}
