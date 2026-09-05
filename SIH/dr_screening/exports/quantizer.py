"""Dynamic INT8 Quantization and CPU Latency Benchmarking."""

import os
import time
from pathlib import Path
from typing import Dict, Tuple
import numpy as np
import torch
import torch.nn as nn
import onnxruntime as ort
from onnxruntime.quantization import quantize_dynamic, QuantType


def quantize_onnx_model(
    input_onnx_path: str,
    output_onnx_path: str = "outputs/exports/dr_screening_model_int8.onnx",
) -> str:
    """Apply dynamic INT8 quantization to ONNX model.

    Drastically reduces model size (often by 3x-4x) and speeds up CPU inference.

    Args:
        input_onnx_path: Path to float32 ONNX model.
        output_onnx_path: Target path for quantized INT8 model.

    Returns:
        Path to quantized ONNX file.
    """
    out_file = Path(output_onnx_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    quantize_dynamic(
        model_input=input_onnx_path,
        model_output=str(out_file),
        weight_type=QuantType.QInt8,
    )
    return str(out_file)


def benchmark_pytorch_cpu(
    model: nn.Module,
    input_shape: Tuple[int, int, int, int] = (1, 3, 384, 384),
    num_iterations: int = 15,
    warmup: int = 3,
) -> Dict[str, float]:
    """Measure PyTorch CPU latency."""
    model.eval()
    dummy = torch.randn(*input_shape)

    # Warmup
    for _ in range(warmup):
        with torch.no_grad():
            _ = model(dummy)

    latencies = []
    for _ in range(num_iterations):
        t0 = time.perf_counter()
        with torch.no_grad():
            _ = model(dummy)
        latencies.append((time.perf_counter() - t0) * 1000.0)

    mean_ms = float(np.mean(latencies))
    std_ms = float(np.std(latencies))
    return {
        "mean_latency_ms": mean_ms,
        "std_latency_ms": std_ms,
        "fps": 1000.0 / mean_ms if mean_ms > 0 else 0.0,
    }


def benchmark_onnx_cpu(
    onnx_path: str,
    input_shape: Tuple[int, int, int, int] = (1, 3, 384, 384),
    num_iterations: int = 15,
    warmup: int = 3,
) -> Dict[str, float]:
    """Measure ONNX Runtime CPU latency."""
    session = ort.InferenceSession(onnx_path, providers=["CPUExecutionProvider"])
    input_name = session.get_inputs()[0].name
    dummy = np.random.randn(*input_shape).astype(np.float32)

    # Warmup
    for _ in range(warmup):
        _ = session.run(None, {input_name: dummy})

    latencies = []
    for _ in range(num_iterations):
        t0 = time.perf_counter()
        _ = session.run(None, {input_name: dummy})
        latencies.append((time.perf_counter() - t0) * 1000.0)

    mean_ms = float(np.mean(latencies))
    std_ms = float(np.std(latencies))
    size_mb = os.path.getsize(onnx_path) / (1024 * 1024)

    return {
        "mean_latency_ms": mean_ms,
        "std_latency_ms": std_ms,
        "fps": 1000.0 / mean_ms if mean_ms > 0 else 0.0,
        "size_mb": size_mb,
    }
