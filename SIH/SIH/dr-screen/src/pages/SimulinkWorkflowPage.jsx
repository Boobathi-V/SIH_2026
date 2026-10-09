import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import WorkflowDiagram from "../components/WorkflowDiagram";
import KPIDashboard from "../components/KPIDashboard";
import BandwidthGauge from "../components/BandwidthGauge";
import QueueMonitor from "../components/QueueMonitor";
import ScenarioSelector from "../components/ScenarioSelector";
import OptimizationCard from "../components/OptimizationCard";
import { API_BASE_URL } from "../api";

export default function SimulinkWorkflowPage() {
  const navigate = useNavigate();

  // District Configuration State
  const [config, setConfig] = useState({
    district_population: 1000000,
    diabetic_population: 100000,
    patients_per_day: 333,
    phcs: 25,
    cameras: 2,
    technicians: 2,
    ai_servers: 3,
    doctors: 5,
    bandwidth: "10 Mbps",
    working_days: 300,
  });

  const [simulationData, setSimulationData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [currentScenario, setCurrentScenario] = useState("normal");

  // Client-side fallback calculation engine to ensure instant rendering with zero delay
  const calculateLocalSimulation = (c) => {
    const patients_per_day = c.patients_per_day || 333;
    const working_days = c.working_days || 300;
    const diabetic_pop = c.diabetic_population || 100000;
    const ai_servers = c.ai_servers || 3;
    const doctors = c.doctors || 5;
    const raw_bw = String(c.bandwidth || "10 Mbps");
    const bw_mbps = parseFloat(raw_bw.toLowerCase().replace("mbps", "").trim()) || 10.0;

    const total_images = patients_per_day * 2;
    const rejection_rate = 0.17;
    const rejected_images = Math.round(total_images * rejection_rate);
    const accepted_images = total_images - rejected_images;

    const upload_time = Number(((1.12 * 8) / bw_mbps + 0.08).toFixed(2));
    const clinic_day_sec = 8 * 3600;
    const bw_util = Math.min(100, Number(((accepted_images * 8.96) / (bw_mbps * clinic_day_sec) * 100).toFixed(1)));

    const ai_ips = Number(((1.0 / 0.32) * ai_servers).toFixed(1));
    const ai_util = Math.min(100, Number((((accepted_images * 0.32) / ai_servers) / clinic_day_sec * 100).toFixed(1)));

    const referred = Math.round(patients_per_day * 0.20);
    const doc_hours_needed = (referred * 4.0) / 60.0;
    const doc_hours_avail = doctors * 6.5;
    const doc_util = Math.min(100, Number(((doc_hours_needed / doc_hours_avail) * 100).toFixed(1)));
    const wait_time = doc_util > 90 ? Number((2.5 + (doc_util - 90) * 0.4).toFixed(1)) : Number(Math.max(0.2, (doc_util / 100) * 1.5).toFixed(1));
    const doc_queue = doc_util > 90 ? Math.round(referred * 0.45) : Math.max(1, Math.round(referred * 0.12));

    const annual_screened = patients_per_day * working_days;
    const diabetic_cov = Math.min(100, Number(((annual_screened / diabetic_pop) * 100).toFixed(1)));
    const days_to_target = Math.ceil(diabetic_pop / patients_per_day);
    const avg_latency = Number((upload_time + 0.32 + 0.15).toFixed(2));

    const bottlenecks = [];
    if (bw_mbps <= 2.0) bottlenecks.push({ component: "Rural Bandwidth", severity: "High", impact: "Upload delays & transmission retries limit throughput." });
    if (ai_util > 85.0) bottlenecks.push({ component: "AI Inference Servers", severity: "Medium", impact: "AI server cluster near peak saturation during surge camps." });
    if (doc_util > 85.0) bottlenecks.push({ component: "Ophthalmologist Review Queue", severity: "Critical", impact: "Doctor review backlog creates patient referral waiting delay." });

    return {
      config: c,
      summary: {
        patients_per_day,
        annual_patients_screened: annual_screened,
        diabetic_coverage_pct: diabetic_cov,
        days_to_complete_target: days_to_target,
        avg_processing_time_sec: avg_latency,
      },
      gateway: {
        total_images_captured: total_images,
        accepted_images,
        rejected_images,
        rejection_rate_pct: 17.0,
        acceptance_rate_pct: 83.0,
        reasons: [
          { reason: "Motion Blur", count: Math.round(rejected_images * 0.29), percentage: 29.4 },
          { reason: "Low Illumination / Underexposure", count: Math.round(rejected_images * 0.24), percentage: 23.5 },
          { reason: "Over Exposure / Flash Artifact", count: Math.round(rejected_images * 0.12), percentage: 11.8 },
          { reason: "Poor Optical Focus", count: Math.round(rejected_images * 0.18), percentage: 17.6 },
          { reason: "Retina Not Centered (Fovea Missed)", count: Math.round(rejected_images * 0.12), percentage: 11.8 },
          { reason: "Low Sensor Resolution / Partial", count: Math.round(rejected_images * 0.05), percentage: 5.9 },
        ],
      },
      bandwidth: {
        bandwidth_mbps: bw_mbps,
        upload_time_per_image_sec: upload_time,
        bandwidth_utilization_pct: bw_util,
        retry_count: Math.round(accepted_images * (bw_mbps <= 2 ? 0.13 : 0.03)),
        dropped_uploads: Math.round(accepted_images * (bw_mbps <= 2 ? 0.025 : 0.005)),
        total_data_uploaded_mb: Number((accepted_images * 1.12).toFixed(1)),
      },
      ai_server: {
        ai_servers,
        images_per_sec: ai_ips,
        avg_ai_latency_sec: 0.32,
        server_utilization_pct: ai_util,
      },
      doctor_queue: {
        reviewing_doctors: doctors,
        referred_patients: referred,
        doctor_utilization_pct: doc_util,
        queue_length: doc_queue,
        waiting_time_hours: wait_time,
        backlog_cases: doc_util > 95 ? Math.round(referred * 0.2) : 0,
      },
      kpis: [
        { label: "Daily Patients Screened", value: `${patients_per_day}`, sub: `${accepted_images} valid eye images`, status: patients_per_day >= 250 ? "green" : "yellow" },
        { label: "Gateway Acceptance", value: "83.0%", sub: `${rejected_images} recaptures guided`, status: "green" },
        { label: "Avg Pipeline Latency", value: `${avg_latency}s`, sub: "Upload + AI + Grad-CAM", status: avg_latency < 4.0 ? "green" : "yellow" },
        { label: "AI Cluster Utilization", value: `${ai_util}%`, sub: `${ai_servers} active AI nodes`, status: ai_util < 75 ? "green" : (ai_util < 90 ? "yellow" : "red") },
        { label: "Doctor Review Queue", value: `${doc_queue} cases`, sub: `${wait_time}h avg turnaround`, status: doc_util < 75 ? "green" : (doc_util < 90 ? "yellow" : "red") },
        { label: "Annual District Capacity", value: annual_screened.toLocaleString(), sub: `${diabetic_cov}% diabetic population`, status: diabetic_cov >= 80 ? "green" : "yellow" },
      ],
      optimization: {
        primary_bottleneck: bottlenecks.length > 0 ? bottlenecks[0].component : "System Well Balanced (No Critical Bottlenecks)",
        bottlenecks,
        recommendations: {
          phcs: Math.max(c.phcs, Math.ceil(patients_per_day / 25)),
          ai_servers: Math.max(2, Math.ceil((patients_per_day * 2 * 0.32) / 18000)),
          doctors: Math.max(2, Math.ceil((patients_per_day * 0.20 * 4.0) / (6.0 * 60))),
          bandwidth: bw_mbps < 10 ? "10 Mbps" : `${Math.round(bw_mbps)} Mbps`,
          action_plan: `Deploy ${Math.max(2, Math.ceil((patients_per_day * 2 * 0.32) / 18000))} AI nodes with ${bw_mbps < 10 ? "10 Mbps" : `${Math.round(bw_mbps)} Mbps`} uplink to support ${c.phcs} PHCs and ${c.doctors} doctors.`,
        },
      },
    };
  };

  // Call simulation backend whenever configuration changes
  const runSimulation = async (updatedConfig) => {
    setLoading(true);
    // Instant initial calculation
    setSimulationData(calculateLocalSimulation(updatedConfig));
    try {
      const response = await fetch(`${API_BASE_URL}/api/simulink/simulate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(updatedConfig),
      });
      if (response.ok) {
        const data = await response.json();
        setSimulationData(data);
      }
    } catch (err) {
      console.warn("Simulation API connecting in background:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    runSimulation(config);
  }, [config]);

  const handleInputChange = (field, value) => {
    setCurrentScenario("custom");
    setConfig((prev) => ({ ...prev, [field]: value }));
  };

  const handleScenarioSelect = (scenarioId, scenarioConfig) => {
    setCurrentScenario(scenarioId);
    setConfig((prev) => ({ ...prev, ...scenarioConfig }));
  };

  return (
    <div className="page-container">
      <div className="content-wrapper">
        {/* Navigation & Header */}
        <div className="header-bar">
          <div>
            <button
              onClick={() => navigate("/")}
              style={{
                background: "transparent",
                border: "none",
                color: "#0284c7",
                fontSize: "13px",
                fontWeight: "600",
                cursor: "pointer",
                padding: 0,
                marginBottom: "4px",
                display: "inline-flex",
                alignItems: "center",
                gap: "4px",
              }}
            >
              ← Return to Screening Home
            </button>
            <h1 style={{ fontSize: "28px", color: "var(--text-main)", margin: 0 }}>
              Simulink Workflow Simulation
            </h1>
            <p style={{ fontSize: "14px", color: "var(--text-muted)", margin: "4px 0 0 0" }}>
              District-Level AI Telemedicine Pipeline for Diabetic Retinopathy Screening (100,000+ Patients/Year)
            </p>
          </div>

          <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
            <span
              style={{
                background: "#f0f9ff",
                color: "#0369a1",
                border: "1px solid #bae6fd",
                padding: "6px 14px",
                borderRadius: "9999px",
                fontSize: "12px",
                fontWeight: "600",
              }}
            >
              {loading ? "Simulating..." : "● Simulink Engine Online"}
            </span>
          </div>
        </div>

        {/* Section 1: System Overview Card (Animated Horizontal Workflow) */}
        <WorkflowDiagram />

        {/* Section 9: Simulation Scenarios & Stress Presets */}
        <ScenarioSelector
          onSelectScenario={handleScenarioSelect}
          currentScenario={currentScenario}
        />

        {/* Section 2: District Configuration Controls */}
        <div className="card" style={{ padding: "24px", marginBottom: "24px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
            <h3 style={{ fontSize: "16px", color: "var(--text-main)", margin: 0, fontWeight: "700" }}>
              ⚙️ District Healthcare Resource Controls
            </h3>
            <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>
              Adjust sliders to dynamically simulate resource impact
            </span>
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
              gap: "18px",
            }}
          >
            {/* Patients per day slider */}
            <div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px", marginBottom: "4px" }}>
                <span style={{ fontWeight: "600", color: "#334155" }}>Daily Screening Arrivals:</span>
                <strong style={{ color: "#0284c7" }}>{config.patients_per_day} patients/day</strong>
              </div>
              <input
                type="range"
                min="100"
                max="1000"
                step="10"
                value={config.patients_per_day}
                onChange={(e) => handleInputChange("patients_per_day", parseInt(e.target.value))}
                style={{ width: "100%", accentColor: "#0284c7" }}
              />
            </div>

            {/* PHCs */}
            <div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px", marginBottom: "4px" }}>
                <span style={{ fontWeight: "600", color: "#334155" }}>Connected PHCs:</span>
                <strong style={{ color: "#0284c7" }}>{config.phcs} centers</strong>
              </div>
              <input
                type="range"
                min="10"
                max="100"
                value={config.phcs}
                onChange={(e) => handleInputChange("phcs", parseInt(e.target.value))}
                style={{ width: "100%", accentColor: "#0284c7" }}
              />
            </div>

            {/* AI Servers */}
            <div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px", marginBottom: "4px" }}>
                <span style={{ fontWeight: "600", color: "#334155" }}>AI Inference Nodes:</span>
                <strong style={{ color: "#0284c7" }}>{config.ai_servers} GPU/CPU nodes</strong>
              </div>
              <input
                type="range"
                min="1"
                max="10"
                value={config.ai_servers}
                onChange={(e) => handleInputChange("ai_servers", parseInt(e.target.value))}
                style={{ width: "100%", accentColor: "#0284c7" }}
              />
            </div>

            {/* Reviewing Doctors */}
            <div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px", marginBottom: "4px" }}>
                <span style={{ fontWeight: "600", color: "#334155" }}>Tele-Ophthalmologists:</span>
                <strong style={{ color: "#0284c7" }}>{config.doctors} doctors</strong>
              </div>
              <input
                type="range"
                min="1"
                max="20"
                value={config.doctors}
                onChange={(e) => handleInputChange("doctors", parseInt(e.target.value))}
                style={{ width: "100%", accentColor: "#0284c7" }}
              />
            </div>

            {/* Bandwidth Dropdown */}
            <div>
              <span style={{ display: "block", fontSize: "12px", fontWeight: "600", color: "#334155", marginBottom: "4px" }}>
                PHC Uplink Bandwidth:
              </span>
              <select
                value={config.bandwidth}
                onChange={(e) => handleInputChange("bandwidth", e.target.value)}
                style={{
                  width: "100%",
                  padding: "6px 10px",
                  borderRadius: "6px",
                  border: "1.5px solid #cbd5e1",
                  fontSize: "13px",
                }}
              >
                <option value="1 Mbps">1 Mbps (Poor 2G/3G)</option>
                <option value="5 Mbps">5 Mbps (Standard 4G)</option>
                <option value="10 Mbps">10 Mbps (Fast 4G/Fiber)</option>
                <option value="20 Mbps">20 Mbps (Dedicated Broadband)</option>
              </select>
            </div>

            {/* Fundus Cameras per PHC */}
            <div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px", marginBottom: "4px" }}>
                <span style={{ fontWeight: "600", color: "#334155" }}>Cameras per PHC:</span>
                <strong style={{ color: "#0284c7" }}>{config.cameras} cameras</strong>
              </div>
              <input
                type="range"
                min="1"
                max="5"
                value={config.cameras}
                onChange={(e) => handleInputChange("cameras", parseInt(e.target.value))}
                style={{ width: "100%", accentColor: "#0284c7" }}
              />
            </div>
          </div>
        </div>

        {/* Section 7: Live KPI Scorecard */}
        {simulationData && <KPIDashboard kpis={simulationData.kpis} />}

        {/* Middle Section: Side-by-Side Network & Queue Gauges */}
        {simulationData && (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
              gap: "20px",
              marginBottom: "24px",
            }}
          >
            {/* Section 4: Bandwidth & Transmission Simulation */}
            <BandwidthGauge bandwidth={simulationData.bandwidth} />

            {/* Section 6: Doctor Review Queue Simulation */}
            <QueueMonitor
              doctorQueue={simulationData.doctor_queue}
              aiServer={simulationData.ai_server}
            />
          </div>
        )}

        {/* Section 3: Image Quality Rejection Gateway Breakdown */}
        {simulationData && simulationData.gateway && (
          <div className="card" style={{ padding: "20px", marginBottom: "24px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px" }}>
              <div>
                <h4 style={{ fontSize: "15px", color: "var(--text-main)", margin: 0, fontWeight: "700" }}>
                  🛡️ Image Quality Rejection Gateway Simulation
                </h4>
                <p style={{ fontSize: "12.5px", color: "var(--text-muted)", margin: "2px 0 0 0" }}>
                  Clinical filtering prevents ungradeable captures from reaching the AI model (Guided Recaptures)
                </p>
              </div>
              <div style={{ display: "flex", gap: "8px" }}>
                <span style={{ fontSize: "11.5px", fontWeight: "700", background: "#f0fdf4", color: "#166534", padding: "3px 8px", borderRadius: "4px", border: "1px solid #bbf7d0" }}>
                  ✓ {simulationData.gateway.accepted_images} Passed ({simulationData.gateway.acceptance_rate_pct}%)
                </span>
                <span style={{ fontSize: "11.5px", fontWeight: "700", background: "#fef2f2", color: "#991b1b", padding: "3px 8px", borderRadius: "4px", border: "1px solid #fecaca" }}>
                  ⚠️ {simulationData.gateway.rejected_images} Rejected ({simulationData.gateway.rejection_rate_pct}%)
                </span>
              </div>
            </div>

            {/* Reasons Grid */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "10px" }}>
              {simulationData.gateway.reasons.map((r, idx) => (
                <div key={idx} style={{ background: "#f8fafc", padding: "10px 12px", borderRadius: "6px", border: "1px solid #e2e8f0" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px", marginBottom: "2px" }}>
                    <span style={{ color: "#334155", fontWeight: "600" }}>{r.reason}</span>
                    <strong style={{ color: "#dc2626" }}>{r.percentage}%</strong>
                  </div>
                  <span style={{ fontSize: "11px", color: "#64748b" }}>
                    ~{r.count} recaptures / day
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Section 8: District Annual Screening Progress Estimation */}
        {simulationData && simulationData.summary && (
          <div className="card" style={{ padding: "20px", marginBottom: "24px" }}>
            <h4 style={{ fontSize: "15px", color: "var(--text-main)", margin: "0 0 10px 0", fontWeight: "700" }}>
              📈 District Diabetic Population Screening Coverage (Annual)
            </h4>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "13px", marginBottom: "6px" }}>
              <span>
                Coverage Progress: <strong>{simulationData.summary.annual_patients_screened.toLocaleString()}</strong> of <strong>{config.diabetic_population.toLocaleString()}</strong> diabetic individuals
              </span>
              <strong style={{ color: "#0284c7" }}>
                {simulationData.summary.diabetic_coverage_pct}% of Target
              </strong>
            </div>
            <div style={{ width: "100%", height: "10px", background: "#f1f5f9", borderRadius: "9999px", overflow: "hidden", marginBottom: "10px" }}>
              <div
                style={{
                  width: `${simulationData.summary.diabetic_coverage_pct}%`,
                  height: "100%",
                  background: simulationData.summary.diabetic_coverage_pct >= 90 ? "#16a34a" : "#0284c7",
                  borderRadius: "9999px",
                  transition: "width 0.3s ease",
                }}
              />
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11.5px", color: "#64748b" }}>
              <span>Operating Schedule: {config.working_days} clinic days/year</span>
              <span>Screening Completion Estimate: ~{simulationData.summary.days_to_complete_target} clinic days</span>
            </div>
          </div>
        )}

        {/* Section 10: Resource Optimization & Actionable Plan */}
        {simulationData && simulationData.optimization && (
          <OptimizationCard optimization={simulationData.optimization} />
        )}
      </div>
    </div>
  );
}
