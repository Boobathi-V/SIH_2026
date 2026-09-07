import { useEffect, useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { predictFundusImage } from "../api";
import { saveScreeningSession, getSyncUploadedImage } from "../storage";

function Analysis() {
  const [progress, setProgress] = useState(15);
  const [currentStage, setCurrentStage] = useState("Initializing clinical screening pipeline...");
  const [error, setError] = useState(null);
  const [qualityRejection, setQualityRejection] = useState(null);
  const hasTriggeredRef = useRef(false);
  const navigate = useNavigate();

  const previewSrc = getSyncUploadedImage();
  const fileName = sessionStorage.getItem("retina_filename") || "retina.png";

  function dataURLtoBlob(dataurl) {
    const arr = dataurl.split(",");
    const mime = arr[0].match(/:(.*?);/)[1];
    const bstr = atob(arr[1]);
    let n = bstr.length;
    const u8arr = new Uint8Array(n);
    while (n--) {
      u8arr[n] = bstr.charCodeAt(n);
    }
    return new Blob([u8arr], { type: mime });
  }

  useEffect(() => {
    if (!previewSrc) {
      navigate("/upload");
      return;
    }

    if (hasTriggeredRef.current) return;
    hasTriggeredRef.current = true;

    async function runInference() {
      try {
        // Stage 1: Quality Gate Verification
        setProgress(25);
        setCurrentStage("Evaluating retinal quality gate (focus, illumination, FOV, reflectance)...");

        const imageBlob = dataURLtoBlob(previewSrc);
        const imageFile = new File([imageBlob], fileName, { type: imageBlob.type });

        // Stage 2: Illumination & Contrast Enhancement
        await new Promise((r) => setTimeout(r, 350));
        setProgress(50);
        setCurrentStage("Applying Ben Graham local contrast & CLAHE enhancement...");

        // Stage 3: Deep Feature Extraction
        const resultPromise = predictFundusImage(imageFile);

        await new Promise((r) => setTimeout(r, 400));
        setProgress(75);
        setCurrentStage("Extracting ResNet-50 pathological feature representations...");

        const result = await resultPromise;

        // Stage 4: Grad-CAM generation
        setProgress(90);
        setCurrentStage("Synthesizing Grad-CAM pathological attention heatmap...");
        await new Promise((r) => setTimeout(r, 350));

        // Complete
        setProgress(100);
        setCurrentStage("Calibrating clinical confidence. Finalizing report...");

        // Save screening session safely using IndexedDB and in-memory cache (quota-safe)
        await saveScreeningSession(result, previewSrc);

        setTimeout(() => {
          navigate("/result");
        }, 600);
      } catch (err) {
        console.error("Inference failed:", err);
        if (err.isQualityRejection) {
          setQualityRejection({
            message: err.message,
            recaptureGuidance: err.recaptureGuidance,
            qualityGate: err.qualityGate || {},
            failureCategory: err.failureCategory || err.qualityGate?.failure_category,
            detailedExplanation: err.detailedExplanation || err.qualityGate?.detailed_explanation,
            checks: err.checks || err.qualityGate?.checks || [],
            qualityScore: err.qualityGate?.quality_score,
          });
        } else {
          setError(err.message || "Failed to communicate with AI Model backend.");
        }
      }
    }

    runInference();
  }, [previewSrc, fileName, navigate]);

  return (
    <div className="page-container">
      <div className="content-wrapper" style={{ maxWidth: "640px", textAlign: "center" }}>

        <div className="card" style={{ padding: "48px 32px" }}>
          {!qualityRejection && (
            <>
              <div style={{ width: "80px", height: "80px", margin: "0 auto 20px auto", position: "relative" }}>
                <div
                  style={{
                    width: "100%",
                    height: "100%",
                    borderRadius: "50%",
                    border: "4px solid #e0f2fe",
                    borderTopColor: "var(--primary)",
                    animation: "spin 1s linear infinite",
                  }}
                />
                <div
                  style={{
                    position: "absolute",
                    top: "50%",
                    left: "50%",
                    transform: "translate(-50%, -50%)",
                    fontSize: "28px",
                  }}
                >
                  👁️
                </div>
              </div>

              <style>
                {`
                  @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                  }
                `}
              </style>

              <h2 style={{ fontSize: "24px", marginBottom: "8px" }}>AI Clinical Analysis in Progress</h2>
              <p style={{ fontSize: "15px", color: "var(--text-muted)", marginBottom: "32px" }}>
                {currentStage}
              </p>

              {/* Progress Bar */}
              <div
                style={{
                  width: "100%",
                  height: "12px",
                  background: "#e2e8f0",
                  borderRadius: "9999px",
                  overflow: "hidden",
                  marginBottom: "12px",
                }}
              >
                <div
                  style={{
                    width: `${progress}%`,
                    height: "100%",
                    background: "linear-gradient(90deg, #0284c7 0%, #38bdf8 100%)",
                    borderRadius: "9999px",
                    transition: "width 0.3s ease",
                  }}
                />
              </div>

              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "13px", color: "var(--text-muted)" }}>
                <span>Input: {fileName}</span>
                <span>{progress}% Completed</span>
              </div>
            </>
          )}

          {/* Quality Rejection View */}
          {qualityRejection && (
            <div
              style={{
                textAlign: "left",
                background: "#fef2f2",
                border: "2px solid #ef4444",
                borderRadius: "14px",
                padding: "24px",
                boxShadow: "0 8px 24px rgba(239, 68, 68, 0.12)",
              }}
            >
              {/* Header */}
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "10px", marginBottom: "14px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                  <span style={{ fontSize: "32px", lineHeight: 1 }}>🚫</span>
                  <div>
                    <span style={{ fontSize: "11px", fontWeight: "800", color: "#b91c1c", textTransform: "uppercase", letterSpacing: "0.06em" }}>
                      Clinical Pre-Screening Quality Gate
                    </span>
                    <h3 style={{ color: "#991b1b", fontSize: "20px", margin: "2px 0 0 0", fontWeight: "800" }}>
                      {qualityRejection.message || "Image Rejected by Quality Gate"}
                    </h3>
                  </div>
                </div>

                {qualityRejection.qualityScore !== undefined && (
                  <div style={{ background: "#fee2e2", border: "1.5px solid #f87171", padding: "6px 14px", borderRadius: "10px", textAlign: "right" }}>
                    <span style={{ fontSize: "11px", color: "#7f1d1d", fontWeight: "700", display: "block" }}>Quality Score</span>
                    <span style={{ fontSize: "18px", fontWeight: "800", color: "#991b1b" }}>
                      {qualityRejection.qualityScore} / 100
                    </span>
                    <span style={{ fontSize: "10px", color: "#991b1b", display: "block" }}>Min 65.0 needed</span>
                  </div>
                )}
              </div>

              {/* Plain English Diagnostic Explanation with Medical Terms in Brackets */}
              {qualityRejection.detailedExplanation && (
                <div
                  style={{
                    background: "#ffffff",
                    padding: "16px 18px",
                    borderRadius: "10px",
                    border: "1px solid #fecaca",
                    marginBottom: "18px",
                  }}
                >
                  <strong style={{ color: "#991b1b", fontSize: "13px", textTransform: "uppercase", letterSpacing: "0.04em", display: "block", marginBottom: "6px" }}>
                    Why Was This Image Rejected?
                  </strong>
                  <p style={{ margin: 0, fontSize: "14px", color: "#334155", lineHeight: "1.65" }}>
                    {qualityRejection.detailedExplanation}
                  </p>
                </div>
              )}

              {/* 5-Pillar Quality Criteria Evaluation Checklist */}
              {qualityRejection.checks && qualityRejection.checks.length > 0 && (
                <div style={{ marginBottom: "18px" }}>
                  <span style={{ fontSize: "12px", fontWeight: "700", color: "#7f1d1d", textTransform: "uppercase", letterSpacing: "0.05em", display: "block", marginBottom: "10px" }}>
                    5-Pillar Quality Gate Breakdown:
                  </span>
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "10px" }}>
                    {qualityRejection.checks.map((chk, idx) => (
                      <div
                        key={idx}
                        style={{
                          background: chk.passed ? "#f0fdf4" : "#ffffff",
                          border: `1.5px solid ${chk.passed ? "#86efac" : "#f87171"}`,
                          borderRadius: "8px",
                          padding: "12px 14px",
                        }}
                      >
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
                          <strong style={{ fontSize: "13px", color: chk.passed ? "#166534" : "#991b1b" }}>
                            {chk.passed ? "✅" : "❌"} {chk.name}
                          </strong>
                          <span
                            style={{
                              fontSize: "10.5px",
                              fontWeight: "700",
                              padding: "2px 8px",
                              borderRadius: "4px",
                              background: chk.passed ? "#dcfce7" : "#fee2e2",
                              color: chk.passed ? "#15803d" : "#b91c1c",
                            }}
                          >
                            {chk.passed ? "PASSED" : "FAILED"}
                          </span>
                        </div>
                        <p style={{ margin: "2px 0", fontSize: "11.5px", color: "#475569", lineHeight: "1.4" }}>
                          {chk.description}
                        </p>
                        {chk.value && (
                          <span style={{ fontSize: "11px", color: "#64748b", display: "block", marginTop: "4px" }}>
                            <strong>Measured:</strong> {chk.value} • <em>({chk.requirement})</em>
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Actionable Step-by-Step Operator Recapture Instructions */}
              {qualityRejection.recaptureGuidance && (
                <div
                  style={{
                    background: "#ffffff",
                    padding: "16px 18px",
                    borderRadius: "10px",
                    border: "1.5px solid #fed7aa",
                    marginBottom: "20px",
                    boxShadow: "0 2px 8px rgba(251, 146, 60, 0.08)",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "8px" }}>
                    <span style={{ fontSize: "18px" }}>📷</span>
                    <strong style={{ color: "#c2410c", fontSize: "13.5px" }}>
                      Recapture Instructions for Health Worker / Operator:
                    </strong>
                  </div>
                  <div style={{ fontSize: "13px", color: "#334155", lineHeight: "1.6" }}>
                    {qualityRejection.recaptureGuidance.split("\n").map((line, idx) => (
                      <p key={idx} style={{ margin: "4px 0" }}>
                        {line}
                      </p>
                    ))}
                  </div>
                </div>
              )}

              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "10px" }}>
                <button
                  className="btn btn-secondary"
                  style={{ padding: "10px 20px", fontSize: "13px" }}
                  onClick={() => navigate("/patient")}
                >
                  ← Change Patient Details
                </button>

                <button
                  className="btn btn-primary"
                  style={{ padding: "10px 24px", fontSize: "14px" }}
                  onClick={() => navigate("/upload")}
                >
                  📁 Upload a Proper Fundus Photograph →
                </button>
              </div>
            </div>
          )}

          {/* Error Notice if Backend is not running */}
          {error && !qualityRejection && (
            <div
              style={{
                marginTop: "24px",
                padding: "16px",
                background: "#fef2f2",
                border: "1px solid #fecaca",
                borderRadius: "8px",
                textAlign: "left",
              }}
            >
              <h4 style={{ color: "#991b1b", fontSize: "15px", marginBottom: "4px" }}>
                ⚠️ AI Server Connection Error
              </h4>
              <p style={{ fontSize: "13px", color: "#b91c1c", marginBottom: "12px" }}>
                {error}
              </p>
              <p style={{ fontSize: "12px", color: "#7f1d1d", marginBottom: "16px" }}>
                Make sure the FastAPI backend is running in your terminal:
                <br />
                <code style={{ background: "#fee2e2", padding: "2px 6px", borderRadius: "4px" }}>
                  python api.py
                </code>
              </p>
              <div style={{ display: "flex", gap: "10px" }}>
                <button
                  className="btn btn-primary"
                  style={{ padding: "8px 18px", fontSize: "13px" }}
                  onClick={() => {
                    setError(null);
                    hasTriggeredRef.current = false;
                    window.location.reload();
                  }}
                >
                  Retry Analysis
                </button>
                <button
                  className="btn btn-secondary"
                  style={{ padding: "8px 18px", fontSize: "13px" }}
                  onClick={() => navigate("/upload")}
                >
                  Change Image
                </button>
              </div>
            </div>
          )}
        </div>

      </div>
    </div>
  );
}

export default Analysis;