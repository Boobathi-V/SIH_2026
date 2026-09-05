"""Clinical evaluation metrics: Accuracy, Precision, Recall, Macro-F1, QWK, and ROC-AUC."""

from typing import Dict, Tuple, Optional
import numpy as np
import torch
from sklearn.metrics import (
    accuracy_score,
    precision_recall_fscore_support,
    roc_auc_score,
    cohen_kappa_score,
    confusion_matrix,
    classification_report,
)

from dr_screening.configs.constants import NUM_CLASSES, CLASS_NAMES


def compute_clinical_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_prob: Optional[np.ndarray] = None,
    num_classes: int = NUM_CLASSES,
) -> Dict[str, float]:
    """Compute standard and clinical-grade evaluation metrics.

    Args:
        y_true: Ground-truth class labels (N,).
        y_pred: Predicted discrete class indices (N,).
        y_prob: Softmax class probability distributions (N, C).
        num_classes: Total number of classes.

    Returns:
        Dictionary containing Accuracy, Macro Precision/Recall/F1, QWK, and ROC-AUC.
    """
    accuracy = float(accuracy_score(y_true, y_pred))

    # Precision, Recall, F1 (macro and weighted)
    prec_macro, rec_macro, f1_macro, _ = precision_recall_fscore_support(
        y_true, y_pred, average="macro", zero_division=0
    )
    prec_weighted, rec_weighted, f1_weighted, _ = precision_recall_fscore_support(
        y_true, y_pred, average="weighted", zero_division=0
    )

    # Quadratic Weighted Kappa (standard clinical ophthalmology metric)
    try:
        qwk = float(cohen_kappa_score(y_true, y_pred, weights="quadratic"))
    except Exception:
        qwk = 0.0

    # Multi-class One-vs-Rest ROC-AUC
    roc_auc = 0.0
    if y_prob is not None:
        try:
            # Handle cases where some classes might not be present in a small test batch
            present_classes = np.unique(y_true)
            if len(present_classes) == num_classes:
                roc_auc = float(roc_auc_score(y_true, y_prob, multi_class="ovr", average="macro"))
            else:
                # Calculate only on present classes
                roc_auc = float(roc_auc_score(y_true, y_prob[:, present_classes], multi_class="ovr", average="macro"))
        except Exception:
            roc_auc = 0.0

    metrics = {
        "accuracy": accuracy,
        "precision_macro": float(prec_macro),
        "recall_macro": float(rec_macro),
        "f1_macro": float(f1_macro),
        "precision_weighted": float(prec_weighted),
        "recall_weighted": float(rec_weighted),
        "f1_weighted": float(f1_weighted),
        "qwk": qwk,
        "roc_auc": roc_auc,
    }
    return metrics


def compute_per_class_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    class_names: Optional[list] = None,
) -> Dict[str, Dict[str, float]]:
    """Compute Sensitivity (Recall), Specificity, Precision, and F1 score for each individual DR class."""
    names = class_names or CLASS_NAMES
    cm = confusion_matrix(y_true, y_pred, labels=list(range(len(names))))

    per_class = {}
    total_samples = np.sum(cm)

    for i, name in enumerate(names):
        tp = cm[i, i]
        fn = np.sum(cm[i, :]) - tp
        fp = np.sum(cm[:, i]) - tp
        tn = total_samples - (tp + fn + fp)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0.0 # Recall
        specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0
        f1 = (2 * precision * sensitivity) / (precision + sensitivity) if (precision + sensitivity) > 0 else 0.0

        per_class[name] = {
            "precision": float(precision),
            "sensitivity_recall": float(sensitivity),
            "specificity": float(specificity),
            "f1_score": float(f1),
            "support": int(np.sum(cm[i, :])),
        }

    return per_class
