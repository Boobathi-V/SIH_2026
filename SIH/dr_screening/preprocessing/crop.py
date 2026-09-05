"""Retinal boundary detection, border removal, and circular cropping functions."""

from typing import Tuple
import cv2
import numpy as np


def remove_black_borders(image: np.ndarray, tol: int = 7) -> np.ndarray:
    """Crop uninformative black outer borders from fundus photograph.

    Args:
        image: RGB image as a numpy array with shape (H, W, 3).
        tol: Grayscale intensity threshold below which a pixel is considered black.

    Returns:
        Cropped RGB numpy array.
    """
    if image is None or image.size == 0:
        raise ValueError("Invalid or empty image provided to remove_black_borders.")

    if image.ndim == 2:
        mask = image > tol
        return image[np.ix_(mask.any(1), mask.any(0))]

    if image.ndim == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        mask = gray > tol

        # Check if the mask contains non-black pixels
        if not mask.any():
            return image

        check_shape = image[:, :, 0][np.ix_(mask.any(1), mask.any(0))].shape[0]
        if check_shape == 0:
            return image

        img1 = image[:, :, 0][np.ix_(mask.any(1), mask.any(0))]
        img2 = image[:, :, 1][np.ix_(mask.any(1), mask.any(0))]
        img3 = image[:, :, 2][np.ix_(mask.any(1), mask.any(0))]
        cropped = np.stack([img1, img2, img3], axis=-1)
        return cropped

    return image


def circular_crop_retina(image: np.ndarray, tol: int = 7) -> np.ndarray:
    """Detect circular retinal boundary, mask out periphery, and center the fundus.

    Args:
        image: RGB image as a numpy array (H, W, 3).
        tol: Grayscale intensity threshold for contour detection.

    Returns:
        Circularly cropped and masked RGB numpy array.
    """
    # First remove any loose rectangular black borders
    image = remove_black_borders(image, tol=tol)
    h, w = image.shape[:2]

    # Convert to grayscale for circular boundary detection
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    _, binary = cv2.threshold(gray, tol, 255, cv2.THRESH_BINARY)

    # Find the largest contour which represents the retina
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        largest_contour = max(contours, key=cv2.contourArea)
        (cx, cy), radius = cv2.minEnclosingCircle(largest_contour)
        center = (int(cx), int(cy))
        radius = int(radius * 0.98) # Slight shrink to avoid outer ring noise
    else:
        center = (w // 2, h // 2)
        radius = min(w, h) // 2

    # Create a smooth circular mask
    mask = np.zeros((h, w), dtype=np.uint8)
    cv2.circle(mask, center, radius, 255, -1)

    # Apply mask to image
    masked = cv2.bitwise_and(image, image, mask=mask)

    # Bounding box around the detected circle
    x1 = max(0, center[0] - radius)
    y1 = max(0, center[1] - radius)
    x2 = min(w, center[0] + radius)
    y2 = min(h, center[1] + radius)

    cropped = masked[y1:y2, x1:x2]
    return cropped
