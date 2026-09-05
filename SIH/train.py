"""Command-line interface for training Diabetic Retinopathy screening model."""

import argparse
from pathlib import Path
import torch

from dr_screening.configs.constants import NUM_CLASSES
from dr_screening.utils.helpers import setup_logger, seed_everything, load_config, get_device
from dr_screening.datasets.aptos_dataset import get_dataloaders
from dr_screening.models.classifier import DRScreeningModel
from dr_screening.training.trainer import DRTrainer


def parse_args():
    parser = argparse.ArgumentParser(description="Train SIH26038 Diabetic Retinopathy Screening Model")
    parser.add_argument("--config", type=str, default="dr_screening/configs/config.yaml", help="Path to config.yaml")
    parser.add_argument("--epochs", type=int, default=None, help="Override total training epochs")
    parser.add_argument("--batch-size", type=int, default=None, help="Override batch size")
    parser.add_argument("--backbone", type=str, default=None, help="Override backbone architecture")
    parser.add_argument("--resume", type=str, default=None, help="Path to checkpoint to resume from")
    parser.add_argument("--device", type=str, default=None, help="Compute device ('cuda' or 'cpu')")
    return parser.parse_args()


def main():
    args = parse_args()
    config = load_config(args.config)

    # Seed
    seed = config.get("project", {}).get("seed", 42)
    seed_everything(seed)

    # Device
    requested_device = args.device or config.get("project", {}).get("device", "cuda")
    device = get_device(requested_device)

    # Logger
    logger = setup_logger("train_cli")
    logger.info("=== SIH26038 Diabetic Retinopathy Screening Model Training ===")
    logger.info(f"Using device: {device}")

    # DataLoaders
    data_cfg = config.get("data", {})
    batch_size = args.batch_size or data_cfg.get("batch_size", 16)
    csv_path = data_cfg.get("csv_path", "datasets/aptos/train.csv")
    raw_dir = data_cfg.get("raw_dir", "datasets/aptos/train_images")
    img_size = data_cfg.get("image_size", 384)
    val_split = data_cfg.get("val_split", 0.2)
    use_weighted_sampler = data_cfg.get("use_weighted_sampler", False)

    logger.info(f"Loading data from: {csv_path} (batch_size={batch_size}, img_size={img_size})")
    train_loader, val_loader, class_weights, class_dist = get_dataloaders(
        csv_path=csv_path,
        image_dir=raw_dir,
        image_size=(img_size, img_size),
        batch_size=batch_size,
        val_split=val_split,
        use_weighted_sampler=use_weighted_sampler,
        num_workers=data_cfg.get("num_workers", 0),
        seed=seed,
    )
    logger.info(f"Class distribution: {class_dist}")
    logger.info(f"Class weights: {class_weights.numpy()}")

    # Model
    model_cfg = config.get("model", {})
    backbone_name = args.backbone or model_cfg.get("backbone", "tf_efficientnetv2_s.in21k_ft_in1k")
    dropout_rate = model_cfg.get("dropout_rate", 0.3)
    hidden_dim = model_cfg.get("classifier_hidden_dim", 256)
    pretrained = model_cfg.get("pretrained", True)

    logger.info(f"Instantiating model with backbone: {backbone_name} (pretrained={pretrained})")
    model = DRScreeningModel(
        backbone_name=backbone_name,
        num_classes=NUM_CLASSES,
        pretrained=pretrained,
        dropout_rate=dropout_rate,
        hidden_dim=hidden_dim,
    )

    # Trainer
    trainer = DRTrainer(
        model=model,
        train_loader=train_loader,
        val_loader=val_loader,
        config=config,
        class_weights=class_weights,
        device=device,
    )

    # Train
    best_metrics = trainer.run_training(
        total_epochs=args.epochs,
        resume_checkpoint=args.resume,
    )

    logger.info(f"Training finalized. Best validation metrics: {best_metrics}")


if __name__ == "__main__":
    main()
