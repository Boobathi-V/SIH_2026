"""End-to-end medical retinal preprocessing pipeline."""

from typing import Tuple, Union, Optional
from pathlib import Path
import cv2
import numpy as np
import torch
from PIL import Image

from dr_screening.configs.constants import DEFAULT_IMAGE_SIZE, IMAGENET_MEAN, IMAGENET_STD
from dr_screening.preprocessing.crop import circular_crop_retina, remove_black_borders
from dr_screening.preprocessing.enhancement import (
    apply_clahe,
    apply_gamma_correction,
    apply_ben_graham,
    resize_image,
    normalize_rgb,
    normalize_imagenet,
)


class FundusPreprocessor:
    """Production-grade retinal fundus preprocessor.

    Applies in strict sequence:
    1. Circular crop retina (boundary detection & center)
    2. Remove black borders
    3. CLAHE enhancement (LAB lightness space)
    4. Gamma correction
    5. Resize to target dimension (384x384 default)
    6. RGB normalization [0, 1]
    7. ImageNet standardization
    """

    def __init__(
        self,
        target_size: Tuple[int, int] = DEFAULT_IMAGE_SIZE,
        crop_tolerance: int = 7,
        clahe_clip_limit: float = 2.0,
        clahe_grid_size: Tuple[int, int] = (8, 8),
        gamma: float = 1.15,
        use_ben_graham: bool = False,
        ben_graham_sigma: int = 10,
        mean: Tuple[float, float, float] = IMAGENET_MEAN,
        std: Tuple[float, float, float] = IMAGENET_STD,
    ):
        self.target_size = target_size
        self.crop_tolerance = crop_tolerance
        self.clahe_clip_limit = clahe_clip_limit
        self.clahe_grid_size = clahe_grid_size
        self.gamma = gamma
        self.use_ben_graham = use_ben_graham
        self.ben_graham_sigma = ben_graham_sigma
        self.mean = mean
        self.std = std

    def load_image(self, image_source: Union[str, Path, np.ndarray, Image.Image]) -> np.ndarray:
        """Load image into RGB numpy array."""
        if isinstance(image_source, (str, Path)):
            img = cv2.imread(str(image_source))
            if img is None:
                raise FileNotFoundError(f"Unable to read retinal image at: {image_source}")
            return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        elif isinstance(image_source, Image.Image):
            return np.array(image_source.convert("RGB"))
        elif isinstance(image_source, np.ndarray):
            if image_source.ndim == 2:
                return cv2.cvtColor(image_source, cv2.COLOR_GRAY2RGB)
            return image_source.copy()
        else:
            raise TypeError(f"Unsupported image input type: {type(image_source)}")

    def preprocess(
        self,
        image_source: Union[str, Path, np.ndarray, Image.Image],
        return_tensor: bool = False,
    ) -> Union[np.ndarray, torch.Tensor]:
        """Execute complete preprocessing pipeline.

        Args:
            image_source: File path, numpy array, or PIL Image.
            return_tensor: If True, returns PyTorch FloatTensor (3, H, W).
                           If False, returns uint8 RGB numpy array (H, W, 3) suitable for Albumentations/plotting.

        Returns:
            Preprocessed RGB image as uint8 numpy array or normalized float tensor.
        """
        # Load RGB
        img = self.load_image(image_source)

        # Step 1 & 2: Circular crop retina and remove black margins
        img = circular_crop_retina(img, tol=self.crop_tolerance)

        # Step 3: CLAHE enhancement in LAB space
        img = apply_clahe(img, clip_limit=self.clahe_clip_limit, tile_grid_size=self.clahe_grid_size)

        # Step 4: Gamma correction
        if self.gamma != 1.0:
            img = apply_gamma_correction(img, gamma=self.gamma)

        # Optional: Ben Graham's local contrast enhancement
        if self.use_ben_graham:
            img = apply_ben_graham(img, sigma_x=self.ben_graham_sigma)

        # Step 5: Resize to standard dimensions
        img = resize_image(img, target_size=self.target_size)

        if not return_tensor:
            return img.astype(np.uint8)

        # Step 6 & 7: RGB normalization [0, 1] + ImageNet standardization
        norm_img = normalize_rgb(img)
        std_img = normalize_imagenet(norm_img, mean=self.mean, std=self.std)

        # Convert to PyTorch Tensor (Channels-First: C, H, W)
        tensor = torch.from_numpy(std_img).permute(2, 0, 1).contiguous().float()
        return tensor


def preprocess_fundus_image(
    image_source: Union[str, Path, np.ndarray, Image.Image],
    target_size: Tuple[int, int] = DEFAULT_IMAGE_SIZE,
    return_tensor: bool = False,
) -> Union[np.ndarray, torch.Tensor]:
    """Functional shortcut for default retinal preprocessor."""
    preprocessor = FundusPreprocessor(target_size=target_size)
    return preprocessor.preprocess(image_source, return_tensor=return_tensor)
