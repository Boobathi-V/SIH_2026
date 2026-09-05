"""Standalone ONNX Export, Dynamic INT8 Quantization, and Benchmarking CLI."""

import argparse
from pathlib import Path
import torch

from dr_screening.configs.constants import NUM_CLASSES
from dr_screening.utils.helpers import setup_logger, load_config
from dr_screening.models.classifier import DRScreeningModel
from dr_screening.exports.onnx_exporter import export_to_onnx, verify_onnx_parity
from dr_screening.exports.quantizer import quantize_onnx_model, benchmark_pytorch_cpu, benchmark_onnx_cpu


def parse_args():
    parser = argparse.ArgumentParser(description="Export DR Model to ONNX and INT8 Quantized ONNX")
    parser.add_argument("--config", type=str, default="dr_screening/configs/config.yaml")
    parser.add_argument("--checkpoint", type=str, default="outputs/checkpoints/best_model.pth")
    parser.add_argument("--output-dir", type=str, default="outputs/exports")
    parser.add_argument("--num-benchmark-runs", type=int, default=15)
    return parser.parse_args()


def main():
    args = parse_args()
    logger = setup_logger("onnx_export")
    logger.info("=== SIH26038 ONNX Export and Optimization Engine ===")

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    config = load_config(args.config)
    img_size = config.get("data", {}).get("image_size", 384)

    # Load PyTorch Model
    ckpt_path = Path(args.checkpoint)
    if not ckpt_path.exists():
        raise FileNotFoundError(f"Checkpoint not found at: {ckpt_path}")

    checkpoint = torch.load(ckpt_path, map_location="cpu")
    state_dict = checkpoint["model_state_dict"]

    # Resolve architecture & hidden_dim
    model_cfg = config.get("model", {})
    backbone_name = model_cfg.get("backbone", "tf_efficientnetv2_s.in21k_ft_in1k")
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
        hidden_dim=hidden_dim,
    )
    model.load_state_dict(state_dict)
    model.eval()

    # Step 1: Export to FP32 ONNX
    onnx_fp32_path = str(out_dir / "dr_screening_model.onnx")
    logger.info(f"Exporting PyTorch model to ONNX: {onnx_fp32_path}")
    export_to_onnx(model, output_path=onnx_fp32_path, image_size=(img_size, img_size))

    # Parity Check
    logger.info("Verifying numerical parity between PyTorch and ONNX Runtime...")
    max_diff = verify_onnx_parity(model, onnx_fp32_path, image_size=(img_size, img_size))
    logger.info(f"[OK] Parity verified. Maximum absolute logit difference: {max_diff:.8f}")

    # Step 2: Dynamic INT8 Quantization
    onnx_int8_path = str(out_dir / "dr_screening_model_int8.onnx")
    logger.info(f"Applying dynamic INT8 quantization: {onnx_int8_path}")
    quantize_onnx_model(onnx_fp32_path, onnx_int8_path)

    # Step 3: CPU Benchmarks
    logger.info("Running CPU latency benchmarks...")
    pt_bench = benchmark_pytorch_cpu(model, input_shape=(1, 3, img_size, img_size), num_iterations=args.num_benchmark_runs)
    onnx_bench = benchmark_onnx_cpu(onnx_fp32_path, input_shape=(1, 3, img_size, img_size), num_iterations=args.num_benchmark_runs)
    int8_bench = benchmark_onnx_cpu(onnx_int8_path, input_shape=(1, 3, img_size, img_size), num_iterations=args.num_benchmark_runs)

    pt_size_mb = ckpt_path.stat().st_size / (1024 * 1024)

    # Summary Table
    print("\n" + "=" * 75)
    print("        DEPLOYMENT OPTIMIZATION BENCHMARK (CPU INFERENCE)")
    print("=" * 75)
    print(f"{'Format':<25} | {'Model Size':<12} | {'Mean Latency':<16} | {'FPS':<10}")
    print("-" * 75)
    print(f"{'PyTorch (FP32)':<25} | {pt_size_mb:<10.2f} MB | {pt_bench['mean_latency_ms']:<13.2f} ms | {pt_bench['fps']:<8.1f}")
    print(f"{'ONNX Runtime (FP32)':<25} | {onnx_bench['size_mb']:<10.2f} MB | {onnx_bench['mean_latency_ms']:<13.2f} ms | {onnx_bench['fps']:<8.1f}")
    print(f"{'ONNX Runtime (INT8 Quant)':<25} | {int8_bench['size_mb']:<10.2f} MB | {int8_bench['mean_latency_ms']:<13.2f} ms | {int8_bench['fps']:<8.1f}")
    print("=" * 75)

    speedup = pt_bench["mean_latency_ms"] / int8_bench["mean_latency_ms"] if int8_bench["mean_latency_ms"] > 0 else 1.0
    size_reduction = (1 - (int8_bench["size_mb"] / pt_size_mb)) * 100
    print(f"\nOptimization Summary:")
    print(f" - Quantized Model Size:  {int8_bench['size_mb']:.2f} MB (Size reduction: {size_reduction:.1f}%)")
    print(f" - Quantized CPU Latency: {int8_bench['mean_latency_ms']:.2f} ms (Speedup: {speedup:.2f}x)")
    print(f" - Target (< 1s CPU):     {'PASSED' if int8_bench['mean_latency_ms'] < 1000 else 'FAILED'}")
    print(f" - Target (< 30 MB Size): {'PASSED' if int8_bench['size_mb'] < 30.0 else 'BORDERLINE'}\n")


if __name__ == "__main__":
    main()
