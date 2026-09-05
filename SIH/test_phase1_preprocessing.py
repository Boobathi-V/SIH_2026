"""Phase 1 Verification: Test each preprocessing component and save visual inspection comparison."""

import os
from pathlib import Path
import cv2
import matplotlib.pyplot as plt
import numpy as np
import torch

from dr_screening.datasets.generate_sample_data import generate_dataset
from dr_screening.preprocessing.crop import remove_black_borders, circular_crop_retina
from dr_screening.preprocessing.enhancement import (
    apply_clahe,
    apply_gamma_correction,
    resize_image,
    normalize_rgb,
    normalize_imagenet,
)
from dr_screening.preprocessing.pipeline import FundusPreprocessor, preprocess_fundus_image


def test_preprocessing_pipeline():
    print("=== Phase 1: Preprocessing Pipeline Test ===")

    # Step 1: Ensure dataset directory and samples exist
    data_dir = Path("datasets/aptos")
    csv_file = data_dir / "train.csv"
    if not csv_file.exists():
        print("Generating initial sample fundus dataset...")
        generate_dataset(output_dir=str(data_dir), samples_per_class=10)

    # Pick a sample image (e.g., class 2 moderate DR)
    sample_path = data_dir / "train_images" / "syn_dr_2_000.png"
    assert sample_path.exists(), f"Sample image {sample_path} not found."

    raw_bgr = cv2.imread(str(sample_path))
    raw_rgb = cv2.cvtColor(raw_bgr, cv2.COLOR_BGR2RGB)
    print(f"[OK] Raw image loaded: shape={raw_rgb.shape}, dtype={raw_rgb.dtype}")

    # Step 2: Individual step tests
    # 2.1 Remove black borders
    cropped_border = remove_black_borders(raw_rgb, tol=7)
    assert cropped_border.shape[0] <= raw_rgb.shape[0] and cropped_border.shape[1] <= raw_rgb.shape[1]
    print(f"[OK] remove_black_borders output shape: {cropped_border.shape}")

    # 2.2 Circular crop retina
    circ_cropped = circular_crop_retina(raw_rgb, tol=7)
    assert circ_cropped.shape[0] > 0 and circ_cropped.shape[1] > 0
    print(f"[OK] circular_crop_retina output shape: {circ_cropped.shape}")

    # 2.3 CLAHE enhancement
    clahe_img = apply_clahe(circ_cropped, clip_limit=2.0)
    assert clahe_img.shape == circ_cropped.shape
    print(f"[OK] apply_clahe output shape: {clahe_img.shape}, dtype={clahe_img.dtype}")

    # 2.4 Gamma correction
    gamma_img = apply_gamma_correction(clahe_img, gamma=1.15)
    assert gamma_img.shape == clahe_img.shape
    print(f"[OK] apply_gamma_correction output shape: {gamma_img.shape}")

    # 2.5 Resize
    resized_img = resize_image(gamma_img, target_size=(384, 384))
    assert resized_img.shape == (384, 384, 3), f"Expected (384, 384, 3), got {resized_img.shape}"
    print(f"[OK] resize_image output shape: {resized_img.shape}")

    # 2.6 RGB Normalization
    norm_img = normalize_rgb(resized_img)
    assert 0.0 <= norm_img.min() and norm_img.max() <= 1.0
    print(f"[OK] normalize_rgb range: [{norm_img.min():.3f}, {norm_img.max():.3f}]")

    # 2.7 ImageNet Normalization
    std_img = normalize_imagenet(norm_img)
    print(f"[OK] normalize_imagenet mean={std_img.mean():.3f}, std={std_img.std():.3f}")

    # Step 3: End-to-end Preprocessor verification
    preprocessor = FundusPreprocessor(target_size=(384, 384))
    processed_uint8 = preprocessor.preprocess(sample_path, return_tensor=False)
    processed_tensor = preprocessor.preprocess(sample_path, return_tensor=True)

    assert isinstance(processed_uint8, np.ndarray)
    assert processed_uint8.shape == (384, 384, 3)
    assert processed_uint8.dtype == np.uint8

    assert isinstance(processed_tensor, torch.Tensor)
    assert processed_tensor.shape == (3, 384, 384), f"Expected torch.Size([3, 384, 384]), got {processed_tensor.shape}"
    assert processed_tensor.dtype == torch.float32

    print(f"[OK] End-to-end Preprocessor: uint8={processed_uint8.shape}, Tensor={processed_tensor.shape}")

    # Step 4: Save visual comparison grid
    out_dir = Path("outputs/preprocessing")
    out_dir.mkdir(parents=True, exist_ok=True)
    comparison_file = out_dir / "preprocessing_stages_comparison.png"

    fig, axes = plt.subplots(1, 5, figsize=(20, 4))
    axes[0].imshow(raw_rgb)
    axes[0].set_title("1. Raw Fundus (with border)", fontsize=11)
    axes[0].axis("off")

    axes[1].imshow(circ_cropped)
    axes[1].set_title("2. Circular Retina Crop", fontsize=11)
    axes[1].axis("off")

    axes[2].imshow(clahe_img)
    axes[2].set_title("3. CLAHE Enhanced (LAB)", fontsize=11)
    axes[2].axis("off")

    axes[3].imshow(gamma_img)
    axes[3].set_title("4. Gamma Corrected", fontsize=11)
    axes[3].axis("off")

    axes[4].imshow(processed_uint8)
    axes[4].set_title("5. Final Preprocessed (384x384)", fontsize=11)
    axes[4].axis("off")

    plt.tight_layout()
    plt.savefig(comparison_file, dpi=200, bbox_inches="tight")
    plt.close()
    print(f"[SUCCESS] Visual comparison saved to: {comparison_file}")
    print("=== Phase 1 Preprocessing Complete & Verified! ===")


if __name__ == "__main__":
    test_preprocessing_pipeline()
