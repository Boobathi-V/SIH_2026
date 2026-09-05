"""Phase 2 Verification: Test Albumentations transforms, PyTorch DataLoaders, and batch shapes."""

import torch
from dr_screening.datasets.aptos_dataset import get_dataloaders
from dr_screening.configs.constants import NUM_CLASSES


def test_phase2():
    print("=== Phase 2: Augmentation and DataLoaders Test ===")

    batch_size = 4
    train_loader, val_loader, class_weights, class_dist = get_dataloaders(
        csv_path="datasets/aptos/train.csv",
        image_dir="datasets/aptos/train_images",
        batch_size=batch_size,
        val_split=0.2,
        num_workers=0,
    )

    print(f"[OK] Total classes: {NUM_CLASSES}")
    print(f"[OK] Class distribution in dataset: {class_dist}")
    print(f"[OK] Computed Class Weights for Loss: {class_weights.numpy()}")
    assert len(class_weights) == NUM_CLASSES, f"Expected {NUM_CLASSES} class weights, got {len(class_weights)}"

    # Test training batch
    train_batch = next(iter(train_loader))
    images = train_batch["image"]
    labels = train_batch["label"]
    id_codes = train_batch["id_code"]

    print(f"[OK] Train batch image shape: {images.shape}")
    print(f"[OK] Train batch label shape: {labels.shape}")
    print(f"[OK] Train batch id_codes: {id_codes}")

    assert images.shape == (batch_size, 3, 384, 384), f"Expected {(batch_size, 3, 384, 384)}, got {images.shape}"
    assert labels.shape == (batch_size,), f"Expected {(batch_size,)}, got {labels.shape}"
    assert images.dtype == torch.float32, f"Expected float32, got {images.dtype}"
    assert labels.dtype == torch.int64, f"Expected int64, got {labels.dtype}"

    # Test validation batch
    val_batch = next(iter(val_loader))
    val_images = val_batch["image"]
    val_labels = val_batch["label"]

    print(f"[OK] Val batch image shape: {val_images.shape}")
    print(f"[OK] Val batch label shape: {val_labels.shape}")

    assert val_images.shape[1:] == (3, 384, 384)
    assert 0 <= val_labels.min() and val_labels.max() < NUM_CLASSES

    print("=== Phase 2 Dataloaders & Augmentations Complete & Verified! ===")


if __name__ == "__main__":
    test_phase2()
