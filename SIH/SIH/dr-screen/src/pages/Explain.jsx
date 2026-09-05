import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { resolveHeatmapUrl } from "../api";

function Explain() {
  const navigate = useNavigate();
  const [opacity, setOpacity] = useState(80);

  const rawResult = localStorage.getItem("screening_result");
  const result = rawResult ? JSON.parse(rawResult) : null;
  const originalImage = localStorage.getItem("uploaded_image");

  const heatmapSrc = result?.heatmap_base64
    ? `data:image/jpeg;base64,${result.heatmap_base64}`
    : result?.heatmap_url
    ? resolveHeatmapUrl(result.heatmap_url)
    : null;

  const LESION_GUIDE = {
    0: {
      title: "Normal Retinal Findings",
      description: "No pathological microvascular alterations observed. Optic disc margins are sharp, macula is intact without edema or lipid exudation, and retinal vessel caliber is uniform.",
    },
    1: {
      title: "Microaneurysm Detection",
      description: "Localized capillary outpouchings (microaneurysms) appear as tiny punctate red dots, primarily focused in the parafoveal capillary net. The AI heatmap highlights focal capillary dilations.",
    },
    2: {
      title: "Hemorrhages & Hard Exudates",
      description: "Deep dot and blot hemorrhages along with yellow, well-demarcated lipid/protein deposits (hard exudates) signify vascular breakdown. The attention map focuses on areas of lipid leakage.",
    },
    3: {
      title: "Extensive Retinal Hypoxia & Cotton Wool Spots",
      description: "Multiple intraretinal microvascular abnormalities (IRMA), venous beading, and soft fluffy white nerve-fiber infarctions (cotton wool spots). Significant regional ischemia.",
    },
    4: {
      title: "Neovascularization & Preretinal Hemorrhage",
      description: "Frond-like proliferation of fragile new blood vessels (NVD/NVE) triggered by severe VEGF release, with risk of vitreous hemorrhage and tractional retinal detachment.",
    },
  };

  const currentGuide = LESION_GUIDE[result?.class_index ?? 0] || LESION_GUIDE[0];

  return (
    <div className="page-container">
      <div className="content-wrapper">

        {/* Top Header */}
        <div className="header-bar">
          <div>
            <span style={{ fontSize: "12px", fontWeight: "700", color: "var(--primary)", textTransform: "uppercase" }}>
              Explainable AI (XAI)
            </span>
            <h1 style={{ fontSize: "28px", marginTop: "4px" }}>Grad-CAM Retinal Attention Analysis</h1>
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

        {/* Subheader summary */}
        <div className="card" style={{ padding: "16px 24px", background: "#f8fafc", marginBottom: "24px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "12px" }}>
            <div>
              <span style={{ fontSize: "14px", color: "var(--text-muted)" }}>Diagnosis Stage:</span>{" "}
              <strong style={{ fontSize: "16px", color: "var(--text-main)" }}>{result?.prediction || "No Data"}</strong>{" "}
              <span style={{ fontSize: "14px", color: "var(--primary)" }}>({Math.round((result?.confidence || 0) * 100)}% confidence)</span>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
              <label style={{ fontSize: "13px", fontWeight: "600", color: "var(--text-main)" }}>
                Heatmap Intensity: {opacity}%
              </label>
              <input
                type="range"
                min="0"
                max="100"
                value={opacity}
                onChange={(e) => setOpacity(e.target.value)}
                style={{ width: "130px", cursor: "pointer" }}
              />
            </div>
          </div>
        </div>

        {/* Side-by-Side Visual Inspection Grid */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "24px", marginBottom: "24px" }}>

          {/* Original Retinal Image */}
          <div className="card" style={{ margin: 0, textAlign: "center" }}>
            <h3 style={{ fontSize: "16px", marginBottom: "12px", textAlign: "left" }}>
              1. Original Retinal Fundus Photograph
            </h3>
            <div
              style={{
                width: "100%",
                height: "380px",
                background: "#0f172a",
                borderRadius: "8px",
                overflow: "hidden",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              {originalImage ? (
                <img
                  src={originalImage}
                  alt="Original fundus"
                  style={{ width: "100%", height: "100%", objectFit: "contain" }}
                />
              ) : (
                <span style={{ color: "#64748b", fontSize: "14px" }}>No fundus image uploaded</span>
              )}
            </div>
            <p style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "10px", textAlign: "left" }}>
              Macula and optic disc centered fundus photograph prior to neural processing.
            </p>
          </div>

          {/* Grad-CAM Heatmap Overlay */}
          <div className="card" style={{ margin: 0, textAlign: "center" }}>
            <h3 style={{ fontSize: "16px", marginBottom: "12px", textAlign: "left" }}>
              2. Grad-CAM Pathological Saliency Map
            </h3>
            <div
              style={{
                width: "100%",
                height: "380px",
                background: "#0f172a",
                borderRadius: "8px",
                overflow: "hidden",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              {heatmapSrc ? (
                <img
                  src={heatmapSrc}
                  alt="Grad-CAM heatmap"
                  style={{
                    width: "100%",
                    height: "100%",
                    objectFit: "contain",
                    opacity: opacity / 100,
                    transition: "opacity 0.15s ease",
                  }}
                />
              ) : (
                <span style={{ color: "#64748b", fontSize: "14px" }}>Heatmap not available</span>
              )}
            </div>
            <p style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "10px", textAlign: "left" }}>
              Warm regions (red/yellow) indicate focal features contributing directly to classification.
            </p>
          </div>

        </div>

        {/* Clinical Pathological Interpretation Card */}
        <div className="card">
          <div style={{ borderBottom: "1px solid var(--border)", paddingBottom: "12px", marginBottom: "16px" }}>
            <span style={{ fontSize: "12px", fontWeight: "700", color: "var(--primary)", textTransform: "uppercase" }}>
              Clinical Pathology Correlation
            </span>
            <h3 style={{ fontSize: "18px", marginTop: "2px" }}>{currentGuide.title}</h3>
          </div>

          <p style={{ fontSize: "15px", color: "#334155", lineHeight: "1.6", marginBottom: "16px" }}>
            {currentGuide.description}
          </p>

          <div style={{ background: "#f8fafc", padding: "14px", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
            <p style={{ fontSize: "13px", color: "var(--text-muted)", margin: 0 }}>
              <strong>How Grad-CAM Works:</strong> Gradient-weighted Class Activation Mapping computes gradients of the target class score with respect to the final convolutional feature maps (`conv_head` of EfficientNetV2). Spatial activations highlighting microaneurysms, blot hemorrhages, or exudates confirm that the network learns clinically relevant features rather than spurious background artifacts.
            </p>
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