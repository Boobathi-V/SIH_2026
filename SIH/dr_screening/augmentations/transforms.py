"""Data augmentation pipelines using Albumentations."""

from typing import Tuple
import albumentations as A
from albumentations.pytorch import ToTensorV2

from dr_screening.configs.constants import IMAGENET_MEAN, IMAGENET_STD


def get_train_transforms(
    image_size: Tuple[int, int] = (384, 384),
    mean: Tuple[float, float, float] = IMAGENET_MEAN,
    std: Tuple[float, float, float] = IMAGENET_STD,
) -> A.Compose:
    """Build heavy, clinical-grade Albumentations training augmentation pipeline."""
    return A.Compose(
        [
            A.HorizontalFlip(p=0.5),
            A.VerticalFlip(p=0.5),
            A.Affine(
                scale=(0.92, 1.08),
                translate_percent=(-0.05, 0.05),
                rotate=(-20, 20),
                p=0.7,
            ),
            A.RandomBrightnessContrast(
                brightness_limit=0.15,
                contrast_limit=0.15,
                p=0.6,
            ),
            A.RandomGamma(gamma_limit=(85, 115), p=0.5),
            A.GaussNoise(p=0.3),
            A.GaussianBlur(blur_limit=(3, 5), p=0.2),
            A.CoarseDropout(
                num_holes_range=(1, 6),
                hole_height_range=(8, 24),
                hole_width_range=(8, 24),
                p=0.25,
            ),
            A.Normalize(mean=mean, std=std, max_pixel_value=255.0),
            ToTensorV2(),
        ]
    )


def get_val_transforms(
    image_size: Tuple[int, int] = (384, 384),
    mean: Tuple[float, float, float] = IMAGENET_MEAN,
    std: Tuple[float, float, float] = IMAGENET_STD,
) -> A.Compose:
    """Build lightweight validation transform pipeline (Normalization only)."""
    return A.Compose(
        [
            A.Normalize(mean=mean, std=std, max_pixel_value=255.0),
            ToTensorV2(),
        ]
    )
