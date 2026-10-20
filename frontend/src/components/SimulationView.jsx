import { useCallback, useEffect, useRef, useState } from "react";

import { createScenario, simulateScenario } from "../api.js";
import MessageLogPanel from "./MessageLogPanel.jsx";
import SimulationControls from "./SimulationControls.jsx";
import SimulationMap from "./SimulationMap.jsx";

const MAX_TICKS = 220;

export default function SimulationView() {
  const [data, setData] = useState(null);
  const [tick, setTick] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(5);
  const [busy, setBusy] = useState(false);
  const [statusMessage, setStatusMessage] = useState("");
  const [hideStatusUpdates, setHideStatusUpdates] = useState(true);
  const intervalRef = useRef(null);

  const handleLoad = useCallback(async () => {
    setBusy(true);
    setPlaying(false);
    setStatusMessage("Loading flood_demo_dynamic and running simulation...");
    try {
      const scenario = await createScenario({ preset: "flood_demo_dynamic" });
      const result = await simulateScenario(scenario.id, { max_ticks: MAX_TICKS, num_uavs: 1 });
      setData(result);
      setTick(0);
      setStatusMessage(`Simulated ${result.snapshots.length} ticks.`);
    } catch (error) {
      setStatusMessage(`Error: ${error.message}`);
    } finally {
      setBusy(false);
    }
  }, []);

  const maxTick = data ? data.snapshots.length - 1 : 0;

  useEffect(() => {
    if (!playing || !data) return undefined;
    intervalRef.current = setInterval(() => {
      setTick((current) => {
        if (current >= maxTick) {
          setPlaying(false);
          return current;
        }
        return current + 1;
      });
    }, 1000 / speed);
    return () => clearInterval(intervalRef.current);
  }, [playing, speed, data, maxTick]);

  const handleTogglePlay = useCallback(() => {
    if (!data) return;
    setPlaying((current) => {
      if (!current && tick >= maxTick) {
        setTick(0);
      }
      return !current;
    });
  }, [data, tick, maxTick]);

  const handleScrub = useCallback((value) => {
    setPlaying(false);
    setTick(value);
  }, []);

  return (
    <div className="app-top">
      <SimulationControls
        hasData={!!data}
        busy={busy}
        onLoad={handleLoad}
        playing={playing}
        onTogglePlay={handleTogglePlay}
        speed={speed}
        onSpeedChange={setSpeed}
        tick={tick}
        maxTick={maxTick}
        onScrub={handleScrub}
        metrics={data?.metrics}
        hiddenEvents={data?.hidden_events || []}
      />

      <div className="map-panel">
        {data ? (
          <SimulationMap
            initialScenario={data.initial_scenario}
            hiddenEvents={data.hidden_events}
            snapshots={data.snapshots}
            tick={tick}
          />
        ) : (
          <div className="map-placeholder">
            {statusMessage || "Load flood_demo_dynamic to run the simulation."}
          </div>
        )}
      </div>

      {data ? (
        <MessageLogPanel
          snapshots={data.snapshots}
          tick={tick}
          hideStatusUpdates={hideStatusUpdates}
          onToggleHideStatusUpdates={() => setHideStatusUpdates((v) => !v)}
        />
      ) : (
        <div className="panel right-panel">
          <p className="empty-note">{statusMessage}</p>
        </div>
      )}
    </div>
  );
}
