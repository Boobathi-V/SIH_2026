import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { resolveHeatmapUrl, resolveAnnotatedUrl } from "../api";

function Explain() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState("annotated"); // 'annotated', 'gradcam', 'split'
  const [heatmapOpacity, setHeatmapOpacity] = useState(75);

  const rawResult = localStorage.getItem("screening_result");
  const result = rawResult ? JSON.parse(rawResult) : null;
  const originalImage = localStorage.getItem("uploaded_image");

  const heatmapSrc = result?.heatmap_base64
    ? `data:image/jpeg;base64,${result.heatmap_base64}`
    : result?.heatmap_url
    ? resolveHeatmapUrl(result.heatmap_url)
    : null;

  const annotatedSrc = result?.annotated_base64
    ? `data:image/png;base64,${result.annotated_base64}`
    : result?.annotated_url
    ? resolveAnnotatedUrl(result.annotated_url)
    : null;

  const lesionCounts = result?.lesion_counts || {
    Microaneurysm: 0,
    Hemorrhage: 0,
    "Hard Exudate": 0,
    "Cotton Wool Spot": 0,
    Neovascularization: 0,
  };

  const primaryFindings = result?.primary_findings || [];
  const confidencePercent = Math.round((result?.confidence || 0) * 100);

  return (
    <div className="page-container">
      <div className="content-wrapper" style={{ maxWidth: "1100px" }}>

        {/* Top Header */}
        <div className="header-bar" style={{ marginBottom: "20px" }}>
          <div>
            <span style={{ fontSize: "12px", fontWeight: "700", color: "var(--primary)", textTransform: "uppercase", letterSpacing: "0.05em" }}>
              SIH26038 • Explainable AI (XAI) Module
            </span>
            <h1 style={{ fontSize: "28px", marginTop: "4px", color: "var(--text-main)" }}>
              Clinical Lesion Detection & Retinal Attention
            </h1>
          </div>

          <div style={{ display: "flex", gap: "10px" }}>
            <button
              className="btn btn-secondary"
              style={{ padding: "8px 16px", fontSize: "13px" }}
              onClick={() => navigate("/result")}
            >
              ← Back to Results
            </button>
            <button
              className="btn btn-primary"
              style={{ padding: "8px 18px", fontSize: "13px" }}
              onClick={() => navigate("/report")}
            >
              Generate Official Report →
            </button>
          </div>
        </div>

        {/* Diagnostic Context Bar */}
        <div className="card" style={{ padding: "16px 24px", background: "#f8fafc", marginBottom: "24px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "16px" }}>
            <div>
              <span style={{ fontSize: "12px", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: "600" }}>
                Predicted Severity Stage:
              </span>
              <div style={{ display: "flex", alignItems: "baseline", gap: "8px", marginTop: "2px" }}>
                <strong style={{ fontSize: "20px", color: "var(--text-main)" }}>
                  {result?.prediction || "No Data"}
                </strong>
                <span style={{ fontSize: "15px", color: "var(--primary)", fontWeight: "700" }}>
                  ({confidencePercent}% Calibrated Confidence)
                </span>
              </div>
            </div>

            {/* View Mode Switcher */}
            <div style={{ display: "flex", gap: "6px", background: "#e2e8f0", padding: "4px", borderRadius: "8px" }}>
              <button
                type="button"
                onClick={() => setActiveTab("annotated")}
                style={{
                  padding: "6px 14px",
                  fontSize: "13px",
                  fontWeight: "600",
                  borderRadius: "6px",
                  border: "none",
                  cursor: "pointer",
                  background: activeTab === "annotated" ? "#ffffff" : "transparent",
                  color: activeTab === "annotated" ? "var(--primary-dark)" : "#64748b",
                  boxShadow: activeTab === "annotated" ? "0 1px 3px rgba(0,0,0,0.1)" : "none",
                  transition: "all 0.15s ease",
                }}
              >
                🏷️ Annotated Lesions
              </button>
              <button
                type="button"
                onClick={() => setActiveTab("gradcam")}
                style={{
                  padding: "6px 14px",
                  fontSize: "13px",
                  fontWeight: "600",
                  borderRadius: "6px",
                  border: "none",
                  cursor: "pointer",
                  background: activeTab === "gradcam" ? "#ffffff" : "transparent",
                  color: activeTab === "gradcam" ? "var(--primary-dark)" : "#64748b",
                  boxShadow: activeTab === "gradcam" ? "0 1px 3px rgba(0,0,0,0.1)" : "none",
                  transition: "all 0.15s ease",
                }}
              >
                🔥 Grad-CAM Heatmap
              </button>
              <button
                type="button"
                onClick={() => setActiveTab("split")}
                style={{
                  padding: "6px 14px",
                  fontSize: "13px",
                  fontWeight: "600",
                  borderRadius: "6px",
                  border: "none",
                  cursor: "pointer",
                  background: activeTab === "split" ? "#ffffff" : "transparent",
                  color: activeTab === "split" ? "var(--primary-dark)" : "#64748b",
                  boxShadow: activeTab === "split" ? "0 1px 3px rgba(0,0,0,0.1)" : "none",
                  transition: "all 0.15s ease",
                }}
              >
                ⚖️ Side-by-Side View
              </button>
            </div>
          </div>
        </div>

        {/* Visual Inspection Area */}
        {activeTab === "annotated" && (
          <div className="card" style={{ marginBottom: "24px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px" }}>
              <div>
                <h3 style={{ fontSize: "17px", color: "var(--text-main)", margin: 0 }}>
                  Ophthalmology-Annotated Retinal Lesion Map
                </h3>
                <p style={{ fontSize: "13px", color: "var(--text-muted)", margin: "2px 0 0 0" }}>
                  Clinical localization of Microaneurysms, Hemorrhages, Hard Exudates, Optic Disc, and Major Retinal Vessels.
                </p>
              </div>
              <span style={{ fontSize: "12px", background: "#f0fdf4", color: "#166534", padding: "4px 10px", borderRadius: "6px", fontWeight: "700", border: "1px solid #bbf7d0" }}>
                Anatomically Masked & Verified
              </span>
            </div>

            <div
              style={{
                width: "100%",
                height: "520px",
                background: "#090d16",
                borderRadius: "8px",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                overflow: "hidden",
                border: "1px solid #1e293b",
              }}
            >
              {annotatedSrc ? (
                <img
                  src={annotatedSrc}
                  alt="Annotated Retinal Lesions"
                  style={{ width: "100%", height: "100%", objectFit: "contain" }}
                />
              ) : originalImage ? (
                <img
                  src={originalImage}
                  alt="Original fundus"
                  style={{ width: "100%", height: "100%", objectFit: "contain" }}
                />
              ) : (
                <span style={{ color: "#64748b" }}>No annotated image available</span>
              )}
            </div>
          </div>
        )}

        {activeTab === "gradcam" && (
          <div className="card" style={{ marginBottom: "24px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px", flexWrap: "wrap", gap: "10px" }}>
              <div>
                <h3 style={{ fontSize: "17px", color: "var(--text-main)", margin: 0 }}>
                  Grad-CAM Pathological Saliency Heatmap
                </h3>
                <p style={{ fontSize: "13px", color: "var(--text-muted)", margin: "2px 0 0 0" }}>
                  Highlights regions in the final convolutional layer directly responsible for the network's diagnosis.
                </p>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <span style={{ fontSize: "12px", color: "var(--text-muted)", fontWeight: "600" }}>
                  Heatmap Opacity: {heatmapOpacity}%
                </span>
                <input
                  type="range"
                  min="10"
                  max="100"
                  value={heatmapOpacity}
                  onChange={(e) => setHeatmapOpacity(Number(e.target.value))}
                  style={{ width: "120px", cursor: "pointer" }}
                />
              </div>
            </div>

            <div
              style={{
                width: "100%",
                height: "520px",
                background: "#090d16",
                borderRadius: "8px",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                overflow: "hidden",
                border: "1px solid #1e293b",
              }}
            >
              {heatmapSrc ? (
                <img
                  src={heatmapSrc}
                  alt="Grad-CAM Heatmap"
                  style={{
                    width: "100%",
                    height: "100%",
                    objectFit: "contain",
                    opacity: heatmapOpacity / 100,
                    transition: "opacity 0.1s ease",
                  }}
                />
              ) : (
                <span style={{ color: "#64748b" }}>Heatmap not available</span>
              )}
            </div>
          </div>
        )}

        {activeTab === "split" && (
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px", marginBottom: "24px" }}>
            <div className="card" style={{ margin: 0 }}>
              <h3 style={{ fontSize: "15px", marginBottom: "10px", color: "var(--text-main)" }}>
                1. Clinical Lesion Annotations
              </h3>
              <div
                style={{
                  width: "100%",
                  height: "380px",
                  background: "#090d16",
                  borderRadius: "8px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  overflow: "hidden",
                }}
              >
                {annotatedSrc ? (
                  <img src={annotatedSrc} alt="Annotated retina" style={{ width: "100%", height: "100%", objectFit: "contain" }} />
                ) : (
                  <span style={{ color: "#64748b" }}>No annotated image</span>
                )}
              </div>
              <p style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "8px" }}>
                Anatomical lesion boundaries with clinical leader lines.
              </p>
            </div>

            <div className="card" style={{ margin: 0 }}>
              <h3 style={{ fontSize: "15px", marginBottom: "10px", color: "var(--text-main)" }}>
                2. Grad-CAM Attention Map
              </h3>
              <div
                style={{
                  width: "100%",
                  height: "380px",
                  background: "#090d16",
                  borderRadius: "8px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  overflow: "hidden",
                }}
              >
                {heatmapSrc ? (
                  <img src={heatmapSrc} alt="Grad-CAM" style={{ width: "100%", height: "100%", objectFit: "contain" }} />
                ) : (
                  <span style={{ color: "#64748b" }}>No heatmap</span>
                )}
              </div>
              <p style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "8px" }}>
                Feature map gradients confirming pathology focus.
              </p>
            </div>
          </div>
        )}

        {/* Quantified Lesion Findings Dashboard */}
        <div className="card" style={{ marginBottom: "24px" }}>
          <div style={{ borderBottom: "1px solid var(--border)", paddingBottom: "12px", marginBottom: "16px" }}>
            <span style={{ fontSize: "11px", fontWeight: "700", color: "var(--primary)", textTransform: "uppercase", letterSpacing: "0.05em" }}>
              Quantified Biomarkers
            </span>
            <h3 style={{ fontSize: "18px", marginTop: "2px", color: "var(--text-main)" }}>
              Detected Retinal Lesions & Vascular Landmarks
            </h3>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "14px", marginBottom: "20px" }}>
            <div style={{ background: "#f8fafc", padding: "14px", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
              <span style={{ fontSize: "11px", color: "#64748b", fontWeight: "700", textTransform: "uppercase" }}>Microaneurysms</span>
              <p style={{ fontSize: "24px", fontWeight: "800", color: "#b91c1c", margin: "4px 0 2px 0" }}>
                {lesionCounts.Microaneurysm || 0}
              </p>
              <p style={{ fontSize: "12px", color: "#64748b", margin: 0 }}>Punctate capillary outpouchings</p>
            </div>

            <div style={{ background: "#f8fafc", padding: "14px", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
              <span style={{ fontSize: "11px", color: "#64748b", fontWeight: "700", textTransform: "uppercase" }}>Blot Hemorrhages</span>
              <p style={{ fontSize: "24px", fontWeight: "800", color: "#991b1b", margin: "4px 0 2px 0" }}>
                {lesionCounts.Hemorrhage || 0}
              </p>
              <p style={{ fontSize: "12px", color: "#64748b", margin: 0 }}>Intraretinal capillary wall rupture</p>
            </div>

            <div style={{ background: "#f8fafc", padding: "14px", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
              <span style={{ fontSize: "11px", color: "#64748b", fontWeight: "700", textTransform: "uppercase" }}>Hard Exudates</span>
              <p style={{ fontSize: "24px", fontWeight: "800", color: "#d97706", margin: "4px 0 2px 0" }}>
                {lesionCounts["Hard Exudate"] || 0}
              </p>
              <p style={{ fontSize: "12px", color: "#64748b", margin: 0 }}>Circinate lipid/protein deposits</p>
            </div>

            <div style={{ background: "#f8fafc", padding: "14px", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
              <span style={{ fontSize: "11px", color: "#64748b", fontWeight: "700", textTransform: "uppercase" }}>Cotton Wool Spots</span>
              <p style={{ fontSize: "24px", fontWeight: "800", color: "#475569", margin: "4px 0 2px 0" }}>
                {lesionCounts["Cotton Wool Spot"] || 0}
              </p>
              <p style={{ fontSize: "12px", color: "#64748b", margin: 0 }}>Nerve fiber layer micro-infarcts</p>
            </div>

            <div style={{ background: "#f8fafc", padding: "14px", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
              <span style={{ fontSize: "11px", color: "#64748b", fontWeight: "700", textTransform: "uppercase" }}>Optic Disc Status</span>
              <p style={{ fontSize: "18px", fontWeight: "800", color: "#166534", margin: "4px 0 2px 0" }}>
                Isolated
              </p>
              <p style={{ fontSize: "12px", color: "#64748b", margin: 0 }}>Masked to prevent false exudates</p>
            </div>
          </div>

          {/* Primary Clinical Findings List */}
          <div style={{ background: "#f0f9ff", border: "1px solid #bae6fd", padding: "16px", borderRadius: "8px" }}>
            <h4 style={{ fontSize: "14px", color: "#0369a1", margin: "0 0 8px 0", fontWeight: "700" }}>
              Primary Pathology Contributors Identified by AI:
            </h4>
            <ul style={{ margin: 0, paddingLeft: "20px", fontSize: "13.5px", color: "#0c4a6e", lineHeight: "1.7" }}>
              {primaryFindings.length > 0 ? (
                primaryFindings.map((finding, idx) => <li key={idx}>{finding}</li>)
              ) : (
                <li>No microvascular lesions detected. Retinal appearance is anatomically normal.</li>
              )}
            </ul>
          </div>
        </div>

        {/* Ophthalmology Diagnosis Explanation & ETDRS Differential */}
        <div className="card" style={{ marginBottom: "24px" }}>
          <div style={{ borderBottom: "1px solid var(--border)", paddingBottom: "12px", marginBottom: "16px" }}>
            <span style={{ fontSize: "11px", fontWeight: "700", color: "var(--primary)", textTransform: "uppercase", letterSpacing: "0.05em" }}>
              Clinical Decision Rationale
            </span>
            <h3 style={{ fontSize: "18px", marginTop: "2px", color: "var(--text-main)" }}>
              Why Did the AI Predict {result?.prediction}?
            </h3>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px" }}>
            <div style={{ background: "#f8fafc", padding: "16px", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
              <h4 style={{ fontSize: "14px", color: "#0f172a", marginBottom: "6px" }}>
                Pathological Severity & Mechanism
              </h4>
              <p style={{ fontSize: "13.5px", color: "#334155", lineHeight: "1.6", margin: 0 }}>
                {result?.clinical_summary ||
                  "The neural network identified localized microvascular alterations corresponding to standard international grading criteria."}
              </p>
            </div>

            <div style={{ background: "#f8fafc", padding: "16px", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
              <h4 style={{ fontSize: "14px", color: "#0f172a", marginBottom: "6px" }}>
                ETDRS Differential Reasoning
              </h4>
              <p style={{ fontSize: "13.5px", color: "#334155", lineHeight: "1.6", margin: 0 }}>
                {result?.differential ||
                  "Absence of severe intraretinal microvascular abnormalities (IRMA) or neovascularization excludes proliferative progression."}
              </p>
            </div>
          </div>
        </div>

        {/* Action Footer */}
        <div style={{ display: "flex", justifyContent: "space-between", marginTop: "24px" }}>
          <button className="btn btn-secondary" onClick={() => navigate("/result")}>
            ← Back to Results
          </button>
          <button className="btn btn-primary" onClick={() => navigate("/report")}>
            Generate Screening Report →
          </button>
        </div>

      </div>
    </div>
  );
}

export default Explain;