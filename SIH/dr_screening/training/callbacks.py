"""Training callbacks: ModelCheckpoint, EarlyStopping, CSVLogger, and TensorBoard logging."""

import os
import csv
from pathlib import Path
from typing import Dict, Any, Optional
import torch
import torch.nn as nn
from torch.utils.tensorboard import SummaryWriter


class ModelCheckpoint:
    """Saves best model weights according to validation metric and saves the latest checkpoint."""

    def __init__(
        self,
        checkpoint_dir: str = "outputs/checkpoints",
        monitor_metric: str = "val_f1",
        mode: str = "max",
    ):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.monitor_metric = monitor_metric
        self.mode = mode
        self.best_score = float("-inf") if mode == "max" else float("inf")
        self.best_epoch = 0

    def is_better(self, score: float) -> bool:
        if self.mode == "max":
            return score > self.best_score
        return score < self.best_score

    def step(
        self,
        epoch: int,
        metrics: Dict[str, float],
        model: nn.Module,
        optimizer: torch.optim.Optimizer,
        scheduler: Optional[Any] = None,
    ) -> bool:
        """Evaluate metric, save latest checkpoint, and update best model if metric improved."""
        current_score = metrics.get(self.monitor_metric, None)
        if current_score is None:
            raise KeyError(f"Monitored metric '{self.monitor_metric}' not found in validation metrics.")

        # Detect model metadata
        hidden_dim = None
        if hasattr(model, "head") and len(model.head) > 3 and hasattr(model.head[2], "out_features"):
            hidden_dim = model.head[2].out_features

        checkpoint_payload = {
            "epoch": epoch,
            "metrics": metrics,
            "model_config": {
                "backbone_name": getattr(model, "backbone_name", "tf_efficientnetv2_s.in21k_ft_in1k"),
                "num_classes": getattr(model, "num_classes", 5),
                "hidden_dim": hidden_dim,
            },
            "model_state_dict": model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            "scheduler_state_dict": scheduler.state_dict() if scheduler else None,
            "best_score": self.best_score,
            "best_epoch": self.best_epoch,
        }
        # Save last checkpoint unconditionally
        last_path = self.checkpoint_dir / "last_checkpoint.pth"
        torch.save(checkpoint_payload, last_path)

        improved = False
        if self.is_better(current_score):
            self.best_score = current_score
            self.best_epoch = epoch
            improved = True
            best_path = self.checkpoint_dir / "best_model.pth"
            torch.save(checkpoint_payload, best_path)

        return improved


class EarlyStopping:
    """Halts training when a monitored metric ceases to improve after patience epochs."""

    def __init__(self, patience: int = 7, min_delta: float = 1e-4, mode: str = "max"):
        self.patience = patience
        self.min_delta = min_delta
        self.mode = mode
        self.counter = 0
        self.best_score = float("-inf") if mode == "max" else float("inf")
        self.early_stop = False

    def step(self, score: float) -> bool:
        if self.mode == "max":
            improved = score > (self.best_score + self.min_delta)
        else:
            improved = score < (self.best_score - self.min_delta)

        if improved:
            self.best_score = score
            self.counter = 0
        else:
            self.counter += 1
            if self.counter >= self.patience:
                self.early_stop = True

        return self.early_stop


class CSVLogger:
    """Logs epoch metrics to a structured CSV file."""

    def __init__(self, log_path: str = "outputs/logs/metrics.csv"):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.file_initialized = self.log_path.exists()

    def log(self, metrics: Dict[str, Any]) -> None:
        file_exists = self.log_path.exists()
        with open(self.log_path, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(metrics.keys()))
            if not file_exists:
                writer.writeheader()
            writer.writerow(metrics)


class TensorBoardLogger:
    """Logs scalar metrics and learning rates to TensorBoard."""

    def __init__(self, log_dir: str = "outputs/logs/tensorboard"):
        self.writer = SummaryWriter(log_dir=log_dir)

    def log_scalars(self, tag_prefix: str, scalar_dict: Dict[str, float], step: int) -> None:
        for key, value in scalar_dict.items():
            self.writer.add_scalar(f"{tag_prefix}/{key}", value, step)

    def close(self) -> None:
        self.writer.close()
