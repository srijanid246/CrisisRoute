import AllocationTable from "./AllocationTable.jsx";
import DiffView from "./DiffView.jsx";
import RiskTable from "./RiskTable.jsx";

export default function RightPanel({ scenario, plan, lastEvent }) {
  if (!scenario || !plan) {
    return (
      <div className="panel right-panel">
        <p className="empty-note">Load a scenario and generate a plan to see results.</p>
      </div>
    );
  }

  return (
    <div className="panel right-panel">
      <RiskTable scenario={scenario} plan={plan} />
      <AllocationTable scenario={scenario} plan={plan} />
      <DiffView event={lastEvent} />
    </div>
  );
}
