import React from "react";

export default function KPIDashboard({ kpis = [] }) {
  if (!kpis || kpis.length === 0) return null;

  const getStatusColors = (status) => {
    switch (status) {
      case "green":
        return { bg: "#f0fdf4", border: "#bbf7d0", text: "#166534", dot: "#22c55e" };
      case "yellow":
        return { bg: "#fffbeb", border: "#fde68a", text: "#92400e", dot: "#f59e0b" };
      case "red":
        return { bg: "#fef2f2", border: "#fecaca", text: "#991b1b", dot: "#ef4444" };
      default:
        return { bg: "#f8fafc", border: "#e2e8f0", text: "#334155", dot: "#64748b" };
    }
  };

  return (
    <div style={{ marginBottom: "24px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px" }}>
        <h3 style={{ fontSize: "16px", color: "var(--text-main)", margin: 0, fontWeight: "700" }}>
          📊 District Screening KPI Scorecard
        </h3>
        <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>
          Updated in real-time from analytical simulation engine
        </span>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
          gap: "14px",
        }}
      >
        {kpis.map((kpi, idx) => {
          const colors = getStatusColors(kpi.status);
          return (
            <div
              key={idx}
              className="card"
              style={{
                padding: "16px",
                margin: 0,
                background: colors.bg,
                borderColor: colors.border,
                borderTop: `4px solid ${colors.dot}`,
                display: "flex",
                flexDirection: "column",
                justifyContent: "space-between",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
                <span style={{ fontSize: "11.5px", fontWeight: "700", color: "#475569", textTransform: "uppercase" }}>
                  {kpi.label}
                </span>
                <span
                  style={{
                    width: "8px",
                    height: "8px",
                    borderRadius: "50%",
                    background: colors.dot,
                    display: "inline-block",
                  }}
                />
              </div>

              <div>
                <div style={{ fontSize: "24px", fontWeight: "800", color: colors.text, lineHeight: "1.1" }}>
                  {kpi.value}
                </div>
                <div style={{ fontSize: "11px", color: "#64748b", marginTop: "4px" }}>
                  {kpi.sub}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
