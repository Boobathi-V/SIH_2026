"""Loss function factory supporting CrossEntropy, Weighted CrossEntropy, and Focal Loss."""

from typing import Optional
import torch
import torch.nn as nn

from dr_screening.losses.focal_loss import FocalLoss


def create_criterion(
    loss_type: str = "focal",
    class_weights: Optional[torch.Tensor] = None,
    focal_gamma: float = 2.0,
) -> nn.Module:
    """Instantiate the loss function based on configuration.

    Args:
        loss_type: One of 'focal', 'cross_entropy', 'weighted_ce'.
        class_weights: Optional per-class weight tensor for class balancing.
        focal_gamma: Focusing exponent for focal loss.

    Returns:
        PyTorch loss criterion module.
    """
    loss_type = loss_type.lower()

    if loss_type == "focal":
        return FocalLoss(alpha=class_weights, gamma=focal_gamma, reduction="mean")
    elif loss_type == "weighted_ce":
        if class_weights is None:
            raise ValueError("class_weights must be provided when loss_type is 'weighted_ce'")
        return nn.CrossEntropyLoss(weight=class_weights)
    elif loss_type == "cross_entropy":
        return nn.CrossEntropyLoss()
    else:
        raise ValueError(
            f"Unsupported loss type '{loss_type}'. Choose from: 'focal', 'weighted_ce', 'cross_entropy'."
        )
