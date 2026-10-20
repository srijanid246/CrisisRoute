import { useEffect, useMemo, useRef } from "react";

const TYPE_COLORS = {
  ASSIGNMENT: "#1565c0",
  STATUS_UPDATE: "#9e9e9e",
  ROUTE_BLOCKED: "#c62828",
  ZONE_REPORT: "#6a1b9a",
  TASK_COMPLETE: "#2e7d32",
  REQUEST_HELP: "#ef6c00",
};

function describe(message) {
  switch (message.type) {
    case "ASSIGNMENT":
      return message.payload.zone_id
        ? `-> zone ${message.payload.zone_id} (${message.payload.reason || "assignment"})`
        : "-> stand down";
    case "ROUTE_BLOCKED":
      return `edge (${message.payload.source},${message.payload.target}) blocked`;
    case "ZONE_REPORT":
      return `zone ${message.payload.zone?.id} observed`;
    case "TASK_COMPLETE":
      return message.payload.task || "task complete";
    case "REQUEST_HELP":
      return "requesting new assignment";
    case "STATUS_UPDATE":
      return message.payload.state || "";
    default:
      return "";
  }
}

export default function MessageLogPanel({ snapshots, tick, hideStatusUpdates, onToggleHideStatusUpdates }) {
  const listRef = useRef(null);

  const messages = useMemo(() => {
    const all = [];
    for (let i = 0; i <= tick && i < snapshots.length; i += 1) {
      for (const message of snapshots[i].messages) {
        if (hideStatusUpdates && message.type === "STATUS_UPDATE") continue;
        all.push(message);
      }
    }
    return all.slice(-80);
  }, [snapshots, tick, hideStatusUpdates]);

  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [messages]);

  return (
    <div className="message-log-panel">
      <div className="message-log-header">
        <h3>Message log</h3>
        <label className="message-log-toggle">
          <input type="checkbox" checked={hideStatusUpdates} onChange={onToggleHideStatusUpdates} />
          hide STATUS_UPDATE
        </label>
      </div>
      <div className="message-log-list" ref={listRef}>
        {messages.map((message, index) => (
          <div key={index} className="message-log-row">
            <span className="message-log-tick">t{message.tick}</span>
            <span className="message-log-type" style={{ color: TYPE_COLORS[message.type] || "#333" }}>
              {message.type}
            </span>
            <span className="message-log-sender">{message.sender}</span>
            <span className="message-log-desc">{describe(message)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
