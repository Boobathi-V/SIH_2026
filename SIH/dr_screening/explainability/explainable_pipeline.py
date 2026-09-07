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

        # 8. Stage 6: High-Magnification Zoomed-In Lesion Inspection Crops
        zoomed_crops = self.generate_zoomed_crops(
            img_bgr=img_bgr,
            od_info=scaled_od_info,
            lesion_info=scaled_lesion_info,
            dominant_lesion=explanation_res.get("dominant_lesion", ""),
            output_dim=320,
        )

        total_elapsed = round(time.time() - start_time, 3)

        return {
            "prediction": explanation_res["title"],
            "prediction_class": prediction_class,
            "confidence": round(float(confidence), 4),
            "confidence_pct": explanation_res["confidence_pct"],
            "risk_level": explanation_res["risk_level"],
            "dominant_lesion": explanation_res.get("dominant_lesion", "Retinal Pathology"),
            "dominant_contribution_pct": explanation_res.get("dominant_contribution_pct", 50),
            "dominant_reason": explanation_res.get("dominant_reason", ""),
            "attributions": explanation_res.get("attributions", []),
            "primary_findings": explanation_res["primary_findings"],
            "clinical_summary": explanation_res["clinical_summary"],
            "differential": explanation_res["differential"],
            "action": explanation_res["action"],
            "explanation_text": explanation_res["full_text"],
            "counts": lesion_info["counts"],
            "lesions": scaled_lesion_info["lesions"],
            "zoomed_crops": zoomed_crops,
            "annotated_image_path": str(annotated_path),
            "annotated_base64": annotated_base64,
            "pipeline_elapsed_sec": total_elapsed,
        }

    def generate_zoomed_crops(
        self,
        img_bgr: np.ndarray,
        od_info: Dict[str, Any],
        lesion_info: Dict[str, Any],
        dominant_lesion: str,
        output_dim: int = 320,
    ) -> List[Dict[str, Any]]:
        """Generate high-magnification zoomed-in ROI crops for detected lesion types."""
        crops = []
        lesions = lesion_info.get("lesions", [])

        # 1. Zoomed crop for Hard Exudates
        exs = [l for l in lesions if l["type"] == "Hard Exudate"]
        if exs:
            target = max(exs, key=lambda x: x.get("area", 0))
            cx, cy = target["center"]
            crop_rad = max(35, min(80, int(target.get("bbox", (0, 0, 30, 30))[2] * 1.8)))
            is_dom = ("Hard Exudate" in dominant_lesion)
            crop_b64 = self._create_magnified_roi(
                img_bgr, cx, cy, crop_rad, output_dim,
                label="3.5x Zoom: Hard Exudate",
            )
            crops.append({
                "type": "Hard Exudate",
                "is_primary": is_dom,
                "title": "Primary Driver: Hard Exudates" if is_dom else "Hard Exudate Cluster",
                "magnification": "3.5x Optical Zoom",
                "center": [cx, cy],
                "image_base64": crop_b64,
                "description": "Dense yellowish intraretinal lipid deposits indicating chronic capillary hyperpermeability.",
            })

        # 2. Zoomed crop for Microaneurysms
        mas = [l for l in lesions if l["type"] == "Microaneurysm"]
        if mas:
            target = max(mas, key=lambda x: x.get("confidence", 0))
            cx, cy = target["center"]
            crop_rad = 30
            is_dom = ("Microaneurysm" in dominant_lesion)
            crop_b64 = self._create_magnified_roi(
                img_bgr, cx, cy, crop_rad, output_dim,
                label="5.0x Zoom: Microaneurysm",
            )
            crops.append({
                "type": "Microaneurysm",
                "is_primary": is_dom,
                "title": "Primary Driver: Microaneurysm" if is_dom else "Capillary Microaneurysm",
                "magnification": "5.0x Optical Zoom",
                "center": [cx, cy],
                "image_base64": crop_b64,
                "description": "Focal punctate capillary outpouching displaying classic spherical red-dot morphology.",
            })

        # 3. Zoomed crop for Hemorrhages
        hms = [l for l in lesions if l["type"] == "Hemorrhage"]
        if hms:
            target = max(hms, key=lambda x: x.get("area", 0))
            cx, cy = target["center"]
            crop_rad = max(40, min(85, int(target.get("bbox", (0, 0, 40, 40))[2] * 1.5)))
            is_dom = ("Hemorrhage" in dominant_lesion)
            crop_b64 = self._create_magnified_roi(
                img_bgr, cx, cy, crop_rad, output_dim,
                label="3.2x Zoom: Blot Hemorrhage",
            )
            crops.append({
                "type": "Hemorrhage",
                "is_primary": is_dom,
                "title": "Primary Driver: Blot Hemorrhage" if is_dom else "Intraretinal Blot Hemorrhage",
                "magnification": "3.2x Optical Zoom",
                "center": [cx, cy],
                "image_base64": crop_b64,
                "description": "Deep intraretinal hemorrhage resulting from capillary wall disruption.",
            })

        # 4. Zoomed crop for Cotton Wool Spots
        cwss = [l for l in lesions if l["type"] == "Cotton Wool Spot"]
        if cwss:
            target = max(cwss, key=lambda x: x.get("area", 0))
            cx, cy = target["center"]
            crop_rad = max(45, min(90, int(target.get("bbox", (0, 0, 50, 50))[2] * 1.4)))
            is_dom = ("Cotton Wool" in dominant_lesion)
            crop_b64 = self._create_magnified_roi(
                img_bgr, cx, cy, crop_rad, output_dim,
                label="3.0x Zoom: Cotton Wool Spot",
            )
            crops.append({
                "type": "Cotton Wool Spot",
                "is_primary": is_dom,
                "title": "Cotton Wool Spot (Soft Exudate)",
                "magnification": "3.0x Optical Zoom",
                "center": [cx, cy],
                "image_base64": crop_b64,
                "description": "Pale, fluffy nerve fiber layer micro-infarct caused by precapillary arteriolar occlusion.",
            })

        # 5. Zoomed crop for Optic Disc
        if od_info.get("detected"):
            cx, cy = od_info["center"]
            rad = od_info.get("radius", 40)
            crop_rad = int(rad * 1.45)
            crop_b64 = self._create_magnified_roi(
                img_bgr, cx, cy, crop_rad, output_dim,
                label="2.2x Zoom: Optic Disc",
            )
            crops.append({
                "type": "Optic Disc",
                "is_primary": False,
                "title": "Optic Nerve Head & Margin",
                "magnification": "2.2x Anatomical Zoom",
                "center": [cx, cy],
                "image_base64": crop_b64,
                "description": "Anatomically localized optic disc; safely isolated to avoid misinterpretation as an exudate.",
            })

        return crops

    def _create_magnified_roi(
        self,
        img_bgr: np.ndarray,
        cx: int,
        cy: int,
        crop_rad: int,
        output_dim: int,
        label: str,
    ) -> str:
        """Helper to crop, upscale with Lanczos, draw targeting ring, and return base64."""
        h, w = img_bgr.shape[:2]
        x1, y1 = max(0, cx - crop_rad), max(0, cy - crop_rad)
        x2, y2 = min(w, cx + crop_rad), min(h, cy + crop_rad)
        roi = img_bgr[y1:y2, x1:x2].copy()

        magnified = cv2.resize(roi, (output_dim, output_dim), interpolation=cv2.INTER_LANCZOS4)

        center_m = output_dim // 2
        reticle_r = int(output_dim * 0.22)
        cv2.circle(magnified, (center_m, center_m), reticle_r, (255, 255, 255), 2, lineType=cv2.LINE_AA)
        cv2.circle(magnified, (center_m, center_m), 3, (255, 255, 255), -1, lineType=cv2.LINE_AA)

        overlay = magnified.copy()
        cv2.rectangle(overlay, (0, output_dim - 36), (output_dim, output_dim), (15, 23, 42), -1)
        cv2.addWeighted(overlay, 0.82, magnified, 0.18, 0, magnified)

        cv2.putText(
            magnified,
            label,
            (10, output_dim - 12),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.50,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )

        _, buffer = cv2.imencode(".jpg", magnified, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
        return base64.b64encode(buffer).decode("utf-8")

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
