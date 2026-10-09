import React from "react";

export default function ScenarioSelector({ onSelectScenario, currentScenario }) {
  const scenarios = [
    {
      id: "normal",
      name: "Normal Day",
      desc: "333 Patients / Day (Baseline Target)",
      config: { patients_per_day: 333, bandwidth: "10 Mbps", ai_servers: 3, doctors: 5, phcs: 25 },
      icon: "🏢",
    },
    {
      id: "camp",
      name: "Village Camp Surge",
      desc: "1,000 Patients / Day (Mass Screening)",
      config: { patients_per_day: 1000, bandwidth: "10 Mbps", ai_servers: 4, doctors: 8, phcs: 40 },
      icon: "🏕️",
    },
    {
      id: "poor_net",
      name: "Poor Rural Network",
      desc: "1 Mbps 2G/3G Uplink (High Latency)",
      config: { patients_per_day: 333, bandwidth: "1 Mbps", ai_servers: 3, doctors: 5, phcs: 25 },
      icon: "📶",
    },
    {
      id: "fiber",
      name: "Fiber Optic PHC",
      desc: "20 Mbps High-Speed Uplink",
      config: { patients_per_day: 500, bandwidth: "20 Mbps", ai_servers: 3, doctors: 6, phcs: 30 },
      icon: "⚡",
    },
    {
      id: "server_fail",
      name: "Server Node Failure",
      desc: "1 AI Server Offline (Failover Test)",
      config: { patients_per_day: 400, bandwidth: "10 Mbps", ai_servers: 1, doctors: 5, phcs: 25 },
      icon: "⚠️",
    },
    {
      id: "doc_shortage",
      name: "Doctor Shortage",
      desc: "50% Ophthalmologist Availability",
      config: { patients_per_day: 333, bandwidth: "10 Mbps", ai_servers: 3, doctors: 2, phcs: 25 },
      icon: "🩺",
    },
    {
      id: "optimal",
      name: "Optimal Balanced",
      desc: "Zero-Bottleneck High-Capacity Config",
      config: { patients_per_day: 333, bandwidth: "10 Mbps", ai_servers: 3, doctors: 5, phcs: 25 },
      icon: "🎯",
    },
  ];

  return (
    <div className="card" style={{ padding: "20px", marginBottom: "24px" }}>
      <h3 style={{ fontSize: "16px", color: "var(--text-main)", margin: "0 0 12px 0", fontWeight: "700" }}>
        🕹️ Simulation Scenarios & Stress Presets
      </h3>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
          gap: "10px",
        }}
      >
        {scenarios.map((sc) => {
          const isActive = currentScenario === sc.id;
          return (
            <button
              key={sc.id}
              onClick={() => onSelectScenario(sc.id, sc.config)}
              style={{
                background: isActive ? "#e0f2fe" : "#ffffff",
                border: "1.5px solid",
                borderColor: isActive ? "#0284c7" : "#e2e8f0",
                borderRadius: "8px",
                padding: "10px 12px",
                textAlign: "left",
                cursor: "pointer",
                transition: "all 0.15s ease",
                display: "flex",
                alignItems: "flex-start",
                gap: "8px",
              }}
            >
              <span style={{ fontSize: "18px" }}>{sc.icon}</span>
              <div>
                <strong style={{ fontSize: "13px", color: isActive ? "#0369a1" : "#0f172a", display: "block" }}>
                  {sc.name}
                </strong>
                <span style={{ fontSize: "11px", color: "#64748b" }}>
                  {sc.desc}
                </span>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
