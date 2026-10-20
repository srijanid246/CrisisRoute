import { useState } from "react";

import PlanningView from "./components/PlanningView.jsx";
import SimulationView from "./components/SimulationView.jsx";

const TABS = [
  { id: "planning", label: "Planning" },
  { id: "simulation", label: "Simulation" },
];

export default function App() {
  const [activeTab, setActiveTab] = useState("planning");

  return (
    <div className="app-layout">
      <div className="tab-bar">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            className={`tab-button ${activeTab === tab.id ? "tab-button-active" : ""}`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === "planning" ? <PlanningView /> : <SimulationView />}
    </div>
  );
}
