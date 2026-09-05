"""PyTorch Dataset and DataLoader factory for APTOS 2019 Diabetic Retinopathy."""

import os
from pathlib import Path
from typing import Dict, Tuple, Optional
import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset, DataLoader, WeightedRandomSampler
from sklearn.model_selection import train_test_split

from dr_screening.configs.constants import NUM_CLASSES, DEFAULT_IMAGE_SIZE
from dr_screening.preprocessing.pipeline import FundusPreprocessor
from dr_screening.augmentations.transforms import get_train_transforms, get_val_transforms


class APTOSDataset(Dataset):
    """PyTorch Dataset for Diabetic Retinopathy screening images."""

    def __init__(
        self,
        df: pd.DataFrame,
        image_dir: str,
        preprocessor: Optional[FundusPreprocessor] = None,
        transform=None,
    ):
        self.df = df.reset_index(drop=True)
        self.image_dir = Path(image_dir)
        self.preprocessor = preprocessor or FundusPreprocessor(target_size=DEFAULT_IMAGE_SIZE)
        self.transform = transform

    def __len__(self) -> int:
        return len(self.df)

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        row = self.df.iloc[idx]
        id_code = str(row["id_code"])
        label = int(row["diagnosis"])

        # Determine image file path
        if "file_path" in row and os.path.exists(str(row["file_path"])):
            img_path = Path(row["file_path"])
        else:
            # Look for png, jpg, or jpeg
            candidates = [
                self.image_dir / f"{id_code}.png",
                self.image_dir / f"{id_code}.jpg",
                self.image_dir / f"{id_code}.jpeg",
            ]
            img_path = None
            for cand in candidates:
                if cand.exists():
                    img_path = cand
                    break
            if img_path is None:
                raise FileNotFoundError(f"Retinal fundus image not found for id_code: {id_code}")

        # Preprocess: crop, CLAHE, gamma, resize to uint8 (H, W, 3)
        processed_uint8 = self.preprocessor.preprocess(img_path, return_tensor=False)

        # Apply Albumentations augmentations + ToTensorV2
        if self.transform is not None:
            augmented = self.transform(image=processed_uint8)
            tensor_img = augmented["image"]
        else:
            # Fallback to standard PyTorch float tensor
            tensor_img = torch.from_numpy(processed_uint8.astype(np.float32) / 255.0).permute(2, 0, 1)

        return {
            "image": tensor_img,
            "label": torch.tensor(label, dtype=torch.long),
            "id_code": id_code,
        }


def compute_class_weights(labels: np.ndarray, num_classes: int = NUM_CLASSES) -> torch.Tensor:
    """Compute balanced inverse class weights for handling severe class imbalance:
    w_c = N / (num_classes * N_c)
    """
    total_samples = len(labels)
    class_counts = np.bincount(labels, minlength=num_classes)

    weights = []
    for count in class_counts:
        if count > 0:
            w = total_samples / (num_classes * count)
        else:
            w = 1.0
        weights.append(w)

    weights_tensor = torch.tensor(weights, dtype=torch.float32)
    # Normalize weights so that mean is 1.0
    weights_tensor = weights_tensor / weights_tensor.mean()
    return weights_tensor


def get_dataloaders(
    csv_path: str = "datasets/aptos/train.csv",
    image_dir: str = "datasets/aptos/train_images",
    image_size: Tuple[int, int] = DEFAULT_IMAGE_SIZE,
    batch_size: int = 16,
    val_split: float = 0.2,
    use_weighted_sampler: bool = False,
    num_workers: int = 0,
    seed: int = 42,
) -> Tuple[DataLoader, DataLoader, torch.Tensor, Dict[str, int]]:
    """Factory creating stratified train and validation PyTorch DataLoaders.

    Returns:
        (train_loader, val_loader, class_weights_tensor, class_distribution_dict)
    """
    df = pd.read_csv(csv_path)
    if "diagnosis" not in df.columns or "id_code" not in df.columns:
        raise ValueError("CSV must contain 'id_code' and 'diagnosis' columns.")

    # Stratified Train / Validation split
    train_df, val_df = train_test_split(
        df,
        test_size=val_split,
        random_state=seed,
        stratify=df["diagnosis"],
    )

    # Preprocessors and transforms
    preprocessor = FundusPreprocessor(target_size=image_size)
    train_transform = get_train_transforms(image_size=image_size)
    val_transform = get_val_transforms(image_size=image_size)

    # Datasets
    train_dataset = APTOSDataset(
        df=train_df,
        image_dir=image_dir,
        preprocessor=preprocessor,
        transform=train_transform,
    )
    val_dataset = APTOSDataset(
        df=val_df,
        image_dir=image_dir,
        preprocessor=preprocessor,
        transform=val_transform,
    )

    # Class weights
    train_labels = train_df["diagnosis"].to_numpy()
    class_weights = compute_class_weights(train_labels, num_classes=NUM_CLASSES)

    # Sampler
    sampler = None
    shuffle = True
    if use_weighted_sampler:
        # Sample probabilities inversely proportional to class frequencies
        sample_weights = [class_weights[label].item() for label in train_labels]
        sampler = WeightedRandomSampler(
            weights=sample_weights,
            num_samples=len(sample_weights),
            replacement=True,
        )
        shuffle = False

    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=shuffle,
        sampler=sampler,
        num_workers=num_workers,
        pin_memory=torch.cuda.is_available(),
    )

    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=torch.cuda.is_available(),
    )

    class_dist = {int(k): int(v) for k, v in df["diagnosis"].value_counts().sort_index().items()}

    return train_loader, val_loader, class_weights, class_dist
