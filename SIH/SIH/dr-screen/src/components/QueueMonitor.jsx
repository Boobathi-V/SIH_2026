import React from "react";

export default function QueueMonitor({ doctorQueue = {}, aiServer = {} }) {
  const {
    reviewing_doctors = 5,
    referred_patients = 67,
    doctor_utilization_pct = 68.7,
    queue_length = 8,
    waiting_time_hours = 1.0,
    backlog_cases = 0,
  } = doctorQueue;

  const {
    ai_servers = 3,
    images_per_sec = 9.4,
    server_utilization_pct = 2.4,
  } = aiServer;

  const isDocOverloaded = doctor_utilization_pct > 85;

  return (
    <div className="card" style={{ padding: "20px", margin: 0 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
        <h4 style={{ fontSize: "15px", color: "var(--text-main)", margin: 0, fontWeight: "700" }}>
          👨‍⚕️ Specialist Review & AI Queue
        </h4>
        <span
          style={{
            fontSize: "11px",
            fontWeight: "700",
            padding: "2px 8px",
            borderRadius: "4px",
            background: isDocOverloaded ? "#fef2f2" : "#f0fdf4",
            color: isDocOverloaded ? "#dc2626" : "#16a34a",
            border: `1px solid ${isDocOverloaded ? "#fecaca" : "#bbf7d0"}`,
          }}
        >
          {reviewing_doctors} Ophthalmologists Active
        </span>
      </div>

      {/* Doctor Utilization Bar */}
      <div style={{ marginBottom: "14px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px", marginBottom: "4px" }}>
          <span style={{ color: "#475569" }}>Doctor Review Workload:</span>
          <strong style={{ color: isDocOverloaded ? "#dc2626" : "#0284c7" }}>
            {doctor_utilization_pct}%
          </strong>
        </div>
        <div style={{ width: "100%", height: "8px", background: "#f1f5f9", borderRadius: "9999px", overflow: "hidden" }}>
          <div
            style={{
              width: `${Math.min(100, doctor_utilization_pct)}%`,
              height: "100%",
              background: isDocOverloaded ? "#dc2626" : "#0284c7",
              borderRadius: "9999px",
              transition: "width 0.3s ease",
            }}
          />
        </div>
      </div>

      {/* Queue Statistics Grid */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px", fontSize: "12px" }}>
        <div style={{ background: "#f8fafc", padding: "8px 10px", borderRadius: "6px", border: "1px solid #e2e8f0" }}>
          <span style={{ color: "#64748b", display: "block" }}>Pending Reviews:</span>
          <strong style={{ color: queue_length > 25 ? "#dc2626" : "#0f172a", fontSize: "14px" }}>
            {queue_length} patients in queue
          </strong>
        </div>

        <div style={{ background: "#f8fafc", padding: "8px 10px", borderRadius: "6px", border: "1px solid #e2e8f0" }}>
          <span style={{ color: "#64748b", display: "block" }}>Avg Waiting Time:</span>
          <strong style={{ color: waiting_time_hours > 3.0 ? "#dc2626" : "#0f172a", fontSize: "14px" }}>
            {waiting_time_hours} hours
          </strong>
        </div>

        <div style={{ background: "#f8fafc", padding: "8px 10px", borderRadius: "6px", border: "1px solid #e2e8f0" }}>
          <span style={{ color: "#64748b", display: "block" }}>AI Cluster Velocity:</span>
          <strong style={{ color: "#16a34a", fontSize: "14px" }}>
            {images_per_sec} images / sec ({ai_servers} nodes)
          </strong>
        </div>

        <div style={{ background: "#f8fafc", padding: "8px 10px", borderRadius: "6px", border: "1px solid #e2e8f0" }}>
          <span style={{ color: "#64748b", display: "block" }}>End-of-Day Backlog:</span>
          <strong style={{ color: backlog_cases > 0 ? "#dc2626" : "#16a34a", fontSize: "14px" }}>
            {backlog_cases > 0 ? `${backlog_cases} cases carried over` : "0 (Cleared Same-Day)"}
          </strong>
        </div>
      </div>
    </div>
  );
}
