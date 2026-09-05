"""Modular backbone factory supporting EfficientNetV2-S, ConvNeXt, ResNet50, and DenseNet121."""

from typing import Tuple
import torch
import torch.nn as nn
import timm

from dr_screening.configs.constants import DEFAULT_BACKBONE, SUPPORTED_BACKBONES


def create_backbone(
    backbone_name: str = DEFAULT_BACKBONE,
    pretrained: bool = True,
    in_chans: int = 3,
) -> Tuple[nn.Module, int, nn.Module]:
    """Create backbone feature extractor via timm and identify the target layer for Grad-CAM.

    Args:
        backbone_name: Architecture identifier supported by timm.
        pretrained: Whether to load ImageNet weights.
        in_chans: Number of input channels (3 for RGB).

    Returns:
        (backbone_module, feature_dim, gradcam_target_layer)
    """
    # Create feature extractor without classification head (num_classes=0)
    # Using global_pool='avg' to get pooled feature vector
    backbone = timm.create_model(
        backbone_name,
        pretrained=pretrained,
        in_chans=in_chans,
        num_classes=0,
        global_pool="avg",
    )

    # Determine feature dimension
    if hasattr(backbone, "num_features"):
        feature_dim = backbone.num_features
    elif hasattr(backbone, "head") and hasattr(backbone.head, "fc"):
        feature_dim = backbone.head.fc.in_features
    else:
        # Dummy pass to resolve shape dynamically
        dummy = torch.zeros(1, in_chans, 224, 224)
        with torch.no_grad():
            out = backbone(dummy)
        feature_dim = out.shape[-1]

    # Resolve Grad-CAM target layer based on architecture
    target_layer = None
    if "efficientnet" in backbone_name.lower():
        if hasattr(backbone, "conv_head"):
            target_layer = backbone.conv_head
        elif hasattr(backbone, "blocks") and len(backbone.blocks) > 0:
            target_layer = backbone.blocks[-1]
    elif "convnext" in backbone_name.lower():
        if hasattr(backbone, "stages") and len(backbone.stages) > 0:
            target_layer = backbone.stages[-1]
    elif "resnet" in backbone_name.lower():
        if hasattr(backbone, "layer4"):
            target_layer = backbone.layer4[-1]
    elif "densenet" in backbone_name.lower():
        if hasattr(backbone, "features"):
            target_layer = backbone.features

    # Fallback to the last child layer that contains parameters
    if target_layer is None:
        children = list(backbone.children())
        target_layer = children[-1] if children else backbone

    return backbone, feature_dim, target_layer
