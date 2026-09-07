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
            qualityGate: err.qualityGate,
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
                border: "1px solid #fecaca",
                borderRadius: "12px",
                padding: "24px",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "12px" }}>
                <span style={{ fontSize: "32px" }}>🚫</span>
                <div>
                  <h3 style={{ color: "#991b1b", fontSize: "20px", margin: 0, fontWeight: "700" }}>
                    Image Rejected by Quality Gate
                  </h3>
                  <p style={{ fontSize: "13px", color: "#b91c1c", margin: 0 }}>
                    SIH26038 Automated Pre-Screening Quality Assessment
                  </p>
                </div>
              </div>

              <div
                style={{
                  background: "#ffffff",
                  padding: "16px",
                  borderRadius: "8px",
                  border: "1px solid #fee2e2",
                  marginBottom: "16px",
                }}
              >
                <p style={{ fontSize: "15px", color: "#991b1b", fontWeight: "700", marginBottom: "8px" }}>
                  Reason: {qualityRejection.message}
                </p>
                <div style={{ fontSize: "13px", color: "#334155" }}>
                  <strong>Recapture Guidance for Field Health Worker:</strong>
                  <p style={{ marginTop: "4px", lineHeight: "1.5" }}>
                    {qualityRejection.recaptureGuidance}
                  </p>
                </div>
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "12px" }}>
                <button
                  className="btn btn-primary"
                  style={{ padding: "10px 24px", fontSize: "14px" }}
                  onClick={() => navigate("/upload")}
                >
                  ← Upload a Proper Fundus Photograph
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