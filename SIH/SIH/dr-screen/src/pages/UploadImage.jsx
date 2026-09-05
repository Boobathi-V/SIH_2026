import { useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { validateImageQuality } from "../api";

function UploadImage() {
  const [imagePreview, setImagePreview] = useState(sessionStorage.getItem("retina_preview") || null);
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
        recapture_guidance: "Please upload a valid retinal fundus image in PNG, JPG, or JPEG format.",
      });
      return;
    }

    const reader = new FileReader();
    reader.onload = () => {
      const base64 = reader.result;
      setImagePreview(base64);
      setFileName(file.name);
      sessionStorage.setItem("retina_preview", base64);
      sessionStorage.setItem("retina_filename", file.name);
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

    setQualityError(null);
    setIsValidating(true);

    try {
      // Run Image Quality Gate Check before proceeding to inference
      const blob = dataURLtoBlob(imagePreview);
      const file = new File([blob], fileName || "retina.png", { type: blob.type });
      
      const qualityRes = await validateImageQuality(file);

      if (!qualityRes.is_gradeable) {
        setQualityError({
          message: qualityRes.message || "Image rejected by Retinal Quality Gate.",
          recapture_guidance: qualityRes.recapture_guidance || "Please recapture a sharp, properly illuminated fundus photograph.",
          quality_score: qualityRes.quality_score,
          metrics: qualityRes.metrics,
        });
        setIsValidating(false);
        return;
      }

      // Quality Gate passed! Store details and navigate to analysis
      setQualityPassed(qualityRes);
      sessionStorage.setItem("quality_gate_result", JSON.stringify(qualityRes));
      
      setTimeout(() => {
        navigate("/analysis");
      }, 500);

    } catch (err) {
      console.warn("Quality gate validation request failed, proceeding with direct pipeline:", err);
      // If server is offline or doesn't support pre-check, let /analysis handle it
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

          {/* Quality Rejection Warning Box */}
          {qualityError && (
            <div
              style={{
                marginTop: "20px",
                padding: "16px 20px",
                background: "#fef2f2",
                border: "1px solid #fecaca",
                borderRadius: "10px",
                textAlign: "left",
                animation: "fadeIn 0.2s ease-in-out",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "8px" }}>
                <span style={{ fontSize: "20px" }}>🚫</span>
                <h4 style={{ color: "#991b1b", fontSize: "16px", margin: 0, fontWeight: "700" }}>
                  Image Rejected by Quality Gate
                </h4>
                {qualityError.quality_score !== undefined && (
                  <span
                    style={{
                      marginLeft: "auto",
                      fontSize: "12px",
                      fontWeight: "700",
                      background: "#fee2e2",
                      color: "#991b1b",
                      padding: "2px 8px",
                      borderRadius: "6px",
                    }}
                  >
                    Quality Score: {qualityError.quality_score} / 100
                  </span>
                )}
              </div>

              <p style={{ fontSize: "14px", color: "#b91c1c", marginBottom: "8px", fontWeight: "600" }}>
                {qualityError.message}
              </p>

              <div
                style={{
                  background: "#ffffff",
                  padding: "10px 14px",
                  borderRadius: "8px",
                  border: "1px solid #fee2e2",
                  fontSize: "13px",
                  color: "#475569",
                }}
              >
                <strong style={{ color: "#0f172a" }}>📷 Recapture Guidance for Health Worker:</strong>
                <p style={{ margin: "4px 0 0 0", color: "#334155" }}>
                  {qualityError.recapture_guidance}
                </p>
              </div>
            </div>
          )}

          {/* Quality Gate Pass Feedback */}
          {qualityPassed && (
            <div
              style={{
                marginTop: "20px",
                padding: "12px 18px",
                background: "#f0fdf4",
                border: "1px solid #bbf7d0",
                borderRadius: "10px",
                display: "flex",
                alignItems: "center",
                gap: "10px",
              }}
            >
              <span style={{ fontSize: "20px" }}>✅</span>
              <div>
                <p style={{ fontSize: "14px", fontWeight: "700", color: "#166534", margin: 0 }}>
                  Quality Gate Passed ({qualityPassed.quality_score} / 100)
                </p>
                <p style={{ fontSize: "12px", color: "#15803d", margin: 0 }}>
                  Optimal focus, illumination, and retinal vascular reflectance confirmed. Ready for screening!
                </p>
              </div>
            </div>
          )}

          {/* Quick Sample Selector for SIH Demonstration */}
          <div style={{ marginTop: "28px", paddingTop: "20px", borderTop: "1px solid var(--border)" }}>
            <p style={{ fontSize: "13px", fontWeight: "700", color: "#475569", marginBottom: "10px" }}>
              ⚡ Quick SIH Demo Samples (1-Click Evaluation):
            </p>
            <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
              {[
                { name: "sample_no_dr.png", label: "No DR (Healthy)", color: "#16a34a" },
                { name: "sample_mild_dr.png", label: "Mild DR", color: "#2563eb" },
                { name: "sample_moderate_dr.png", label: "Moderate DR", color: "#d97706" },
                { name: "sample_severe_dr.png", label: "Severe DR", color: "#ea580c" },
                { name: "sample_pdr.png", label: "Proliferative DR", color: "#dc2626" },
              ].map((s) => (
                <button
                  key={s.name}
                  type="button"
                  onClick={(e) => { e.stopPropagation(); loadSample(s.name, s.label); }}
                  className="btn btn-secondary"
                  style={{
                    padding: "6px 14px",
                    fontSize: "12px",
                    borderColor: s.color,
                    color: s.color,
                    background: "#ffffff",
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