import "../chartSetup.js";

import { Bar } from "react-chartjs-2";

const ALGORITHMS = ["astar", "bfs", "dfs"];
const ALGORITHM_COLORS = { astar: "#1565c0", bfs: "#2e7d32", dfs: "#ef6c00" };

function average(values) {
  if (values.length === 0) return 0;
  return values.reduce((sum, v) => sum + v, 0) / values.length;
}

function buildAverages(routingComparison, field) {
  const perAlgorithm = { astar: [], bfs: [], dfs: [] };
  for (const algorithms of Object.values(routingComparison.routes)) {
    for (const algorithm of ALGORITHMS) {
      const result = algorithms[algorithm];
      if (result && Number.isFinite(result[field])) {
        perAlgorithm[algorithm].push(result[field]);
      }
    }
  }
  return ALGORITHMS.map((algorithm) => average(perAlgorithm[algorithm]));
}

function miniBarData(routingComparison, field) {
  return {
    labels: ALGORITHMS,
    datasets: [
      {
        data: buildAverages(routingComparison, field),
        backgroundColor: ALGORITHMS.map((a) => ALGORITHM_COLORS[a]),
      },
    ],
  };
}

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { display: false } },
  scales: { y: { beginAtZero: true } },
};

export default function RoutingChart({ routingComparison }) {
  if (!routingComparison) return null;

  return (
    <div className="chart-group">
      <h4>BFS vs DFS vs A*</h4>
      <div className="chart-row">
        <div className="chart-box">
          <p className="chart-label">Avg cost (h)</p>
          <Bar data={miniBarData(routingComparison, "cost")} options={chartOptions} />
        </div>
        <div className="chart-box">
          <p className="chart-label">Avg nodes explored</p>
          <Bar data={miniBarData(routingComparison, "nodes_explored")} options={chartOptions} />
        </div>
        <div className="chart-box">
          <p className="chart-label">Avg time (ms)</p>
          <Bar data={miniBarData(routingComparison, "exec_time_ms")} options={chartOptions} />
        </div>
      </div>
    </div>
  );
}
