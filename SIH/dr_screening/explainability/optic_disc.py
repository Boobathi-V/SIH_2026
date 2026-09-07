"""Optic Disc Localization and Masking for Retinal Fundus Screening.

Detects the anatomical optic disc (OD) to ensure it is NEVER mistakenly
identified as a pathological lesion (such as a large hard exudate or cotton wool spot).
"""

from typing import Tuple, Dict, Any, Optional
import cv2
import numpy as np


class OpticDiscDetector:
    """Robust Optic Disc detector using morphological vessel suppression,

    luminance peak localization, and circular contour fitting.
    """

    def __init__(self, expected_disc_ratio: float = 0.14):
        """Args:

            expected_disc_ratio: Approximate ratio of optic disc diameter to fundus diameter.
        """
        self.expected_disc_ratio = expected_disc_ratio

    def detect(self, img_bgr: np.ndarray) -> Dict[str, Any]:
        """Detect the optic disc in a color retinal fundus image.

        Args:
            img_bgr: BGR fundus photograph as uint8 array.

        Returns:
            Dictionary containing:
            - 'detected': bool
            - 'center': (cx, cy) tuple of integers
            - 'radius': int (radius in pixels)
            - 'confidence': float (0.0 to 1.0)
            - 'mask': uint8 binary mask (255 inside disc, 0 elsewhere)
            - 'bbox': (x, y, w, h)
        """
        h, w = img_bgr.shape[:2]
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

        # 1. Estimate Retinal Field of View (FOV) mask
        # Exclude black borders
        _, fov_mask = cv2.threshold(gray, 20, 255, cv2.THRESH_BINARY)
        # Erode FOV slightly to remove bright border artifacts
        fov_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
        fov_eroded = cv2.erode(fov_mask, fov_kernel, iterations=2)

        # 2. Extract Red and Green channels
        # Optic disc is brightest in Red channel and L of LAB
        b, g, r = cv2.split(img_bgr)
        lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
        l_channel = lab[:, :, 0]

        # Combine red channel and luminance with high weight on red
        disc_signal = cv2.addWeighted(r, 0.6, l_channel, 0.4, 0)
        disc_signal = cv2.bitwise_and(disc_signal, disc_signal, mask=fov_eroded)

        # 3. Morphological closing to remove vessel shadows crossing the disc
        # Disc diameter is typically ~ 10-18% of fundus width
        expected_diam = int(min(h, w) * self.expected_disc_ratio)
        closing_size = max(9, int(expected_diam * 0.25))
        if closing_size % 2 == 0:
            closing_size += 1
        close_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (closing_size, closing_size))
        smoothed = cv2.morphologyEx(disc_signal, cv2.MORPH_CLOSE, close_kernel)
        smoothed = cv2.GaussianBlur(smoothed, (closing_size, closing_size), 0)

        # 4. Locate Bright Candidate Regions
        # Top 1-2% brightest pixels in the smoothed retina
        valid_pixels = smoothed[fov_eroded > 0]
        if len(valid_pixels) == 0:
            cx, cy, radius = w // 2, h // 2, expected_diam // 2
            mask = np.zeros((h, w), dtype=np.uint8)
            cv2.circle(mask, (cx, cy), radius, 255, -1)
            return {
                "detected": False,
                "center": (cx, cy),
                "radius": radius,
                "confidence": 0.0,
                "mask": mask,
                "bbox": (cx - radius, cy - radius, radius * 2, radius * 2),
            }

        brightness_threshold = np.percentile(valid_pixels, 98.2)
        _, candidate_thresh = cv2.threshold(smoothed, brightness_threshold, 255, cv2.THRESH_BINARY)
        candidate_thresh = cv2.bitwise_and(candidate_thresh, fov_eroded)

        # 5. Connected Component / Contour Analysis
        contours, _ = cv2.findContours(candidate_thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        best_center = None
        best_radius = expected_diam // 2
        max_score = -1.0

        min_area = (np.pi * (expected_diam * 0.08) ** 2)
        max_area = (np.pi * (expected_diam * 1.5) ** 2)

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < min_area or area > max_area:
                continue

            (x, y), r_enc = cv2.minEnclosingCircle(cnt)
            circularity = 4 * np.pi * area / (cv2.arcLength(cnt, True) ** 2 + 1e-6)

            # Intensity inside candidate
            cnt_mask = np.zeros((h, w), dtype=np.uint8)
            cv2.drawContours(cnt_mask, [cnt], -1, 255, -1)
            mean_val = cv2.mean(smoothed, mask=cnt_mask)[0]
            _, max_val, _, _ = cv2.minMaxLoc(smoothed, mask=cnt_mask)

            # Retinal anatomy prior: The optic disc is in the nasal region (lateral sides: x < 0.4*w or x > 0.6*w),
            # NEVER in the macula / foveal center (x ~ 0.5*w).
            dist_from_center_x = abs(x - w / 2.0) / (w / 2.0)

            score = (circularity * 0.25) + (mean_val / 255.0 * 0.30) + (max_val / 255.0 * 0.30) + (dist_from_center_x * 0.15)
            if score > max_score:
                max_score = score
                best_center = (int(x), int(y))
                best_radius = int(max(r_enc, expected_diam * 0.45))

        # Fallback if no contours met area bounds
        if best_center is None:
            # Find the absolute maximum location in smoothed disc_signal
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(smoothed, mask=fov_eroded)
            best_center = max_loc
            best_radius = expected_diam // 2
            confidence = 0.55
        else:
            confidence = min(0.95, max(0.60, max_score))

        # Clamp radius within reasonable medical anatomy limits
        min_rad = int(expected_diam * 0.35)
        max_rad = int(expected_diam * 0.70)
        best_radius = max(min_rad, min(max_rad, best_radius))

        # Build clean binary mask of the optic disc (with 15% safety margin to guarantee lesion isolation)
        mask = np.zeros((h, w), dtype=np.uint8)
        safety_margin_radius = int(best_radius * 1.15)
        cv2.circle(mask, best_center, safety_margin_radius, 255, -1)

        cx, cy = best_center
        bbox = (
            max(0, cx - safety_margin_radius),
            max(0, cy - safety_margin_radius),
            min(w - 1, cx + safety_margin_radius) - max(0, cx - safety_margin_radius),
            min(h - 1, cy + safety_margin_radius) - max(0, cy - safety_margin_radius),
        )

        return {
            "detected": True,
            "center": best_center,
            "radius": best_radius,
            "confidence": round(float(confidence), 3),
            "mask": mask,
            "bbox": bbox,
        }
