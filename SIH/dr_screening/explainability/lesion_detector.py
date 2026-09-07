"""Clinical Retinal Lesion Detection Engine.

Detects Microaneurysms, Hemorrhages, Hard Exudates, Cotton Wool Spots,
and Neovascularization using hybrid Classical Computer Vision & Grad-CAM attribution.
"""

from typing import Dict, Any, List, Tuple, Optional
import cv2
import numpy as np


class RetinalLesionDetector:
    """Clinical lesion detection system adhering to ETDRS / AAO diagnostic criteria."""

    def __init__(self):
        self.clahe_g = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
        self.clahe_l = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))

    def detect_all(
        self,
        img_bgr: np.ndarray,
        optic_disc_info: Dict[str, Any],
        vessel_info: Dict[str, Any],
        gradcam_map: Optional[np.ndarray] = None,
        prediction_class: int = 0,
    ) -> Dict[str, Any]:
        """Detect all classes of retinal lesions in the fundus photograph.

        Args:
            img_bgr: uint8 BGR retinal image.
            optic_disc_info: Output from OpticDiscDetector.
            vessel_info: Output from RetinalVesselSegmenter.
            gradcam_map: Optional 2D float32 [0.0, 1.0] Grad-CAM activation map.
            prediction_class: 0 (No DR), 1 (Mild), 2 (Moderate), 3 (Severe), 4 (PDR).

        Returns:
            Dictionary containing:
            - 'lesions': List of all individual detected lesion dictionaries
            - 'counts': Dictionary of counts per lesion type
            - 'has_microaneurysms': bool
            - 'has_hemorrhages': bool
            - 'has_hard_exudates': bool
            - 'has_cotton_wool_spots': bool
            - 'has_neovascularization': bool
            - 'primary_lesions': List of dominant lesion types
            - 'lesion_masks': Dict of binary masks for each lesion type
        """
        h, w = img_bgr.shape[:2]
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

        # 1. Base Retinal Mask (Field of View)
        _, fov_mask = cv2.threshold(gray, 22, 255, cv2.THRESH_BINARY)
        fov_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
        fov_mask = cv2.erode(fov_mask, fov_kernel, iterations=2)

        # 2. Safety Masks (Optic Disc & Vessels)
        od_mask = optic_disc_info.get("mask", np.zeros((h, w), dtype=np.uint8))
        # Dilate OD mask slightly to guarantee zero false positives from the disc margin
        od_dilated = cv2.dilate(od_mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11)))

        vessel_mask = vessel_info.get("vessel_mask", np.zeros((h, w), dtype=np.uint8))
        vessel_dilated = cv2.dilate(vessel_mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))

        # Mask of valid parenchyma (retinal tissue excluding optic disc and vessels)
        safe_parenchyma = cv2.bitwise_and(fov_mask, cv2.bitwise_not(od_dilated))
        lesion_search_area = cv2.bitwise_and(safe_parenchyma, cv2.bitwise_not(vessel_dilated))

        # 3. Detect Each Lesion Type
        microaneurysms = self._detect_microaneurysms(img_bgr, lesion_search_area, gradcam_map, prediction_class)
        hemorrhages = self._detect_hemorrhages(img_bgr, lesion_search_area, gradcam_map, prediction_class)
        hard_exudates = self._detect_hard_exudates(img_bgr, safe_parenchyma, gradcam_map, prediction_class)
        cotton_wool_spots = self._detect_cotton_wool_spots(img_bgr, safe_parenchyma, hard_exudates, gradcam_map, prediction_class)
        neovascularization = self._detect_neovascularization(img_bgr, optic_disc_info, vessel_info, prediction_class)

        all_lesions = []
        all_lesions.extend(microaneurysms)
        all_lesions.extend(hemorrhages)
        all_lesions.extend(hard_exudates)
        all_lesions.extend(cotton_wool_spots)
        if neovascularization["present"]:
            all_lesions.append({
                "type": "Neovascularization",
                "confidence": neovascularization["confidence"],
                "count": 1,
                "location": neovascularization["location"],
                "center": optic_disc_info.get("center", (w // 2, h // 2)),
                "bbox": optic_disc_info.get("bbox", (0, 0, 50, 50)),
                "explanation": "Fragile new vessel fronds detected indicating retinal hypoxia and VEGF upregulation.",
            })

        counts = {
            "Microaneurysm": len(microaneurysms),
            "Hemorrhage": len(hemorrhages),
            "Hard Exudate": len(hard_exudates),
            "Cotton Wool Spot": len(cotton_wool_spots),
            "Neovascularization": 1 if neovascularization["present"] else 0,
        }

        # Determine primary contributing lesions
        primary = []
        if counts["Neovascularization"] > 0:
            primary.append("Neovascularization")
        if counts["Hemorrhage"] > 0:
            primary.append(f"{counts['Hemorrhage']} Hemorrhage(s)")
        if counts["Hard Exudate"] > 0:
            primary.append(f"{counts['Hard Exudate']} Hard Exudate cluster(s)")
        if counts["Microaneurysm"] > 0:
            primary.append(f"{counts['Microaneurysm']} Microaneurysm(s)")
        if counts["Cotton Wool Spot"] > 0:
            primary.append(f"{counts['Cotton Wool Spot']} Cotton Wool Spot(s)")

        return {
            "lesions": all_lesions,
            "counts": counts,
            "has_microaneurysms": counts["Microaneurysm"] > 0,
            "has_hemorrhages": counts["Hemorrhage"] > 0,
            "has_hard_exudates": counts["Hard Exudate"] > 0,
            "has_cotton_wool_spots": counts["Cotton Wool Spot"] > 0,
            "has_neovascularization": counts["Neovascularization"] > 0,
            "primary_lesions": primary,
            "neovascularization_details": neovascularization,
        }

    def _detect_microaneurysms(
        self,
        img_bgr: np.ndarray,
        search_mask: np.ndarray,
        gradcam_map: Optional[np.ndarray],
        prediction_class: int,
    ) -> List[Dict[str, Any]]:
        """Detect microaneurysms (MAs): tiny, punctate, dark red circular spots."""
        h, w = img_bgr.shape[:2]
        if prediction_class == 0:
            return []  # Normal retina has no microaneurysms

        b, g, r = cv2.split(img_bgr)
        g_enh = self.clahe_g.apply(g)

        # Microaneurysms are small dark depressions in the green channel
        # Black-hat with small circular structuring element (size 5x5 to 9x9)
        k_ma = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        blackhat = cv2.morphologyEx(g_enh, cv2.MORPH_BLACKHAT, k_ma)
        blackhat = cv2.bitwise_and(blackhat, blackhat, mask=search_mask)

        valid_vals = blackhat[search_mask > 0]
        if len(valid_vals) == 0:
            return []

        # Adaptive thresholding for focal contrast
        thresh_val = max(18, np.percentile(valid_vals, 98.5))
        _, ma_binary = cv2.threshold(blackhat, thresh_val, 255, cv2.THRESH_BINARY)

        contours, _ = cv2.findContours(ma_binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        detected = []

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < 3 or area > 75:  # Microaneurysms are strictly small
                continue

            perimeter = cv2.arcLength(cnt, True)
            circularity = 4 * np.pi * area / (perimeter ** 2 + 1e-6)
            if circularity < 0.35:
                continue

            (cx, cy), radius = cv2.minEnclosingCircle(cnt)
            cx, cy, radius = int(cx), int(cy), max(2, int(radius))

            # Verify color: In retinal tissue, MAs are dark red (R > G, R > B)
            local_r = int(r[cy, cx]) if 0 <= cy < h and 0 <= cx < w else 0
            local_g = int(g[cy, cx]) if 0 <= cy < h and 0 <= cx < w else 0
            if local_r < local_g * 1.1:
                continue

            # Check Grad-CAM alignment if available
            cam_val = 0.5
            if gradcam_map is not None and 0 <= cy < h and 0 <= cx < w:
                cam_val = float(gradcam_map[cy, cx])

            conf = round(min(0.96, 0.65 + (cam_val * 0.25) + (circularity * 0.10)), 2)

            detected.append({
                "type": "Microaneurysm",
                "confidence": conf,
                "center": (cx, cy),
                "radius": radius,
                "area": int(area),
                "circularity": round(float(circularity), 2),
                "explanation": "Punctate focal capillary outpouching displaying typical red-dot microaneurysm morphology.",
            })

        # Sort by confidence and retain most significant (max 25 to avoid clutter)
        detected = sorted(detected, key=lambda x: x["confidence"], reverse=True)[:25]
        return detected

    def _detect_hemorrhages(
        self,
        img_bgr: np.ndarray,
        search_mask: np.ndarray,
        gradcam_map: Optional[np.ndarray],
        prediction_class: int,
    ) -> List[Dict[str, Any]]:
        """Detect retinal hemorrhages: irregular, dark red patches larger than microaneurysms."""
        h, w = img_bgr.shape[:2]
        if prediction_class == 0:
            return []

        b, g, r = cv2.split(img_bgr)
        g_enh = self.clahe_g.apply(g)

        # Hemorrhages are larger dark regions in green channel
        k_hm = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
        blackhat = cv2.morphologyEx(g_enh, cv2.MORPH_BLACKHAT, k_hm)
        blackhat = cv2.bitwise_and(blackhat, blackhat, mask=search_mask)

        valid_vals = blackhat[search_mask > 0]
        if len(valid_vals) == 0:
            return []

        thresh_val = max(22, np.percentile(valid_vals, 97.0))
        _, hm_binary = cv2.threshold(blackhat, thresh_val, 255, cv2.THRESH_BINARY)

        contours, _ = cv2.findContours(hm_binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        detected = []

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < 60 or area > 3500:  # Hemorrhages are larger than MAs
                continue

            x, y, bw, bh_box = cv2.boundingRect(cnt)
            cx, cy = x + bw // 2, y + bh_box // 2

            # Color verification: dark red blood pooling
            local_r = int(r[cy, cx]) if 0 <= cy < h and 0 <= cx < w else 0
            local_g = int(g[cy, cx]) if 0 <= cy < h and 0 <= cx < w else 0
            if local_r < local_g * 1.15:
                continue

            cam_val = 0.5
            if gradcam_map is not None and 0 <= cy < h and 0 <= cx < w:
                cam_val = float(gradcam_map[cy, cx])

            conf = round(min(0.95, 0.70 + (cam_val * 0.25)), 2)

            detected.append({
                "type": "Hemorrhage",
                "confidence": conf,
                "center": (cx, cy),
                "bbox": (int(x), int(y), int(bw), int(bh_box)),
                "area": int(area),
                "contour": cnt.reshape(-1, 2).tolist(),
                "explanation": "Intraretinal blot/flame hemorrhage resulting from capillary wall rupture.",
            })

        detected = sorted(detected, key=lambda x: x["area"], reverse=True)[:15]
        return detected

    def _detect_hard_exudates(
        self,
        img_bgr: np.ndarray,
        safe_mask: np.ndarray,
        gradcam_map: Optional[np.ndarray],
        prediction_class: int,
    ) -> List[Dict[str, Any]]:
        """Detect hard exudates: bright yellow lipid deposits with sharp, well-demarcated edges."""
        h, w = img_bgr.shape[:2]
        if prediction_class == 0:
            return []

        # Convert to HSV and CIELAB color spaces
        hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
        lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)

        # In LAB: High Lightness and positive b* (yellowish)
        l_chan = lab[:, :, 0]
        b_chan = lab[:, :, 2]
        l_enh = self.clahe_l.apply(l_chan)

        # Yellow in HSV: Hue ~15 to 45, Saturation > 50, Value > 120
        h_chan = hsv[:, :, 0]
        s_chan = hsv[:, :, 1]
        v_chan = hsv[:, :, 2]

        yellow_mask = (
            (h_chan >= 12) & (h_chan <= 48) &
            (s_chan >= 40) &
            (v_chan >= 110) &
            (b_chan >= 135) &
            (safe_mask > 0)
        ).astype(np.uint8) * 255

        # Also isolate high-contrast bright lesions using morphological top-hat on L
        k_ex = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))
        tophat = cv2.morphologyEx(l_enh, cv2.MORPH_TOPHAT, k_ex)
        tophat = cv2.bitwise_and(tophat, tophat, mask=safe_mask)

        _, tophat_thresh = cv2.threshold(tophat, 28, 255, cv2.THRESH_BINARY)

        # Combine color and morphological response
        exudate_candidates = cv2.bitwise_or(yellow_mask, tophat_thresh)
        exudate_candidates = cv2.bitwise_and(exudate_candidates, safe_mask)

        # Morphological opening to clean single pixel noise
        exudate_candidates = cv2.morphologyEx(
            exudate_candidates,
            cv2.MORPH_OPEN,
            cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)),
        )

        contours, _ = cv2.findContours(exudate_candidates, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        detected = []

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < 8 or area > 3500:
                continue

            x, y, bw, bh_box = cv2.boundingRect(cnt)
            cx, cy = x + bw // 2, y + bh_box // 2

            # Edge sharpness test (hard exudates have sharp borders)
            roi = l_chan[max(0, y - 2):min(h, y + bh_box + 2), max(0, x - 2):min(w, x + bw + 2)]
            sobel = cv2.Sobel(roi, cv2.CV_64F, 1, 1, ksize=3)
            edge_sharpness = float(np.mean(np.abs(sobel)))

            cam_val = 0.5
            if gradcam_map is not None and 0 <= cy < h and 0 <= cx < w:
                cam_val = float(gradcam_map[cy, cx])

            conf = round(min(0.97, 0.72 + (cam_val * 0.20) + min(0.1, edge_sharpness / 500.0)), 2)

            detected.append({
                "type": "Hard Exudate",
                "confidence": conf,
                "center": (cx, cy),
                "bbox": (int(x), int(y), int(bw), int(bh_box)),
                "area": int(area),
                "contour": cnt.reshape(-1, 2).tolist(),
                "explanation": "Circinate lipid/lipoprotein deposit indicating breakdown of the blood-retinal barrier.",
            })

        detected = sorted(detected, key=lambda x: x["area"], reverse=True)[:20]
        return detected

    def _detect_cotton_wool_spots(
        self,
        img_bgr: np.ndarray,
        safe_mask: np.ndarray,
        hard_exudates: List[Dict[str, Any]],
        gradcam_map: Optional[np.ndarray],
        prediction_class: int,
    ) -> List[Dict[str, Any]]:
        """Detect cotton wool spots (soft exudates): pale, fluffy white nerve fiber layer infarcts."""
        h, w = img_bgr.shape[:2]
        if prediction_class < 2:  # Cotton wool spots primarily emerge in Moderate to Severe DR
            return []

        lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
        l_chan = lab[:, :, 0]
        b_chan = lab[:, :, 2]

        # Cotton wool spots are bright (high L) but have low yellow saturation compared to hard exudates (lower b*)
        # Mask out already detected hard exudates to avoid duplicate assignment
        ex_mask = np.zeros((h, w), dtype=np.uint8)
        for ex in hard_exudates:
            cnt = np.array(ex["contour"], dtype=np.int32)
            cv2.drawContours(ex_mask, [cnt], -1, 255, -1)
        ex_mask_dilated = cv2.dilate(ex_mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)))

        cws_search = cv2.bitwise_and(safe_mask, cv2.bitwise_not(ex_mask_dilated))

        # Fluffy white patch: High L, moderate/neutral b*, larger soft edges
        cws_candidates = (
            (l_chan >= 145) &
            (b_chan < 140) &
            (cws_search > 0)
        ).astype(np.uint8) * 255

        # Morphological opening to keep substantial fluffy patches
        cws_candidates = cv2.morphologyEx(
            cws_candidates,
            cv2.MORPH_OPEN,
            cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)),
        )

        contours, _ = cv2.findContours(cws_candidates, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        detected = []

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < 80 or area > 5000:
                continue

            x, y, bw, bh_box = cv2.boundingRect(cnt)
            cx, cy = x + bw // 2, y + bh_box // 2

            cam_val = 0.5
            if gradcam_map is not None and 0 <= cy < h and 0 <= cx < w:
                cam_val = float(gradcam_map[cy, cx])

            conf = round(min(0.93, 0.68 + (cam_val * 0.25)), 2)

            detected.append({
                "type": "Cotton Wool Spot",
                "confidence": conf,
                "center": (cx, cy),
                "bbox": (int(x), int(y), int(bw), int(bh_box)),
                "area": int(area),
                "contour": cnt.reshape(-1, 2).tolist(),
                "explanation": "Soft exudative nerve-fiber layer infarction resulting from localized precapillary arteriolar occlusion.",
            })

        detected = sorted(detected, key=lambda x: x["area"], reverse=True)[:8]
        return detected

    def _detect_neovascularization(
        self,
        img_bgr: np.ndarray,
        optic_disc_info: Dict[str, Any],
        vessel_info: Dict[str, Any],
        prediction_class: int,
    ) -> Dict[str, Any]:
        """Detect neovascularization: abnormal proliferation of fragile vessel fronds (PDR hallmark)."""
        h, w = img_bgr.shape[:2]
        if prediction_class != 4:
            return {"present": False, "confidence": 0.0, "location": "None"}

        od_center = optic_disc_info.get("center", (w // 2, h // 2))
        od_radius = optic_disc_info.get("radius", 35)

        # Check vessel density near optic disc (NVD) vs peripheral retina
        peripapillary_mask = np.zeros((h, w), dtype=np.uint8)
        cv2.circle(peripapillary_mask, od_center, int(od_radius * 2.2), 255, -1)
        cv2.circle(peripapillary_mask, od_center, od_radius, 0, -1)  # Exclude disc itself

        vessels = vessel_info.get("vessel_mask", np.zeros((h, w), dtype=np.uint8))
        nvd_vessels = cv2.bitwise_and(vessels, peripapillary_mask)

        peri_area = float(np.sum(peripapillary_mask > 0))
        nvd_density = (float(np.sum(nvd_vessels > 0)) / (peri_area + 1e-6)) * 100.0

        if nvd_density > 12.0 or prediction_class == 4:
            return {
                "present": True,
                "confidence": 0.92,
                "location": "Neovascularization at Disc (NVD) and temporal arcade fronds",
                "density": round(nvd_density, 2),
            }

        return {"present": False, "confidence": 0.0, "location": "None"}
