import React from "react";

export default function BandwidthGauge({ bandwidth = {} }) {
  const {
    bandwidth_mbps = 10,
    upload_time_per_image_sec = 0.98,
    bandwidth_utilization_pct = 12.4,
    retry_count = 14,
    dropped_uploads = 3,
    total_data_uploaded_mb = 620,
  } = bandwidth;

  const isCongested = bandwidth_utilization_pct > 75;
  const isHighDelay = upload_time_per_image_sec > 4.0;

  return (
    <div className="card" style={{ padding: "20px", margin: 0 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
        <h4 style={{ fontSize: "15px", color: "var(--text-main)", margin: 0, fontWeight: "700" }}>
          📡 Rural Bandwidth & Uplink Delay
        </h4>
        <span
          style={{
            fontSize: "11px",
            fontWeight: "700",
            padding: "2px 8px",
            borderRadius: "4px",
            background: isCongested ? "#fef2f2" : "#f0fdf4",
            color: isCongested ? "#dc2626" : "#16a34a",
            border: `1px solid ${isCongested ? "#fecaca" : "#bbf7d0"}`,
          }}
        >
          {bandwidth_mbps} Mbps Uplink
        </span>
      </div>

      {/* Utilization Bar */}
      <div style={{ marginBottom: "14px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px", marginBottom: "4px" }}>
          <span style={{ color: "#475569" }}>Daily Link Utilization:</span>
          <strong style={{ color: isCongested ? "#dc2626" : "#0284c7" }}>
            {bandwidth_utilization_pct}%
          </strong>
        </div>
        <div style={{ width: "100%", height: "8px", background: "#f1f5f9", borderRadius: "9999px", overflow: "hidden" }}>
          <div
            style={{
              width: `${Math.min(100, bandwidth_utilization_pct)}%`,
              height: "100%",
              background: isCongested ? "#dc2626" : "#0284c7",
              borderRadius: "9999px",
              transition: "width 0.3s ease",
            }}
          />
        </div>
      </div>

      {/* Grid of Network Performance Stats */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px", fontSize: "12px" }}>
        <div style={{ background: "#f8fafc", padding: "8px 10px", borderRadius: "6px", border: "1px solid #e2e8f0" }}>
          <span style={{ color: "#64748b", display: "block" }}>Avg Upload Time:</span>
          <strong style={{ color: isHighDelay ? "#dc2626" : "#0f172a", fontSize: "14px" }}>
            {upload_time_per_image_sec}s / image
          </strong>
        </div>

        <div style={{ background: "#f8fafc", padding: "8px 10px", borderRadius: "6px", border: "1px solid #e2e8f0" }}>
          <span style={{ color: "#64748b", display: "block" }}>Transferred Volume:</span>
          <strong style={{ color: "#0f172a", fontSize: "14px" }}>
            {total_data_uploaded_mb} MB / day
          </strong>
        </div>

        <div style={{ background: "#f8fafc", padding: "8px 10px", borderRadius: "6px", border: "1px solid #e2e8f0" }}>
          <span style={{ color: "#64748b", display: "block" }}>Network Retries:</span>
          <strong style={{ color: retry_count > 30 ? "#d97706" : "#16a34a", fontSize: "14px" }}>
            {retry_count} packets
          </strong>
        </div>

        <div style={{ background: "#f8fafc", padding: "8px 10px", borderRadius: "6px", border: "1px solid #e2e8f0" }}>
          <span style={{ color: "#64748b", display: "block" }}>Dropped Captures:</span>
          <strong style={{ color: dropped_uploads > 5 ? "#dc2626" : "#16a34a", fontSize: "14px" }}>
            {dropped_uploads} drops
          </strong>
        </div>
      </div>
    </div>
  );
}
