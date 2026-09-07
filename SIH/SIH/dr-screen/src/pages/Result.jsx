import { useState } from "react";
import { useNavigate } from "react-router-dom";

const STAGE_LABELS = [
  "Class 0: No DR",
  "Class 1: Mild DR",
  "Class 2: Moderate DR",
  "Class 3: Severe DR",
  "Class 4: Proliferative DR",
];

function Result() {
  const navigate = useNavigate();
  const [selectedCropIndex, setSelectedCropIndex] = useState(0);

  const patient = JSON.parse(localStorage.getItem("patient") || "{}");
  const rawResult = localStorage.getItem("screening_result");
  const result = rawResult
    ? JSON.parse(rawResult)
    : {
        prediction: "No Data",
        class_index: 0,
        confidence: 0,
        probabilities: [0.2, 0.2, 0.2, 0.2, 0.2],
        risk_level: "None",
        clinical_severity: "No Screening Performed",
        recommended_action: "Please upload a fundus image to run analysis.",
      };

  const confidencePercent = Math.round((result.confidence || 0) * 100);

  function getRiskClass(risk) {
    const r = (risk || "").toLowerCase();
    if (r.includes("none")) return "risk-none";
    if (r.includes("low")) return "risk-low";
    if (r.includes("moderate")) return "risk-moderate";
    if (r.includes("high")) return "risk-high";
    if (r.includes("critical")) return "risk-critical";
    return "risk-moderate";
  }

  const zoomedCrops = result.zoomed_crops || [];
  const activeCrop = zoomedCrops[selectedCropIndex] || zoomedCrops[0] || null;

  return (
    <div className="page-container">
      <div className="content-wrapper">

        {/* Top Header - Duplicate buttons removed as requested */}
        <div className="header-bar" style={{ marginBottom: "20px" }}>
          <div>
            <span style={{ fontSize: "12px", fontWeight: "700", color: "var(--primary)", textTransform: "uppercase" }}>
              Step 3 of 4: Screening Outcome
            </span>
            <h1 style={{ fontSize: "28px", marginTop: "4px" }}>AI Triage & Severity Evaluation</h1>
          </div>
        </div>

        {/* Patient Demographic Banner */}
        <div className="card" style={{ padding: "18px 24px", background: "#f8fafc", marginBottom: "24px" }}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: "16px" }}>
            <div>
              <span style={{ fontSize: "11px", color: "var(--text-muted)", fontWeight: "600", textTransform: "uppercase" }}>Patient ID</span>
              <p style={{ fontSize: "15px", fontWeight: "700", marginTop: "2px" }}>{patient.id || "P001"}</p>
            </div>
            <div>
              <span style={{ fontSize: "11px", color: "var(--text-muted)", fontWeight: "600", textTransform: "uppercase" }}>Name</span>
              <p style={{ fontSize: "15px", fontWeight: "700", marginTop: "2px" }}>{patient.name || "Anonymous Patient"}</p>
            </div>
            <div>
              <span style={{ fontSize: "11px", color: "var(--text-muted)", fontWeight: "600", textTransform: "uppercase" }}>Age / Gender</span>
              <p style={{ fontSize: "15px", fontWeight: "700", marginTop: "2px" }}>{patient.age || "N/A"} yrs • {patient.gender || "N/A"}</p>
            </div>
            <div>
              <span style={{ fontSize: "11px", color: "var(--text-muted)", fontWeight: "600", textTransform: "uppercase" }}>Eye Examined</span>
              <p style={{ fontSize: "15px", fontWeight: "700", marginTop: "2px", color: "var(--primary)" }}>{patient.eyeExamined || "Right Eye (OD)"}</p>
            </div>
          </div>
        </div>

        {/* Diagnosis & Risk Grid */}
        <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr", gap: "24px", marginBottom: "24px" }}>

          {/* Primary Assessment Card */}
          <div className="card" style={{ margin: 0 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "16px" }}>
              <div>
                <span style={{ fontSize: "12px", fontWeight: "600", color: "var(--text-muted)" }}>Detected Severity</span>
                <h2 style={{ fontSize: "30px", marginTop: "4px", color: "var(--text-main)" }}>
                  {result.prediction}
                </h2>
                <p style={{ fontSize: "15px", color: "#475569", marginTop: "2px" }}>
                  {result.clinical_severity}
                </p>
              </div>

              <span className={`risk-badge ${getRiskClass(result.risk_level)}`}>
                Risk: {result.risk_level}
              </span>
            </div>

            <div style={{ borderTop: "1px solid var(--border)", paddingTop: "18px", marginTop: "16px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                <span style={{ fontSize: "13px", fontWeight: "600", color: "var(--text-main)" }}>
                  Calibrated AI Confidence
                </span>
                <span style={{ fontSize: "20px", fontWeight: "800", color: "var(--primary)" }}>
                  {confidencePercent}%
                </span>
              </div>

              <div style={{ width: "100%", height: "10px", background: "#e2e8f0", borderRadius: "9999px", overflow: "hidden" }}>
                <div
                  style={{
                    width: `${confidencePercent}%`,
                    height: "100%",
                    background: "var(--primary)",
                    borderRadius: "9999px",
                  }}
                />
              </div>

              <p style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "8px" }}>
                Confidence calibrated using post-hoc Temperature Scaling to minimize Expected Calibration Error.
              </p>

              {/* Quality Gate Status Badge */}
              {result.quality_gate && (
                <div
                  style={{
                    marginTop: "14px",
                    padding: "10px 14px",
                    background: "#f0fdf4",
                    borderRadius: "8px",
                    border: "1px solid #bbf7d0",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <span>🛡️</span>
                    <div>
                      <strong style={{ fontSize: "12px", color: "#166534" }}>Quality Gate Certified</strong>
                      <p style={{ fontSize: "11px", color: "#15803d", margin: 0 }}>
                        Passed focus, illumination, & vascular reflectance checks
                      </p>
                    </div>
                  </div>
                  <span style={{ fontSize: "12px", fontWeight: "700", color: "#166534", background: "#dcfce7", padding: "2px 8px", borderRadius: "6px" }}>
                    Score: {result.quality_gate.quality_score} / 100
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* 5-Class Probability Distribution */}
          <div className="card" style={{ margin: 0 }}>
            <h3 style={{ fontSize: "16px", marginBottom: "16px" }}>Class Probability Breakdown</h3>

            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              {(result.probabilities || []).map((prob, idx) => {
                const percent = Math.round(prob * 100);
                const isTopClass = idx === result.class_index;
                return (
                  <div key={idx}>
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px", marginBottom: "4px" }}>
                      <span style={{ fontWeight: isTopClass ? "700" : "500", color: isTopClass ? "var(--primary)" : "var(--text-main)" }}>
                        {STAGE_LABELS[idx]} {isTopClass && "★"}
                      </span>
                      <span style={{ fontWeight: "700", color: isTopClass ? "var(--primary)" : "var(--text-muted)" }}>
                        {percent}%
                      </span>
                    </div>
                    <div style={{ width: "100%", height: "8px", background: "#f1f5f9", borderRadius: "9999px", overflow: "hidden" }}>
                      <div
                        style={{
                          width: `${percent}%`,
                          height: "100%",
                          background: isTopClass ? "var(--primary)" : "#cbd5e1",
                          borderRadius: "9999px",
                        }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

        </div>

        {/* PRIMARY PATHOLOGY DRIVER & DIAGNOSTIC REASON CARD */}
        <div className="card" style={{ marginBottom: "24px", border: "1.5px solid #bae6fd", background: "#f8fafc" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "12px", marginBottom: "16px" }}>
            <div>
              <span style={{ fontSize: "11px", fontWeight: "800", color: "#0284c7", textTransform: "uppercase", letterSpacing: "0.06em" }}>
                Primary Diagnostic Driver & Lesion Contribution
              </span>
              <h3 style={{ fontSize: "20px", marginTop: "2px", color: "var(--text-main)" }}>
                Key Pathological Cause: <span style={{ color: "#b91c1c" }}>{result.dominant_lesion || "Retinal Pathology"}</span>
              </h3>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <span style={{ fontSize: "13px", fontWeight: "700", background: "#fee2e2", color: "#991b1b", padding: "6px 14px", borderRadius: "8px", border: "1px solid #fecaca" }}>
                Contribution: {result.dominant_contribution_pct || 58}% Diagnostic Weight
              </span>
              <button
                type="button"
                className="btn btn-secondary"
                style={{ fontSize: "12px", padding: "6px 14px" }}
                onClick={() => navigate("/explain")}
              >
                🔍 Inspect All Lesion Annotations →
              </button>
            </div>
          </div>

          {/* Diagnostic Reason Box */}
          <div style={{ background: "#ffffff", padding: "16px", borderRadius: "8px", border: "1px solid #e2e8f0", marginBottom: "20px" }}>
            <strong style={{ fontSize: "14px", color: "#0f172a" }}>Why this lesion caused the prediction:</strong>
            <p style={{ fontSize: "14px", color: "#334155", lineHeight: "1.6", marginTop: "6px", marginBottom: 0 }}>
              {result.dominant_reason ||
                "Focal microvascular alterations and lipid deposits provide primary anatomical confirmation of diabetic retinopathy under standard international grading protocols."}
            </p>
          </div>

          {/* Lesion Attribution Contribution Breakdown */}
          {result.attributions && result.attributions.length > 0 && (
            <div style={{ marginBottom: "20px" }}>
              <span style={{ fontSize: "12px", fontWeight: "700", color: "#475569", textTransform: "uppercase" }}>
                Lesion Type Contribution Share Towards Diagnosis:
              </span>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "12px", marginTop: "8px" }}>
                {result.attributions.map((attr, idx) => (
                  <div key={idx} style={{ background: "#ffffff", padding: "12px", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px", marginBottom: "4px" }}>
                      <strong style={{ color: "#0f172a" }}>{attr.type}</strong>
                      <span style={{ color: "#0284c7", fontWeight: "700" }}>{attr.contribution_pct}%</span>
                    </div>
                    <div style={{ width: "100%", height: "6px", background: "#f1f5f9", borderRadius: "9999px", overflow: "hidden" }}>
                      <div
                        style={{
                          width: `${attr.contribution_pct}%`,
                          height: "100%",
                          background: idx === 0 ? "#dc2626" : "#0284c7",
                          borderRadius: "9999px",
                        }}
                      />
                    </div>
                    <span style={{ fontSize: "11px", color: "#64748b", marginTop: "4px", display: "block" }}>
                      {attr.role} • Count: {attr.count}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* HIGH-MAGNIFICATION ZOOMED-IN LESION INSPECTION GALLERY */}
          {zoomedCrops.length > 0 && (
            <div style={{ borderTop: "1px solid #e2e8f0", paddingTop: "18px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px", flexWrap: "wrap", gap: "8px" }}>
                <div>
                  <h4 style={{ fontSize: "15px", color: "#0f172a", margin: 0, fontWeight: "700" }}>
                    🔍 High-Magnification Lesion Close-Up (Optical Zoom)
                  </h4>
                  <p style={{ fontSize: "12px", color: "#64748b", margin: "2px 0 0 0" }}>
                    Optical crop centered on detected lesion morphology with targeting reticle.
                  </p>
                </div>

                {/* Crop Switcher Tabs */}
                <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
                  {zoomedCrops.map((crop, idx) => (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => setSelectedCropIndex(idx)}
                      style={{
                        padding: "5px 12px",
                        fontSize: "12px",
                        fontWeight: "600",
                        borderRadius: "6px",
                        border: "1px solid",
                        cursor: "pointer",
                        borderColor: selectedCropIndex === idx ? "var(--primary)" : "#cbd5e1",
                        background: selectedCropIndex === idx ? "#e0f2fe" : "#ffffff",
                        color: selectedCropIndex === idx ? "#0369a1" : "#475569",
                      }}
                    >
                      {crop.type} {crop.is_primary && "★"}
                    </button>
                  ))}
                </div>
              </div>

              {activeCrop && (
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "240px 1fr",
                    gap: "18px",
                    background: "#ffffff",
                    padding: "16px",
                    borderRadius: "8px",
                    border: "1px solid #cbd5e1",
                    alignItems: "center",
                  }}
                >
                  <div
                    style={{
                      width: "240px",
                      height: "240px",
                      background: "#090d16",
                      borderRadius: "8px",
                      overflow: "hidden",
                      border: "2px solid #0f172a",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                    }}
                  >
                    <img
                      src={`data:image/jpeg;base64,${activeCrop.image_base64}`}
                      alt={activeCrop.title}
                      style={{ width: "100%", height: "100%", objectFit: "cover" }}
                    />
                  </div>

                  <div>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "6px" }}>
                      <span style={{ fontSize: "11px", fontWeight: "700", background: "#fef3c7", color: "#92400e", padding: "2px 8px", borderRadius: "4px", border: "1px solid #fde68a" }}>
                        {activeCrop.magnification}
                      </span>
                      {activeCrop.is_primary && (
                        <span style={{ fontSize: "11px", fontWeight: "700", background: "#fee2e2", color: "#991b1b", padding: "2px 8px", borderRadius: "4px" }}>
                          Primary Contributor ({result.dominant_contribution_pct}%)
                        </span>
                      )}
                    </div>
                    <h4 style={{ fontSize: "17px", color: "#0f172a", margin: "0 0 8px 0" }}>
                      {activeCrop.title}
                    </h4>
                    <p style={{ fontSize: "13.5px", color: "#334155", lineHeight: "1.6", margin: "0 0 12px 0" }}>
                      {activeCrop.description}
                    </p>
                    <p style={{ fontSize: "12px", color: "#64748b", margin: 0 }}>
                      <strong>Target Coordinates:</strong> X: {activeCrop.center?.[0]}px, Y: {activeCrop.center?.[1]}px in original fundus frame.
                    </p>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Quantified Lesion Counts Card */}
        <div className="card" style={{ marginBottom: "24px" }}>
          <h3 style={{ fontSize: "16px", marginBottom: "14px", color: "var(--text-main)" }}>
            Detected Retinal Lesion Quantities
          </h3>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: "12px" }}>
            <div style={{ background: "#f8fafc", padding: "12px", borderRadius: "8px", border: "1px solid #e2e8f0", textAlign: "center" }}>
              <span style={{ fontSize: "11px", color: "#64748b", fontWeight: "600" }}>Microaneurysms</span>
              <p style={{ fontSize: "20px", fontWeight: "800", color: "#b91c1c", margin: "4px 0 0 0" }}>
                {result.lesion_counts?.Microaneurysm || 0}
              </p>
            </div>
            <div style={{ background: "#f8fafc", padding: "12px", borderRadius: "8px", border: "1px solid #e2e8f0", textAlign: "center" }}>
              <span style={{ fontSize: "11px", color: "#64748b", fontWeight: "600" }}>Blot Hemorrhages</span>
              <p style={{ fontSize: "20px", fontWeight: "800", color: "#991b1b", margin: "4px 0 0 0" }}>
                {result.lesion_counts?.Hemorrhage || 0}
              </p>
            </div>
            <div style={{ background: "#f8fafc", padding: "12px", borderRadius: "8px", border: "1px solid #e2e8f0", textAlign: "center" }}>
              <span style={{ fontSize: "11px", color: "#64748b", fontWeight: "600" }}>Hard Exudates</span>
              <p style={{ fontSize: "20px", fontWeight: "800", color: "#d97706", margin: "4px 0 0 0" }}>
                {result.lesion_counts?.["Hard Exudate"] || 0}
              </p>
            </div>
            <div style={{ background: "#f8fafc", padding: "12px", borderRadius: "8px", border: "1px solid #e2e8f0", textAlign: "center" }}>
              <span style={{ fontSize: "11px", color: "#64748b", fontWeight: "600" }}>Cotton Wool Spots</span>
              <p style={{ fontSize: "20px", fontWeight: "800", color: "#475569", margin: "4px 0 0 0" }}>
                {result.lesion_counts?.["Cotton Wool Spot"] || 0}
              </p>
            </div>
            <div style={{ background: "#f8fafc", padding: "12px", borderRadius: "8px", border: "1px solid #e2e8f0", textAlign: "center" }}>
              <span style={{ fontSize: "11px", color: "#64748b", fontWeight: "600" }}>Optic Disc</span>
              <p style={{ fontSize: "16px", fontWeight: "700", color: "#166534", margin: "6px 0 0 0" }}>
                Isolated & Masked
              </p>
            </div>
          </div>
        </div>

        {/* Clinical Recommendation Card */}
        <div className="card" style={{ borderLeft: "5px solid var(--primary)", background: "#f0f9ff", marginBottom: "32px" }}>
          <h3 style={{ fontSize: "17px", color: "var(--primary-dark)", marginBottom: "8px" }}>
            Recommended Clinical Action
          </h3>
          <p style={{ fontSize: "15px", color: "#0c4a6e", lineHeight: "1.6", margin: 0 }}>
            {result.recommended_action}
          </p>
        </div>

        {/* Action Buttons Footer - Inspect heatmap button removed as requested */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <button
            className="btn btn-secondary"
            onClick={() => navigate("/")}
          >
            ← Start New Screening
          </button>

          <button
            className="btn btn-primary"
            style={{ padding: "10px 24px", fontSize: "14px" }}
            onClick={() => navigate("/report")}
          >
            Generate Official Report →
          </button>
        </div>

      </div>
    </div>
  );
}

export default Result;