"""Clinical Ophthalmology Retinal Annotation Renderer.

Renders high-resolution, publication-quality annotated fundus images
with leader lines, boundary contours, and collision-free typography matching
clinical ophthalmology diagnostic standards.
"""

from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
import os
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


class RetinalAnnotationRenderer:
    """Renders professional clinical lesion annotations with leader lines and labels."""

    def __init__(self, font_size: int = 20):
        self.font_size = font_size
        self.font = self._load_font(font_size)
        self.font_small = self._load_font(max(12, int(font_size * 0.75)))

    def _load_font(self, size: int) -> ImageFont.ImageFont:
        """Attempt to load Arial or fallback to default PIL font."""
        candidates = [
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/calibrib.ttf",
            "C:/Windows/Fonts/calibri.ttf",
            "C:/Windows/Fonts/seguiemj.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ]
        for c in candidates:
            if os.path.exists(c):
                try:
                    return ImageFont.truetype(c, size)
                except Exception:
                    continue
        return ImageFont.load_default()

    def render(
        self,
        img_bgr: np.ndarray,
        optic_disc_info: Dict[str, Any],
        vessel_info: Dict[str, Any],
        lesion_info: Dict[str, Any],
        save_path: Optional[str] = "outputs/annotated_retina.png",
    ) -> Tuple[np.ndarray, str]:
        """Render complete annotated fundus image.

        Args:
            img_bgr: Base fundus photograph as uint8 BGR.
            optic_disc_info: Output from OpticDiscDetector.
            vessel_info: Output from RetinalVesselSegmenter.
            lesion_info: Output from RetinalLesionDetector.
            save_path: Optional file path to save the generated PNG.

        Returns:
            Tuple of (annotated_bgr_image, saved_filepath).
        """
        # Work in RGB for PIL drawing
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        h, w = img_rgb.shape[:2]

        # Convert to PIL Image for crisp typography and anti-aliased geometry
        pil_img = Image.fromarray(img_rgb)
        draw = ImageDraw.Draw(pil_img)

        # Scale line thickness and font according to image size
        scale_factor = max(1.0, min(h, w) / 512.0)
        line_thick = max(2, int(2 * scale_factor))
        circle_thick = max(2, int(2 * scale_factor))
        current_font = self._load_font(int(self.font_size * scale_factor))

        white_color = (255, 255, 255)
        shadow_color = (15, 23, 42)

        # 1. Annotate Optic Disc (Prominent white circle + leader line)
        # 1. Annotate Optic Disc (Prominent white/cyan circle + leader line)
        if optic_disc_info.get("detected"):
            cx, cy = optic_disc_info["center"]
            rad = optic_disc_info["radius"]

            # Draw clean circle around optic disc
            bbox = [cx - rad, cy - rad, cx + rad, cy + rad]
            draw.ellipse(bbox, outline=(56, 189, 248), width=circle_thick)

            # Place Optic Disc label on the side away from center
            dx = -1 if cx < w // 2 else 1
            dy = 1 if cy > h // 2 else -1

            start_pt = (cx + int(dx * rad * 0.7), cy + int(dy * rad * 0.7))
            label_x = max(20, min(w - 220, cx + int(dx * rad * 2.2)))
            label_y = max(20, min(h - 40, cy + int(dy * rad * 2.5)))

            self._draw_leader_line_with_label(
                draw=draw,
                start_pt=start_pt,
                label_pt=(label_x, label_y),
                text="Eye Nerve Head (Optic Disc)",
                font=current_font,
                line_width=line_thick,
            )

        # 2. Annotate Confirmed Microaneurysms
        mas = [l for l in lesion_info.get("lesions", []) if l["type"] == "Microaneurysm"]
        if mas:
            # Draw distinct red/white circles around top microaneurysms
            for ma in mas[:4]:
                mx, my = ma["center"]
                m_rad = max(5, int(ma.get("radius", 4) * scale_factor * 1.5))
                draw.ellipse([mx - m_rad, my - m_rad, mx + m_rad, my + m_rad], outline=(239, 68, 68), width=line_thick)

            # Point to the most prominent microaneurysm
            target_ma = mas[0]
            tx, ty = target_ma["center"]
            lbl_x = max(20, min(w - 240, tx - int(60 * scale_factor)))
            lbl_y = max(20, min(h - 40, ty - int(70 * scale_factor)))
            self._draw_leader_line_with_label(
                draw=draw,
                start_pt=(tx, ty),
                label_pt=(lbl_x, lbl_y),
                text="Red Dot (Microaneurysm)",
                font=current_font,
                line_width=line_thick,
            )

        # 3. Annotate Confirmed Hard Exudates
        exs = [l for l in lesion_info.get("lesions", []) if l["type"] == "Hard Exudate"]
        if exs:
            for ex in exs[:3]:
                bx, by, bw, bh_box = ex.get("bbox", (ex["center"][0] - 8, ex["center"][1] - 8, 16, 16))
                pad = max(2, int(4 * scale_factor))
                draw.ellipse([bx - pad, by - pad, bx + bw + pad, by + bh_box + pad], outline=(245, 158, 11), width=line_thick)

            target_ex = exs[0]
            tx, ty = target_ex["center"]
            lbl_x = max(20, min(w - 220, tx + int(40 * scale_factor)))
            lbl_y = max(20, min(h - 40, ty - int(80 * scale_factor)))
            self._draw_leader_line_with_label(
                draw=draw,
                start_pt=(tx, ty),
                label_pt=(lbl_x, lbl_y),
                text="Yellow Spot (Hard Exudate)",
                font=current_font,
                line_width=line_thick,
            )

        # 4. Annotate Confirmed Hemorrhages
        hms = [l for l in lesion_info.get("lesions", []) if l["type"] == "Hemorrhage"]
        if hms:
            for hm in hms[:2]:
                bx, by, bw, bh_box = hm.get("bbox", (hm["center"][0] - 10, hm["center"][1] - 10, 20, 20))
                pad = max(2, int(4 * scale_factor))
                draw.rectangle([bx - pad, by - pad, bx + bw + pad, by + bh_box + pad], outline=(220, 38, 38), width=line_thick)

            target_hm = hms[0]
            tx, ty = target_hm["center"]
            lbl_x = max(20, min(w - 240, tx + int(60 * scale_factor)))
            lbl_y = max(20, min(h - 40, ty - int(50 * scale_factor)))
            self._draw_leader_line_with_label(
                draw=draw,
                start_pt=(tx, ty),
                label_pt=(lbl_x, lbl_y),
                text="Bleeding Spot (Hemorrhage)",
                font=current_font,
                line_width=line_thick,
            )

        # 5. Annotate Cotton-Wool Spots
        cwss = [l for l in lesion_info.get("lesions", []) if l["type"] == "Cotton Wool Spot"]
        if cwss:
            for cws in cwss[:2]:
                bx, by, bw, bh_box = cws.get("bbox", (cws["center"][0] - 15, cws["center"][1] - 15, 30, 30))
                pad = max(4, int(6 * scale_factor))
                draw.ellipse([bx - pad, by - pad, bx + bw + pad, by + bh_box + pad], outline=(203, 213, 225), width=line_thick)

            target_cws = cwss[0]
            tx, ty = target_cws["center"]
            lbl_x = max(20, min(w - 240, tx - int(100 * scale_factor)))
            lbl_y = max(20, min(h - 40, ty + int(10 * scale_factor)))
            self._draw_leader_line_with_label(
                draw=draw,
                start_pt=(tx, ty),
                label_pt=(lbl_x, lbl_y),
                text="Pale Patch (Cotton Wool Spot)",
                font=current_font,
                line_width=line_thick,
            )

        # 7. Annotate Neovascularization if present
        if lesion_info.get("has_neovascularization"):
            od_c = optic_disc_info.get("center", (w // 2, h // 2))
            lbl_x = max(20, min(w - 220, od_c[0] + int(80 * scale_factor)))
            lbl_y = max(20, min(h - 40, od_c[1] + int(40 * scale_factor)))
            self._draw_leader_line_with_label(
                draw=draw,
                start_pt=od_c,
                label_pt=(lbl_x, lbl_y),
                text="Neovascularization (NVD)",
                font=current_font,
                line_width=line_thick,
            )

        # Save to file if path specified
        annotated_bgr = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

        if save_path:
            out_file = Path(save_path)
            out_file.parent.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(out_file), annotated_bgr)

        return annotated_bgr, str(save_path) if save_path else ""

    def _draw_leader_line_with_label(
        self,
        draw: ImageDraw.ImageDraw,
        start_pt: Tuple[int, int],
        label_pt: Tuple[int, int],
        text: str,
        font: ImageFont.ImageFont,
        line_width: int = 2,
    ) -> None:
        """Draw a clean leader line connecting a retinal lesion to an anti-aliased label."""
        sx, sy = start_pt
        lx, ly = label_pt

        # Calculate bounding box of text
        bbox = font.getbbox(text)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

        # Draw a tiny anchor point at the lesion
        anchor_rad = max(2, line_width + 1)
        draw.ellipse([sx - anchor_rad, sy - anchor_rad, sx + anchor_rad, sy + anchor_rad], fill=(255, 255, 255))

        # Leader line from lesion anchor to text edge
        target_x = lx + text_w // 2 if abs(lx + text_w // 2 - sx) < abs(lx - sx) else (lx if lx > sx else lx + text_w)
        target_y = ly + text_h // 2
        draw.line([(sx, sy), (target_x, target_y)], fill=(255, 255, 255), width=line_width)

        # Render clean text with high contrast shadow
        for off_x, off_y in [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, 1), (-1, 1), (1, -1)]:
            draw.text((lx + off_x, ly + off_y), text, font=font, fill=(0, 0, 0))

        draw.text((lx, ly), text, font=font, fill=(255, 255, 255))
