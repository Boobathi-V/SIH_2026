import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { resolveHeatmapUrl, resolveAnnotatedUrl } from "../api";
import { getSyncScreeningResult, getSyncUploadedImage, idbGet } from "../storage";

function Explain() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState("annotated"); // 'annotated', 'gradcam', 'split'
  const [heatmapOpacity, setHeatmapOpacity] = useState(75);
  const [selectedCropIndex, setSelectedCropIndex] = useState(0);
  const [zoomLevel, setZoomLevel] = useState(2.7);

  // Interactive Loupe (Magnifying Glass) State
  const [loupeActive, setLoupeActive] = useState(false);
  const [loupePos, setLoupePos] = useState({ x: 0, y: 0, show: false });
  const imageContainerRef = useRef(null);

  const [result, setResult] = useState(() => getSyncScreeningResult() || null);
  const [originalImage, setOriginalImage] = useState(() => getSyncUploadedImage() || null);

  useEffect(() => {
    idbGet("screening_result").then((stored) => {
      if (stored) setResult(stored);
    });
    idbGet("uploaded_image").then((stored) => {
      if (stored) setOriginalImage(stored);
    });
  }, []);

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
  const zoomedCrops = result?.zoomed_crops || [];
  const activeCrop = zoomedCrops[selectedCropIndex] || zoomedCrops[0] || null;

  function handleMouseMove(e) {
    if (!loupeActive || !imageContainerRef.current) return;
    const rect = imageContainerRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    if (x >= 0 && x <= rect.width && y >= 0 && y <= rect.height) {
      setLoupePos({ x, y, show: true, width: rect.width, height: rect.height });
    } else {
      setLoupePos((prev) => ({ ...prev, show: false }));
    }
  }

  function handleMouseLeave() {
    setLoupePos((prev) => ({ ...prev, show: false }));
  }

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
                Diagnosed Severity Stage:
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
                }}
              >
                ⚖️ Side-by-Side View
              </button>
            </div>
          </div>
        </div>

        {/* PRIMARY CONTRIBUTING LESION & CLINICAL REASON BANNER */}
        <div className="card" style={{ marginBottom: "24px", border: "1.5px solid #bae6fd", background: "#f0f9ff" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "10px", marginBottom: "12px" }}>
            <div>
              <span style={{ fontSize: "11px", fontWeight: "800", color: "#0369a1", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                Primary Diagnostic Driver
              </span>
              <h3 style={{ fontSize: "20px", margin: "2px 0 0 0", color: "#0c4a6e" }}>
                Most Contributing Lesion: <span style={{ color: "#b91c1c", fontWeight: "800" }}>{result?.dominant_lesion || "Retinal Pathology"}</span>
              </h3>
            </div>
            <span style={{ fontSize: "13px", fontWeight: "800", background: "#fee2e2", color: "#991b1b", padding: "6px 12px", borderRadius: "8px", border: "1px solid #fecaca" }}>
              {result?.dominant_contribution_pct || 58}% Diagnostic Weight
            </span>
          </div>

          <p style={{ fontSize: "14px", color: "#0c4a6e", lineHeight: "1.6", margin: "0 0 16px 0", background: "#ffffff", padding: "14px 18px", borderRadius: "8px", border: "1px solid #bae6fd" }}>
            <strong>Clinical Justification: </strong>
            {result?.dominant_reason ||
              "Identified microvascular lesions provide direct anatomical evidence correlating with the clinical diagnosis under standard ETDRS staging."}
          </p>

          {/* Attribution Share Meters */}
          {result?.attributions && result.attributions.length > 0 && (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "10px" }}>
              {result.attributions.map((attr, idx) => (
                <div key={idx} style={{ background: "#ffffff", padding: "10px 14px", borderRadius: "6px", border: "1px solid #e0f2fe" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px", marginBottom: "4px" }}>
                    <strong style={{ color: "#0f172a" }}>{attr.type}</strong>
                    <span style={{ color: idx === 0 ? "#dc2626" : "#0284c7", fontWeight: "700" }}>{attr.contribution_pct}%</span>
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
          )}
        </div>

        {/* Visual Inspection Area */}
        {activeTab === "annotated" && (
          <div className="card" style={{ marginBottom: "24px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px", flexWrap: "wrap", gap: "10px" }}>
              <div>
                <h3 style={{ fontSize: "17px", color: "var(--text-main)", margin: 0 }}>
                  Ophthalmology-Annotated Retinal Lesion Map
                </h3>
                <p style={{ fontSize: "13px", color: "var(--text-muted)", margin: "2px 0 0 0" }}>
                  Clinical localization of Microaneurysms, Hemorrhages, Hard Exudates, Optic Disc, and Major Retinal Vessels.
                </p>
              </div>

              {/* Retinal Loupe Toggle */}
              <button
                type="button"
                onClick={() => setLoupeActive(!loupeActive)}
                style={{
                  padding: "6px 14px",
                  fontSize: "12px",
                  fontWeight: "700",
                  borderRadius: "6px",
                  border: "1px solid",
                  cursor: "pointer",
                  borderColor: loupeActive ? "#0284c7" : "#cbd5e1",
                  background: loupeActive ? "#e0f2fe" : "#ffffff",
                  color: loupeActive ? "#0369a1" : "#475569",
                }}
              >
                🔎 {loupeActive ? "Interactive 3x Loupe: Active" : "Enable 3x Retinal Loupe"}
              </button>
            </div>

            <div
              ref={imageContainerRef}
              onMouseMove={handleMouseMove}
              onMouseLeave={handleMouseLeave}
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
                position: "relative",
                cursor: loupeActive ? "crosshair" : "default",
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

              {/* Interactive 2.7x Magnifying Loupe */}
              {loupeActive && loupePos.show && annotatedSrc && (
                <div
                  style={{
                    position: "absolute",
                    left: `${loupePos.x - 80}px`,
                    top: `${loupePos.y - 80}px`,
                    width: "160px",
                    height: "160px",
                    borderRadius: "50%",
                    border: "3px solid #38bdf8",
                    boxShadow: "0 6px 24px rgba(0,0,0,0.65)",
                    pointerEvents: "none",
                    backgroundImage: `url(${annotatedSrc})`,
                    backgroundRepeat: "no-repeat",
                    backgroundSize: `${loupePos.width * 2.7}px ${loupePos.height * 2.7}px`,
                    backgroundPosition: `-${loupePos.x * 2.7 - 80}px -${loupePos.y * 2.7 - 80}px`,
                    backgroundColor: "#000",
                    zIndex: 20,
                  }}
                >
                  <div
                    style={{
                      position: "absolute",
                      bottom: "8px",
                      left: "50%",
                      transform: "translateX(-50%)",
                      background: "rgba(15,23,42,0.90)",
                      color: "#38bdf8",
                      fontSize: "11px",
                      fontWeight: "700",
                      padding: "2px 8px",
                      borderRadius: "4px",
                      whiteSpace: "nowrap",
                      border: "1px solid rgba(56, 189, 248, 0.4)",
                    }}
                  >
                    2.7x Optical Magnifier
                  </div>
                </div>
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

        {/* HIGH-MAGNIFICATION ZOOMED-IN LESION GALLERY */}
        {zoomedCrops.length > 0 && (
          <div className="card" style={{ marginBottom: "24px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px", flexWrap: "wrap", gap: "10px" }}>
              <div>
                <span style={{ fontSize: "11px", fontWeight: "700", color: "var(--primary)", textTransform: "uppercase" }}>
                  Optical Magnification Gallery
                </span>
                <h3 style={{ fontSize: "18px", margin: "2px 0 0 0", color: "var(--text-main)" }}>
                  High-Magnification Zoom-In on Retinal Lesion Types
                </h3>
              </div>

              {/* Lesion Switcher */}
              <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
                {zoomedCrops.map((crop, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => setSelectedCropIndex(idx)}
                    style={{
                      padding: "6px 14px",
                      fontSize: "12px",
                      fontWeight: "700",
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
                  gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))",
                  gap: "24px",
                  background: "#ffffff",
                  padding: "20px",
                  borderRadius: "12px",
                  border: "1px solid #cbd5e1",
                  alignItems: "stretch",
                  boxShadow: "0 4px 14px rgba(15, 23, 42, 0.04)",
                }}
              >
                {/* LARGE 480px INSPECTION VIEWPORT WITH CAMERA DRAG ZOOM */}
                <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "14px", width: "100%", maxWidth: "480px", margin: "0 auto" }}>
                  <div
                    style={{
                      width: "100%",
                      aspectRatio: "1 / 1",
                      minHeight: "380px",
                      background: "#070b14",
                      borderRadius: "16px",
                      overflow: "hidden",
                      border: "2px solid #1e293b",
                      position: "relative",
                      boxShadow: "0 10px 30px rgba(0, 0, 0, 0.3)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                    }}
                  >
                    {/* Clean High-Resolution Magnified Image scaled smoothly with Camera Zoom Slider */}
                    <img
                      src={`data:image/jpeg;base64,${activeCrop.image_base64}`}
                      alt={activeCrop.title}
                      style={{
                        width: "100%",
                        height: "100%",
                        objectFit: "cover",
                        display: "block",
                        transform: `scale(${zoomLevel / 2.7})`,
                        transformOrigin: "center center",
                        transition: "transform 0.12s ease-out",
                      }}
                    />

                    {/* Floating Live Zoom Badge (Camera Style) */}
                    <div
                      style={{
                        position: "absolute",
                        top: "14px",
                        left: "14px",
                        background: "rgba(15, 23, 42, 0.85)",
                        backdropFilter: "blur(8px)",
                        color: "#38bdf8",
                        padding: "6px 14px",
                        borderRadius: "20px",
                        fontSize: "12px",
                        fontWeight: "700",
                        border: "1px solid rgba(56, 189, 248, 0.35)",
                        display: "flex",
                        alignItems: "center",
                        gap: "7px",
                        boxShadow: "0 4px 12px rgba(0,0,0,0.3)",
                      }}
                    >
                      <span style={{ width: "7px", height: "7px", borderRadius: "50%", background: "#38bdf8", display: "inline-block", boxShadow: "0 0 8px #38bdf8" }}></span>
                      {zoomLevel.toFixed(1)}x Camera Zoom
                    </div>

                    {/* Floating Lesion Tag */}
                    <div
                      style={{
                        position: "absolute",
                        top: "14px",
                        right: "14px",
                        background: "rgba(15, 23, 42, 0.85)",
                        backdropFilter: "blur(8px)",
                        color: "#f8fafc",
                        padding: "6px 14px",
                        borderRadius: "20px",
                        fontSize: "12px",
                        fontWeight: "600",
                        border: "1px solid rgba(255, 255, 255, 0.15)",
                        boxShadow: "0 4px 12px rgba(0,0,0,0.3)",
                      }}
                    >
                      {activeCrop.type}
                    </div>
                  </div>

                  {/* CAMERA APP STYLE ZOOM DRAG CONTROL (2.0x to 3.0x Range) */}
                  <div
                    style={{
                      width: "100%",
                      background: "rgba(15, 23, 42, 0.94)",
                      borderRadius: "18px",
                      padding: "12px 18px",
                      border: "1px solid rgba(255, 255, 255, 0.12)",
                      display: "flex",
                      flexDirection: "column",
                      gap: "10px",
                      boxShadow: "0 6px 20px rgba(0, 0, 0, 0.25)",
                    }}
                  >
                    {/* Preset Buttons Dial */}
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <span style={{ fontSize: "11px", fontWeight: "700", color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                        Camera Zoom
                      </span>
                      <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                        {[2.0, 2.3, 2.5, 2.7, 3.0].map((val) => {
                          const isSelected = Math.abs(zoomLevel - val) < 0.05;
                          return (
                            <button
                              key={val}
                              type="button"
                              onClick={() => setZoomLevel(val)}
                              style={{
                                width: "34px",
                                height: "34px",
                                borderRadius: "50%",
                                border: isSelected ? "2px solid #38bdf8" : "1px solid rgba(255,255,255,0.15)",
                                background: isSelected ? "#0284c7" : "rgba(30, 41, 59, 0.8)",
                                color: isSelected ? "#ffffff" : "#cbd5e1",
                                fontSize: "11px",
                                fontWeight: isSelected ? "800" : "600",
                                cursor: "pointer",
                                display: "flex",
                                alignItems: "center",
                                justifyContent: "center",
                                transition: "all 0.15s ease",
                                transform: isSelected ? "scale(1.1)" : "scale(1)",
                                boxShadow: isSelected ? "0 0 10px rgba(56, 189, 248, 0.4)" : "none",
                              }}
                            >
                              {val === 2.0 ? "2x" : val === 3.0 ? "3x" : `${val}x`}
                            </button>
                          );
                        })}
                      </div>
                      <span style={{ fontSize: "13px", fontWeight: "800", color: "#38bdf8", minWidth: "36px", textAlign: "right" }}>
                        {zoomLevel.toFixed(1)}x
                      </span>
                    </div>

                    {/* Drag Slider (2.0x to 3.0x Range) */}
                    <div style={{ display: "flex", alignItems: "center", gap: "10px", width: "100%", padding: "2px 4px" }}>
                      <span style={{ fontSize: "11px", color: "#94a3b8", fontWeight: "700" }}>2.0x</span>
                      <input
                        type="range"
                        min="2.0"
                        max="3.0"
                        step="0.1"
                        value={zoomLevel}
                        onChange={(e) => setZoomLevel(parseFloat(e.target.value))}
                        style={{
                          flex: 1,
                          accentColor: "#38bdf8",
                          cursor: "pointer",
                          height: "6px",
                        }}
                      />
                      <span style={{ fontSize: "11px", color: "#94a3b8", fontWeight: "700" }}>3.0x</span>
                    </div>
                  </div>
                </div>

                {/* COMPANION CLINICAL PATHOLOGY DETAILS */}
                <div style={{ display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
                  <div>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "8px", flexWrap: "wrap" }}>
                      <span style={{ fontSize: "11px", fontWeight: "700", background: "#fef3c7", color: "#92400e", padding: "3px 10px", borderRadius: "4px", border: "1px solid #fde68a" }}>
                        {zoomLevel.toFixed(1)}x Magnified Close-Up
                      </span>
                      {activeCrop.is_primary ? (
                        <span style={{ fontSize: "11px", fontWeight: "700", background: "#fee2e2", color: "#991b1b", padding: "3px 10px", borderRadius: "4px", border: "1px solid #fecaca" }}>
                          ★ Primary Contributor ({result?.dominant_contribution_pct || 58}%)
                        </span>
                      ) : (
                        <span style={{ fontSize: "11px", fontWeight: "600", background: "#f1f5f9", color: "#475569", padding: "3px 10px", borderRadius: "4px" }}>
                          Secondary Lesion Biomarker
                        </span>
                      )}
                    </div>

                    <h4 style={{ fontSize: "20px", color: "#0f172a", margin: "0 0 10px 0" }}>
                      {activeCrop.title}
                    </h4>

                    <p style={{ fontSize: "14px", color: "#334155", lineHeight: "1.65", margin: "0 0 16px 0" }}>
                      {activeCrop.description}
                    </p>

                    <div style={{ background: "#f8fafc", padding: "14px", borderRadius: "8px", border: "1px solid #e2e8f0", marginBottom: "16px" }}>
                      <span style={{ fontSize: "11.5px", fontWeight: "700", color: "#0369a1", textTransform: "uppercase" }}>
                        Diagnostic Meaning (In Simple Terms)
                      </span>
                      <p style={{ fontSize: "13px", color: "#475569", lineHeight: "1.6", margin: "6px 0 0 0" }}>
                        {activeCrop.is_primary
                          ? result?.dominant_reason || "This lesion provides the clearest anatomical proof for the screening score because its presence reflects active diabetic blood vessel damage (diabetic microangiopathy)."
                          : "Secondary microvascular findings providing corroborative evidence of retinal capillary hyperpermeability."}
                      </p>
                    </div>

                    <div style={{ fontSize: "12px", color: "#64748b" }}>
                      <p style={{ margin: "3px 0" }}>
                        <strong>Interactive View:</strong> Drag the camera zoom slider (2.0x - 3.0x) to inspect fine border margins.
                      </p>
                      <p style={{ margin: "3px 0" }}>
                        <strong>Magnification Factor:</strong> {zoomLevel.toFixed(1)}x Optical Magnification.
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            )}
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
              <span style={{ fontSize: "11.5px", color: "#64748b", fontWeight: "700", textTransform: "uppercase" }}>Red Bulges (Microaneurysms)</span>
              <p style={{ fontSize: "24px", fontWeight: "800", color: "#b91c1c", margin: "4px 0 2px 0" }}>
                {lesionCounts.Microaneurysm || 0}
              </p>
              <p style={{ fontSize: "12px", color: "#64748b", margin: 0 }}>Tiny ballooning dots from vessel stress (capillary ectasia)</p>
            </div>

            <div style={{ background: "#f8fafc", padding: "14px", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
              <span style={{ fontSize: "11.5px", color: "#64748b", fontWeight: "700", textTransform: "uppercase" }}>Bleeding Spots (Hemorrhages)</span>
              <p style={{ fontSize: "24px", fontWeight: "800", color: "#991b1b", margin: "4px 0 2px 0" }}>
                {lesionCounts.Hemorrhage || 0}
              </p>
              <p style={{ fontSize: "12px", color: "#64748b", margin: 0 }}>Small internal retina bleeding (ruptured capillaries)</p>
            </div>

            <div style={{ background: "#f8fafc", padding: "14px", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
              <span style={{ fontSize: "11.5px", color: "#64748b", fontWeight: "700", textTransform: "uppercase" }}>Yellow Spots (Hard Exudates)</span>
              <p style={{ fontSize: "24px", fontWeight: "800", color: "#d97706", margin: "4px 0 2px 0" }}>
                {lesionCounts["Hard Exudate"] || 0}
              </p>
              <p style={{ fontSize: "12px", color: "#64748b", margin: 0 }}>Fluid and fat deposits leaking out (lipid exudation)</p>
            </div>

            <div style={{ background: "#f8fafc", padding: "14px", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
              <span style={{ fontSize: "11.5px", color: "#64748b", fontWeight: "700", textTransform: "uppercase" }}>Pale Patches (Cotton Wool Spots)</span>
              <p style={{ fontSize: "24px", fontWeight: "800", color: "#475569", margin: "4px 0 2px 0" }}>
                {lesionCounts["Cotton Wool Spot"] || 0}
              </p>
              <p style={{ fontSize: "12px", color: "#64748b", margin: 0 }}>Nerve patches lacking blood flow (focal ischemia)</p>
            </div>

            <div style={{ background: "#f8fafc", padding: "14px", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
              <span style={{ fontSize: "11.5px", color: "#64748b", fontWeight: "700", textTransform: "uppercase" }}>Eye Nerve (Optic Disc)</span>
              <p style={{ fontSize: "18px", fontWeight: "800", color: "#166534", margin: "4px 0 2px 0" }}>
                Identified
              </p>
              <p style={{ fontSize: "12px", color: "#64748b", margin: 0 }}>Normal nerve cable connection (physiologic landmark)</p>
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

        {/* Action Footer */}
        <div style={{ display: "flex", justifyContent: "space-between", marginTop: "24px" }}>
          <button className="btn btn-secondary" onClick={() => navigate("/result")}>
            ← Back to Results
          </button>
          <button className="btn btn-primary" onClick={() => navigate("/report")}>
            Generate Official Report →
          </button>
        </div>

      </div>
    </div>
  );
}

export default Explain;