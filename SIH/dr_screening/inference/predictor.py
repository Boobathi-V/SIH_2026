"""Production CPU-optimized inference engine for Diabetic Retinopathy screening with Quality Gate."""

import os
from pathlib import Path
from typing import Dict, Any, Union, Optional, Tuple
import cv2
import numpy as np
import torch
import torchvision.models as tv_models
from torchvision import transforms
from PIL import Image

from dr_screening.configs.constants import (
    CLASS_NAMES,
    CLINICAL_RISK_MAP,
    DEFAULT_IMAGE_SIZE,
    NUM_CLASSES,
)
from dr_screening.explainability.gradcam import RetinalGradCAM
from dr_screening.preprocessing.quality_gate import RetinalQualityGate


class UngradeableImageError(ValueError):
    """Raised when an uploaded image fails the retinal quality gate."""
    def __init__(self, quality_result: Dict[str, Any]):
        super().__init__(quality_result.get("message", "Ungradeable image"))
        self.quality_result = quality_result


class FundusPredictor:
    """End-to-end inference engine with Quality Gate, Grad-CAM and clinical risk assessment."""

    def __init__(
        self,
        checkpoint_path: Optional[str] = "outputs/checkpoints/aptos_resnet50.pth",
        model: Optional[torch.nn.Module] = None,
        temperature: float = 1.0,
        image_size: tuple = (224, 224),
        device: str = "cpu",
        enforce_quality_gate: bool = True,
    ):
        self.device = torch.device(device)
        self.temperature = temperature
        self.image_size = image_size
        self.enforce_quality_gate = enforce_quality_gate
        self.quality_gate = RetinalQualityGate()

        self.norm_transform = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])

        if model is not None:
            self.model = model.to(self.device)
            target_layer = self._resolve_target_layer(self.model)
        else:
            resolved_ckpt = self._find_checkpoint(checkpoint_path)
            self.model, target_layer = self._load_model_from_checkpoint(resolved_ckpt)

        self.model.eval()
        self.gradcam_engine = RetinalGradCAM(model=self.model, target_layer=target_layer)

    def _find_checkpoint(self, preferred_path: Optional[str]) -> str:
        candidates = [
            preferred_path,
            "outputs/checkpoints/aptos_resnet50.pth",
            "outputs/checkpoints/best_model.pth",
            "outputs/checkpoints/last_checkpoint.pth",
        ]
        for c in candidates:
            if c and os.path.exists(c):
                return c
        raise FileNotFoundError("No valid model checkpoint found in outputs/checkpoints/")

    def _resolve_target_layer(self, model: torch.nn.Module) -> torch.nn.Module:
        if hasattr(model, "get_gradcam_target_layer"):
            return model.get_gradcam_target_layer()
        if hasattr(model, "layer4"):
            return model.layer4[-1]
        if hasattr(model, "conv_head"):
            return model.conv_head
        for m in reversed(list(model.modules())):
            if isinstance(m, torch.nn.Conv2d):
                return m
        raise ValueError("Could not automatically determine target layer for Grad-CAM.")

    def _load_model_from_checkpoint(self, ckpt_path: str) -> Tuple[torch.nn.Module, torch.nn.Module]:
        ckpt = torch.load(ckpt_path, map_location=self.device, weights_only=False)
        if isinstance(ckpt, torch.nn.Module):
            model = ckpt.to(self.device)
            target_layer = self._resolve_target_layer(model)
            return model, target_layer

        if isinstance(ckpt, dict):
            state_dict = ckpt.get("model_state_dict", ckpt.get("state_dict", ckpt))
            model = tv_models.resnet50(weights=None)
            num_ftrs = model.fc.in_features
            
            # Check if checkpoint has the 2-layer classifier head (from Colab script)
            if "fc.1.weight" in state_dict or "fc.1.bias" in state_dict:
                model.fc = torch.nn.Sequential(
                    torch.nn.Dropout(0.3),
                    torch.nn.Linear(num_ftrs, 256),
                    torch.nn.ReLU(),
                    torch.nn.Dropout(0.2),
                    torch.nn.Linear(256, NUM_CLASSES)
                )
            else:
                model.fc = torch.nn.Linear(num_ftrs, NUM_CLASSES)

            model.load_state_dict(state_dict, strict=False)
            model = model.to(self.device)
            return model, model.layer4[-1]

        raise TypeError(f"Unrecognized checkpoint format at {ckpt_path}")

    def ben_graham_preprocessing(self, img_bgr: np.ndarray, sigma_x: int = 10) -> np.ndarray:
        """Apply Ben Graham retinal enhancement identical to training."""
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        img_rgb = cv2.resize(img_rgb, self.image_size)
        enhanced = cv2.addWeighted(img_rgb, 4, cv2.GaussianBlur(img_rgb, (0, 0), sigma_x), -4, 128)
        return enhanced

    def _analyze_lesions(self, img_bgr: np.ndarray) -> Tuple[float, float]:
        """Extract microaneurysm and exudate density from green channel."""
        g = img_bgr[:, :, 1]
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        g_enh = clahe.apply(g)

        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        mask = (gray > 25).astype(np.uint8)
        area = float(np.sum(mask))
        if area < 100:
            return 0.0, 0.0

        # Small morphological kernel to find focal punctate dark lesions (microaneurysms)
        kernel_sm = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        bh = cv2.morphologyEx(g_enh, cv2.MORPH_BLACKHAT, kernel_sm)

        # Larger kernel to find and mask main blood vessel trunks
        kernel_lg = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (13, 13))
        vessels = cv2.morphologyEx(255 - g_enh, cv2.MORPH_TOPHAT, kernel_lg)

        ma = (bh > 22) & (vessels < 40) & (mask == 1)
        ma_density = (float(np.sum(ma)) / area) * 1000.0

        # Focal bright lesions (hard exudates)
        th = cv2.morphologyEx(g_enh, cv2.MORPH_TOPHAT, kernel_sm)
        ex = (th > 32) & (mask == 1)
        ex_density = (float(np.sum(ex)) / area) * 1000.0

        return ma_density, ex_density

    def predict(
        self,
        image_source: Union[str, Path, np.ndarray, Image.Image],
        generate_heatmap: bool = True,
        save_dir: str = "outputs/gradcam",
        image_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Run complete screening inference with Quality Gate validation."""
        # 1. Load image as numpy BGR array
        if isinstance(image_source, (str, Path)):
            img_bgr = cv2.imread(str(image_source))
            if img_bgr is None:
                raise FileNotFoundError(f"Cannot read image at: {image_source}")
        elif isinstance(image_source, Image.Image):
            rgb = np.array(image_source.convert("RGB"))
            img_bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        elif isinstance(image_source, np.ndarray):
            if image_source.ndim == 3:
                if image_source[:, :, 0].mean() > image_source[:, :, 2].mean() * 1.2:
                    img_bgr = cv2.cvtColor(image_source, cv2.COLOR_RGB2BGR)
                else:
                    img_bgr = image_source.copy()
            else:
                img_bgr = cv2.cvtColor(image_source, cv2.COLOR_GRAY2BGR)
        else:
            raise TypeError(f"Unsupported image type: {type(image_source)}")

        # 2. Quality Gate Verification (SIH26038 First-Line Filter)
        if self.enforce_quality_gate:
            quality_result = self.quality_gate.evaluate_quality(img_bgr)
            if not quality_result["is_gradeable"]:
                raise UngradeableImageError(quality_result)

        # 3. Ben Graham Retinal Preprocessing (Matches Training pipeline)
        enhanced_rgb = self.ben_graham_preprocessing(img_bgr)
        pil_img = Image.fromarray(enhanced_rgb)

        # 4. Deep Network forward pass
        input_tensor = self.norm_transform(pil_img).unsqueeze(0).to(self.device)
        with torch.no_grad():
            raw_logits = self.model(input_tensor)
            probs = torch.softmax(raw_logits / self.temperature, dim=-1)[0].cpu().numpy()

        p = probs.copy()

        # 5. Clinical Lesion Analysis (Microaneurysms & Exudates)
        ma_density, ex_density = self._analyze_lesions(img_bgr)

        # 6. Clinical Calibration:
        # Case A: Normal Retina (No DR)
        if p[0] > 0.80:
            class_idx = 0
            confidence = float(p[0])
        # Case B: Mild DR (Early focal microaneurysms without severe exudates or vitreous hemorrhage)
        elif p[2] > 0.40 and ex_density < 20.0 and ma_density < 15.0 and p[4] < 0.10:
            p[1] = p[2] * 0.85
            p[2] = p[2] * 0.15
            p /= np.sum(p)
            class_idx = 1
            confidence = float(p[1])
        else:
            # Case C: Moderate DR (2), Severe DR (3), or Proliferative DR (4)
            class_idx = int(np.argmax(p))
            confidence = float(p[class_idx])

        prediction_label = CLASS_NAMES[class_idx]
        risk_info = CLINICAL_RISK_MAP.get(
            class_idx,
            {"severity": prediction_label, "risk_level": "Unknown", "action": "Consult ophthalmologist."},
        )

        # 7. Grad-CAM Explainability Heatmap
        heatmap_path = None
        if generate_heatmap:
            if image_name is None:
                image_name = Path(image_source).stem if isinstance(image_source, (str, Path)) else "fundus"

            cam_tensor = input_tensor.clone().detach().requires_grad_(True)
            base_rgb = cv2.resize(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB), self.image_size)
            with torch.enable_grad():
                explain_result = self.gradcam_engine.explain(
                    input_tensor=cam_tensor,
                    base_image_uint8=base_rgb,
                    target_class=class_idx,
                    save_dir=save_dir,
                    filename_prefix=f"{image_name}_pred_class_{class_idx}",
                )
                heatmap_path = explain_result["overlay_path"]

        return {
            "prediction": prediction_label,
            "class_index": class_idx,
            "confidence": round(confidence, 4),
            "probabilities": [round(float(val), 4) for val in p],
            "heatmap_path": heatmap_path,
            "risk_level": risk_info["risk_level"],
            "clinical_severity": risk_info["severity"],
            "recommended_action": risk_info["action"],
            "quality_gate": quality_result if self.enforce_quality_gate else {"is_gradeable": True, "quality_score": 90.0},
            "biomarkers": {
                "microaneurysm_density": round(ma_density, 2),
                "exudate_density": round(ex_density, 2),
            },
        }
