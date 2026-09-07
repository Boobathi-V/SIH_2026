"""End-to-End Explainable AI Pipeline for Retinal Fundus Lesion Detection (SIH26038).

Integrates Optic Disc localization, Retinal Vasculature Segmentation, Multi-Lesion
Detection (Microaneurysms, Hemorrhages, Hard Exudates, Cotton Wool Spots, Neovascularization),
Clinical Annotation Rendering, and Automated Ophthalmology Diagnosis Generation.
"""

from pathlib import Path
from typing import Dict, Any, Optional, Union
import base64
import time
import cv2
import numpy as np

from dr_screening.explainability.optic_disc import OpticDiscDetector
from dr_screening.explainability.vessel_segmentation import RetinalVesselSegmenter
from dr_screening.explainability.lesion_detector import RetinalLesionDetector
from dr_screening.explainability.annotation_renderer import RetinalAnnotationRenderer
from dr_screening.explainability.explanation_generator import RetinalExplanationGenerator


class ExplainableLesionPipeline:
    """Master orchestrator for clinical lesion detection and explainability."""

    def __init__(self, target_analysis_dim: int = 512):
        self.target_analysis_dim = target_analysis_dim
        self.optic_disc_detector = OpticDiscDetector()
        self.vessel_segmenter = RetinalVesselSegmenter()
        self.lesion_detector = RetinalLesionDetector()
        self.annotation_renderer = RetinalAnnotationRenderer()
        self.explanation_generator = RetinalExplanationGenerator()

    def process(
        self,
        img_bgr: np.ndarray,
        prediction_class: int,
        confidence: float,
        gradcam_map: Optional[np.ndarray] = None,
        save_dir: str = "outputs/annotated",
        image_name: str = "retina",
    ) -> Dict[str, Any]:
        """Execute complete explainability pipeline.

        Args:
            img_bgr: uint8 BGR image at original camera resolution.
            prediction_class: Predicted DR stage (0 to 4).
            confidence: Float confidence score (0.0 to 1.0).
            gradcam_map: Optional normalized Grad-CAM activation map [0.0, 1.0].
            save_dir: Directory to store generated annotated images.
            image_name: Stem name for saved files.

        Returns:
            Dictionary containing structured lesions, counts, explanation, and annotation paths.
        """
        start_time = time.time()
        orig_h, orig_w = img_bgr.shape[:2]

        # 1. Performance-Optimized Spatial Normalization
        # For high-res inputs (e.g. 2000x2000), perform morphological detection on 512x512
        # then scale coordinates back for full-resolution rendering.
        scale_x = orig_w / float(self.target_analysis_dim)
        scale_y = orig_h / float(self.target_analysis_dim)

        if orig_w != self.target_analysis_dim or orig_h != self.target_analysis_dim:
            analysis_img = cv2.resize(
                img_bgr,
                (self.target_analysis_dim, self.target_analysis_dim),
                interpolation=cv2.INTER_AREA,
            )
        else:
            analysis_img = img_bgr

        if gradcam_map is not None:
            if gradcam_map.shape[:2] != (self.target_analysis_dim, self.target_analysis_dim):
                analysis_cam = cv2.resize(
                    gradcam_map,
                    (self.target_analysis_dim, self.target_analysis_dim),
                    interpolation=cv2.INTER_LINEAR,
                )
            else:
                analysis_cam = gradcam_map
        else:
            analysis_cam = None

        # 2. Stage 1: Optic Disc Detection & Safe Parenchyma Isolation
        od_info = self.optic_disc_detector.detect(analysis_img)

        # 3. Stage 2: Retinal Vasculature Segmentation & Caliber Profiling
        vessel_info = self.vessel_segmenter.segment(analysis_img)

        # 4. Stage 3: Multi-Lesion Detection (MAs, HMs, Exudates, CWS, NV)
        lesion_info = self.lesion_detector.detect_all(
            img_bgr=analysis_img,
            optic_disc_info=od_info,
            vessel_info=vessel_info,
            gradcam_map=analysis_cam,
            prediction_class=prediction_class,
        )

        # 5. Scale coordinates back to original image resolution for rendering
        scaled_od_info = self._scale_od_info(od_info, scale_x, scale_y)
        scaled_vessel_info = self._scale_vessel_info(vessel_info, scale_x, scale_y)
        scaled_lesion_info = self._scale_lesion_info(lesion_info, scale_x, scale_y)

        # 6. Stage 4: Publication-Quality Clinical Annotation Rendering
        out_dir = Path(save_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        annotated_path = out_dir / f"{image_name}_annotated.png"

        annotated_bgr, saved_file = self.annotation_renderer.render(
            img_bgr=img_bgr,
            optic_disc_info=scaled_od_info,
            vessel_info=scaled_vessel_info,
            lesion_info=scaled_lesion_info,
            save_path=str(annotated_path),
        )

        # Generate base64 string for immediate web streaming
        with open(str(annotated_path), "rb") as f:
            annotated_base64 = base64.b64encode(f.read()).decode("utf-8")

        # 7. Stage 5: Structured Ophthalmology Medical Explanation
        explanation_res = self.explanation_generator.generate(
            prediction_class=prediction_class,
            confidence=confidence,
            lesion_info=scaled_lesion_info,
            optic_disc_info=scaled_od_info,
            vessel_info=scaled_vessel_info,
        )

        total_elapsed = round(time.time() - start_time, 3)

        return {
            "prediction": explanation_res["title"],
            "prediction_class": prediction_class,
            "confidence": round(float(confidence), 4),
            "confidence_pct": explanation_res["confidence_pct"],
            "risk_level": explanation_res["risk_level"],
            "primary_findings": explanation_res["primary_findings"],
            "clinical_summary": explanation_res["clinical_summary"],
            "differential": explanation_res["differential"],
            "action": explanation_res["action"],
            "explanation_text": explanation_res["full_text"],
            "counts": lesion_info["counts"],
            "lesions": scaled_lesion_info["lesions"],
            "annotated_image_path": str(annotated_path),
            "annotated_base64": annotated_base64,
            "pipeline_elapsed_sec": total_elapsed,
        }

    def _scale_od_info(self, od_info: Dict[str, Any], sx: float, sy: float) -> Dict[str, Any]:
        scaled = dict(od_info)
        if "center" in od_info:
            scaled["center"] = (int(od_info["center"][0] * sx), int(od_info["center"][1] * sy))
        if "radius" in od_info:
            scaled["radius"] = int(od_info["radius"] * (sx + sy) / 2.0)
        return scaled

    def _scale_vessel_info(self, vessel_info: Dict[str, Any], sx: float, sy: float) -> Dict[str, Any]:
        scaled = dict(vessel_info)
        scaled["arteriole_points"] = [(int(p[0] * sx), int(p[1] * sy)) for p in vessel_info.get("arteriole_points", [])]
        scaled["venule_points"] = [(int(p[0] * sx), int(p[1] * sy)) for p in vessel_info.get("venule_points", [])]
        return scaled

    def _scale_lesion_info(self, lesion_info: Dict[str, Any], sx: float, sy: float) -> Dict[str, Any]:
        scaled = dict(lesion_info)
        scaled_lesions = []
        for l in lesion_info.get("lesions", []):
            item = dict(l)
            if "center" in item:
                item["center"] = (int(item["center"][0] * sx), int(item["center"][1] * sy))
            if "radius" in item:
                item["radius"] = int(item["radius"] * (sx + sy) / 2.0)
            if "bbox" in item:
                x, y, w, h = item["bbox"]
                item["bbox"] = (int(x * sx), int(y * sy), int(w * sx), int(h * sy))
            if "contour" in item:
                item["contour"] = [[int(pt[0] * sx), int(pt[1] * sy)] for pt in item["contour"]]
            scaled_lesions.append(item)
        scaled["lesions"] = scaled_lesions
        return scaled
