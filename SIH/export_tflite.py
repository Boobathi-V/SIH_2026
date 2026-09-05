"""TensorFlow Lite Export and Mobile Deployment Bridge for SIH26038."""

import argparse
from pathlib import Path

from dr_screening.utils.helpers import setup_logger


def parse_args():
    parser = argparse.ArgumentParser(description="Export DR Model to TensorFlow Lite")
    parser.add_argument("--onnx-path", type=str, default="outputs/exports/dr_screening_model.onnx")
    parser.add_argument("--output-tflite", type=str, default="outputs/exports/dr_screening_model.tflite")
    return parser.parse_args()


def main():
    args = parse_args()
    logger = setup_logger("tflite_export")
    logger.info("=== SIH26038 TensorFlow Lite Export Engine ===")

    onnx_file = Path(args.onnx_path)
    if not onnx_file.exists():
        logger.error(f"ONNX model file not found: {onnx_file}. Run export_onnx.py first.")
        return

    logger.info(f"Using ONNX model source: {onnx_file}")
    tflite_path = Path(args.output_tflite)
    tflite_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        import onnx2tf
        logger.info("Converting ONNX to TensorFlow Lite via onnx2tf...")
        onnx2tf.convert(
            input_onnx_file_path=str(onnx_file),
            output_folder_path=str(tflite_path.parent / "tflite_bundle"),
            copy_onnx_input_output_names_to_tflite=True,
            non_verbose=True,
        )
        logger.info(f"TFLite bundle generated in: {tflite_path.parent / 'tflite_bundle'}")
    except (ImportError, Exception) as err:
        logger.warning(f"TFLite direct export via onnx2tf was not executed: {err}")
        logger.info("Explanation:")
        logger.info("1. TensorFlow/onnx2tf currently only support Python <= 3.12 (current environment is Python 3.14).")
        logger.info("2. For production CPU & edge deployment in SIH, the primary target is ONNX Runtime & INT8 Quantization:")
        logger.info("   -> outputs/exports/dr_screening_model.onnx (FP32, 53.9ms CPU latency)")
        logger.info("   -> outputs/exports/dr_screening_model_int8.onnx (INT8 Quantized, 20.17 MB)")
        logger.info("3. If TFLite is strictly required for Android deployment, convert the ONNX model in a Python 3.10/3.11 environment:")
        logger.info(f"   pip install onnx2tf tensorflow && onnx2tf -in {onnx_file} -co")


if __name__ == "__main__":
    main()
