"""Explainable AI: High-resolution Grad-CAM visual heatmaps for Diabetic Retinopathy."""

from pathlib import Path
from typing import Tuple, Optional, Dict, Any
import cv2
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


class RetinalGradCAM:
    """Gradient-weighted Class Activation Mapping (Grad-CAM) engine for retinal fundus models."""

    def __init__(self, model: nn.Module, target_layer: Optional[nn.Module] = None):
        self.model = model
        self.model.eval()

        if target_layer is None and hasattr(model, "get_gradcam_target_layer"):
            self.target_layer = model.get_gradcam_target_layer()
        else:
            self.target_layer = target_layer

        if self.target_layer is None:
            raise ValueError("Target convolutional layer for Grad-CAM could not be resolved.")

        self.gradients = None
        self.activations = None
        self._register_hooks()

    def _register_hooks(self) -> None:
        """Register forward and backward hooks to capture feature maps and gradients."""
        def forward_hook(module, input, output):
            self.activations = output

        def backward_hook(module, grad_in, grad_out):
            self.gradients = grad_out[0]

        self.target_layer.register_forward_hook(forward_hook)
        self.target_layer.register_full_backward_hook(backward_hook)

    def generate(
        self,
        input_tensor: torch.Tensor,
        target_class: Optional[int] = None,
    ) -> np.ndarray:
        """Generate raw 2D Grad-CAM activation map [0.0, 1.0].

        Args:
            input_tensor: Tensor of shape (1, 3, H, W).
            target_class: Integer index of target DR class. If None, uses top predicted class.

        Returns:
            Normalized 2D float32 numpy array with shape (H, W).
        """
        self.model.zero_grad()
        output_logits = self.model(input_tensor) # (1, num_classes)

        if target_class is None:
            target_class = int(torch.argmax(output_logits, dim=-1).item())

        score = output_logits[0, target_class]
        score.backward(retain_graph=True)

        # Gradients: (1, C, h, w)
        gradients = self.gradients
        activations = self.activations

        # Global average pooling over spatial dimensions to get alpha weights: (1, C, 1, 1)
        weights = torch.mean(gradients, dim=(2, 3), keepdim=True)

        # Weighted combination of forward activation maps
        cam = torch.sum(weights * activations, dim=1, keepdim=True) # (1, 1, h, w)

        # ReLU to focus on features having a positive influence
        cam = F.relu(cam)

        # Upsample to input image dimensions
        cam = F.interpolate(
            cam,
            size=(input_tensor.shape[2], input_tensor.shape[3]),
            mode="bilinear",
            align_corners=False,
        )

        cam_np = cam.squeeze().detach().cpu().numpy()

        # Min-max normalization
        cam_min, cam_max = cam_np.min(), cam_np.max()
        if cam_max - cam_min > 1e-8:
            cam_norm = (cam_np - cam_min) / (cam_max - cam_min)
        else:
            cam_norm = np.zeros_like(cam_np)

        return cam_norm

    def create_overlay(
        self,
        raw_activation: np.ndarray,
        base_image: np.ndarray,
        alpha: float = 0.55,
        colormap: int = cv2.COLORMAP_JET,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Create colored heatmap and blended overlay on base retinal image.

        Args:
            raw_activation: 2D float32 array in [0, 1] with shape (H, W).
            base_image: uint8 RGB numpy array (H, W, 3).
            alpha: Transparency factor for heatmap overlay (0.0 to 1.0).
            colormap: OpenCV colormap (default: JET).

        Returns:
            (heatmap_rgb, overlay_rgb)
        """
        # Convert activation map to 8-bit image [0, 255]
        heatmap_gray = np.uint8(255 * raw_activation)

        # Apply colormap (yields BGR)
        heatmap_bgr = cv2.applyColorMap(heatmap_gray, colormap)
        heatmap_rgb = cv2.cvtColor(heatmap_bgr, cv2.COLOR_BGR2RGB)

        # Ensure base image is same size
        if base_image.shape[:2] != raw_activation.shape[:2]:
            base_image = cv2.resize(base_image, (raw_activation.shape[1], raw_activation.shape[0]))

        # Alpha blend overlay
        overlay = cv2.addWeighted(base_image, 1.0 - alpha, heatmap_rgb, alpha, 0)
        return heatmap_rgb, overlay

    def explain(
        self,
        input_tensor: torch.Tensor,
        base_image_uint8: np.ndarray,
        target_class: Optional[int] = None,
        save_dir: Optional[str] = "outputs/gradcam",
        filename_prefix: str = "sample",
    ) -> Dict[str, Any]:
        """Generate and optionally save all explainability outputs.

        Returns:
            Dictionary containing:
            - 'raw_cam': 2D float numpy array
            - 'heatmap': uint8 RGB numpy array
            - 'overlay': uint8 RGB numpy array
            - 'heatmap_path': str or None
            - 'overlay_path': str or None
        """
        raw_cam = self.generate(input_tensor, target_class=target_class)
        heatmap_rgb, overlay_rgb = self.create_overlay(raw_cam, base_image_uint8)

        heatmap_path = None
        overlay_path = None

        if save_dir:
            out_dir = Path(save_dir)
            out_dir.mkdir(parents=True, exist_ok=True)

            heatmap_file = out_dir / f"{filename_prefix}_heatmap.jpg"
            overlay_file = out_dir / f"{filename_prefix}_overlay.jpg"

            cv2.imwrite(str(heatmap_file), cv2.cvtColor(heatmap_rgb, cv2.COLOR_RGB2BGR))
            cv2.imwrite(str(overlay_file), cv2.cvtColor(overlay_rgb, cv2.COLOR_RGB2BGR))

            heatmap_path = str(heatmap_file)
            overlay_path = str(overlay_file)

        return {
            "raw_cam": raw_cam,
            "heatmap": heatmap_rgb,
            "overlay": overlay_rgb,
            "heatmap_path": heatmap_path,
            "overlay_path": overlay_path,
        }
