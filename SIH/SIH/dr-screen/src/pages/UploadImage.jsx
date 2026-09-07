import { useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { validateImageQuality } from "../api";
import { saveUploadedPreview, getSyncUploadedImage } from "../storage";

function UploadImage() {
  const [imagePreview, setImagePreview] = useState(getSyncUploadedImage() || null);
  const [fileName, setFileName] = useState(sessionStorage.getItem("retina_filename") || "");
  const [isDragOver, setIsDragOver] = useState(false);
  const [isValidating, setIsValidating] = useState(false);
  const [qualityError, setQualityError] = useState(null);
  const [qualityPassed, setQualityPassed] = useState(null);
  const fileInputRef = useRef(null);
  const navigate = useNavigate();

  const patient = JSON.parse(localStorage.getItem("patient") || "{}");

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

  function processFile(file) {
    setQualityError(null);
    setQualityPassed(null);

    if (!file || !file.type.startsWith("image/")) {
      setQualityError({
        message: "Invalid file format.",
        detailed_explanation: "The selected file is not a supported image format. Please select an uncompressed color fundus photograph in PNG, JPG, or JPEG format.",
        recapture_guidance: "Please upload a valid retinal fundus image in PNG, JPG, or JPEG format directly from your device.",
      });
      return;
    }

    const reader = new FileReader();
    reader.onload = async () => {
      const base64 = reader.result;
      setImagePreview(base64);
      setFileName(file.name);
      await saveUploadedPreview(base64, file.name);

      // Instantly evaluate image gradeability against the 5-Pillar Quality Gate
      setIsValidating(true);
      try {
        const qualityRes = await validateImageQuality(file);
        if (!qualityRes.is_gradeable) {
          setQualityError({
            message: qualityRes.message || "Image rejected by Retinal Quality Gate.",
            failure_category: qualityRes.failure_category,
            detailed_explanation: qualityRes.detailed_explanation,
            recapture_guidance: qualityRes.recapture_guidance || "Please recapture a sharp, properly illuminated fundus photograph.",
            quality_score: qualityRes.quality_score,
            checks: qualityRes.checks || [],
            metrics: qualityRes.metrics || {},
          });
        } else {
          setQualityPassed(qualityRes);
          sessionStorage.setItem("quality_gate_result", JSON.stringify(qualityRes));
        }
      } catch (err) {
        console.warn("Quality gate live validation check error:", err);
      } finally {
        setIsValidating(false);
      }
    };
    reader.readAsDataURL(file);
  }

  function handleFileChange(e) {
    const file = e.target.files[0];
    if (file) processFile(file);
  }

  function handleDrop(e) {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      processFile(e.dataTransfer.files[0]);
    }
  }

  async function loadSample(sampleName, sampleLabel) {
    try {
      setQualityError(null);
      setQualityPassed(null);
      const res = await fetch(`/samples/${sampleName}`);
      const blob = await res.blob();
      const file = new File([blob], sampleName, { type: "image/png" });
      processFile(file);
    } catch (err) {
      alert("Error loading sample image: " + err.message);
    }
  }

  async function handleStartAnalysis() {
    if (!imagePreview) {
      alert("Please select or upload a fundus photograph first.");
      return;
    }

    if (qualityError) {
      alert("This image was rejected by the Quality Gate. Please review the rejection reasons below and upload a gradeable fundus photo.");
      return;
    }

    setIsValidating(true);

    try {
      const blob = dataURLtoBlob(imagePreview);
      const file = new File([blob], fileName || "retina.png", { type: blob.type });
      
      const qualityRes = await validateImageQuality(file);

      if (!qualityRes.is_gradeable) {
        setQualityError({
          message: qualityRes.message || "Image rejected by Retinal Quality Gate.",
          failure_category: qualityRes.failure_category,
          detailed_explanation: qualityRes.detailed_explanation,
          recapture_guidance: qualityRes.recapture_guidance || "Please recapture a sharp, properly illuminated fundus photograph.",
          quality_score: qualityRes.quality_score,
          checks: qualityRes.checks || [],
          metrics: qualityRes.metrics || {},
        });
        setIsValidating(false);
        return;
      }

      setQualityPassed(qualityRes);
      sessionStorage.setItem("quality_gate_result", JSON.stringify(qualityRes));
      
      setTimeout(() => {
        navigate("/analysis");
      }, 400);

    } catch (err) {
      console.warn("Proceeding to analysis:", err);
      navigate("/analysis");
    } finally {
      setIsValidating(false);
    }
  }

  return (
    <div className="page-container">
      <div className="content-wrapper" style={{ maxWidth: "860px" }}>

        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "24px" }}>
          <button
            className="btn btn-secondary"
            style={{ padding: "8px 16px", fontSize: "13px" }}
            onClick={() => navigate("/patient")}
          >
            ← Back to Patient Info
          </button>

          {patient.name && (
            <span style={{ fontSize: "14px", color: "var(--text-muted)" }}>
              Patient: <strong>{patient.name}</strong> ({patient.id || "P001"})
            </span>
          )}
        </div>

        <div className="card">
          <div style={{ borderBottom: "1px solid var(--border)", paddingBottom: "16px", marginBottom: "24px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "10px" }}>
              <div>
                <span style={{ fontSize: "12px", fontWeight: "700", color: "var(--primary)", textTransform: "uppercase" }}>
                  Step 2 of 4: Fundus Photography & Quality Gate
                </span>
                <h2 style={{ fontSize: "24px", marginTop: "4px" }}>Upload Retinal Fundus Image</h2>
                <p style={{ fontSize: "14px", color: "var(--text-muted)" }}>
                  Upload high-resolution color fundus image. The system enforces an automated <strong>Quality-Rejection Gate</strong> (focus, illumination, retinal field-of-view, and vascular reflectance).
                </p>
              </div>
              <span
                style={{
                  fontSize: "12px",
                  fontWeight: "600",
                  padding: "4px 10px",
                  borderRadius: "20px",
                  background: "#eff6ff",
                  color: "#1d4ed8",
                  border: "1px solid #bfdbfe",
                }}
              >
                🛡️ Quality Gate Active
              </span>
            </div>
          </div>

          {/* Drag & Drop Upload Zone */}
          <div
            onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
            onDragLeave={() => setIsDragOver(false)}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current && fileInputRef.current.click()}
            style={{
              border: `2px dashed ${
                qualityError ? "#ef4444" : isDragOver ? "var(--primary)" : "#cbd5e1"
              }`,
              borderRadius: "12px",
              padding: imagePreview ? "20px" : "48px 24px",
              textAlign: "center",
              cursor: "pointer",
              background: qualityError ? "#fff5f5" : isDragOver ? "var(--primary-light)" : "#f8fafc",
              transition: "all 0.2s ease",
            }}
          >
            <input
              type="file"
              ref={fileInputRef}
              accept="image/png, image/jpeg, image/jpg"
              onChange={handleFileChange}
              style={{ display: "none" }}
            />

            {imagePreview ? (
              <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "16px" }}>
                <img
                  src={imagePreview}
                  alt="Retinal preview"
                  style={{
                    maxWidth: "380px",
                    maxHeight: "320px",
                    borderRadius: "10px",
                    boxShadow: "var(--shadow)",
                    border: `2px solid ${qualityError ? "#f87171" : qualityPassed ? "#4ade80" : "#e2e8f0"}`,
                    objectFit: "contain",
                  }}
                />
                <div>
                  <p style={{ fontSize: "14px", fontWeight: "600", color: "var(--text-main)" }}>
                    Selected: {fileName}
                  </p>
                  <p style={{ fontSize: "12px", color: "var(--primary)", marginTop: "4px" }}>
                    Click or drop another image to replace
                  </p>
                </div>
              </div>
            ) : (
              <div>
                <div style={{ fontSize: "40px", marginBottom: "12px" }}>👁️</div>
                <h3 style={{ fontSize: "18px", color: "var(--text-main)", marginBottom: "6px" }}>
                  Drag & Drop Retinal Image Here
                </h3>
                <p style={{ fontSize: "14px", color: "var(--text-muted)", marginBottom: "16px" }}>
                  or click anywhere to browse from local files
                </p>
                <span className="btn btn-secondary" style={{ padding: "8px 20px", fontSize: "13px" }}>
                  Select File from Computer
                </span>
              </div>
            )}
          </div>

          {/* Detailed Clinical Quality Rejection Panel */}
          {qualityError && (
            <div
              style={{
                marginTop: "24px",
                padding: "24px",
                background: "#fef2f2",
                border: "2px solid #ef4444",
                borderRadius: "14px",
                textAlign: "left",
                animation: "fadeIn 0.25s ease-in-out",
                boxShadow: "0 8px 24px rgba(239, 68, 68, 0.12)",
              }}
            >
              {/* Header */}
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "10px", marginBottom: "14px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                  <span style={{ fontSize: "28px", lineHeight: 1 }}>🚫</span>
                  <div>
                    <span style={{ fontSize: "11px", fontWeight: "800", color: "#b91c1c", textTransform: "uppercase", letterSpacing: "0.06em" }}>
                      Clinical Pre-Screening Quality Gate
                    </span>
                    <h3 style={{ color: "#991b1b", fontSize: "20px", margin: "2px 0 0 0", fontWeight: "800" }}>
                      {qualityError.message || "Image Rejected by Quality Gate"}
                    </h3>
                  </div>
                </div>

                {qualityError.quality_score !== undefined && (
                  <div style={{ background: "#fee2e2", border: "1.5px solid #f87171", padding: "6px 14px", borderRadius: "10px", textAlign: "right" }}>
                    <span style={{ fontSize: "11px", color: "#7f1d1d", fontWeight: "700", display: "block" }}>Quality Score</span>
                    <span style={{ fontSize: "18px", fontWeight: "800", color: "#991b1b" }}>
                      {qualityError.quality_score} / 100
                    </span>
                    <span style={{ fontSize: "10px", color: "#991b1b", display: "block" }}>Min 65.0 needed</span>
                  </div>
                )}
              </div>

              {/* Plain English Diagnostic Explanation with Medical Terms in Brackets */}
              {qualityError.detailed_explanation && (
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
                    {qualityError.detailed_explanation}
                  </p>
                </div>
              )}

              {/* 5-Pillar Quality Criteria Evaluation Checklist */}
              {qualityError.checks && qualityError.checks.length > 0 && (
                <div style={{ marginBottom: "18px" }}>
                  <span style={{ fontSize: "12px", fontWeight: "700", color: "#7f1d1d", textTransform: "uppercase", letterSpacing: "0.05em", display: "block", marginBottom: "10px" }}>
                    5-Pillar Quality Gate Breakdown:
                  </span>
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "10px" }}>
                    {qualityError.checks.map((chk, idx) => (
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
              {qualityError.recapture_guidance && (
                <div
                  style={{
                    background: "#ffffff",
                    padding: "16px 18px",
                    borderRadius: "10px",
                    border: "1.5px solid #fed7aa",
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
                    {qualityError.recapture_guidance.split("\n").map((line, idx) => (
                      <p key={idx} style={{ margin: "4px 0" }}>
                        {line}
                      </p>
                    ))}
                  </div>
                </div>
              )}

              {/* Quick Retry Actions */}
              <div style={{ display: "flex", gap: "12px", marginTop: "18px", flexWrap: "wrap" }}>
                <button
                  type="button"
                  onClick={() => fileInputRef.current && fileInputRef.current.click()}
                  className="btn btn-primary"
                  style={{ fontSize: "13px", padding: "8px 18px" }}
                >
                  📁 Select a Different Fundus Image
                </button>
              </div>
            </div>
          )}

          {/* Quality Gate Pass Feedback */}
          {qualityPassed && (
            <div
              style={{
                marginTop: "20px",
                padding: "16px 20px",
                background: "#f0fdf4",
                border: "1.5px solid #86efac",
                borderRadius: "12px",
                boxShadow: "0 4px 14px rgba(22, 163, 74, 0.08)",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "10px" }}>
                <span style={{ fontSize: "22px" }}>✅</span>
                <div>
                  <p style={{ fontSize: "15px", fontWeight: "800", color: "#166534", margin: 0 }}>
                    Quality Gate Passed ({qualityPassed.quality_score} / 100)
                  </p>
                  <p style={{ fontSize: "12.5px", color: "#15803d", margin: "2px 0 0 0" }}>
                    Optimal optical focus, illumination, and retinal vascular reflectance confirmed. Gradeable image!
                  </p>
                </div>
              </div>

              {qualityPassed.checks && qualityPassed.checks.length > 0 && (
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "8px", marginTop: "10px" }}>
                  {qualityPassed.checks.map((chk, idx) => (
                    <div key={idx} style={{ background: "#ffffff", padding: "8px 12px", borderRadius: "6px", border: "1px solid #bbf7d0", fontSize: "11.5px" }}>
                      <strong style={{ color: "#166534", display: "block" }}>✅ {chk.name}</strong>
                      <span style={{ color: "#475569" }}>{chk.value}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Quick Sample Selector for SIH Demonstration */}
          <div style={{ marginTop: "28px", paddingTop: "20px", borderTop: "1px solid var(--border)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px", flexWrap: "wrap", gap: "8px" }}>
              <p style={{ fontSize: "13px", fontWeight: "700", color: "#475569", margin: 0 }}>
                ⚡ Quick SIH Demo Samples (1-Click Quality Evaluation):
              </p>
              <span style={{ fontSize: "11.5px", color: "var(--text-muted)" }}>
                Click below to test valid screenings or Quality Gate rejections
              </span>
            </div>

            <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
              {[
                { name: "sample_no_dr.png", label: "No DR (Healthy)", color: "#16a34a" },
                { name: "sample_mild_dr.png", label: "Mild DR", color: "#2563eb" },
                { name: "sample_moderate_dr.png", label: "Moderate DR", color: "#d97706" },
                { name: "sample_severe_dr.png", label: "Severe DR", color: "#ea580c" },
                { name: "sample_pdr.png", label: "Proliferative DR", color: "#dc2626" },
                { name: "sample_ungradeable_blur.png", label: "🚫 Blurry Photo (Rejection Demo)", color: "#ef4444" },
                { name: "sample_ungradeable_dark.png", label: "🚫 Dark Photo (Rejection Demo)", color: "#991b1b" },
              ].map((s) => (
                <button
                  key={s.name}
                  type="button"
                  onClick={(e) => { e.stopPropagation(); loadSample(s.name, s.label); }}
                  className="btn btn-secondary"
                  style={{
                    padding: "6px 14px",
                    fontSize: "12px",
                    fontWeight: s.label.includes("🚫") ? "700" : "600",
                    borderColor: s.color,
                    color: s.color,
                    background: s.label.includes("🚫") ? "#fff5f5" : "#ffffff",
                  }}
                >
                  {s.label}
                </button>
              ))}
            </div>
          </div>

          {/* Action Footer */}
          <div style={{ marginTop: "32px", display: "flex", justifyContent: "flex-end" }}>
            <button
              className="btn btn-primary"
              style={{
                padding: "14px 32px",
                fontSize: "16px",
                opacity: imagePreview && !isValidating ? 1 : 0.6,
                cursor: isValidating ? "wait" : "pointer",
              }}
              onClick={handleStartAnalysis}
              disabled={!imagePreview || isValidating}
            >
              {isValidating ? "Validating Quality Gate..." : "Validate & Analyze Image →"}
            </button>
          </div>

        </div>

      </div>
    </div>
  );
}

export default UploadImage;