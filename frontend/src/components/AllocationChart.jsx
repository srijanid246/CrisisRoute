import "../chartSetup.js";

import { Bar } from "react-chartjs-2";

const LABELS = ["genetic_algorithm", "greedy"];
const DISPLAY_LABELS = ["GA", "Greedy"];
const COLORS = ["#1565c0", "#ef6c00"];

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { display: false } },
  scales: { y: { beginAtZero: true } },
};

export default function AllocationChart({ allocationComparison }) {
  if (!allocationComparison) return null;

  const populationCovered = {
    labels: DISPLAY_LABELS,
    datasets: [
      {
        data: LABELS.map((key) => allocationComparison[key].metrics.population_covered),
        backgroundColor: COLORS,
      },
    ],
  };

  const averageResponse = {
    labels: DISPLAY_LABELS,
    datasets: [
      {
        data: LABELS.map((key) => allocationComparison[key].metrics.average_response_time_hours),
        backgroundColor: COLORS,
      },
    ],
  };

  return (
    <div className="chart-group">
      <h4>GA vs Greedy</h4>
      <div className="chart-row">
        <div className="chart-box">
          <p className="chart-label">Population covered</p>
          <Bar data={populationCovered} options={chartOptions} />
        </div>
        <div className="chart-box">
          <p className="chart-label">Avg response (h)</p>
          <Bar data={averageResponse} options={chartOptions} />
        </div>
      </div>
    </div>
  );
}
