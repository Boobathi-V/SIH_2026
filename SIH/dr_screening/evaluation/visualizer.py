"""Visualization utilities for clinical evaluation: Confusion Matrix, ROC curves, PR curves, and Calibration."""

from pathlib import Path
from typing import List, Optional
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import (
    confusion_matrix,
    roc_curve,
    auc,
    precision_recall_curve,
    average_precision_score,
)
from sklearn.preprocessing import label_binarize

from dr_screening.configs.constants import CLASS_NAMES, NUM_CLASSES
from dr_screening.models.calibration import compute_ece


def plot_confusion_matrix(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    class_names: Optional[List[str]] = None,
    save_path: str = "outputs/evaluation/confusion_matrix.png",
    normalize: bool = False,
) -> None:
    """Plot and save publication-grade confusion matrix."""
    names = class_names or CLASS_NAMES
    cm = confusion_matrix(y_true, y_pred, labels=list(range(len(names))))

    if normalize:
        cm_norm = cm.astype("float") / cm.sum(axis=1)[:, np.newaxis]
        cm_norm = np.nan_to_num(cm_norm) # handle zero rows
        data_to_plot = cm_norm
        fmt = ".2f"
        title = "Normalized Confusion Matrix (Diabetic Retinopathy)"
    else:
        data_to_plot = cm
        fmt = "d"
        title = "Confusion Matrix (Sample Counts)"

    fig, ax = plt.subplots(figsize=(8, 7))
    sns.heatmap(
        data_to_plot,
        annot=True,
        fmt=fmt,
        cmap="Blues",
        xticklabels=names,
        yticklabels=names,
        cbar=True,
        ax=ax,
        linewidths=1,
        linecolor="#dddddd",
    )
    ax.set_title(title, fontsize=14, pad=12, fontweight="bold")
    ax.set_ylabel("True Clinical Diagnosis", fontsize=12)
    ax.set_xlabel("Model Predicted Diagnosis", fontsize=12)
    plt.xticks(rotation=30, ha="right")
    plt.yticks(rotation=0)

    Path(save_path).parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches="tight")
    plt.close()


def plot_multiclass_roc(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    class_names: Optional[List[str]] = None,
    save_path: str = "outputs/evaluation/roc_curves.png",
) -> None:
    """Plot and save multi-class One-vs-Rest ROC curves."""
    names = class_names or CLASS_NAMES
    n_classes = len(names)

    # Binarize labels for One-vs-Rest
    y_true_bin = label_binarize(y_true, classes=list(range(n_classes)))
    if y_true_bin.shape[1] == 1:
        # Fallback if only 2 unique classes in slice
        y_true_bin = np.hstack([1 - y_true_bin, y_true_bin])

    fpr = dict()
    tpr = dict()
    roc_auc = dict()

    plt.figure(figsize=(9, 7))
    colors = ["#2b5c8f", "#2ca02c", "#d62728", "#9467bd", "#ff7f0e"]

    for i in range(min(n_classes, y_true_bin.shape[1])):
        if np.sum(y_true_bin[:, i]) > 0:
            fpr[i], tpr[i], _ = roc_curve(y_true_bin[:, i], y_prob[:, i])
            roc_auc[i] = auc(fpr[i], tpr[i])
            plt.plot(
                fpr[i],
                tpr[i],
                color=colors[i % len(colors)],
                lw=2,
                label=f"{names[i]} (AUC = {roc_auc[i]:.3f})",
            )

    plt.plot([0, 1], [0, 1], "k--", lw=1.5, alpha=0.7, label="Chance")
    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.05])
    plt.xlabel("False Positive Rate (1 - Specificity)", fontsize=12)
    plt.ylabel("True Positive Rate (Sensitivity / Recall)", fontsize=12)
    plt.title("Multi-Class One-vs-Rest ROC Curves", fontsize=14, fontweight="bold", pad=12)
    plt.legend(loc="lower right", fontsize=10, frameon=True)
    plt.grid(True, alpha=0.3)

    Path(save_path).parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches="tight")
    plt.close()


def plot_multiclass_pr(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    class_names: Optional[List[str]] = None,
    save_path: str = "outputs/evaluation/pr_curves.png",
) -> None:
    """Plot and save multi-class Precision-Recall curves."""
    names = class_names or CLASS_NAMES
    n_classes = len(names)

    y_true_bin = label_binarize(y_true, classes=list(range(n_classes)))
    if y_true_bin.shape[1] == 1:
        y_true_bin = np.hstack([1 - y_true_bin, y_true_bin])

    plt.figure(figsize=(9, 7))
    colors = ["#2b5c8f", "#2ca02c", "#d62728", "#9467bd", "#ff7f0e"]

    for i in range(min(n_classes, y_true_bin.shape[1])):
        if np.sum(y_true_bin[:, i]) > 0:
            prec, rec, _ = precision_recall_curve(y_true_bin[:, i], y_prob[:, i])
            ap = average_precision_score(y_true_bin[:, i], y_prob[:, i])
            plt.plot(
                rec,
                prec,
                color=colors[i % len(colors)],
                lw=2,
                label=f"{names[i]} (AP = {ap:.3f})",
            )

    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.05])
    plt.xlabel("Recall (Sensitivity)", fontsize=12)
    plt.ylabel("Precision (Positive Predictive Value)", fontsize=12)
    plt.title("Multi-Class Precision-Recall Curves", fontsize=14, fontweight="bold", pad=12)
    plt.legend(loc="lower left", fontsize=10, frameon=True)
    plt.grid(True, alpha=0.3)

    Path(save_path).parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches="tight")
    plt.close()


def plot_calibration_curve(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    calibrated_prob: Optional[np.ndarray] = None,
    save_path: str = "outputs/evaluation/calibration_curve.png",
) -> None:
    """Plot reliability diagram before and after temperature scaling."""
    ece_raw, acc_raw, conf_raw = compute_ece(y_prob, y_true)

    plt.figure(figsize=(8, 6))
    bins = np.linspace(0, 1, len(acc_raw) + 1)
    bin_centers = (bins[:-1] + bins[1:]) / 2

    plt.plot(bin_centers, acc_raw, "s-", color="#d62728", lw=2, label=f"Uncalibrated (ECE = {ece_raw:.4f})")

    if calibrated_prob is not None:
        ece_cal, acc_cal, conf_cal = compute_ece(calibrated_prob, y_true)
        plt.plot(
            bin_centers,
            acc_cal,
            "o-",
            color="#2ca02c",
            lw=2,
            label=f"Calibrated via Temp Scaling (ECE = {ece_cal:.4f})",
        )

    plt.plot([0, 1], [0, 1], "k--", label="Perfect Calibration")
    plt.xlabel("Confidence (Predicted Probability)", fontsize=12)
    plt.ylabel("Observed Empirical Accuracy", fontsize=12)
    plt.title("Confidence Calibration Reliability Diagram", fontsize=14, fontweight="bold", pad=12)
    plt.legend(loc="upper left", fontsize=10)
    plt.grid(True, alpha=0.3)

    Path(save_path).parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches="tight")
    plt.close()
