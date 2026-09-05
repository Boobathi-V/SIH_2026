"""Production Diabetic Retinopathy screening model with multi-stage unfreezing and Grad-CAM hooks."""

from typing import Tuple, Optional
import torch
import torch.nn as nn

from dr_screening.configs.constants import NUM_CLASSES, DEFAULT_BACKBONE
from dr_screening.models.backbones import create_backbone


class DRScreeningModel(nn.Module):
    """Deep learning model for Diabetic Retinopathy 5-class severity classification."""

    def __init__(
        self,
        backbone_name: str = DEFAULT_BACKBONE,
        num_classes: int = NUM_CLASSES,
        pretrained: bool = True,
        dropout_rate: float = 0.3,
        hidden_dim: Optional[int] = None,
    ):
        super().__init__()
        self.backbone_name = backbone_name
        self.num_classes = num_classes

        # Create backbone and identify Grad-CAM hook layer
        self.backbone, self.feature_dim, self.gradcam_layer = create_backbone(
            backbone_name=backbone_name,
            pretrained=pretrained,
            in_chans=3,
        )

        # Classification Head
        if hidden_dim is not None and hidden_dim > 0:
            self.head = nn.Sequential(
                nn.LayerNorm(self.feature_dim),
                nn.Dropout(p=dropout_rate),
                nn.Linear(self.feature_dim, hidden_dim),
                nn.SiLU(),
                nn.Dropout(p=dropout_rate / 2),
                nn.Linear(hidden_dim, num_classes),
            )
        else:
            self.head = nn.Sequential(
                nn.LayerNorm(self.feature_dim),
                nn.Dropout(p=dropout_rate),
                nn.Linear(self.feature_dim, num_classes),
            )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass generating raw class logits: (B, 3, H, W) -> (B, num_classes)."""
        features = self.backbone(x)
        logits = self.head(features)
        return logits

    def extract_features(self, x: torch.Tensor) -> torch.Tensor:
        """Extract bottleneck embedding vector for clustering or visualization."""
        return self.backbone(x)

    def get_gradcam_target_layer(self) -> nn.Module:
        """Return target convolutional layer for Grad-CAM explainability."""
        return self.gradcam_layer

    def freeze_backbone(self, freeze: bool = True) -> None:
        """Stage 1: Freeze all backbone layers to train only the classification head."""
        for param in self.backbone.parameters():
            param.requires_grad = not freeze

        # Ensure head parameters always require gradients
        for param in self.head.parameters():
            param.requires_grad = True

    def unfreeze_top_stages(self, unfreeze_ratio: float = 0.3) -> None:
        """Stage 2: Unfreeze the top specified percentage of backbone parameters."""
        params = list(self.backbone.parameters())
        num_params = len(params)
        num_unfrozen = int(num_params * unfreeze_ratio)

        # Freeze earlier layers
        for param in params[:-num_unfrozen]:
            param.requires_grad = False

        # Unfreeze top layers
        for param in params[-num_unfrozen:]:
            param.requires_grad = True

        for param in self.head.parameters():
            param.requires_grad = True

    def unfreeze_all(self) -> None:
        """Stage 3: Unfreeze all network parameters for end-to-end fine-tuning."""
        for param in self.parameters():
            param.requires_grad = True

    def get_trainable_parameters_count(self) -> Tuple[int, int]:
        """Return (trainable_params, total_params)."""
        trainable = sum(p.numel() for p in self.parameters() if p.requires_grad)
        total = sum(p.numel() for p in self.parameters())
        return trainable, total
