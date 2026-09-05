"""Standalone single-image inference CLI for Diabetic Retinopathy screening."""

import argparse
import json
import sys
from pathlib import Path

from dr_screening.inference.predictor import FundusPredictor


def parse_args():
    parser = argparse.ArgumentParser(description="Run Diabetic Retinopathy Screening Inference on Retinal Image")
    parser.add_argument("--image", type=str, required=True, help="Path to retinal fundus image")
    parser.add_argument("--checkpoint", type=str, default="outputs/checkpoints/best_model.pth", help="Model checkpoint")
    parser.add_argument("--temperature", type=float, default=1.0, help="Confidence calibration temperature")
    parser.add_argument("--save-heatmap", action="store_true", default=True, help="Generate and save Grad-CAM heatmap")
    parser.add_argument("--output-json", type=str, default=None, help="Optional path to save JSON output")
    parser.add_argument("--device", type=str, default="cpu", help="Compute device ('cpu' or 'cuda')")
    return parser.parse_args()


def main():
    args = parse_args()

    image_path = Path(args.image)
    if not image_path.exists():
        print(json.dumps({"error": f"Image file not found: {args.image}"}, indent=2))
        sys.exit(1)

    ckpt_path = Path(args.checkpoint)
    if not ckpt_path.exists():
        print(json.dumps({"error": f"Checkpoint file not found: {args.checkpoint}"}, indent=2))
        sys.exit(1)

    predictor = FundusPredictor(
        checkpoint_path=str(ckpt_path),
        temperature=args.temperature,
        device=args.device,
    )

    result = predictor.predict(
        image_source=str(image_path),
        generate_heatmap=args.save_heatmap,
        save_dir="outputs/gradcam",
        image_name=image_path.stem,
    )

    # Print formatted JSON to stdout
    json_output = json.dumps(result, indent=2)
    print(json_output)

    if args.output_json:
        out_p = Path(args.output_json)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        with open(out_p, "w", encoding="utf-8") as f:
            f.write(json_output)


if __name__ == "__main__":
    main()
