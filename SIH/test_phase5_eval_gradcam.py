"""Phase 5 Verification: Test standalone evaluation, metrics JSON, plot generation, and Grad-CAM heatmaps."""

import os
from pathlib import Path
import subprocess
import json


def test_phase5():
    print("=== Phase 5: Evaluation and Grad-CAM Verification ===")

    # Ensure best model exists
    ckpt_path = Path("outputs/checkpoints/best_model.pth")
    assert ckpt_path.exists(), f"Checkpoint {ckpt_path} does not exist. Run Phase 4 first."

    # Run evaluate.py
    cmd = [
        "python",
        "evaluate.py",
        "--checkpoint",
        str(ckpt_path),
        "--gradcam-samples",
        "3",
        "--device",
        "cpu",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print("STDERR:", result.stderr)
    assert result.returncode == 0, f"evaluate.py failed with code {result.returncode}"

    # Verify generated evaluation assets
    eval_dir = Path("outputs/evaluation")
    report_json = eval_dir / "evaluation_report.json"
    cm_plot = eval_dir / "confusion_matrix.png"
    cm_norm_plot = eval_dir / "confusion_matrix_normalized.png"
    roc_plot = eval_dir / "roc_curves.png"
    pr_plot = eval_dir / "pr_curves.png"
    calib_plot = eval_dir / "calibration_curve.png"

    assert report_json.exists(), "Missing evaluation_report.json"
    assert cm_plot.exists(), "Missing confusion_matrix.png"
    assert cm_norm_plot.exists(), "Missing confusion_matrix_normalized.png"
    assert roc_plot.exists(), "Missing roc_curves.png"
    assert pr_plot.exists(), "Missing pr_curves.png"
    assert calib_plot.exists(), "Missing calibration_curve.png"

    with open(report_json, "r") as f:
        metrics_data = json.load(f)
    assert "summary_metrics" in metrics_data
    assert "per_class_metrics" in metrics_data

    print(f"[OK] Evaluation report verified:")
    print(f"     Accuracy: {metrics_data['summary_metrics']['accuracy']*100:.1f}%")
    print(f"     Macro F1: {metrics_data['summary_metrics']['f1_macro']:.4f}")
    print(f"     QWK:      {metrics_data['summary_metrics']['qwk']:.4f}")
    print(f"     ROC-AUC:  {metrics_data['summary_metrics']['roc_auc']:.4f}")

    # Verify Grad-CAM heatmaps
    gradcam_dir = Path("outputs/gradcam")
    heatmaps = list(gradcam_dir.glob("*_heatmap.jpg"))
    overlays = list(gradcam_dir.glob("*_overlay.jpg"))

    assert len(heatmaps) >= 1, "No Grad-CAM heatmaps found."
    assert len(overlays) >= 1, "No Grad-CAM overlays found."

    print(f"[OK] Grad-CAM heatmaps verified: {len(heatmaps)} heatmaps, {len(overlays)} overlays generated.")
    for ov in overlays[:3]:
        print(f"     - Overlay: {ov} ({ov.stat().st_size / 1024:.1f} KB)")

    print("=== Phase 5 Evaluation and Grad-CAM Complete & Verified! ===")


if __name__ == "__main__":
    test_phase5()
