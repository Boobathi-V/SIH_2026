"""Post-hoc confidence calibration using Temperature Scaling and Expected Calibration Error (ECE)."""

from typing import Tuple
import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np


class TemperatureScaler(nn.Module):
    """Calibrates classification predictions via learned temperature parameter T:
    p_i = exp(z_i / T) / sum(exp(z_j / T))
    """

    def __init__(self):
        super().__init__()
        self.temperature = nn.Parameter(torch.ones(1) * 1.5)

    def forward(self, logits: torch.Tensor) -> torch.Tensor:
        """Scale logits by temperature."""
        temperature = self.temperature.clamp(min=0.01)
        return logits / temperature

    def fit(self, val_logits: torch.Tensor, val_labels: torch.Tensor, lr: float = 0.01, max_iter: int = 100) -> float:
        """Fit temperature parameter on validation set using Negative Log Likelihood."""
        device = val_logits.device
        self.to(device)

        nll_criterion = nn.CrossEntropyLoss()
        optimizer = optim.LBFGS([self.temperature], lr=lr, max_iter=max_iter)

        def eval_step():
            optimizer.zero_grad()
            loss = nll_criterion(self.forward(val_logits), val_labels)
            loss.backward()
            return loss

        optimizer.step(eval_step)
        return self.temperature.item()


def compute_ece(probs: np.ndarray, labels: np.ndarray, n_bins: int = 10) -> Tuple[float, np.ndarray, np.ndarray]:
    """Compute Expected Calibration Error (ECE) and bin statistics.

    Args:
        probs: Array of predicted probability distributions (N, C).
        labels: Ground truth labels (N,).
        n_bins: Number of confidence bins.

    Returns:
        (ece_score, bin_accuracies, bin_confidences)
    """
    confidences = np.max(probs, axis=1)
    predictions = np.argmax(probs, axis=1)
    accuracies = predictions == labels

    bin_boundaries = np.linspace(0, 1, n_bins + 1)
    bin_lowers = bin_boundaries[:-1]
    bin_uppers = bin_boundaries[1:]

    ece = 0.0
    bin_accs = []
    bin_confs = []

    for bin_lower, bin_upper in zip(bin_lowers, bin_uppers):
        in_bin = (confidences > bin_lower) & (confidences <= bin_upper)
        prop_in_bin = np.mean(in_bin)

        if prop_in_bin > 0:
            accuracy_in_bin = np.mean(accuracies[in_bin])
            avg_confidence_in_bin = np.mean(confidences[in_bin])
            ece += np.abs(avg_confidence_in_bin - accuracy_in_bin) * prop_in_bin
            bin_accs.append(accuracy_in_bin)
            bin_confs.append(avg_confidence_in_bin)
        else:
            bin_accs.append(0.0)
            bin_confs.append(0.0)

    return float(ece), np.array(bin_accs), np.array(bin_confs)
