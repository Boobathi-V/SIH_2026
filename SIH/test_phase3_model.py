"""Phase 3 Verification: EfficientNetV2-S model forward pass, parameter unfreezing, and Grad-CAM target layer."""

import torch
from dr_screening.models.classifier import DRScreeningModel
from dr_screening.configs.constants import NUM_CLASSES


def test_phase3():
    print("=== Phase 3: Model Architecture Verification ===")

    # Test Primary Architecture: EfficientNetV2-S
    print("Instantiating primary model: tf_efficientnetv2_s...")
    model = DRScreeningModel(
        backbone_name="tf_efficientnetv2_s.in21k_ft_in1k",
        num_classes=NUM_CLASSES,
        pretrained=False, # Verify architecture mechanics immediately
        dropout_rate=0.3,
        hidden_dim=256,
    )

    # 1. Forward Pass Test
    dummy_input = torch.randn(2, 3, 384, 384)
    logits = model(dummy_input)

    print(f"[OK] Forward pass output shape: {logits.shape}")
    assert logits.shape == (2, NUM_CLASSES), f"Expected (2, {NUM_CLASSES}), got {logits.shape}"
    assert not torch.isnan(logits).any(), "NaN detected in logits"

    # 2. Feature Extraction Test
    features = model.extract_features(dummy_input)
    print(f"[OK] Bottleneck features shape: {features.shape}")
    assert features.shape == (2, model.feature_dim)

    # 3. Grad-CAM Layer Resolution
    gradcam_layer = model.get_gradcam_target_layer()
    print(f"[OK] Grad-CAM target layer: {gradcam_layer.__class__.__name__}")
    assert gradcam_layer is not None, "Grad-CAM target layer cannot be None"

    # 4. Multi-Stage Freezing / Unfreezing Tests
    trainable_full, total = model.get_trainable_parameters_count()
    print(f"[OK] Total parameters: {total:,} | Trainable (Stage 3 Full): {trainable_full:,}")

    # Stage 1: Freeze backbone
    model.freeze_backbone(True)
    trainable_stage1, _ = model.get_trainable_parameters_count()
    print(f"[OK] Trainable params in Stage 1 (Backbone frozen): {trainable_stage1:,}")
    assert trainable_stage1 < trainable_full, "Backbone was not frozen properly"

    # Stage 2: Unfreeze top 30%
    model.unfreeze_top_stages(unfreeze_ratio=0.3)
    trainable_stage2, _ = model.get_trainable_parameters_count()
    print(f"[OK] Trainable params in Stage 2 (Top 30% unfrozen): {trainable_stage2:,}")
    assert trainable_stage1 < trainable_stage2 < trainable_full

    # Stage 3: Unfreeze all
    model.unfreeze_all()
    trainable_stage3, _ = model.get_trainable_parameters_count()
    print(f"[OK] Trainable params in Stage 3 (All unfrozen): {trainable_stage3:,}")
    assert trainable_stage3 == trainable_full

    # 5. Interchangeable Backbone Test (e.g. ResNet50)
    print("Testing interchangeable backbone: resnet50...")
    resnet_model = DRScreeningModel(
        backbone_name="resnet50",
        num_classes=NUM_CLASSES,
        pretrained=False,
    )
    resnet_logits = resnet_model(dummy_input)
    assert resnet_logits.shape == (2, NUM_CLASSES)
    print(f"[OK] ResNet50 forward pass shape: {resnet_logits.shape}")

    print("=== Phase 3 Model Implementation Complete & Verified! ===")


if __name__ == "__main__":
    test_phase3()
