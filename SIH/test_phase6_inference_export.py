"""Phase 6 Verification: Test predict.py clinical JSON, ONNX export, INT8 quantization, and latency."""

import os
from pathlib import Path
import subprocess
import json
import time


def test_phase6():
    print("=== Phase 6: Inference and ONNX Export Verification ===")

    # 1. Test predict.py on a sample image
    sample_img = "datasets/aptos/train_images/syn_dr_2_000.png"
    ckpt_path = "outputs/checkpoints/best_model.pth"
    assert os.path.exists(sample_img), f"Sample image {sample_img} not found."
    assert os.path.exists(ckpt_path), f"Checkpoint {ckpt_path} not found."

    print(f"Running predict.py on: {sample_img}...")
    t0 = time.perf_counter()
    predict_cmd = [
        "python",
        "predict.py",
        "--image",
        sample_img,
        "--checkpoint",
        ckpt_path,
        "--device",
        "cpu",
    ]
    proc = subprocess.run(predict_cmd, capture_output=True, text=True)
    latency_sec = time.perf_counter() - t0

    if proc.returncode != 0:
        print("STDERR:", proc.stderr)
    assert proc.returncode == 0, f"predict.py failed with code {proc.returncode}"

    # Parse stdout JSON
    pred_data = json.loads(proc.stdout)
    print(f"[OK] Prediction JSON output received ({latency_sec:.2f}s total execution):")
    print(json.dumps(pred_data, indent=2))

    assert "prediction" in pred_data
    assert "class_index" in pred_data
    assert "confidence" in pred_data
    assert "probabilities" in pred_data
    assert len(pred_data["probabilities"]) == 5
    assert "heatmap_path" in pred_data
    assert "risk_level" in pred_data
    assert os.path.exists(pred_data["heatmap_path"]), f"Heatmap file {pred_data['heatmap_path']} does not exist!"
    print(f"[OK] Heatmap overlay verified on disk at: {pred_data['heatmap_path']}")

    # 2. Test export_onnx.py and Quantization
    print("\nRunning export_onnx.py and INT8 Quantization...")
    export_cmd = [
        "python",
        "export_onnx.py",
        "--checkpoint",
        ckpt_path,
        "--num-benchmark-runs",
        "5",
    ]
    export_proc = subprocess.run(export_cmd, capture_output=True, text=True)
    print(export_proc.stdout)
    if export_proc.returncode != 0:
        print("STDERR:", export_proc.stderr)
    assert export_proc.returncode == 0, f"export_onnx.py failed with code {export_proc.returncode}"

    # Verify exported ONNX models
    fp32_onnx = Path("outputs/exports/dr_screening_model.onnx")
    int8_onnx = Path("outputs/exports/dr_screening_model_int8.onnx")

    assert fp32_onnx.exists(), "Missing dr_screening_model.onnx"
    assert int8_onnx.exists(), "Missing dr_screening_model_int8.onnx"

    fp32_size_mb = fp32_onnx.stat().st_size / (1024 * 1024)
    int8_size_mb = int8_onnx.stat().st_size / (1024 * 1024)

    print(f"[OK] ONNX FP32 Model:      {fp32_onnx} ({fp32_size_mb:.2f} MB)")
    print(f"[OK] ONNX INT8 Quantized:  {int8_onnx} ({int8_size_mb:.2f} MB)")
    assert int8_size_mb < fp32_size_mb, "Quantized model size should be strictly smaller than FP32"

    print("=== Phase 6 Inference, ONNX Export & INT8 Quantization Complete & Verified! ===")


if __name__ == "__main__":
    test_phase6()
