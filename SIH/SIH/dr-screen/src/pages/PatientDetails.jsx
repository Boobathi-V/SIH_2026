import { useState } from "react";
import { useNavigate } from "react-router-dom";

function PatientDetails() {
  const navigate = useNavigate();

  const [patient, setPatient] = useState({
    id: "PAT-" + Math.floor(100000 + Math.random() * 900000),
    name: "",
    age: "",
    gender: "Male",
    diabetesDuration: "5 years",
    eyeExamined: "Right Eye (OD)",
  });

  function handleChange(e) {
    setPatient({
      ...patient,
      [e.target.name]: e.target.value,
    });
  }

  function handleSubmit(e) {
    e.preventDefault();
    localStorage.setItem("patient", JSON.stringify(patient));
    navigate("/upload");
  }

  return (
    <div className="page-container">
      <div className="content-wrapper" style={{ maxWidth: "680px" }}>

        <div style={{ marginBottom: "24px" }}>
          <button
            className="btn btn-secondary"
            style={{ padding: "8px 16px", fontSize: "13px" }}
            onClick={() => navigate("/")}
          >
            ← Back to Home
          </button>
        </div>

        <div className="card">
          <div style={{ borderBottom: "1px solid var(--border)", paddingBottom: "16px", marginBottom: "24px" }}>
            <span style={{ fontSize: "12px", fontWeight: "700", color: "var(--primary)", textTransform: "uppercase" }}>
              Step 1 of 4: Patient Intake
            </span>
            <h2 style={{ fontSize: "24px", marginTop: "4px" }}>Patient Demographics & Medical History</h2>
            <p style={{ fontSize: "14px", color: "var(--text-muted)" }}>
              Enter patient details to associate with the AI screening report and clinical records.
            </p>
          </div>

          <form onSubmit={handleSubmit}>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
              <div className="form-group">
                <label className="form-label">Patient ID</label>
                <input
                  className="form-input"
                  name="id"
                  placeholder="e.g. PAT-98214"
                  value={patient.id}
                  onChange={handleChange}
                  required
                />
              </div>

              <div className="form-group">
                <label className="form-label">Eye Examined</label>
                <select
                  className="form-select"
                  name="eyeExamined"
                  value={patient.eyeExamined}
                  onChange={handleChange}
                  required
                >
                  <option value="Right Eye (OD)">Right Eye (OD)</option>
                  <option value="Left Eye (OS)">Left Eye (OS)</option>
                  <option value="Bilateral">Bilateral</option>
                </select>
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">Full Patient Name</label>
              <input
                className="form-input"
                name="name"
                placeholder="e.g. John Doe"
                value={patient.name}
                onChange={handleChange}
                required
              />
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
              <div className="form-group">
                <label className="form-label">Age (Years)</label>
                <input
                  className="form-input"
                  name="age"
                  type="number"
                  placeholder="e.g. 54"
                  value={patient.age}
                  onChange={handleChange}
                  min="1"
                  max="120"
                  required
                />
              </div>

              <div className="form-group">
                <label className="form-label">Gender</label>
                <select
                  className="form-select"
                  name="gender"
                  value={patient.gender}
                  onChange={handleChange}
                  required
                >
                  <option value="Male">Male</option>
                  <option value="Female">Female</option>
                  <option value="Other">Other</option>
                </select>
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">Known Diabetes Duration / Type</label>
              <input
                className="form-input"
                name="diabetesDuration"
                placeholder="e.g. Type 2 Diabetes, 8 years"
                value={patient.diabetesDuration}
                onChange={handleChange}
              />
            </div>

            <div style={{ marginTop: "28px", display: "flex", justifyContent: "flex-end" }}>
              <button
                type="submit"
                className="btn btn-primary"
                style={{ width: "100%", padding: "14px" }}
              >
                Proceed to Fundus Image Upload →
              </button>
            </div>
          </form>
        </div>

      </div>
    </div>
  );
}

export default PatientDetails;