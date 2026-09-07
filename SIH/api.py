"""FastAPI REST API Server for Diabetic Retinopathy Screening Model (SIH26038).

Provides:
- POST /predict: Retinal screening with Image Quality Gate, clinical risk, and Grad-CAM heatmap.
- POST /validate-quality: Fast standalone pre-check for image gradeability before full inference.
- GET /heatmap/{filename}: Serves generated explainability heatmaps.
- GET /health: Health check and model metadata.
"""

import os
import shutil
import base64
from pathlib import Path
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, status
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from dr_screening.inference.predictor import FundusPredictor, UngradeableImageError
from dr_screening.preprocessing.quality_gate import RetinalQualityGate
from dr_screening.configs.constants import CLASS_NAMES, NUM_CLASSES

app = FastAPI(
    title="SIH26038 — Diabetic Retinopathy Screening API",
    description="Production ML inference API for 5-class Diabetic Retinopathy severity detection with Image Quality Gate and Grad-CAM explainability.",
    version="2.0.0",
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
PREDICTOR: Optional[FundusPredictor] = None
QUALITY_GATE = RetinalQualityGate()

UPLOAD_DIR = Path("outputs/api_uploads")
GRADCAM_DIR = Path("outputs/gradcam")
ANNOTATED_DIR = Path("outputs/annotated")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
GRADCAM_DIR.mkdir(parents=True, exist_ok=True)
ANNOTATED_DIR.mkdir(parents=True, exist_ok=True)


def get_predictor() -> FundusPredictor:
    """Lazy load predictor singleton."""
    global PREDICTOR
    if PREDICTOR is None:
        ckpt_path = "outputs/checkpoints/aptos_resnet50.pth"
        if not os.path.exists(ckpt_path):
            ckpt_path = "outputs/checkpoints/best_model.pth"
        if not os.path.exists(ckpt_path):
            ckpt_path = "outputs/checkpoints/last_checkpoint.pth"
        PREDICTOR = FundusPredictor(checkpoint_path=ckpt_path, device="cpu", enforce_quality_gate=True)
    return PREDICTOR


class QualityGateResponse(BaseModel):
    is_gradeable: bool
    quality_score: float
    message: str
    recapture_guidance: str
    failure_category: Optional[str] = None
    detailed_explanation: Optional[str] = None
    checks: Optional[List[Dict[str, Any]]] = None
    metrics: Dict[str, Any] = {}


class PredictionResponse(BaseModel):
    prediction: str = Field(..., description="Class name (No DR, Mild DR, Moderate DR, Severe DR, Proliferative DR)")
    class_index: int = Field(..., description="Class index (0 to 4)")
    confidence: float = Field(..., description="Predicted probability for top class")
    probabilities: List[float] = Field(..., description="Probability distribution across all 5 classes")
    heatmap_url: Optional[str] = Field(None, description="URL endpoint to fetch Grad-CAM heatmap overlay")
    heatmap_base64: Optional[str] = Field(None, description="Base64 encoded Grad-CAM overlay image")
    annotated_url: Optional[str] = Field(None, description="URL endpoint to fetch annotated retinal lesions image")
    annotated_base64: Optional[str] = Field(None, description="Base64 encoded annotated retinal image")
    risk_level: str = Field(..., description="Clinical triage risk level (None, Low, Moderate, High, Critical)")
    clinical_severity: str = Field(..., description="Full clinical severity classification")
    recommended_action: str = Field(..., description="Ophthalmologist referral or follow-up recommendation")
    quality_gate: Optional[Dict[str, Any]] = Field(None, description="Quality gate score and evaluation details")
    biomarkers: Optional[Dict[str, Any]] = Field(None, description="Extracted microaneurysm and exudate densities")
    lesion_counts: Optional[Dict[str, int]] = Field(None, description="Counts of microaneurysms, hemorrhages, exudates, cotton wool spots")
    lesions: Optional[List[Dict[str, Any]]] = Field(None, description="Detected lesion entities with coordinates and confidence")
    dominant_lesion: Optional[str] = Field(None, description="Primary pathological lesion driving the diagnosis")
    dominant_contribution_pct: Optional[int] = Field(None, description="Percentage contribution of the primary lesion")
    dominant_reason: Optional[str] = Field(None, description="Detailed diagnostic reason for prediction based on dominant lesion")
    attributions: Optional[List[Dict[str, Any]]] = Field(None, description="Ranked lesion contribution percentages")
    zoomed_crops: Optional[List[Dict[str, Any]]] = Field(None, description="High-magnification optical zoom ROI crops")
    primary_findings: Optional[List[str]] = Field(None, description="Key clinical lesion findings bullet points")
    clinical_explanation: Optional[str] = Field(None, description="Full ophthalmologist-grade structured narrative explanation")
    clinical_summary: Optional[str] = Field(None, description="Concise pathological summary")
    differential: Optional[str] = Field(None, description="ETDRS differential reasoning")


@app.get("/", tags=["General"])
def root():
    return {
        "project": "SIH26038 Explainable AI for Diabetic Retinopathy Screening in Rural India",
        "status": "online",
        "model_architecture": "ResNet-50 with Ben Graham Retinal Preprocessing & Quality Gate",
        "num_classes": NUM_CLASSES,
        "classes": CLASS_NAMES,
        "features": [
            "Clinical Retinal Image Quality Gate (Blur, Illumination, Vascular Spectrum)",
            "Ben Graham Retinal Feature Isolation",
            "5-Class Severity Grading (AAO/ICO Guidelines)",
            "Grad-CAM Pathological Lesion Attribution",
            "Clinical Decision Calibration Layer"
        ],
        "docs_url": "/docs",
    }


@app.get("/health", tags=["General"])
def health():
    return {"status": "healthy", "service": "dr-screening-api"}


@app.post("/validate-quality", response_model=QualityGateResponse, tags=["Quality Assessment"])
async def validate_image_quality(
    file: UploadFile = File(..., description="Retinal fundus photograph to assess for gradeability"),
):
    """Assess whether an image is a valid, gradeable retinal photograph before running inference."""
    suffix = Path(file.filename).suffix.lower()
    if suffix not in [".png", ".jpg", ".jpeg"]:
        raise HTTPException(status_code=400, detail="Invalid image file format. Use PNG or JPG.")

    temp_path = UPLOAD_DIR / f"temp_qual_{file.filename}"
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        quality_res = QUALITY_GATE.evaluate_quality(str(temp_path))
        return QualityGateResponse(**quality_res)
    finally:
        if temp_path.exists():
            try:
                os.remove(temp_path)
            except Exception:
                pass


@app.post("/predict", response_model=PredictionResponse, tags=["Inference"])
async def predict_retina(
    file: UploadFile = File(..., description="Retinal fundus photograph (PNG, JPG, JPEG)"),
    include_base64: bool = Form(True, description="Include base64 encoded heatmap overlay in response"),
):
    """Run diabetic retinopathy screening on an uploaded retinal fundus image with Quality Gate check."""
    suffix = Path(file.filename).suffix.lower()
    if suffix not in [".png", ".jpg", ".jpeg"]:
        raise HTTPException(status_code=400, detail="Invalid image file format. Use PNG or JPG.")

    temp_path = UPLOAD_DIR / file.filename
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        predictor = get_predictor()

        try:
            result = predictor.predict(
                image_source=str(temp_path),
                generate_heatmap=True,
                save_dir=str(GRADCAM_DIR),
                image_name=Path(file.filename).stem,
            )
        except UngradeableImageError as qe:
            # Quality Gate rejected ungradeable image with clinical guidance
            q_res = qe.quality_result
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={
                    "error": "ImageQualityRejection",
                    "detail": q_res.get("message", "Ungradeable image"),
                    "failure_category": q_res.get("failure_category"),
                    "detailed_explanation": q_res.get("detailed_explanation"),
                    "checks": q_res.get("checks", []),
                    "quality_gate": q_res,
                    "recapture_guidance": q_res.get("recapture_guidance", "Please provide a clear fundus image.")
                }
            )

        heatmap_path = result.get("heatmap_path")
        heatmap_url = None
        heatmap_base64 = None

        if heatmap_path and os.path.exists(heatmap_path):
            filename = Path(heatmap_path).name
            heatmap_url = f"/heatmap/{filename}"

            if include_base64:
                with open(heatmap_path, "rb") as img_f:
                    heatmap_base64 = base64.b64encode(img_f.read()).decode("utf-8")

        annotated_path = result.get("annotated_path")
        annotated_url = None
        annotated_base64 = result.get("annotated_base64")

        if annotated_path and os.path.exists(annotated_path):
            ann_filename = Path(annotated_path).name
            annotated_url = f"/annotated/{ann_filename}"

        return PredictionResponse(
            prediction=result["prediction"],
            class_index=result["class_index"],
            confidence=result["confidence"],
            probabilities=result["probabilities"],
            heatmap_url=heatmap_url,
            heatmap_base64=heatmap_base64,
            annotated_url=annotated_url,
            annotated_base64=annotated_base64,
            risk_level=result["risk_level"],
            clinical_severity=result["clinical_severity"],
            recommended_action=result["recommended_action"],
            quality_gate=result.get("quality_gate"),
            biomarkers=result.get("biomarkers"),
            lesion_counts=result.get("lesion_counts"),
            lesions=result.get("lesions"),
            dominant_lesion=result.get("dominant_lesion"),
            dominant_contribution_pct=result.get("dominant_contribution_pct"),
            dominant_reason=result.get("dominant_reason"),
            attributions=result.get("attributions"),
            zoomed_crops=result.get("zoomed_crops"),
            primary_findings=result.get("primary_findings"),
            clinical_explanation=result.get("clinical_explanation"),
            clinical_summary=result.get("clinical_summary"),
            differential=result.get("differential"),
        )

    finally:
        if temp_path.exists():
            try:
                os.remove(temp_path)
            except Exception:
                pass


@app.get("/heatmap/{filename}", tags=["Explainability"])
def get_heatmap(filename: str):
    """Retrieve the generated Grad-CAM overlay heatmap image."""
    file_path = GRADCAM_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Heatmap image not found.")
    return FileResponse(str(file_path), media_type="image/jpeg")


@app.get("/annotated/{filename}", tags=["Explainability"])
def get_annotated(filename: str):
    """Retrieve the generated clinical lesion annotated fundus image."""
    file_path = ANNOTATED_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Annotated image not found.")
    return FileResponse(str(file_path), media_type="image/png")


@app.post("/explain", response_model=PredictionResponse, tags=["Explainability"])
async def explain_fundus(
    file: UploadFile = File(..., description="Retinal fundus photograph for clinical lesion explainability"),
):
    """Run full explainability analysis with lesion localization and ophthalmology annotation."""
    return await predict_retina(file=file, include_base64=True)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
