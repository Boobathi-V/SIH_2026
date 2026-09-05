"""Synthetic Retinal Fundus Dataset Generator for Immediate Verification and Pipeline Testing.

Generates realistic fundus images matching the official APTOS 2019 format:
- Retinal orange-red circular background with dark borders
- Optic disc (pale yellow/orange circular region)
- Retinal vascular arcade (branching vessel tree)
- Class-specific Diabetic Retinopathy lesions:
  - Class 0 (No DR): Healthy fundus
  - Class 1 (Mild DR): Small microaneurysms (tiny red dots)
  - Class 2 (Moderate DR): Multiple microaneurysms + blot hemorrhages + hard exudates (yellow flecks)
  - Class 3 (Severe DR): Extensive retinal hemorrhages, cotton wool spots (soft exudates), venous beading
  - Class 4 (Proliferative DR): Neovascularization (frond-like fine vessel proliferation) and large preretinal hemorrhages
"""

import os
import random
from pathlib import Path
from typing import Tuple
import cv2
import numpy as np
import pandas as pd
from tqdm import tqdm


def draw_synthetic_fundus(severity: int, size: Tuple[int, int] = (600, 600)) -> np.ndarray:
    """Render a single synthetic fundus photograph with severity-specific DR lesions."""
    w, h = size
    # Outer black margin
    img = np.zeros((h, w, 3), dtype=np.uint8)

    # Retinal circle
    center = (w // 2, h // 2)
    radius = int(min(w, h) * 0.44)

    # Base orange-red retinal color gradient
    retina_mask = np.zeros((h, w), dtype=np.uint8)
    cv2.circle(retina_mask, center, radius, 255, -1)

    # Gradient background: center brighter orange-red, perimeter darker
    y, x = np.ogrid[:h, :w]
    dist_from_center = np.sqrt((x - center[0]) ** 2 + (y - center[1]) ** 2)
    norm_dist = np.clip(dist_from_center / radius, 0.0, 1.0)

    # Retinal base colors (RGB)
    r = np.clip(220 - norm_dist * 80, 80, 240).astype(np.uint8)
    g = np.clip(110 - norm_dist * 60, 30, 140).astype(np.uint8)
    b = np.clip(45 - norm_dist * 35, 10, 60).astype(np.uint8)
    base_retina = np.stack([r, g, b], axis=-1)
    img[retina_mask == 255] = base_retina[retina_mask == 255]

    # Optic Disc (pale yellowish circle slightly to the left/nasal side)
    disc_center = (center[0] - int(radius * 0.45), center[1])
    disc_radius = int(radius * 0.16)
    cv2.circle(img, disc_center, disc_radius, (245, 230, 160), -1)
    cv2.circle(img, disc_center, int(disc_radius * 0.6), (255, 245, 190), -1)

    # Retinal Vessels (branching dark red tree radiating from optic disc)
    vessel_color = (130, 20, 10)
    for angle in [-60, -30, -10, 10, 30, 60]:
        rad = np.deg2rad(angle)
        pt1 = disc_center
        # Curved vessel trajectory
        for step in range(1, 5):
            r_step = disc_radius + step * int(radius * 0.18)
            curve = np.sin(step) * 20
            pt2 = (
                int(disc_center[0] + r_step * np.cos(rad)),
                int(disc_center[1] + r_step * np.sin(rad) + curve),
            )
            thickness = max(1, 4 - step)
            cv2.line(img, pt1, pt2, vessel_color, thickness, cv2.LINE_AA)
            # Small branching
            if step >= 2:
                branch_pt = (pt2[0] + random.randint(-15, 15), pt2[1] + random.randint(-20, 20))
                cv2.line(img, pt2, branch_pt, vessel_color, max(1, thickness - 1), cv2.LINE_AA)
            pt1 = pt2

    # Macula / Fovea (slightly darker region temporal to disc)
    macula_center = (center[0] + int(radius * 0.2), center[1])
    macula_radius = int(radius * 0.12)
    cv2.circle(img, macula_center, macula_radius, (150, 40, 15), -1)

    # Class-specific DR lesions:
    # 0 = No DR
    if severity >= 1:
        # Mild DR: Microaneurysms (tiny dark red pinpoints)
        num_ma = random.randint(5, 12) if severity == 1 else random.randint(15, 35)
        for _ in range(num_ma):
            offset_x = random.randint(-int(radius * 0.7), int(radius * 0.7))
            offset_y = random.randint(-int(radius * 0.7), int(radius * 0.7))
            pt = (center[0] + offset_x, center[1] + offset_y)
            if cv2.pointPolygonTest(np.array([[center[0] - radius, center[1]], [center[0], center[1] - radius], [center[0] + radius, center[1]], [center[0], center[1] + radius]]), pt, True) > -radius * 0.2:
                cv2.circle(img, pt, random.randint(1, 3), (120, 10, 5), -1)

    if severity >= 2:
        # Moderate DR: Blot hemorrhages & Hard Exudates (bright yellow lipid deposits)
        num_hem = random.randint(4, 10)
        for _ in range(num_hem):
            pt = (center[0] + random.randint(-int(radius * 0.6), int(radius * 0.6)), center[1] + random.randint(-int(radius * 0.6), int(radius * 0.6)))
            cv2.ellipse(img, pt, (random.randint(4, 9), random.randint(2, 6)), random.randint(0, 180), 0, 360, (110, 8, 5), -1)

        num_exudates = random.randint(5, 14)
        for _ in range(num_exudates):
            pt = (center[0] + random.randint(-int(radius * 0.5), int(radius * 0.5)), center[1] + random.randint(-int(radius * 0.5), int(radius * 0.5)))
            cv2.circle(img, pt, random.randint(2, 5), (250, 245, 140), -1)

    if severity >= 3:
        # Severe DR: Cotton wool spots (soft white fluffy exudates) & Extensive hemorrhages
        num_cws = random.randint(3, 7)
        for _ in range(num_cws):
            pt = (center[0] + random.randint(-int(radius * 0.5), int(radius * 0.5)), center[1] + random.randint(-int(radius * 0.5), int(radius * 0.5)))
            cv2.circle(img, pt, random.randint(6, 14), (235, 235, 230), -1)

        # Venous beading & irregular hemorrhages
        for _ in range(8):
            pt = (center[0] + random.randint(-int(radius * 0.7), int(radius * 0.7)), center[1] + random.randint(-int(radius * 0.7), int(radius * 0.7)))
            cv2.ellipse(img, pt, (random.randint(8, 16), random.randint(5, 10)), random.randint(0, 180), 0, 360, (90, 5, 5), -1)

    if severity == 4:
        # Proliferative DR: Neovascularization (fine tangled vessels) + large vitreous hemorrhage
        nv_center = (disc_center[0] + random.randint(-20, 40), disc_center[1] + random.randint(-30, 30))
        for _ in range(12):
            end_pt = (nv_center[0] + random.randint(-40, 40), nv_center[1] + random.randint(-40, 40))
            cv2.line(img, nv_center, end_pt, (160, 15, 15), 1, cv2.LINE_AA)

        # Vitreous hemorrhage (large dark irregular pool)
        vh_pt = (center[0] + random.randint(-50, 80), center[1] + random.randint(-60, 60))
        cv2.ellipse(img, vh_pt, (random.randint(25, 45), random.randint(18, 30)), random.randint(0, 180), 0, 360, (70, 5, 5), -1)

    # Apply slight natural blurring and sensor noise
    img = cv2.GaussianBlur(img, (3, 3), 0.5)
    noise = np.random.normal(0, 3, img.shape).astype(np.int16)
    img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    # Re-apply circular retina mask to keep borders pure black
    img[retina_mask == 0] = 0

    return img


def generate_dataset(
    output_dir: str = "datasets/aptos",
    samples_per_class: int = 20,
    seed: int = 42,
) -> pd.DataFrame:
    """Generate mock APTOS 2019 dataset structure with images and train.csv."""
    random.seed(seed)
    np.random.seed(seed)

    base_path = Path(output_dir)
    images_dir = base_path / "train_images"
    images_dir.mkdir(parents=True, exist_ok=True)

    records = []
    print(f"Generating synthetic fundus dataset in {output_dir} ({samples_per_class} per class)...")

    for severity in range(5):
        for i in range(samples_per_class):
            id_code = f"syn_dr_{severity}_{i:03d}"
            file_name = f"{id_code}.png"
            file_path = images_dir / file_name

            # Generate fundus
            img = draw_synthetic_fundus(severity=severity, size=(512, 512))
            # Save as BGR for OpenCV
            cv2.imwrite(str(file_path), cv2.cvtColor(img, cv2.COLOR_RGB2BGR))

            records.append({
                "id_code": id_code,
                "diagnosis": severity,
                "file_path": str(file_path),
            })

    df = pd.DataFrame(records)
    csv_path = base_path / "train.csv"
    df.to_csv(csv_path, index=False)
    print(f"Saved {len(df)} samples to {csv_path}")
    return df


if __name__ == "__main__":
    generate_dataset(samples_per_class=20)
