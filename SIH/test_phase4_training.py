"""Phase 4 Verification: Test training pipeline, Focal Loss, checkpoint saving, and metric logging."""

import os
from pathlib import Path
import torch
from dr_screening.utils.helpers import load_config, get_device
from dr_screening.datasets.aptos_dataset import get_dataloaders
from dr_screening.models.classifier import DRScreeningModel
from dr_screening.training.trainer import DRTrainer
from dr_screening.configs.constants import NUM_CLASSES


def test_phase4():
    print("=== Phase 4: Training Pipeline and Checkpoint Verification ===")

    config = load_config("dr_screening/configs/config.yaml")
    device = get_device("cpu") # Test training steps on CPU for portability

    # Get data
    train_loader, val_loader, class_weights, _ = get_dataloaders(
        csv_path="datasets/aptos/train.csv",
        image_dir="datasets/aptos/train_images",
        batch_size=4,
        val_split=0.2,
        num_workers=0,
    )

    # Instantiate model without downloading huge weights for fast offline verification
    model = DRScreeningModel(
        backbone_name="tf_efficientnetv2_s.in21k_ft_in1k",
        num_classes=NUM_CLASSES,
        pretrained=False,
        dropout_rate=0.2,
        hidden_dim=128,
    )

    # Initialize trainer
    trainer = DRTrainer(
        model=model,
        train_loader=train_loader,
        val_loader=val_loader,
        config=config,
        class_weights=class_weights,
        device=device,
    )

    # Run for 2 epochs
    print("Running 2-epoch training cycle with Focal Loss...")
    trainer.run_training(total_epochs=2)

    # Verification 1: Checkpoints exist
    checkpoints_dir = Path("outputs/checkpoints")
    best_ckpt = checkpoints_dir / "best_model.pth"
    last_ckpt = checkpoints_dir / "last_checkpoint.pth"

    assert last_ckpt.exists(), f"Last checkpoint not found at {last_ckpt}"
    assert best_ckpt.exists(), f"Best model checkpoint not found at {best_ckpt}"
    print(f"[OK] Checkpoints successfully created:")
    print(f"     - Last: {last_ckpt} ({last_ckpt.stat().st_size / (1024*1024):.1f} MB)")
    print(f"     - Best: {best_ckpt} ({best_ckpt.stat().st_size / (1024*1024):.1f} MB)")

    # Verification 2: Checkpoint payload integrity
    payload = torch.load(last_ckpt, map_location="cpu")
    assert "model_state_dict" in payload, "Missing model_state_dict in checkpoint"
    assert "optimizer_state_dict" in payload, "Missing optimizer_state_dict in checkpoint"
    assert "metrics" in payload, "Missing metrics in checkpoint"
    print(f"[OK] Checkpoint integrity confirmed: epoch={payload['epoch']}, metrics={payload['metrics']}")

    # Verification 3: Metrics CSV log exists
    csv_log = Path("outputs/logs/metrics.csv")
    assert csv_log.exists(), f"Metrics CSV log not found at {csv_log}"
    print(f"[OK] Metrics CSV log exists at {csv_log} ({csv_log.stat().st_size} bytes)")

    print("=== Phase 4 Training Pipeline Complete & Verified! ===")


if __name__ == "__main__":
    test_phase4()
