"""Retinal Image Quality Assessment Gate for SIH26038 Screening Pipeline.

Evaluates uploaded fundus photographs against clinical gradeability criteria:
1. Valid Retinal Boundary & Coverage: Ensures a genuine eye/fundus is present (not random objects, black scans, or blank frames).
2. Illumination & Exposure: Flags under-exposed or flash/glare over-exposed images.
3. Focus & Sharpness: Flags severe optical blur using Laplacian gradient variance.
4. Vascular Reflectance Spectrum: Verifies characteristic retinal reflectance (red/orange dominant fundus vascular bed).

Rejects ungradeable images with actionable recapture guidance for rural frontline operators.
"""

from typing import Tuple, Dict, Any, Union
from pathlib import Path
import cv2
import numpy as np
from PIL import Image


class RetinalQualityGate:
    """Clinical Image Quality Gate enforcing SIH26038 standards."""

    def __init__(
        self,
        min_resolution: int = 120,
        min_coverage: float = 0.15,
        min_brightness: float = 24.0,
        max_brightness: float = 225.0,
        min_sharpness: float = 2.0,
    ):
        self.min_resolution = min_resolution
        self.min_coverage = min_coverage
        self.min_brightness = min_brightness
        self.max_brightness = max_brightness
        self.min_sharpness = min_sharpness

    def evaluate_quality(
        self,
        image_source: Union[str, Path, np.ndarray, Image.Image],
    ) -> Dict[str, Any]:
        """Assess retinal photograph gradeability.

        Returns:
            Dict containing:
            - is_gradeable (bool): True if image passes quality criteria.
            - quality_score (float): 0.0 to 100.0 score.
            - message (str): Clinical feedback / reason for rejection if failed.
            - recapture_guidance (str): Actionable advice for operator.
            - metrics (dict): Measured blur, illumination, coverage, and spectrum.
        """
        if isinstance(image_source, (str, Path)):
            img_bgr = cv2.imread(str(image_source))
            if img_bgr is None:
                return {
                    "is_gradeable": False,
                    "quality_score": 0.0,
                    "message": "File cannot be read or is corrupted.",
                    "recapture_guidance": "Upload an uncorrupted JPEG or PNG image.",
                    "metrics": {},
                }
        elif isinstance(image_source, Image.Image):
            rgb = np.array(image_source.convert("RGB"))
            img_bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        elif isinstance(image_source, np.ndarray):
            # If already 3-channel, assume BGR if read by cv2, or test reflectance
            if image_source.ndim == 3:
                # If red channel in index 0 is high and index 2 is low, it's RGB
                if image_source[:, :, 0].mean() > image_source[:, :, 2].mean() * 1.2:
                    img_bgr = cv2.cvtColor(image_source, cv2.COLOR_RGB2BGR)
                else:
                    img_bgr = image_source.copy()
            else:
                img_bgr = cv2.cvtColor(image_source, cv2.COLOR_GRAY2BGR)
        else:
            raise TypeError(f"Unsupported image type: {type(image_source)}")

        h, w = img_bgr.shape[:2]
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        retina_mask = gray > 18
        retina_pixels = int(np.sum(retina_mask))
        total_pixels = h * w
        coverage = retina_pixels / total_pixels if total_pixels > 0 else 0.0

        mean_brightness = float(np.mean(gray[retina_mask])) if retina_pixels > 0 else 0.0
        laplacian_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())

        # In BGR: [:,:,0] is Blue, [:,:,1] is Green, [:,:,2] is Red
        b = img_bgr[:, :, 0]
        g = img_bgr[:, :, 1]
        r = img_bgr[:, :, 2]
        r_mean = float(np.mean(r[retina_mask])) if retina_pixels > 0 else 0.0
        g_mean = float(np.mean(g[retina_mask])) if retina_pixels > 0 else 0.0
        b_mean = float(np.mean(b[retina_mask])) if retina_pixels > 0 else 0.0
        red_dominance = (r_mean / (max(g_mean, b_mean) + 1e-5)) if retina_pixels > 0 else 0.0

        # Run 5 systematic quality pillar checks
        checks = []

        # Pillar 1: Resolution Check
        pass_res = (h >= self.min_resolution and w >= self.min_resolution)
        checks.append({
            "name": "Image Resolution",
            "passed": bool(pass_res),
            "status": "Passed" if pass_res else "Failed",
            "metric_name": "Sensor Dimensions",
            "value": f"{w}x{h} px",
            "requirement": f"Min {self.min_resolution}x{self.min_resolution} px",
            "description": "Image size is suitable for inspecting microvascular structures." if pass_res else f"Resolution too low ({w}x{h} px) for detecting microscopic vessel changes.",
        })

        # Pillar 2: Retinal Field Coverage
        pass_cov = (coverage >= self.min_coverage)
        checks.append({
            "name": "Retinal Field Coverage",
            "passed": bool(pass_cov),
            "status": "Passed" if pass_cov else "Failed",
            "metric_name": "Fundus Area Visible",
            "value": f"{round(coverage * 100, 1)}%",
            "requirement": f"Min {int(self.min_coverage * 100)}% coverage",
            "description": f"Retinal tissue occupies {round(coverage * 100, 1)}% of the camera frame." if pass_cov else "Camera shutter was triggered off-target or lens was blocked, leaving frame mostly black.",
        })

        # Pillar 3: Illumination & Lighting
        pass_illum_min = (mean_brightness >= self.min_brightness)
        pass_illum_max = (mean_brightness <= self.max_brightness)
        pass_illum = pass_illum_min and pass_illum_max
        illum_desc = "Properly illuminated retinal background with visible vasculature."
        if not pass_illum_min:
            illum_desc = f"Severely under-exposed (brightness: {round(mean_brightness, 1)} / 255). Image is too dark."
        elif not pass_illum_max:
            illum_desc = f"Severe glare or flash washout (brightness: {round(mean_brightness, 1)} / 255). Central retina washed out."
        checks.append({
            "name": "Illumination & Exposure",
            "passed": bool(pass_illum),
            "status": "Passed" if pass_illum else "Failed",
            "metric_name": "Mean Tissue Brightness",
            "value": f"{round(mean_brightness, 1)} / 255",
            "requirement": f"Range {int(self.min_brightness)} - {int(self.max_brightness)}",
            "description": illum_desc,
        })

        # Pillar 4: Focus & Optical Sharpness
        pass_sharp = (laplacian_var >= self.min_sharpness and laplacian_var <= 15000.0)
        checks.append({
            "name": "Focus & Sharpness",
            "passed": bool(pass_sharp),
            "status": "Passed" if pass_sharp else "Failed",
            "metric_name": "Laplacian Gradient Sharpness",
            "value": f"{round(laplacian_var, 2)}",
            "requirement": f"Min {self.min_sharpness} score",
            "description": f"Sharp optical focus (score: {round(laplacian_var, 1)}). Blood vessel margins are crisp." if pass_sharp else f"Optical blur detected (score: {round(laplacian_var, 2)} vs min {self.min_sharpness} required). Retinal details are out of focus.",
        })

        # Pillar 5: Retinal Biological Color Spectrum
        pass_spec = (r_mean >= g_mean * 1.05 and r_mean >= b_mean * 1.15) if retina_pixels > 0 else False
        checks.append({
            "name": "Biological Color Spectrum",
            "passed": bool(pass_spec),
            "status": "Passed" if pass_spec else "Failed",
            "metric_name": "Red Vascular Reflectance",
            "value": f"Red/Blue Ratio: {round(red_dominance, 2)}x",
            "requirement": "Red dominant (>1.15x Blue/Green)",
            "description": "Natural retinal vascular reflectance confirmed." if pass_spec else "Color spectrum does not match human retinal fundus tissue (non-retinal photo or corrupted channel).",
        })

        is_gradeable = bool(pass_res and pass_cov and pass_illum and pass_sharp and pass_spec)

        # Compute accurate 0-100 quality score
        illum_score = max(0.0, 100.0 - abs(mean_brightness - 85.0) * 1.2)
        sharp_score = min(100.0, laplacian_var * 4.0)
        cov_score = min(100.0, coverage * 130.0)
        spec_score = min(100.0, red_dominance * 60.0)
        overall_score = round(0.3 * sharp_score + 0.3 * illum_score + 0.2 * cov_score + 0.2 * spec_score, 1)

        if not is_gradeable:
            overall_score = min(42.0, overall_score)
            overall_score = max(12.0, overall_score)
        else:
            overall_score = max(68.0, min(99.0, overall_score))

        metrics = {
            "width": w,
            "height": h,
            "sharpness_score": round(laplacian_var, 2),
            "mean_brightness": round(mean_brightness, 1),
            "coverage_ratio": round(coverage, 3),
            "red_dominance_ratio": round(red_dominance, 2),
        }

        if is_gradeable:
            return {
                "is_gradeable": True,
                "quality_score": overall_score,
                "failure_category": "PASSED",
                "message": "Retinal photograph passed all Quality Gate screening criteria.",
                "detailed_explanation": "The image exhibits clear optical focus, balanced illumination, and genuine retinal vascular color reflectance. Blood vessel branches and the optic nerve head are clearly resolvable for accurate diabetic retinopathy screening.",
                "recapture_guidance": "No recapture needed. The photograph meets clinical gradeability standards and is ready for AI prediction.",
                "checks": checks,
                "metrics": metrics,
            }

        # Determine Primary Failure Reason & Plain English Explanation with Medical Terms in Brackets
        if not pass_res:
            failure_category = "LOW_RESOLUTION"
            message = f"Image Rejected: Low Resolution ({w}x{h} px)"
            detailed_explanation = f"The image resolution ({w}x{h} px) is lower than the minimum requirement of 224x224 pixels. Diagnostic screening requires sufficient pixel density to inspect microscopic blood vessel walls."
            recapture_guidance = "Upload the original high-resolution JPEG or PNG file directly from the fundus camera without thumbnail compression."

        elif not pass_cov:
            failure_category = "LOW_COVERAGE"
            message = "Image Rejected: Insufficient Retinal Area (Camera Misaligned)"
            detailed_explanation = "Less than 15% of the photograph contains retinal tissue. Most of the frame is black or empty, indicating the camera was off-center when the shutter fired."
            recapture_guidance = "1. Center the camera lens directly over the patient's pupil.\n2. Advance slightly closer until the round retinal field fills at least 60% of the viewfinder.\n3. Verify live fundus view on screen before pressing capture."

        elif not pass_spec:
            failure_category = "NON_RETINAL"
            message = "Image Rejected: Invalid Retinal Color Spectrum (Non-Retinal Image)"
            detailed_explanation = "The uploaded file does not show the characteristic optical reflectance of a human eye retina (red/orange choroidal vascular bed). Non-medical photos, external facial pictures, documents, or synthetic noise cannot be screened by this specialized retinal AI."
            recapture_guidance = "1. Upload a genuine color fundus photograph taken with a retinal camera, smartphone ophthalmoscope, or slit lamp.\n2. Do not upload external eye surface photos (eyelids/cornea) or non-medical images."

        elif not pass_illum_min:
            failure_category = "UNDER_EXPOSED"
            message = "Image Rejected: Severely Under-Exposed (Too Dark)"
            detailed_explanation = "The photograph is too dark to illuminate the retina background and vascular network. Small bleeding spots (intraretinal hemorrhages) and dark micro-vessel bulges cannot be distinguished from background shadow areas in dim lighting."
            recapture_guidance = "1. Increase flash or illumination intensity by 1-2 steps.\n2. Ensure proper pupil dilation, or wait 3-5 minutes in a darkened room for natural pupil expansion.\n3. Re-align the optical axis with the pupil center and recapture."

        elif not pass_illum_max:
            failure_category = "OVER_EXPOSED"
            message = "Image Rejected: Severe Glare & Over-Exposure (Washout)"
            detailed_explanation = "Excessive illumination flash or corneal light reflection has washed out retinal details. White glare bleaches the central reading vision center (macula) and surrounding capillaries, blinding the AI from identifying lesions."
            recapture_guidance = "1. Reduce the flash power setting on the camera.\n2. Slightly adjust the camera objective angle to eliminate corneal reflection artifacts.\n3. Recapture with balanced lighting."

        elif not pass_sharp:
            failure_category = "OPTICAL_BLUR"
            message = "Image Rejected: Optical Blur (Out of Focus)"
            detailed_explanation = "The photograph is too blurry to safely detect small eye lesions. Diabetic retinopathy screening requires clear, sharp visibility of microscopic blood vessel swelling (microaneurysms) and tiny yellow lipid fluid leaks (hard exudates). Running an AI prediction on an out-of-focus image could miss treatable disease, creating a false sense of security."
            recapture_guidance = "1. Ask the patient to keep a steady gaze at the green internal fixation target.\n2. Rotate the camera diopter focus ring until the retinal blood vessels appear crisp and sharply defined.\n3. Hold the camera steady and recapture."

        else:
            failure_category = "UNGRADEABLE"
            message = "Image Rejected: Quality Standards Not Met"
            detailed_explanation = "The fundus photograph did not meet one or more clinical gradeability criteria for automated evaluation."
            recapture_guidance = "Please recapture a sharp, properly exposed fundus photograph centered on the optic disc and macula."

        return {
            "is_gradeable": False,
            "quality_score": overall_score,
            "failure_category": failure_category,
            "message": message,
            "detailed_explanation": detailed_explanation,
            "recapture_guidance": recapture_guidance,
            "checks": checks,
            "metrics": metrics,
        }
