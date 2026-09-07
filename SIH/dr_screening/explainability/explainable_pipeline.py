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

        # Generate lightweight base64 string for immediate web streaming (JPEG 85 for fast network transfer & low memory footprint)
        _, ann_buf = cv2.imencode(".jpg", annotated_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
        annotated_base64 = base64.b64encode(ann_buf).decode("utf-8")

        # 7. Stage 5: Structured Ophthalmology Medical Explanation
        explanation_res = self.explanation_generator.generate(
            prediction_class=prediction_class,
            confidence=confidence,
            lesion_info=scaled_lesion_info,
            optic_disc_info=scaled_od_info,
            vessel_info=scaled_vessel_info,
        )

        # 8. Stage 6: High-Magnification Zoomed-In Lesion Inspection Crops (2.7x Optical Zoom, 480px Large Box)
        zoomed_crops = self.generate_zoomed_crops(
            img_bgr=img_bgr,
            od_info=scaled_od_info,
            lesion_info=scaled_lesion_info,
            dominant_lesion=explanation_res.get("dominant_lesion", ""),
            output_dim=480,
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
        output_dim: int = 480,
    ) -> List[Dict[str, Any]]:
        """Generate pristine optical zoom ROI crops for detected lesion types."""
        crops = []
        lesions = lesion_info.get("lesions", [])
        h, w = img_bgr.shape[:2]

        # Optical Zoom: field of view radius = min(h, w) / (2.7 * 2)
        default_zoom_rad = max(45, int(min(h, w) / 5.4))

        # 1. Zoomed crop for Hard Exudates (prioritize Grad-CAM aligned true lesions)
        exs = [l for l in lesions if l["type"] == "Hard Exudate"]
        if exs:
            target = max(exs, key=lambda x: (x.get("gradcam_score", 0.5) * 0.7 + x.get("confidence", 0.7) * 0.3))
            cx, cy = target["center"]
            is_dom = ("Hard Exudate" in dominant_lesion or "Yellow" in dominant_lesion)
            crop_b64 = self._create_magnified_roi(img_bgr, cx, cy, default_zoom_rad, output_dim)
            crops.append({
                "type": "Hard Exudate",
                "is_primary": is_dom,
                "title": "Yellow Fluid Spots (Hard Exudates)",
                "magnification": "2.7x Optical Zoom",
                "center": [cx, cy],
                "image_base64": crop_b64,
                "description": "Small yellow fluid and fat deposits (Hard Exudates) that leak into the retina when tiny blood vessels become weak and porous (microvascular hyperpermeability). Over time, this fluid can build up and threaten central reading vision (macular edema).",
            })

        # 2. Zoomed crop for Microaneurysms
        mas = [l for l in lesions if l["type"] == "Microaneurysm"]
        if mas:
            target = max(mas, key=lambda x: (x.get("gradcam_score", 0.5) * 0.7 + x.get("confidence", 0.7) * 0.3))
            cx, cy = target["center"]
            is_dom = ("Microaneurysm" in dominant_lesion or "Red" in dominant_lesion)
            crop_b64 = self._create_magnified_roi(img_bgr, cx, cy, default_zoom_rad, output_dim)
            crops.append({
                "type": "Microaneurysm",
                "is_primary": is_dom,
                "title": "Red Swelling Dots (Capillary Microaneurysms)",
                "magnification": "2.7x Optical Zoom",
                "center": [cx, cy],
                "image_base64": crop_b64,
                "description": "Tiny red balloon-like swelling dots (Capillary Microaneurysms) that bulge out from weakened eye blood vessels. These are typically the earliest visible sign of diabetic damage in the retina (Grade 1 Diabetic Retinopathy).",
            })

        # 3. Zoomed crop for Hemorrhages
        hms = [l for l in lesions if l["type"] == "Hemorrhage"]
        if hms:
            target = max(hms, key=lambda x: (x.get("gradcam_score", 0.5) * 0.7 + x.get("area", 100) * 0.001))
            cx, cy = target["center"]
            is_dom = ("Hemorrhage" in dominant_lesion or "Bleeding" in dominant_lesion)
            crop_b64 = self._create_magnified_roi(img_bgr, cx, cy, default_zoom_rad, output_dim)
            crops.append({
                "type": "Hemorrhage",
                "is_primary": is_dom,
                "title": "Bleeding Spots (Intraretinal Hemorrhages)",
                "magnification": "2.7x Optical Zoom",
                "center": [cx, cy],
                "image_base64": crop_b64,
                "description": "Small spots of bleeding inside the eye retina (Intraretinal Blot Hemorrhages) that happen when fragile, weakened blood vessels burst and leak blood into retinal tissue layers.",
            })

        # 4. Zoomed crop for Cotton Wool Spots
        cwss = [l for l in lesions if l["type"] == "Cotton Wool Spot"]
        if cwss:
            target = max(cwss, key=lambda x: (x.get("gradcam_score", 0.5) * 0.7 + x.get("area", 100) * 0.001))
            cx, cy = target["center"]
            is_dom = ("Cotton Wool" in dominant_lesion or "Pale" in dominant_lesion)
            crop_b64 = self._create_magnified_roi(img_bgr, cx, cy, default_zoom_rad, output_dim)
            crops.append({
                "type": "Cotton Wool Spot",
                "is_primary": is_dom,
                "title": "Fluffy White Patches (Cotton Wool Spots)",
                "magnification": "2.7x Optical Zoom",
                "center": [cx, cy],
                "image_base64": crop_b64,
                "description": "Fluffy white or grayish patches (Cotton Wool Spots / Soft Exudates) that show up when tiny blood vessels get blocked, cutting off oxygen and blood flow to the nerve fibers (retinal nerve fiber layer micro-infarctions).",
            })

        # 5. Zoomed crop for Optic Disc (clean healthy anatomical landmark)
        if od_info.get("detected"):
            cx, cy = od_info["center"]
            crop_b64 = self._create_magnified_roi(img_bgr, cx, cy, default_zoom_rad, output_dim)
            crops.append({
                "type": "Optic Disc",
                "is_primary": False,
                "title": "Eye Nerve Head (Optic Nerve Disc)",
                "magnification": "2.7x Anatomical Zoom",
                "center": [cx, cy],
                "image_base64": crop_b64,
                "description": "The main eye nerve head (Optic Nerve Disc) where vision cables connect the eye to the brain. This is normal healthy anatomy and is carefully mapped so it is not mistaken for disease spots.",
            })

        return crops

    def _create_magnified_roi(
        self,
        img_bgr: np.ndarray,
        cx: int,
        cy: int,
        crop_rad: int,
        output_dim: int,
    ) -> str:
        """Helper to crop and upscale with Lanczos-4. Pure pristine retina image without crosshairs or reticles."""
        h, w = img_bgr.shape[:2]
        x1, y1 = max(0, cx - crop_rad), max(0, cy - crop_rad)
        x2, y2 = min(w, cx + crop_rad), min(h, cy + crop_rad)
        roi = img_bgr[y1:y2, x1:x2].copy()

        # Pad if near edge to guarantee exact 1:1 square aspect ratio
        rh, rw = roi.shape[:2]
        target_size = crop_rad * 2
        if rh != target_size or rw != target_size:
            pad_top = max(0, crop_rad - cy)
            pad_bottom = max(0, (cy + crop_rad) - h)
            pad_left = max(0, crop_rad - cx)
            pad_right = max(0, (cx + crop_rad) - w)
            roi = cv2.copyMakeBorder(
                roi, pad_top, pad_bottom, pad_left, pad_right,
                cv2.BORDER_CONSTANT, value=[10, 10, 10]
            )

        magnified = cv2.resize(roi, (output_dim, output_dim), interpolation=cv2.INTER_LANCZOS4)

        # Pure pristine medical image: NO crosshairs, NO circle, NO center dot, NO reticle banner
        _, buffer = cv2.imencode(".jpg", magnified, [int(cv2.IMWRITE_JPEG_QUALITY), 88])
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
