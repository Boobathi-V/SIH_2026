import React from "react";

export default function OptimizationCard({ optimization = {} }) {
  const {
    primary_bottleneck = "System Well Balanced (No Critical Bottlenecks)",
    bottlenecks = [],
    recommendations = {},
  } = optimization;

  const {
    phcs = 25,
    ai_servers = 3,
    doctors = 5,
    bandwidth = "10 Mbps",
    estimated_daily_capacity = 333,
    estimated_annual_capacity = 99900,
    action_plan = "Maintain current balanced operational parameters.",
  } = recommendations;

  const isBalanced = bottlenecks.length === 0;

  return (
    <div
      className="card"
      style={{
        padding: "24px",
        background: isBalanced ? "linear-gradient(135deg, #ffffff 0%, #f0fdf4 100%)" : "linear-gradient(135deg, #ffffff 0%, #fffbeb 100%)",
        borderColor: isBalanced ? "#bbf7d0" : "#fde68a",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px", flexWrap: "wrap", gap: "10px" }}>
        <div>
          <span style={{ fontSize: "11px", fontWeight: "700", textTransform: "uppercase", color: isBalanced ? "#16a34a" : "#d97706", letterSpacing: "0.05em" }}>
            Automated Resource Optimization & Scaling Engine
          </span>
          <h3 style={{ fontSize: "18px", color: "#0f172a", margin: "4px 0 0 0", fontWeight: "700" }}>
            🎯 Healthcare Capacity & Bottleneck Diagnosis
          </h3>
        </div>
        <span
          style={{
            fontSize: "12px",
            fontWeight: "700",
            padding: "4px 12px",
            borderRadius: "9999px",
            background: isBalanced ? "#dcfce7" : "#fef3c7",
            color: isBalanced ? "#15803d" : "#b45309",
            border: `1px solid ${isBalanced ? "#86efac" : "#fcd34d"}`,
          }}
        >
          {isBalanced ? "✓ Status: Highly Optimized" : `⚠️ ${bottlenecks.length} Bottleneck(s) Detected`}
        </span>
      </div>

      {/* Primary Bottleneck Display */}
      <div
        style={{
          background: "#ffffff",
          padding: "14px 18px",
          borderRadius: "8px",
          border: "1px solid #e2e8f0",
          marginBottom: "18px",
        }}
      >
        <div style={{ fontSize: "12px", color: "#64748b", fontWeight: "600", textTransform: "uppercase" }}>
          Current Pipeline Bottleneck:
        </div>
        <div style={{ fontSize: "15px", fontWeight: "700", color: isBalanced ? "#15803d" : "#b91c1c", marginTop: "2px" }}>
          {primary_bottleneck}
        </div>
        {bottlenecks.map((b, idx) => (
          <div key={idx} style={{ fontSize: "12px", color: "#475569", marginTop: "4px", paddingLeft: "8px", borderLeft: "2px solid #cbd5e1" }}>
            • <strong>{b.component}</strong> ({b.severity} Severity): {b.impact}
          </div>
        ))}
      </div>

      {/* Recommended Scaling Specs */}
      <div style={{ marginBottom: "16px" }}>
        <div style={{ fontSize: "13px", fontWeight: "700", color: "#334155", marginBottom: "8px" }}>
          Recommended Resource Allocation for 100,000 Annual Screenings:
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))", gap: "10px" }}>
          <div style={{ background: "#ffffff", padding: "10px", borderRadius: "6px", border: "1px solid #e2e8f0", textAlign: "center" }}>
            <span style={{ fontSize: "11px", color: "#64748b", display: "block" }}>Primary Health Centers</span>
            <strong style={{ fontSize: "16px", color: "#0284c7" }}>{phcs} PHCs</strong>
          </div>
          <div style={{ background: "#ffffff", padding: "10px", borderRadius: "6px", border: "1px solid #e2e8f0", textAlign: "center" }}>
            <span style={{ fontSize: "11px", color: "#64748b", display: "block" }}>AI Inference Nodes</span>
            <strong style={{ fontSize: "16px", color: "#0284c7" }}>{ai_servers} Servers</strong>
          </div>
          <div style={{ background: "#ffffff", padding: "10px", borderRadius: "6px", border: "1px solid #e2e8f0", textAlign: "center" }}>
            <span style={{ fontSize: "11px", color: "#64748b", display: "block" }}>Reviewing Doctors</span>
            <strong style={{ fontSize: "16px", color: "#0284c7" }}>{doctors} Doctors</strong>
          </div>
          <div style={{ background: "#ffffff", padding: "10px", borderRadius: "6px", border: "1px solid #e2e8f0", textAlign: "center" }}>
            <span style={{ fontSize: "11px", color: "#64748b", display: "block" }}>PHC Uplink Tier</span>
            <strong style={{ fontSize: "16px", color: "#0284c7" }}>{bandwidth}</strong>
          </div>
        </div>
      </div>

      {/* Action Plan Text */}
      <div style={{ fontSize: "13px", color: "#334155", lineHeight: "1.5", background: "#ffffff", padding: "12px 16px", borderRadius: "6px", border: "1px solid #e2e8f0" }}>
        <strong>Actionable Recommendation:</strong> {action_plan}
      </div>
    </div>
  );
}
