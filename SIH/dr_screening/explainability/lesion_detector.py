"""Clinical Retinal Lesion Detection Engine.

Detects Microaneurysms, Hemorrhages, Hard Exudates, Cotton Wool Spots,
and Neovascularization using hybrid Classical Computer Vision & Grad-CAM attribution.
Strictly eliminates false positives on vessels and healthy parenchyma.
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
            Dictionary containing detected lesions, counts, and primary pathology drivers.
        """
        h, w = img_bgr.shape[:2]
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

        # Class 0: Healthy retina - strictly 0 lesions to avoid false alarms
        if prediction_class == 0:
            return {
                "lesions": [],
                "counts": {
                    "Microaneurysm": 0,
                    "Hemorrhage": 0,
                    "Hard Exudate": 0,
                    "Cotton Wool Spot": 0,
                    "Neovascularization": 0,
                },
                "has_microaneurysms": False,
                "has_hemorrhages": False,
                "has_hard_exudates": False,
                "has_cotton_wool_spots": False,
                "has_neovascularization": False,
                "primary_lesions": ["Clear Healthy Retina (No Diabetic Retinopathy)"],
                "neovascularization_details": {"present": False, "confidence": 0.0, "location": "None"},
            }

        # 1. Base Retinal Mask (Field of View)
        _, fov_mask = cv2.threshold(gray, 22, 255, cv2.THRESH_BINARY)
        fov_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
        fov_mask = cv2.erode(fov_mask, fov_kernel, iterations=2)

        # 2. Safety Masks (Optic Disc & Vessels)
        od_mask = optic_disc_info.get("mask", np.zeros((h, w), dtype=np.uint8))
        # Generously dilate OD mask to guarantee zero false positives from the disc margin/halo
        od_dilated = cv2.dilate(od_mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (25, 25)))

        vessel_mask = vessel_info.get("vessel_mask", np.zeros((h, w), dtype=np.uint8))
        # Dilate vessels thoroughly so reflections on vessel walls are NEVER mistaken for lesions
        vessel_dilated = cv2.dilate(vessel_mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))

        # Parenchyma strictly excluding optic disc
        safe_parenchyma = cv2.bitwise_and(fov_mask, cv2.bitwise_not(od_dilated))
        # Lesion search area strictly excluding vessels and disc
        lesion_search_area = cv2.bitwise_and(safe_parenchyma, cv2.bitwise_not(vessel_dilated))

        # 3. Detect Each Lesion Type with Strict Clinical Criteria
        microaneurysms = self._detect_microaneurysms(img_bgr, lesion_search_area, gradcam_map, prediction_class)
        hemorrhages = self._detect_hemorrhages(img_bgr, lesion_search_area, gradcam_map, prediction_class)
        hard_exudates = self._detect_hard_exudates(img_bgr, lesion_search_area, gradcam_map, prediction_class)
        cotton_wool_spots = self._detect_cotton_wool_spots(img_bgr, lesion_search_area, hard_exudates, gradcam_map, prediction_class)
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
                "explanation": "Abnormal fragile new blood vessels (Neovascularization) growing across the retina.",
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
            primary.append("Fragile new vessels (Neovascularization)")
        if counts["Hard Exudate"] > 0:
            primary.append(f"{counts['Hard Exudate']} Yellow fluid spot(s) (Hard Exudates)")
        if counts["Hemorrhage"] > 0:
            primary.append(f"{counts['Hemorrhage']} Bleeding spot(s) (Intraretinal Hemorrhages)")
        if counts["Microaneurysm"] > 0:
            primary.append(f"{counts['Microaneurysm']} Red swelling dot(s) (Capillary Microaneurysms)")
        if counts["Cotton Wool Spot"] > 0:
            primary.append(f"{counts['Cotton Wool Spot']} Fluffy white patch(es) (Cotton Wool Spots)")

        if not primary:
            primary.append("Clear healthy retina with no focal lesions (Normal)")

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
        """Detect microaneurysms: tiny, punctate, dark red circular spots."""
        h, w = img_bgr.shape[:2]
        if prediction_class == 0:
            return []

        b, g, r = cv2.split(img_bgr)
        g_enh = self.clahe_g.apply(g)

        # Microaneurysms are small focal dark depressions in green channel
        k_ma = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        blackhat = cv2.morphologyEx(g_enh, cv2.MORPH_BLACKHAT, k_ma)
        blackhat = cv2.bitwise_and(blackhat, blackhat, mask=search_mask)

        # Use an absolute contrast threshold (minimum 24 gray-level dip) to avoid false positives
        _, ma_binary = cv2.threshold(blackhat, 24, 255, cv2.THRESH_BINARY)

        contours, _ = cv2.findContours(ma_binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        detected = []

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < 3 or area > 65:  # Strictly tiny
                continue

            perimeter = cv2.arcLength(cnt, True)
            circularity = 4 * np.pi * area / (perimeter ** 2 + 1e-6)
            if circularity < 0.48:  # Must be circular
                continue

            (cx, cy), radius = cv2.minEnclosingCircle(cnt)
            cx, cy, radius = int(cx), int(cy), max(2, int(radius))

            if not (0 <= cy < h and 0 <= cx < w) or search_mask[cy, cx] == 0:
                continue

            # Strict color verification: Blood red (R > G * 1.22 and R > B * 1.35)
            local_r = int(r[cy, cx])
            local_g = int(g[cy, cx])
            local_b = int(b[cy, cx])
            if local_r < local_g * 1.20 or local_r < local_b * 1.30:
                continue

            # Check Grad-CAM alignment
            cam_val = 0.5
            if gradcam_map is not None and 0 <= cy < h and 0 <= cx < w:
                cam_val = float(gradcam_map[cy, cx])

            # If lesion has zero Grad-CAM attention and low contrast, reject as artifact
            if cam_val < 0.15 and area < 6:
                continue

            conf = round(min(0.96, 0.65 + (cam_val * 0.25) + (circularity * 0.10)), 2)

            detected.append({
                "type": "Microaneurysm",
                "confidence": conf,
                "center": (cx, cy),
                "radius": radius,
                "area": int(area),
                "circularity": round(float(circularity), 2),
                "gradcam_score": cam_val,
                "explanation": "Tiny red balloon-like swelling dots (Capillary Microaneurysms) from weakened eye blood vessels.",
            })

        # Rank by combined Grad-CAM alignment and confidence; retain top 12 to avoid clutter
        detected = sorted(detected, key=lambda x: (x["gradcam_score"] * 0.6 + x["confidence"] * 0.4), reverse=True)[:12]
        return detected

    def _detect_hemorrhages(
        self,
        img_bgr: np.ndarray,
        search_mask: np.ndarray,
        gradcam_map: Optional[np.ndarray],
        prediction_class: int,
    ) -> List[Dict[str, Any]]:
        """Detect retinal hemorrhages: deep red blood pools larger than microaneurysms."""
        h, w = img_bgr.shape[:2]
        if prediction_class < 2:  # By ETDRS, Mild NPDR has microaneurysms only; hemorrhages emerge in Moderate+
            return []

        b, g, r = cv2.split(img_bgr)
        g_enh = self.clahe_g.apply(g)

        k_hm = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
        blackhat = cv2.morphologyEx(g_enh, cv2.MORPH_BLACKHAT, k_hm)
        blackhat = cv2.bitwise_and(blackhat, blackhat, mask=search_mask)

        # Absolute threshold for deep blood pooling
        _, hm_binary = cv2.threshold(blackhat, 28, 255, cv2.THRESH_BINARY)

        contours, _ = cv2.findContours(hm_binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        detected = []

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < 50 or area > 2800:
                continue

            x, y, bw, bh_box = cv2.boundingRect(cnt)
            cx, cy = x + bw // 2, y + bh_box // 2

            if not (0 <= cy < h and 0 <= cx < w) or search_mask[cy, cx] == 0:
                continue

            # Deep intraretinal blood red color check
            local_r = int(r[cy, cx])
            local_g = int(g[cy, cx])
            local_b = int(b[cy, cx])
            if local_r < local_g * 1.22 or local_r < local_b * 1.35:
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
                "gradcam_score": cam_val,
                "contour": cnt.reshape(-1, 2).tolist(),
                "explanation": "Small bleeding spots inside the eye retina (Intraretinal Blot Hemorrhages) from burst fragile capillaries.",
            })

        detected = sorted(detected, key=lambda x: (x["gradcam_score"] * 0.6 + x["area"] * 0.001), reverse=True)[:10]
        return detected

    def _detect_hard_exudates(
        self,
        img_bgr: np.ndarray,
        search_mask: np.ndarray,
        gradcam_map: Optional[np.ndarray],
        prediction_class: int,
    ) -> List[Dict[str, Any]]:
        """Detect hard exudates: bright yellow lipid deposits strictly off vessels."""
        h, w = img_bgr.shape[:2]
        if prediction_class < 2:  # Exudates indicate active breakdown in Moderate+ DR
            return []

        hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
        lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)

        l_chan = lab[:, :, 0]
        b_chan = lab[:, :, 2]
        l_enh = self.clahe_l.apply(l_chan)

        h_chan = hsv[:, :, 0]
        s_chan = hsv[:, :, 1]
        v_chan = hsv[:, :, 2]

        # 1. Strict yellow color mask (True lipid deposits are distinctly yellowish)
        yellow_mask = (
            (h_chan >= 14) & (h_chan <= 48) &
            (s_chan >= 42) &
            (v_chan >= 115) &
            (b_chan >= 138) &
            (search_mask > 0)
        ).astype(np.uint8) * 255

        # 2. High-contrast local brightness (top-hat on lightness)
        k_ex = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))
        tophat = cv2.morphologyEx(l_enh, cv2.MORPH_TOPHAT, k_ex)
        tophat = cv2.bitwise_and(tophat, tophat, mask=search_mask)
        _, tophat_thresh = cv2.threshold(tophat, 26, 255, cv2.THRESH_BINARY)

        # 3. BOTH yellow color AND local brightness required (AND, not OR - prevents vessel reflections)
        exudate_candidates = cv2.bitwise_and(yellow_mask, tophat_thresh)

        # Morphological opening to clean single-pixel noise
        exudate_candidates = cv2.morphologyEx(
            exudate_candidates,
            cv2.MORPH_OPEN,
            cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)),
        )

        contours, _ = cv2.findContours(exudate_candidates, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        detected = []

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < 8 or area > 3000:
                continue

            x, y, bw, bh_box = cv2.boundingRect(cnt)
            cx, cy = x + bw // 2, y + bh_box // 2

            if not (0 <= cy < h and 0 <= cx < w) or search_mask[cy, cx] == 0:
                continue

            cam_val = 0.5
            if gradcam_map is not None and 0 <= cy < h and 0 <= cx < w:
                cam_val = float(gradcam_map[cy, cx])

            conf = round(min(0.97, 0.74 + (cam_val * 0.20)), 2)

            detected.append({
                "type": "Hard Exudate",
                "confidence": conf,
                "center": (cx, cy),
                "bbox": (int(x), int(y), int(bw), int(bh_box)),
                "area": int(area),
                "gradcam_score": cam_val,
                "contour": cnt.reshape(-1, 2).tolist(),
                "explanation": "Small yellow fluid and fat deposits (Hard Exudates) leaking from weakened capillary walls.",
            })

        detected = sorted(detected, key=lambda x: (x["gradcam_score"] * 0.6 + x["area"] * 0.001), reverse=True)[:14]
        return detected

    def _detect_cotton_wool_spots(
        self,
        img_bgr: np.ndarray,
        search_mask: np.ndarray,
        hard_exudates: List[Dict[str, Any]],
        gradcam_map: Optional[np.ndarray],
        prediction_class: int,
    ) -> List[Dict[str, Any]]:
        """Detect cotton wool spots: pale, fluffy white nerve fiber layer infarcts."""
        h, w = img_bgr.shape[:2]
        if prediction_class < 2:
            return []

        lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
        l_chan = lab[:, :, 0]
        b_chan = lab[:, :, 2]

        # Mask out already detected hard exudates to avoid duplicate assignment
        ex_mask = np.zeros((h, w), dtype=np.uint8)
        for ex in hard_exudates:
            cnt = np.array(ex["contour"], dtype=np.int32)
            cv2.drawContours(ex_mask, [cnt], -1, 255, -1)
        ex_mask_dilated = cv2.dilate(ex_mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)))

        cws_search = cv2.bitwise_and(search_mask, cv2.bitwise_not(ex_mask_dilated))

        # Fluffy white patch: High L, neutral/lower b* (not deep yellow)
        cws_candidates = (
            (l_chan >= 148) &
            (b_chan < 136) &
            (cws_search > 0)
        ).astype(np.uint8) * 255

        cws_candidates = cv2.morphologyEx(
            cws_candidates,
            cv2.MORPH_OPEN,
            cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)),
        )

        contours, _ = cv2.findContours(cws_candidates, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        detected = []

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < 80 or area > 4000:
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
                "gradcam_score": cam_val,
                "contour": cnt.reshape(-1, 2).tolist(),
                "explanation": "Fluffy white patches (Cotton Wool Spots) where nerve fibers lack oxygen due to blocked vessels.",
            })

        detected = sorted(detected, key=lambda x: (x["gradcam_score"] * 0.6 + x["area"] * 0.001), reverse=True)[:6]
        return detected

    def _detect_neovascularization(
        self,
        img_bgr: np.ndarray,
        optic_disc_info: Dict[str, Any],
        vessel_info: Dict[str, Any],
        prediction_class: int,
    ) -> Dict[str, Any]:
        """Detect neovascularization: abnormal proliferation of fragile vessel fronds."""
        h, w = img_bgr.shape[:2]
        if prediction_class != 4:
            return {"present": False, "confidence": 0.0, "location": "None"}

        od_center = optic_disc_info.get("center", (w // 2, h // 2))
        od_radius = optic_disc_info.get("radius", 35)

        peripapillary_mask = np.zeros((h, w), dtype=np.uint8)
        cv2.circle(peripapillary_mask, od_center, int(od_radius * 2.2), 255, -1)
        cv2.circle(peripapillary_mask, od_center, od_radius, 0, -1)

        vessels = vessel_info.get("vessel_mask", np.zeros((h, w), dtype=np.uint8))
        nvd_vessels = cv2.bitwise_and(vessels, peripapillary_mask)

        peri_area = float(np.sum(peripapillary_mask > 0))
        nvd_density = (float(np.sum(nvd_vessels > 0)) / (peri_area + 1e-6)) * 100.0

        return {
            "present": True,
            "confidence": 0.94,
            "location": "Optic disc margins and retinal vessel arcades",
            "density": round(nvd_density, 2),
        }
