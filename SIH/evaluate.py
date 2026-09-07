"""Standalone Clinical Evaluation and Explainability Script for Diabetic Retinopathy Screening."""

import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
import torch
from sklearn.metrics import classification_report

from dr_screening.configs.constants import CLASS_NAMES, NUM_CLASSES
from dr_screening.utils.helpers import setup_logger, load_config, get_device
from dr_screening.datasets.aptos_dataset import get_dataloaders
from dr_screening.models.classifier import DRScreeningModel
from dr_screening.models.calibration import TemperatureScaler, compute_ece
from dr_screening.evaluation.metrics import compute_clinical_metrics, compute_per_class_metrics
from dr_screening.evaluation.visualizer import (
    plot_confusion_matrix,
    plot_multiclass_roc,
    plot_multiclass_pr,
    plot_calibration_curve,
)
from dr_screening.explainability.gradcam import RetinalGradCAM


def parse_args():
    parser = argparse.ArgumentParser(description="Evaluate Diabetic Retinopathy Screening Model")
    parser.add_argument("--config", type=str, default="dr_screening/configs/config.yaml")
    parser.add_argument("--checkpoint", type=str, default="outputs/checkpoints/best_model.pth")
    parser.add_argument("--output-dir", type=str, default="outputs/evaluation")
    parser.add_argument("--gradcam-samples", type=int, default=5, help="Number of Grad-CAM samples to generate")
    parser.add_argument("--device", type=str, default="cpu")
    return parser.parse_args()


