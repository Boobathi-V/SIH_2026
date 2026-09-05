"""ONNX Export and Numerical Parity Verification Engine."""

from pathlib import Path
from typing import Tuple, Optional
import numpy as np
import torch
import torch.nn as nn
import onnx
import onnxruntime as ort

from dr_screening.configs.constants import DEFAULT_IMAGE_SIZE


def export_to_onnx(
    model: nn.Module,
    output_path: str = "outputs/exports/dr_screening_model.onnx",
    image_size: Tuple[int, int] = DEFAULT_IMAGE_SIZE,
    opset_version: int = 17,
    device: str = "cpu",
) -> str:
    """Export PyTorch DR model to optimized ONNX graph with dynamic batch dimension.

    Args:
        model: PyTorch DRScreeningModel in eval mode.
        output_path: Target path for the .onnx file.
        image_size: Input spatial dimensions (H, W).
        opset_version: ONNX operator set version.
        device: Device to use during export.

    Returns:
        Absolute string path to exported ONNX file.
    """
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    model = model.to(device)
    model.eval()

    dummy_input = torch.randn(1, 3, image_size[0], image_size[1], device=device)

    # Export using PyTorch ONNX exporter (prefer classic TorchScript exporter for maximum compatibility)
    try:
        torch.onnx.export(
            model,
            dummy_input,
            str(out_file),
            export_params=True,
            opset_version=opset_version,
            do_constant_folding=True,
            input_names=["input"],
            output_names=["logits"],
            dynamic_axes={
                "input": {0: "batch_size"},
                "logits": {0: "batch_size"},
            },
            dynamo=False,
        )
    except TypeError:
        # Fallback if dynamo parameter is not supported
        torch.onnx.export(
            model,
            dummy_input,
            str(out_file),
            export_params=True,
            opset_version=opset_version,
            do_constant_folding=True,
            input_names=["input"],
            output_names=["logits"],
            dynamic_axes={
                "input": {0: "batch_size"},
                "logits": {0: "batch_size"},
            },
        )

    # Verify ONNX structure integrity
    onnx_model = onnx.load(str(out_file))
    onnx.checker.check_model(onnx_model)

    return str(out_file)


def verify_onnx_parity(
    pytorch_model: nn.Module,
    onnx_path: str,
    image_size: Tuple[int, int] = DEFAULT_IMAGE_SIZE,
    tolerance: float = 1e-4,
) -> float:
    """Check that PyTorch and ONNX Runtime produce identical numerical output logits.

    Returns:
        Maximum absolute error between PyTorch and ONNX Runtime predictions.
    """
    pytorch_model.eval()
    dummy_input = torch.randn(1, 3, image_size[0], image_size[1])

    # PyTorch inference
    with torch.no_grad():
        pt_out = pytorch_model(dummy_input).cpu().numpy()

    # ONNX Runtime inference
    session = ort.InferenceSession(onnx_path, providers=["CPUExecutionProvider"])
    ort_inputs = {session.get_inputs()[0].name: dummy_input.numpy()}
    ort_out = session.run(None, ort_inputs)[0]

    max_diff = float(np.max(np.abs(pt_out - ort_out)))
    if max_diff > tolerance:
        raise ValueError(f"ONNX parity check failed! Max difference {max_diff:.6f} exceeds tolerance {tolerance}")

    return max_diff
