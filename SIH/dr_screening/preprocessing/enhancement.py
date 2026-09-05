"""Retinal image enhancement: CLAHE, Gamma Correction, Ben Graham subtraction, and Normalization."""

from typing import Tuple
import cv2
import numpy as np


def apply_clahe(
    image: np.ndarray,
    clip_limit: float = 2.0,
    tile_grid_size: Tuple[int, int] = (8, 8),
) -> np.ndarray:
    """Apply Contrast Limited Adaptive Histogram Equalization (CLAHE).

    Operates in LAB color space on the Luminance (L) channel to enhance
    retinal microvasculature, exudates, and hemorrhages without color distortion.

    Args:
        image: RGB image (H, W, 3) with uint8 values in [0, 255].
        clip_limit: Threshold for contrast limiting.
        tile_grid_size: Size of grid for histogram equalization.

    Returns:
        Enhanced RGB numpy array with shape (H, W, 3).
    """
    lab = cv2.cvtColor(image, cv2.COLOR_RGB2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)

    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
    cl = clahe.apply(l_channel)

    merged = cv2.merge((cl, a_channel, b_channel))
    enhanced_rgb = cv2.cvtColor(merged, cv2.COLOR_LAB2RGB)
    return enhanced_rgb


def apply_gamma_correction(image: np.ndarray, gamma: float = 1.15) -> np.ndarray:
    """Apply non-linear gamma luminance correction to normalize retinal exposure.

    Args:
        image: RGB image (H, W, 3) in [0, 255].
        gamma: Gamma correction exponent (>1 brightens mid-tones, <1 darkens).

    Returns:
        Gamma-corrected RGB numpy array.
    """
    if gamma <= 0:
        raise ValueError(f"Gamma value must be positive, got {gamma}")

    inv_gamma = 1.0 / gamma
    table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in range(256)]).astype(np.uint8)
    return cv2.LUT(image, table)


def apply_ben_graham(
    image: np.ndarray,
    sigma_x: int = 10,
    alpha: float = 4.0,
    beta: float = -4.0,
    gamma_offset: int = 128,
) -> np.ndarray:
    """Apply Ben Graham's weighted local contrast normalization for fundus images.

    Enhances microaneurysms and neovascularization by subtracting a blurred version of the image.
    Formula: output = alpha * image + beta * GaussianBlur(image, sigma) + gamma_offset

    Args:
        image: RGB image (H, W, 3) in [0, 255].
        sigma_x: Standard deviation for Gaussian blur kernel.
        alpha: Multiplier for original image.
        beta: Multiplier for blurred image.
        gamma_offset: Additive constant to center contrast.

    Returns:
        Contrast-normalized RGB numpy array.
    """
    blurred = cv2.GaussianBlur(image, (0, 0), sigmaX=sigma_x)
    enhanced = cv2.addWeighted(image, alpha, blurred, beta, gamma_offset)
    return enhanced


def resize_image(image: np.ndarray, target_size: Tuple[int, int] = (384, 384)) -> np.ndarray:
    """Resize image using anti-aliased interpolation."""
    return cv2.resize(image, target_size, interpolation=cv2.INTER_AREA)


def normalize_rgb(image: np.ndarray) -> np.ndarray:
    """Normalize pixel intensities to float range [0.0, 1.0]."""
    return image.astype(np.float32) / 255.0


def normalize_imagenet(
    image: np.ndarray,
    mean: Tuple[float, float, float] = (0.485, 0.456, 0.406),
    std: Tuple[float, float, float] = (0.229, 0.224, 0.225),
) -> np.ndarray:
    """Standardize normalized RGB image with ImageNet mean and std."""
    mean_arr = np.array(mean, dtype=np.float32)
    std_arr = np.array(std, dtype=np.float32)
    return (image - mean_arr) / std_arr
