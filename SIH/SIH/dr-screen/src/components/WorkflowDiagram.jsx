import React from "react";

export default function WorkflowDiagram({ activeStep = 3 }) {
  const steps = [
    { id: 1, name: "Patient Registration", icon: "👤", desc: "PHC Community Intake" },
    { id: 2, name: "Fundus Capture", icon: "📸", desc: "Non-Mydriatic Camera" },
    { id: 3, name: "Quality Rejection Gate", icon: "🛡️", desc: "Blur, Focus & Illumination" },
    { id: 4, name: "Telemedicine Upload", icon: "📡", desc: "Rural 4G / Fiber Uplink" },
    { id: 5, name: "AI Screening Server", icon: "🧠", desc: "ResNet-50 5-Class Inference" },
    { id: 6, name: "Grad-CAM Heatmaps", icon: "🔥", desc: "Visual Attention Localization" },
    { id: 7, name: "Lesion Detection", icon: "🔴", desc: "MAs, Exudates & Hemorrhages" },
    { id: 8, name: "Doctor Review Queue", icon: "👨‍⚕️", desc: "Tele-Ophthalmologist Sign-off" },
    { id: 9, name: "Referral Report", icon: "📄", desc: "District Hospital Action Plan" },
  ];

  return (
    <div className="card" style={{ padding: "24px", marginBottom: "24px", overflowX: "auto" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
        <div>
          <h3 style={{ fontSize: "16px", color: "var(--text-main)", margin: 0, fontWeight: "700" }}>
            ⚡ Live Telemedicine Pipeline Architecture
          </h3>
          <p style={{ fontSize: "13px", color: "var(--text-muted)", margin: "4px 0 0 0" }}>
            End-to-end discrete event flow from rural PHC fundus acquisition to tertiary hospital referral
          </p>
        </div>
        <span
          style={{
            fontSize: "12px",
            fontWeight: "600",
            background: "#eff6ff",
            color: "#0284c7",
            padding: "4px 10px",
            borderRadius: "9999px",
            border: "1px solid #bfdbfe",
          }}
        >
          Simulink Discrete-Event Model
        </span>
      </div>

      {/* Horizontal Workflow Stepper */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "8px",
          minWidth: "880px",
          padding: "12px 4px",
        }}
      >
        {steps.map((step, idx) => (
          <React.Fragment key={step.id}>
            <div
              style={{
                flex: "1",
                minWidth: "90px",
                background: idx + 1 <= 4 ? "#f8fafc" : idx + 1 <= 7 ? "#f0f9ff" : "#fefce8",
                border: "1.5px solid",
                borderColor: idx + 1 === 3 ? "#ef4444" : idx + 1 === 5 ? "#0284c7" : "#cbd5e1",
                borderRadius: "10px",
                padding: "10px 8px",
                textAlign: "center",
                boxShadow: "0 1px 3px rgba(0,0,0,0.05)",
                position: "relative",
              }}
            >
              <div style={{ fontSize: "20px", marginBottom: "4px" }}>{step.icon}</div>
              <div style={{ fontSize: "11px", fontWeight: "700", color: "#0f172a", lineHeight: "1.2" }}>
                {step.name}
              </div>
              <div style={{ fontSize: "10px", color: "#64748b", marginTop: "4px" }}>
                {step.desc}
              </div>
            </div>

            {idx < steps.length - 1 && (
              <div
                style={{
                  color: "#94a3b8",
                  fontSize: "14px",
                  fontWeight: "bold",
                  userSelect: "none",
                }}
              >
                →
              </div>
            )}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
}
