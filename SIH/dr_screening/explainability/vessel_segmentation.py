"""Retinal Vasculature Segmentation and Arteriolar/Venular Classification.

Extracts the retinal blood vessel tree and classifies major branches
into arterioles and venules for clinical landmarking and lesion isolation.
"""

from typing import Tuple, Dict, Any, List
import cv2
import numpy as np


class RetinalVesselSegmenter:
    """Extracts retinal vasculature using green-channel enhancement,

    morphological filtering, and caliber/color profiling.
    """

    def __init__(self, clahe_clip: float = 3.0, tile_grid: Tuple[int, int] = (8, 8)):
        self.clahe = cv2.createCLAHE(clipLimit=clahe_clip, tileGridSize=tile_grid)

    def segment(self, img_bgr: np.ndarray, fov_mask: Optional[np.ndarray] = None) -> Dict[str, Any]:
        """Segment blood vessels from color retinal fundus image.

        Args:
            img_bgr: BGR fundus photograph as uint8 array.
            fov_mask: Optional binary mask of the retina FOV.

        Returns:
            Dictionary containing:
            - 'vessel_mask': uint8 binary mask of complete vascular tree (255=vessel)
            - 'arteriole_mask': uint8 binary mask of arterioles
            - 'venule_mask': uint8 binary mask of venules
            - 'arteriole_points': List of (x, y) coordinates for clinical annotation
            - 'venule_points': List of (x, y) coordinates for clinical annotation
            - 'vessel_density': float percentage of retinal area covered by vessels
        """
        h, w = img_bgr.shape[:2]

        # 1. FOV Mask if not provided
        if fov_mask is None:
            gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
            _, fov_mask = cv2.threshold(gray, 20, 255, cv2.THRESH_BINARY)
            fov_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))
            fov_mask = cv2.erode(fov_mask, fov_kernel, iterations=2)

        # 2. Extract Green channel & Apply CLAHE
        # Blood absorbs green light strongly (hemoglobin peak absorbance ~540-575 nm)
        g = img_bgr[:, :, 1]
        g_enh = self.clahe.apply(g)

        # Invert green so vessels are bright on dark background
        inv_g = 255 - g_enh

        # 3. Multi-scale morphological vessel isolation
        # Retinal vessels are elongated, tubular structures
        # Top-hat with disk structuring element
        kernel_med = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
        kernel_large = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
        tophat_med = cv2.morphologyEx(inv_g, cv2.MORPH_TOPHAT, kernel_med)
        tophat_large = cv2.morphologyEx(inv_g, cv2.MORPH_TOPHAT, kernel_large)
        vessel_response = cv2.addWeighted(tophat_med, 0.6, tophat_large, 0.4, 0)
        vessel_response = cv2.bitwise_and(vessel_response, vessel_response, mask=fov_mask)

        # 4. Adaptive Thresholding & Median Filter
        # Threshold to separate vessel tree from diffuse background
        thresh_val = np.percentile(vessel_response[fov_mask > 0], 85.0) if np.any(fov_mask > 0) else 30
        _, binary_vessels = cv2.threshold(vessel_response, thresh_val, 255, cv2.THRESH_BINARY)

        # Remove tiny specks that are not vessels (min area filtering)
        nb_components, output, stats, centroids = cv2.connectedComponentsWithStats(binary_vessels, connectivity=8)
        clean_vessels = np.zeros_like(binary_vessels)
        for i in range(1, nb_components):
            area = stats[i, cv2.CC_STAT_AREA]
            if area >= 25:  # Keep continuous vessel segments
                clean_vessels[output == i] = 255

        # 5. Distinguish Arterioles vs Venules
        # Venules: thicker caliber, lower red reflectance, darker lumen
        # Arterioles: narrower caliber (A/V ratio ~ 2:3), brighter red lumen
        dist_transform = cv2.distanceTransform(clean_vessels, cv2.DIST_L2, 3)
        b, g, r = cv2.split(img_bgr)
        # Red-to-green ratio is higher in oxygenated arterioles
        rg_ratio = np.zeros((h, w), dtype=np.float32)
        valid_v = clean_vessels > 0
        rg_ratio[valid_v] = (r[valid_v].astype(np.float32) + 1.0) / (g[valid_v].astype(np.float32) + 1.0)

        # Distance transform indicates caliber (radius)
        # Venules have larger distance transform (> median vessel width) and lower rg_ratio
        vessel_calibers = dist_transform[valid_v]
        med_caliber = np.median(vessel_calibers) if len(vessel_calibers) > 0 else 2.0

        venule_mask = np.zeros_like(clean_vessels)
        arteriole_mask = np.zeros_like(clean_vessels)

        for i in range(1, nb_components):
            comp_mask = (output == i)
            if not np.any(comp_mask):
                continue
            mean_cal = np.mean(dist_transform[comp_mask])
            mean_rg = np.mean(rg_ratio[comp_mask])

            # Major venules are wider (> median caliber)
            if mean_cal > med_caliber and mean_rg < 1.4:
                venule_mask[comp_mask] = 255
            elif mean_rg >= 1.25 or mean_cal <= med_caliber:
                arteriole_mask[comp_mask] = 255
            else:
                arteriole_mask[comp_mask] = 255

        # 6. Sample Clean Coordinate Points for Annotation Pointers
        # Find continuous branches away from the edge for representative arrows
        arteriole_points = self._find_sample_points(arteriole_mask, fov_mask, max_points=2)
        venule_points = self._find_sample_points(venule_mask, fov_mask, max_points=2)

        if not venule_points and arteriole_points:
            # Fallback: pick another distinct branch from the vessel tree
            all_points = self._find_sample_points(clean_vessels, fov_mask, max_points=4)
            for p in all_points:
                if p not in arteriole_points:
                    venule_points.append(p)
                    if len(venule_points) >= 1:
                        break

        retina_area = float(np.sum(fov_mask > 0)) if np.any(fov_mask > 0) else float(h * w)
        vessel_area = float(np.sum(clean_vessels > 0))
        density = (vessel_area / retina_area) * 100.0

        return {
            "vessel_mask": clean_vessels,
            "arteriole_mask": arteriole_mask,
            "venule_mask": venule_mask,
            "arteriole_points": arteriole_points,
            "venule_points": venule_points,
            "vessel_density": round(density, 2),
        }

    def _find_sample_points(self, mask: np.ndarray, fov_mask: np.ndarray, max_points: int = 2) -> List[Tuple[int, int]]:
        """Find prominent, stable points along vessel segments for annotation arrows."""
        points = []
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        # Sort contours by length/area
        contours = sorted(contours, key=cv2.contourArea, reverse=True)

        h, w = mask.shape[:2]
        center_x, center_y = w // 2, h // 2

        for cnt in contours[:max_points * 2]:
            if cv2.contourArea(cnt) < 60:
                continue
            # Pick mid-point of the contour
            pts = cnt[:, 0, :]
            mid_idx = len(pts) // 2
            pt = (int(pts[mid_idx][0]), int(pts[mid_idx][1]))
            # Make sure it's safely inside retina
            if fov_mask[pt[1], pt[0]] > 0:
                points.append(pt)
                if len(points) >= max_points:
                    break

        return points
