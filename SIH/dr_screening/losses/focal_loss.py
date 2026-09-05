"""Multi-class Focal Loss with alpha class balancing and gamma modulation."""

from typing import Optional
import torch
import torch.nn as nn
import torch.nn.functional as F


class FocalLoss(nn.Module):
    """Multi-Class Focal Loss for handling severe class imbalance.

    FL(p_t) = -alpha_t * (1 - p_t)^gamma * log(p_t)

    Where:
        p_t is the model's estimated probability for the ground truth class.
        gamma is the focusing parameter (default: 2.0).
        alpha is the per-class weighting factor tensor.
    """

    def __init__(
        self,
        alpha: Optional[torch.Tensor] = None,
        gamma: float = 2.0,
        reduction: str = "mean",
    ):
        super().__init__()
        self.gamma = gamma
        self.reduction = reduction
        if alpha is not None:
            self.register_buffer("alpha", alpha.float())
        else:
            self.alpha = None

    def forward(self, inputs: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        """Args:
            inputs: Logits tensor (N, C).
            targets: Ground truth class indices (N,).
        """
        # Compute log probabilities and probabilities in a numerically stable manner
        log_p = F.log_softmax(inputs, dim=-1) # (N, C)
        p = torch.exp(log_p) # (N, C)

        # Gather target log_p and p
        targets = targets.view(-1, 1) # (N, 1)
        log_pt = log_p.gather(1, targets).squeeze(-1) # (N,)
        pt = p.gather(1, targets).squeeze(-1) # (N,)

        # Focal modulating factor: (1 - p_t)^gamma
        modulating_factor = torch.pow(1.0 - pt, self.gamma)

        # Compute focal loss
        loss = -modulating_factor * log_pt

        # Apply alpha class weighting
        if self.alpha is not None:
            alpha_t = self.alpha.gather(0, targets.squeeze(-1))
            loss = alpha_t * loss

        if self.reduction == "mean":
            return loss.mean()
        elif self.reduction == "sum":
            return loss.sum()
        else:
            return loss
