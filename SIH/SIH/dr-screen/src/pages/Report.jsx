import { useNavigate } from "react-router-dom";
import { resolveHeatmapUrl } from "../api";

function Report() {
  const navigate = useNavigate();

  const patient = JSON.parse(localStorage.getItem("patient") || "{}");
  const rawResult = localStorage.getItem("screening_result");
  const result = rawResult ? JSON.parse(rawResult) : null;
  const originalImage = localStorage.getItem("uploaded_image");

  const heatmapSrc = result?.heatmap_base64
    ? `data:image/jpeg;base64,${result.heatmap_base64}`
    : result?.heatmap_url
    ? resolveHeatmapUrl(result.heatmap_url)
    : null;

  const today = new Date().toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });

  function handlePrint() {
    window.print();
  }

  return (
    <div className="page-container" style={{ background: "#f1f5f9" }}>
      <div className="content-wrapper" style={{ maxWidth: "880px" }}>

        {/* Action Header (Hidden in Print) */}
        <div className="no-print" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
          <button className="btn btn-secondary" onClick={() => navigate("/result")}>
            ← Back to Results
          </button>
          <div style={{ display: "flex", gap: "10px" }}>
            <button className="btn btn-primary" onClick={handlePrint}>
              🖨️ Print / Save as PDF
            </button>
            <button className="btn btn-secondary" onClick={() => navigate("/")}>
              + New Patient
            </button>
          </div>
        </div>

        {/* Printable Document Paper */}
        <div
          className="card"
          style={{
            background: "white",
            padding: "48px 40px",
            border: "1px solid #cbd5e1",
            borderRadius: "8px",
            boxShadow: "var(--shadow)",
          }}
        >

          {/* Header & Logo */}
          <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "2px solid #0f172a", paddingBottom: "20px", marginBottom: "28px" }}>
            <div>
              <h1 style={{ fontSize: "28px", color: "var(--primary-dark)", letterSpacing: "-0.02em" }}>
                DR Screen — AI Diagnostic Triage
              </h1>
              <p style={{ fontSize: "14px", color: "#475569", marginTop: "4px" }}>
                Smart India Hackathon 2026 • Automated Retinopathy Tele-Screening
              </p>
            </div>

            <div style={{ textAlign: "right" }}>
              <span style={{ fontSize: "12px", fontWeight: "700", background: "#f0fdf4", color: "#166534", padding: "4px 10px", borderRadius: "4px", border: "1px solid #bbf7d0" }}>
                VERIFIED AI REPORT
              </span>
              <p style={{ fontSize: "13px", color: "#64748b", marginTop: "6px" }}>
                Report Date: <strong>{today}</strong>
              </p>
            </div>
          </div>

          {/* Patient Details Table */}
          <h2 style={{ fontSize: "17px", color: "#0f172a", marginBottom: "12px" }}>1. Patient Information</h2>
          <table style={{ width: "100%", borderCollapse: "collapse", marginBottom: "28px", fontSize: "14px" }}>
            <tbody>
              <tr>
                <td style={{ padding: "8px 12px", border: "1px solid #e2e8f0", background: "#f8fafc", width: "25%", fontWeight: "600" }}>Patient ID</td>
                <td style={{ padding: "8px 12px", border: "1px solid #e2e8f0", width: "25%" }}>{patient.id || "P001"}</td>
                <td style={{ padding: "8px 12px", border: "1px solid #e2e8f0", background: "#f8fafc", width: "25%", fontWeight: "600" }}>Full Name</td>
                <td style={{ padding: "8px 12px", border: "1px solid #e2e8f0", width: "25%" }}>{patient.name || "Anonymous Patient"}</td>
              </tr>
              <tr>
                <td style={{ padding: "8px 12px", border: "1px solid #e2e8f0", background: "#f8fafc", fontWeight: "600" }}>Age</td>
                <td style={{ padding: "8px 12px", border: "1px solid #e2e8f0" }}>{patient.age || "N/A"} years</td>
                <td style={{ padding: "8px 12px", border: "1px solid #e2e8f0", background: "#f8fafc", fontWeight: "600" }}>Gender</td>
                <td style={{ padding: "8px 12px", border: "1px solid #e2e8f0" }}>{patient.gender || "N/A"}</td>
              </tr>
              <tr>
                <td style={{ padding: "8px 12px", border: "1px solid #e2e8f0", background: "#f8fafc", fontWeight: "600" }}>Eye Examined</td>
                <td style={{ padding: "8px 12px", border: "1px solid #e2e8f0", color: "var(--primary-dark)", fontWeight: "600" }}>{patient.eyeExamined || "Right Eye (OD)"}</td>
                <td style={{ padding: "8px 12px", border: "1px solid #e2e8f0", background: "#f8fafc", fontWeight: "600" }}>Diabetes Duration</td>
                <td style={{ padding: "8px 12px", border: "1px solid #e2e8f0" }}>{patient.diabetesDuration || "N/A"}</td>
              </tr>
            </tbody>
          </table>

          {/* Screening Outcome Summary */}
          <h2 style={{ fontSize: "17px", color: "#0f172a", marginBottom: "12px" }}>2. AI Screening Evaluation</h2>
          <table style={{ width: "100%", borderCollapse: "collapse", marginBottom: "28px", fontSize: "14px" }}>
            <tbody>
              <tr>
                <td style={{ padding: "10px 12px", border: "1px solid #e2e8f0", background: "#f8fafc", width: "35%", fontWeight: "600" }}>
                  Detected Severity Stage
                </td>
                <td style={{ padding: "10px 12px", border: "1px solid #e2e8f0", fontSize: "16px", fontWeight: "700" }}>
                  {result?.prediction || "No Data"} — {result?.clinical_severity || ""}
                </td>
              </tr>
              <tr>
                <td style={{ padding: "10px 12px", border: "1px solid #e2e8f0", background: "#f8fafc", fontWeight: "600" }}>
                  Clinical Risk Level
                </td>
                <td style={{ padding: "10px 12px", border: "1px solid #e2e8f0", fontWeight: "700" }}>
                  {result?.risk_level || "Unknown"}
                </td>
              </tr>
              <tr>
                <td style={{ padding: "10px 12px", border: "1px solid #e2e8f0", background: "#f8fafc", fontWeight: "600" }}>
                  Calibrated Confidence
                </td>
                <td style={{ padding: "10px 12px", border: "1px solid #e2e8f0", fontWeight: "700", color: "var(--primary)" }}>
                  {Math.round((result?.confidence || 0) * 100)}% (Temperature Scaled)
                </td>
              </tr>
              <tr>
                <td style={{ padding: "10px 12px", border: "1px solid #e2e8f0", background: "#f8fafc", fontWeight: "600" }}>
                  Neural Architecture
                </td>
                <td style={{ padding: "10px 12px", border: "1px solid #e2e8f0", color: "#475569" }}>
                  EfficientNetV2-S (384x384 resolution, Focal Loss multi-class transfer learning)
                </td>
              </tr>
            </tbody>
          </table>

          {/* Visual Evidence (Fundus + Grad-CAM Heatmap) */}
          <h2 style={{ fontSize: "17px", color: "#0f172a", marginBottom: "12px" }}>3. Photographic & XAI Visual Evidence</h2>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px", marginBottom: "28px" }}>
            <div style={{ border: "1px solid #cbd5e1", borderRadius: "6px", padding: "12px", textAlign: "center" }}>
              <p style={{ fontSize: "12px", fontWeight: "600", color: "#475569", marginBottom: "8px" }}>
                Patient Retinal Fundus Photograph
              </p>
              <div style={{ height: "240px", background: "#0f172a", display: "flex", alignItems: "center", justifyContent: "center" }}>
                {originalImage ? (
                  <img src={originalImage} alt="Original fundus" style={{ width: "100%", height: "100%", objectFit: "contain" }} />
                ) : (
                  <span style={{ color: "#94a3b8", fontSize: "12px" }}>No image available</span>
                )}
              </div>
            </div>

            <div style={{ border: "1px solid #cbd5e1", borderRadius: "6px", padding: "12px", textAlign: "center" }}>
              <p style={{ fontSize: "12px", fontWeight: "600", color: "#475569", marginBottom: "8px" }}>
                Grad-CAM Pathological Saliency Map
              </p>
              <div style={{ height: "240px", background: "#0f172a", display: "flex", alignItems: "center", justifyContent: "center" }}>
                {heatmapSrc ? (
                  <img src={heatmapSrc} alt="Grad-CAM overlay" style={{ width: "100%", height: "100%", objectFit: "contain" }} />
                ) : (
                  <span style={{ color: "#94a3b8", fontSize: "12px" }}>No heatmap available</span>
                )}
              </div>
            </div>
          </div>

          {/* Clinical Action Recommendation */}
          <div style={{ background: "#f0f9ff", border: "1.5px solid #bae6fd", padding: "20px", borderRadius: "8px", marginBottom: "28px" }}>
            <h3 style={{ fontSize: "15px", color: "var(--primary-dark)", marginBottom: "6px" }}>
              4. Recommended Clinical Protocol
            </h3>
            <p style={{ fontSize: "14px", color: "#0c4a6e", lineHeight: "1.5" }}>
              {result?.recommended_action || "Consult an eye-care specialist."}
            </p>
          </div>

          {/* Disclaimer & Signatures */}
          <div style={{ borderTop: "1px solid #e2e8f0", paddingTop: "20px", display: "grid", gridTemplateColumns: "1.5fr 1fr", gap: "24px" }}>
            <div>
              <p style={{ fontSize: "11px", color: "#64748b", lineHeight: "1.5" }}>
                <strong>Medical Disclaimer:</strong> This automated screening evaluation is an artificial intelligence decision-support tool. It does not constitute a definitive medical diagnosis. Final diagnostic confirmation and therapeutic decisions must be performed by a licensed ophthalmologist or optometrist.
              </p>
            </div>

            <div style={{ textAlign: "right" }}>
              <div style={{ height: "45px", borderBottom: "1px solid #94a3b8", width: "200px", marginLeft: "auto" }}></div>
              <p style={{ fontSize: "12px", fontWeight: "600", color: "#334155", marginTop: "6px" }}>
                Attending Reviewing Clinician
              </p>
            </div>
          </div>

        </div>

      </div>
    </div>
  );
}

export default Report;