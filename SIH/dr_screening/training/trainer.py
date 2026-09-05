"""Production-grade PyTorch Trainer supporting 3-stage transfer learning, Focal Loss, and checkpointing."""

import os
from pathlib import Path
from typing import Dict, Any, Optional
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from tqdm import tqdm

from dr_screening.configs.constants import NUM_CLASSES
from dr_screening.utils.helpers import setup_logger, get_device
from dr_screening.losses.loss_factory import create_criterion
from dr_screening.evaluation.metrics import compute_clinical_metrics
from dr_screening.training.callbacks import (
    ModelCheckpoint,
    EarlyStopping,
    CSVLogger,
    TensorBoardLogger,
)


class DRTrainer:
    """Trainer orchestrating 3-stage transfer learning for Diabetic Retinopathy screening."""

    def __init__(
        self,
        model: nn.Module,
        train_loader: DataLoader,
        val_loader: DataLoader,
        config: Dict[str, Any],
        class_weights: Optional[torch.Tensor] = None,
        device: Optional[torch.device] = None,
    ):
        self.config = config
        self.device = device or get_device(config.get("project", {}).get("device", "cuda"))
        self.model = model.to(self.device)
        self.train_loader = train_loader
        self.val_loader = val_loader
        self.class_weights = class_weights.to(self.device) if class_weights is not None else None

        # Paths
        paths = config.get("paths", {})
        self.checkpoints_dir = Path(paths.get("checkpoints_dir", "outputs/checkpoints"))
        self.logs_dir = Path(paths.get("logs_dir", "outputs/logs"))
        self.checkpoints_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        # Logger
        self.logger = setup_logger(
            "dr_trainer",
            log_file=str(self.logs_dir / "training.log"),
        )
        self.logger.info(f"Initialized DRTrainer on device: {self.device}")

        # Loss Criterion
        loss_cfg = config.get("loss", {})
        loss_type = loss_cfg.get("type", "focal")
        focal_gamma = float(loss_cfg.get("focal_gamma", 2.0))
        use_weights = loss_cfg.get("use_class_weights", True)
        weights_to_use = self.class_weights if use_weights else None

        self.criterion = create_criterion(
            loss_type=loss_type,
            class_weights=weights_to_use,
            focal_gamma=focal_gamma,
        ).to(self.device)
        self.logger.info(f"Loss criterion created: {loss_type} (gamma={focal_gamma})")

        # Callbacks
        train_cfg = config.get("training", {})
        patience = train_cfg.get("early_stopping_patience", 7)
        self.checkpoint_cb = ModelCheckpoint(
            checkpoint_dir=str(self.checkpoints_dir),
            monitor_metric="val_f1",
            mode="max",
        )
        self.early_stopping = EarlyStopping(patience=patience, mode="max")
        self.csv_logger = CSVLogger(log_path=str(self.logs_dir / "metrics.csv"))
        self.tb_logger = TensorBoardLogger(log_dir=str(self.logs_dir / "tensorboard"))

        # Training params
        self.grad_clip_norm = float(train_cfg.get("grad_clip_norm", 1.0))
        self.weight_decay = float(train_cfg.get("weight_decay", 1e-4))
        self.use_amp = bool(train_cfg.get("mixed_precision", True)) and self.device.type == "cuda"
        self.scaler = torch.amp.GradScaler("cuda", enabled=self.use_amp)
        self.logger.info(f"Mixed Precision (AMP) enabled: {self.use_amp}")

    def train_epoch(self, optimizer: torch.optim.Optimizer, epoch: int) -> float:
        """Run one training epoch."""
        self.model.train()
        running_loss = 0.0
        total_samples = 0

        pbar = tqdm(self.train_loader, desc=f"Epoch {epoch} [Train]", leave=False)
        for batch in pbar:
            images = batch["image"].to(self.device)
            labels = batch["label"].to(self.device)

            optimizer.zero_grad()

            with torch.amp.autocast(device_type=self.device.type, enabled=self.use_amp):
                logits = self.model(images)
                loss = self.criterion(logits, labels)

            self.scaler.scale(loss).backward()

            # Gradient clipping
            if self.grad_clip_norm > 0:
                self.scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), self.grad_clip_norm)

            self.scaler.step(optimizer)
            self.scaler.update()

            batch_size = images.size(0)
            running_loss += loss.item() * batch_size
            total_samples += batch_size

            pbar.set_postfix({"loss": f"{loss.item():.4f}"})

        return running_loss / total_samples if total_samples > 0 else 0.0

    @torch.no_grad()
    def evaluate(self) -> Dict[str, float]:
        """Evaluate model on validation set."""
        self.model.eval()
        running_loss = 0.0
        total_samples = 0
        all_preds = []
        all_labels = []
        all_probs = []

        for batch in self.val_loader:
            images = batch["image"].to(self.device)
            labels = batch["label"].to(self.device)

            with torch.amp.autocast(device_type=self.device.type, enabled=self.use_amp):
                logits = self.model(images)
                loss = self.criterion(logits, labels)

            probs = torch.softmax(logits, dim=-1)
            preds = torch.argmax(probs, dim=-1)

            batch_size = images.size(0)
            running_loss += loss.item() * batch_size
            total_samples += batch_size

            all_labels.extend(labels.cpu().numpy())
            all_preds.extend(preds.cpu().numpy())
            all_probs.extend(probs.cpu().numpy())

        y_true = np.array(all_labels)
        y_pred = np.array(all_preds)
        y_prob = np.array(all_probs)

        metrics = compute_clinical_metrics(y_true, y_pred, y_prob, num_classes=NUM_CLASSES)
        metrics["val_loss"] = running_loss / total_samples if total_samples > 0 else 0.0
        return metrics

    def run_training(self, total_epochs: Optional[int] = None, resume_checkpoint: Optional[str] = None) -> Dict[str, float]:
        """Execute multi-stage training pipeline."""
        stages = self.config.get("training", {}).get("stages", [])
        if not stages:
            # Default single stage
            stages = [{"stage": 1, "name": "training", "epochs": 10, "lr": 3e-4, "unfreeze_all": True}]

        start_epoch = 1
        global_epoch = 1

        if resume_checkpoint and os.path.exists(resume_checkpoint):
            self.logger.info(f"Resuming training from checkpoint: {resume_checkpoint}")
            ckpt = torch.load(resume_checkpoint, map_location=self.device)
            self.model.load_state_dict(ckpt["model_state_dict"])
            start_epoch = ckpt.get("epoch", 0) + 1
            global_epoch = start_epoch

        best_metrics = {}

        for stage_idx, stage_info in enumerate(stages, 1):
            stage_name = stage_info.get("name", f"stage_{stage_idx}")
            stage_epochs = stage_info.get("epochs", 5)
            stage_lr = float(stage_info.get("lr", 3e-4))

            # Apply stage freeze/unfreeze
            if stage_info.get("freeze_backbone", False):
                self.logger.info(f"=== Starting Stage {stage_idx}: {stage_name} (Freeze Backbone) ===")
                self.model.freeze_backbone(True)
            elif stage_info.get("unfreeze_ratio", None):
                ratio = float(stage_info["unfreeze_ratio"])
                self.logger.info(f"=== Starting Stage {stage_idx}: {stage_name} (Unfreeze Top {ratio*100:.0f}%) ===")
                self.model.unfreeze_top_stages(ratio)
            else:
                self.logger.info(f"=== Starting Stage {stage_idx}: {stage_name} (Full Fine-tuning) ===")
                self.model.unfreeze_all()

            trainable_params, total_params = self.model.get_trainable_parameters_count()
            self.logger.info(f"Trainable parameters: {trainable_params:,} / {total_params:,}")

            # Configure Optimizer and Cosine Scheduler for this stage
            optimizer = torch.optim.AdamW(
                filter(lambda p: p.requires_grad, self.model.parameters()),
                lr=stage_lr,
                weight_decay=self.weight_decay,
            )
            scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
                optimizer,
                T_max=stage_epochs,
                eta_min=stage_lr * 0.05,
            )

            for epoch_in_stage in range(1, stage_epochs + 1):
                if total_epochs and global_epoch > total_epochs:
                    break

                current_lr = optimizer.param_groups[0]["lr"]
                train_loss = self.train_epoch(optimizer, global_epoch)
                val_metrics = self.evaluate()
                scheduler.step()

                val_loss = val_metrics["val_loss"]
                val_acc = val_metrics["accuracy"]
                val_f1 = val_metrics["f1_macro"]
                val_qwk = val_metrics["qwk"]
                val_auc = val_metrics["roc_auc"]

                # Log to console
                self.logger.info(
                    f"Epoch {global_epoch:02d} (Stage {stage_idx}) | "
                    f"LR: {current_lr:.6f} | "
                    f"Train Loss: {train_loss:.4f} | "
                    f"Val Loss: {val_loss:.4f} | "
                    f"Acc: {val_acc*100:.1f}% | "
                    f"F1: {val_f1:.4f} | "
                    f"QWK: {val_qwk:.4f} | "
                    f"AUC: {val_auc:.4f}"
                )

                # Checkpoint step
                metric_dict = {"val_loss": val_loss, "val_acc": val_acc, "val_f1": val_f1, "val_qwk": val_qwk, "val_auc": val_auc}
                improved = self.checkpoint_cb.step(
                    epoch=global_epoch,
                    metrics=metric_dict,
                    model=self.model,
                    optimizer=optimizer,
                    scheduler=scheduler,
                )
                if improved:
                    self.logger.info(f"--> [NEW BEST] Validation Macro F1 improved to {val_f1:.4f}! Saved best_model.pth")
                    best_metrics = metric_dict

                # CSV and TensorBoard logging
                log_row = {
                    "epoch": global_epoch,
                    "stage": stage_name,
                    "lr": current_lr,
                    "train_loss": train_loss,
                    **val_metrics,
                }
                self.csv_logger.log(log_row)
                self.tb_logger.log_scalars("Loss", {"train": train_loss, "val": val_loss}, global_epoch)
                self.tb_logger.log_scalars("Metrics", {"acc": val_acc, "f1": val_f1, "qwk": val_qwk, "auc": val_auc}, global_epoch)
                self.tb_logger.log_scalars("LR", {"lr": current_lr}, global_epoch)

                # Early stopping check
                if self.early_stopping.step(val_f1):
                    self.logger.info(f"Early stopping triggered at global epoch {global_epoch}")
                    break

                global_epoch += 1

            if total_epochs and global_epoch > total_epochs:
                break

        self.tb_logger.close()
        self.logger.info("Training pipeline execution completed successfully.")
        return best_metrics