def main():
    args = parse_args()
    config = load_config(args.config)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    gradcam_dir = Path(config.get("paths", {}).get("gradcam_dir", "outputs/gradcam"))
    gradcam_dir.mkdir(parents=True, exist_ok=True)

    logger = setup_logger("evaluate_cli", log_file=str(output_dir / "evaluation.log"))
    logger.info("=== SIH26038 Model Evaluation & Explainability Analysis ===")

    device = get_device(args.device)
    logger.info(f"Using device: {device}")

    # Load Checkpoint weights first to dynamically resolve architecture and hidden_dim
    ckpt_path = Path(args.checkpoint)
    if not ckpt_path.exists():
        raise FileNotFoundError(f"Checkpoint file not found: {ckpt_path}")

    logger.info(f"Loading checkpoint weights from: {ckpt_path}")
    checkpoint = torch.load(ckpt_path, map_location=device)
    state_dict = checkpoint["model_state_dict"]

    # Auto-detect hidden_dim from checkpoint state_dict if available
    model_cfg = config.get("model", {})
    backbone_name = model_cfg.get("backbone", "resnet50")
    hidden_dim = model_cfg.get("classifier_hidden_dim", 256)

    if "model_config" in checkpoint and checkpoint["model_config"].get("hidden_dim") is not None:
        hidden_dim = checkpoint["model_config"]["hidden_dim"]
        backbone_name = checkpoint["model_config"].get("backbone_name", backbone_name)
    elif "head.2.weight" in state_dict:
        hidden_dim = state_dict["head.2.weight"].shape[0]

    model = DRScreeningModel(
        backbone_name=backbone_name,
        num_classes=NUM_CLASSES,
        pretrained=False,
        dropout_rate=model_cfg.get("dropout_rate", 0.3),
        hidden_dim=hidden_dim,
    ).to(device)

    model.load_state_dict(state_dict)
    model.eval()

    # Load Validation Data
    data_cfg = config.get("data", {})
    csv_path = data_cfg.get("csv_path", "datasets/aptos/train.csv")
    raw_dir = data_cfg.get("raw_dir", "datasets/aptos/train_images")
    img_size = data_cfg.get("image_size", 384)

    _, val_loader, _, _ = get_dataloaders(
        csv_path=csv_path,
        image_dir=raw_dir,
        image_size=(img_size, img_size),
        batch_size=8,
        val_split=data_cfg.get("val_split", 0.2),
        num_workers=0,
    )

    # Run inference across validation dataset
    logger.info("Executing validation inference...")
    all_logits = []
    all_labels = []
    all_id_codes = []
    sample_images_tensor = []

    with torch.no_grad():
        for batch in val_loader:
            images = batch["image"].to(device)
            labels = batch["label"].to(device)
            id_codes = batch["id_code"]

            logits = model(images)
            all_logits.append(logits.cpu())
            all_labels.append(labels.cpu())
            all_id_codes.extend(id_codes)

            if len(sample_images_tensor) < args.gradcam_samples:
                sample_images_tensor.append((images.cpu(), labels.cpu(), id_codes))

    val_logits_tensor = torch.cat(all_logits, dim=0)
    val_labels_tensor = torch.cat(all_labels, dim=0)

    val_probs_raw = torch.softmax(val_logits_tensor, dim=-1).numpy()
    val_preds_raw = np.argmax(val_probs_raw, axis=-1)
    y_true = val_labels_tensor.numpy()

    # Temperature Scaling Confidence Calibration
    logger.info("Fitting post-hoc temperature scaler for confidence calibration...")
    scaler = TemperatureScaler()
    optimal_t = scaler.fit(val_logits_tensor, val_labels_tensor)
    logger.info(f"Optimal learned temperature T = {optimal_t:.3f}")

    with torch.no_grad():
        calibrated_logits = scaler(val_logits_tensor)
        val_probs_calibrated = torch.softmax(calibrated_logits, dim=-1).numpy()

    ece_before, _, _ = compute_ece(val_probs_raw, y_true)
    ece_after, _, _ = compute_ece(val_probs_calibrated, y_true)
    logger.info(f"Expected Calibration Error: Before={ece_before:.4f}, After={ece_after:.4f}")

    # Compute Overall Clinical Metrics
    summary_metrics = compute_clinical_metrics(y_true, val_preds_raw, val_probs_raw, num_classes=NUM_CLASSES)
    summary_metrics["optimal_temperature"] = optimal_t
    summary_metrics["ece_uncalibrated"] = ece_before
    summary_metrics["ece_calibrated"] = ece_after

    # Compute Per-Class Breakdown
    per_class_table = compute_per_class_metrics(y_true, val_preds_raw, class_names=CLASS_NAMES)

    # Scikit-learn Classification Report
    clf_report = classification_report(y_true, val_preds_raw, target_names=CLASS_NAMES, zero_division=0, output_dict=True)

    # Save Metrics JSON
    report_data = {
        "summary_metrics": summary_metrics,
        "per_class_metrics": per_class_table,
        "classification_report": clf_report,
    }
    metrics_json_path = output_dir / "evaluation_report.json"
    with open(metrics_json_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=4)
    logger.info(f"Saved evaluation metrics JSON to: {metrics_json_path}")

    # Visualizations
    logger.info("Generating evaluation diagnostic plots...")
    cm_path = output_dir / "confusion_matrix.png"
    cm_norm_path = output_dir / "confusion_matrix_normalized.png"
    roc_path = output_dir / "roc_curves.png"
    pr_path = output_dir / "pr_curves.png"
    calib_path = output_dir / "calibration_curve.png"

    plot_confusion_matrix(y_true, val_preds_raw, class_names=CLASS_NAMES, save_path=str(cm_path), normalize=False)
    plot_confusion_matrix(y_true, val_preds_raw, class_names=CLASS_NAMES, save_path=str(cm_norm_path), normalize=True)
    plot_multiclass_roc(y_true, val_probs_raw, class_names=CLASS_NAMES, save_path=str(roc_path))
    plot_multiclass_pr(y_true, val_probs_raw, class_names=CLASS_NAMES, save_path=str(pr_path))
    plot_calibration_curve(y_true, val_probs_raw, calibrated_prob=val_probs_calibrated, save_path=str(calib_path))

    logger.info(f"Plots saved:\n - {cm_path}\n - {cm_norm_path}\n - {roc_path}\n - {pr_path}\n - {calib_path}")

    # Generate Sample Grad-CAM Explainability Overlays
    logger.info(f"Generating Grad-CAM overlays for {args.gradcam_samples} samples...")
    gradcam_engine = RetinalGradCAM(model=model)

    saved_gradcam_files = []
    sample_count = 0
    for imgs, labels, codes in sample_images_tensor:
        for i in range(imgs.shape[0]):
            if sample_count >= args.gradcam_samples:
                break
            single_img_tensor = imgs[i:i+1].to(device)
            true_label = int(labels[i].item())
            code = codes[i]

            # Reconstruct uint8 RGB image for visualization
            # Denormalize ImageNet
            img_np = single_img_tensor.squeeze(0).permute(1, 2, 0).cpu().numpy()
            img_np = (img_np * np.array([0.229, 0.224, 0.225])) + np.array([0.485, 0.456, 0.406])
            img_np = np.clip(img_np * 255.0, 0, 255).astype(np.uint8)

            result = gradcam_engine.explain(
                input_tensor=single_img_tensor,
                base_image_uint8=img_np,
                save_dir=str(gradcam_dir),
                filename_prefix=f"sample_{code}_class_{true_label}",
            )
            saved_gradcam_files.append(result["overlay_path"])
            sample_count += 1

    logger.info(f"Successfully generated {len(saved_gradcam_files)} Grad-CAM overlay heatmaps in: {gradcam_dir}")

    # Print Summary Table to console
    print("\n" + "=" * 65)
    print("      DIABETIC RETINOPATHY EVALUATION REPORT (SIH26038)")
    print("=" * 65)
    print(f"Overall Accuracy:       {summary_metrics['accuracy'] * 100:.2f}%")
    print(f"Macro Recall:           {summary_metrics['recall_macro']:.4f}")
    print(f"Macro F1 Score:         {summary_metrics['f1_macro']:.4f}")
    print(f"Quadratic Weighted Kappa:{summary_metrics['qwk']:.4f}")
    print(f"Macro ROC-AUC:          {summary_metrics['roc_auc']:.4f}")
    print(f"Expected Calib. Error:  {summary_metrics['ece_calibrated']:.4f} (Calibrated)")
    print("-" * 65)
    print(f"{'Class':<22} | {'Sens (Recall)':<14} | {'Spec':<8} | {'F1':<8} | {'Support':<8}")
    print("-" * 65)
    for c_name, m in per_class_table.items():
        print(f"{c_name:<22} | {m['sensitivity_recall']:<14.3f} | {m['specificity']:<8.3f} | {m['f1_score']:<8.3f} | {m['support']:<8}")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    main()
