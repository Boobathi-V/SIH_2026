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

        # 1. Dimension Check
        if h < self.min_resolution or w < self.min_resolution:
            return {
                "is_gradeable": False,
                "quality_score": 10.0,
                "message": f"Image resolution too low ({w}x{h} px).",
                "recapture_guidance": "Standard fundus photographs should be at least 224x224 pixels. Please recapture at higher resolution.",
                "metrics": {"width": w, "height": h},
            }

        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        retina_mask = gray > 18
        retina_pixels = int(np.sum(retina_mask))
        total_pixels = h * w
        coverage = retina_pixels / total_pixels

        # 2. Retinal Coverage / Black Screen Check
        if coverage < self.min_coverage:
            return {
                "is_gradeable": False,
                "quality_score": 15.0,
                "message": "Insufficient retinal area detected (image is mostly black or empty).",
                "recapture_guidance": "Ensure camera lens is positioned directly over the pupil and flash is triggered properly.",
                "metrics": {"coverage_ratio": round(coverage, 3)},
            }

        # 3. Illumination / Exposure Check
        mean_brightness = float(np.mean(gray[retina_mask])) if retina_pixels > 0 else 0.0
        if mean_brightness < self.min_brightness:
            return {
                "is_gradeable": False,
                "quality_score": 25.0,
                "message": "Retinal photograph severely under-exposed (too dark).",
                "recapture_guidance": "Increase illumination intensity or pupil dilation to expose retinal microvasculature.",
                "metrics": {"mean_brightness": round(mean_brightness, 1)},
            }

        if mean_brightness > self.max_brightness:
            return {
                "is_gradeable": False,
                "quality_score": 30.0,
                "message": "Retinal photograph over-exposed with severe glare/washout.",
                "recapture_guidance": "Reduce illumination flash intensity to prevent macular blowout and reflections.",
                "metrics": {"mean_brightness": round(mean_brightness, 1)},
            }

        # 4. Blur & Focus Check (Laplacian Variance)
        laplacian_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        if laplacian_var < self.min_sharpness:
            return {
                "is_gradeable": False,
                "quality_score": 35.0,
                "message": "Optical blur detected — fundus structures are not in focus.",
                "recapture_guidance": "Adjust camera diopter focus on the optic disc and ensure patient keeps steady gaze during capture.",
                "metrics": {"sharpness_score": round(laplacian_var, 2)},
            }

        # 5. Biological Fundus Spectrum Verification
        # In BGR: img_bgr[:,:,0] is Blue, [:,:,1] is Green, [:,:,2] is Red
        b = img_bgr[:, :, 0]
        g = img_bgr[:, :, 1]
        r = img_bgr[:, :, 2]
        
        r_mean = float(np.mean(r[retina_mask])) if retina_pixels > 0 else 0.0
        g_mean = float(np.mean(g[retina_mask])) if retina_pixels > 0 else 0.0
        b_mean = float(np.mean(b[retina_mask])) if retina_pixels > 0 else 0.0

        # In retinal fundus photography, Red channel reflectance dominates Green and Blue significantly
        # (r_mean must be notably greater than b_mean and >= g_mean)
        if r_mean < g_mean * 1.05 or r_mean < b_mean * 1.15:
            return {
                "is_gradeable": False,
                "quality_score": 20.0,
                "message": "Uploaded image does not exhibit standard retinal fundus vascular reflectance.",
                "recapture_guidance": "Please upload a genuine retinal fundus photograph showing the optic disc, macula, and retinal blood vessels.",
                "metrics": {
                    "red_mean": round(r_mean, 1),
                    "green_mean": round(g_mean, 1),
                    "blue_mean": round(b_mean, 1),
                },
            }

        # Reject pure synthetic noise / unnatural high variance
        if laplacian_var > 15000.0:
            return {
                "is_gradeable": False,
                "quality_score": 25.0,
                "message": "Artificial noise or digital artifact detected instead of natural retinal tissue.",
                "recapture_guidance": "Please provide an optical photograph from a fundus camera, smartphone ophthalmoscope, or slit lamp.",
                "metrics": {"sharpness_score": round(laplacian_var, 2)},
            }

        # Compute Quality Score (0 to 100)
        illum_score = max(0, 100 - abs(mean_brightness - 85) * 1.2)
        sharp_score = min(100, laplacian_var * 4.0)
        cov_score = min(100, coverage * 130)
        overall_score = round(0.4 * illum_score + 0.35 * sharp_score + 0.25 * cov_score, 1)
        overall_score = max(60.0, min(99.0, overall_score))

        return {
            "is_gradeable": True,
            "quality_score": overall_score,
            "message": "Retinal photograph passed clinical quality screening gate.",
            "recapture_guidance": "No recapture needed. Image is clear and gradeable.",
            "metrics": {
                "sharpness_score": round(laplacian_var, 2),
                "mean_brightness": round(mean_brightness, 1),
                "coverage_ratio": round(coverage, 3),
                "red_reflectance_ratio": round(r_mean / (g_mean + 1e-5), 2),
            },
        }
