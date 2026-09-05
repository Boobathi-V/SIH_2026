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

  return (
    <div className="page-container">
      <div className="content-wrapper">

        {/* Top Header */}
        <div className="header-bar">
          <div>
            <span style={{ fontSize: "12px", fontWeight: "700", color: "var(--primary)", textTransform: "uppercase" }}>
              Step 3 of 4: Screening Outcome
            </span>
            <h1 style={{ fontSize: "28px", marginTop: "4px" }}>AI Triage & Severity Evaluation</h1>
          </div>

          <div style={{ display: "flex", gap: "10px" }}>
            <button
              className="btn btn-secondary"
              style={{ padding: "8px 16px", fontSize: "13px" }}
              onClick={() => navigate("/explain")}
            >
              🔍 View Grad-CAM Explanation
            </button>
            <button
              className="btn btn-primary"
              style={{ padding: "8px 18px", fontSize: "13px" }}
              onClick={() => navigate("/report")}
            >
              📄 Generate Official Report
            </button>
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

        {/* Clinical Recommendation Card */}
        <div className="card" style={{ borderLeft: "5px solid var(--primary)", background: "#f0f9ff" }}>
          <h3 style={{ fontSize: "17px", color: "var(--primary-dark)", marginBottom: "8px" }}>
            Recommended Clinical Action
          </h3>
          <p style={{ fontSize: "15px", color: "#0c4a6e", lineHeight: "1.6" }}>
            {result.recommended_action}
          </p>
        </div>

        {/* Action Buttons Footer */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "32px" }}>
          <button
            className="btn btn-secondary"
            onClick={() => navigate("/")}
          >
            ← Start New Screening
          </button>

          <div style={{ display: "flex", gap: "12px" }}>
            <button
              className="btn btn-secondary"
              onClick={() => navigate("/explain")}
            >
              🔍 Inspect Attention Heatmap
            </button>
            <button
              className="btn btn-primary"
              onClick={() => navigate("/report")}
            >
              Generate Official Report →
            </button>
          </div>
        </div>

      </div>
    </div>
  );
}

export default Result;