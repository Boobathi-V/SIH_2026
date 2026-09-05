import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { checkBackendHealth } from "../api";

function Home() {
  const navigate = useNavigate();
  const [backendStatus, setBackendStatus] = useState({ checking: true, online: false });

  useEffect(() => {
    checkBackendHealth().then((res) => {
      setBackendStatus({ checking: false, online: res.online });
    });
  }, []);

  return (
    <div className="page-container">
      <div className="content-wrapper">

        {/* Top bar with Backend Status Badge */}
        <div className="header-bar">
          <div>
            <h3 style={{ fontSize: "20px", color: "var(--primary)" }}>Smart India Hackathon 2026</h3>
            <p style={{ fontSize: "13px", color: "var(--text-muted)" }}>Project SIH26038 — Clinical Screening System</p>
          </div>

          <div>
            {backendStatus.checking ? (
              <span className="brand-badge" style={{ background: "#f1f5f9", color: "#475569" }}>
                Connecting to AI Engine...
              </span>
            ) : backendStatus.online ? (
              <span className="brand-badge">
                <span className="status-dot"></span>
                EfficientNetV2-S Model Online
              </span>
            ) : (
              <span className="brand-badge offline">
                <span className="status-dot offline"></span>
                Backend Offline (Start python api.py)
              </span>
            )}
          </div>
        </div>

        {/* Hero Card */}
        <div className="card" style={{ padding: "48px 36px", background: "linear-gradient(135deg, #ffffff 0%, #f0f9ff 100%)", borderColor: "#bae6fd" }}>
          <div style={{ maxWidth: "720px" }}>
            <span style={{ fontSize: "12px", fontWeight: "700", textTransform: "uppercase", letterSpacing: "0.08em", color: "var(--primary)" }}>
              AI-Powered Ophthalmology Triage
            </span>
            <h1 style={{ fontSize: "38px", margin: "12px 0 16px 0", lineHeight: "1.2" }}>
              Diabetic Retinopathy Screening & Explainable AI
            </h1>
            <p style={{ fontSize: "17px", color: "#475569", marginBottom: "32px", lineHeight: "1.6" }}>
              Automated 5-class severity classification from retinal fundus photographs. Incorporates deep feature extraction,
              post-hoc confidence calibration, and visual Grad-CAM heatmaps for interpretable clinical decision support.
            </p>

            <div style={{ display: "flex", gap: "16px", flexWrap: "wrap" }}>
              <button
                className="btn btn-primary"
                style={{ padding: "14px 32px", fontSize: "16px" }}
                onClick={() => navigate("/patient")}
              >
                Start New Patient Screening →
              </button>
            </div>
          </div>
        </div>

        {/* 5-Stage Clinical Severity Matrix */}
        <h2 style={{ fontSize: "20px", marginBottom: "16px" }}>Supported Diabetic Retinopathy Stages</h2>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))", gap: "16px", marginBottom: "32px" }}>
          {[
            { stage: "Class 0: No DR", risk: "None", color: "#16a34a", desc: "No detectable vascular lesions; annual screening." },
            { stage: "Class 1: Mild DR", risk: "Low", color: "#2563eb", desc: "Microaneurysms only; 6-12 month follow-up." },
            { stage: "Class 2: Moderate DR", risk: "Moderate", color: "#d97706", desc: "Hemorrhages and hard exudates; referral in 4-8 weeks." },
            { stage: "Class 3: Severe DR", risk: "High", color: "#ea580c", desc: "Cotton wool spots & venous beading; urgent referral." },
            { stage: "Class 4: Proliferative", risk: "Critical", color: "#dc2626", desc: "Neovascularization; emergency intervention." },
          ].map((item, idx) => (
            <div key={idx} className="card" style={{ padding: "20px", borderTop: `4px solid ${item.color}`, margin: 0 }}>
              <span style={{ fontSize: "11px", fontWeight: "700", color: item.color, textTransform: "uppercase" }}>
                Risk: {item.risk}
              </span>
              <h3 style={{ fontSize: "16px", margin: "6px 0 8px 0" }}>{item.stage}</h3>
              <p style={{ fontSize: "13px", color: "var(--text-muted)", lineHeight: "1.4" }}>{item.desc}</p>
            </div>
          ))}
        </div>

        {/* Technical Architecture Feature Highlights */}
        <div className="card" style={{ padding: "28px" }}>
          <h3 style={{ fontSize: "18px", marginBottom: "16px" }}>Technical Pipeline Highlights</h3>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "20px" }}>
            <div>
              <h4 style={{ fontSize: "15px", color: "var(--primary)" }}>✓ Medical-Grade Preprocessing</h4>
              <p style={{ fontSize: "13px", color: "var(--text-muted)" }}>Circular retinal masking, border removal, LAB CLAHE enhancement, and gamma normalization.</p>
            </div>
            <div>
              <h4 style={{ fontSize: "15px", color: "var(--primary)" }}>✓ EfficientNetV2-S Architecture</h4>
              <p style={{ fontSize: "13px", color: "var(--text-muted)" }}>High-accuracy transfer learning with multi-stage unfreezing and Multi-class Focal Loss.</p>
            </div>
            <div>
              <h4 style={{ fontSize: "15px", color: "var(--primary)" }}>✓ Explainable AI (Grad-CAM)</h4>
              <p style={{ fontSize: "13px", color: "var(--text-muted)" }}>Pixel-level attention heatmaps highlight specific hemorrhages and exudates triggering the diagnosis.</p>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}

export default Home;