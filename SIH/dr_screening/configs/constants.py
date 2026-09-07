"""Clinical and architectural constants for SIH26038 Diabetic Retinopathy Screening."""

from typing import Dict, List, Tuple

# Number of classes
NUM_CLASSES: int = 5

# Human-readable DR class labels
CLASS_NAMES: List[str] = [
    "No DR",
    "Mild DR",
    "Moderate DR",
    "Severe DR",
    "Proliferative DR",
]

# Clinical risk mapping for triage recommendations
CLINICAL_RISK_MAP: Dict[int, Dict[str, str]] = {
    0: {
        "severity": "No Diabetic Retinopathy",
        "risk_level": "None",
        "action": "Routine annual dilated retinal screening recommended.",
    },
    1: {
        "severity": "Mild Non-Proliferative DR",
        "risk_level": "Low",
        "action": "Follow-up screening in 6 to 12 months; optimize glycemic control.",
    },
    2: {
        "severity": "Moderate Non-Proliferative DR",
        "risk_level": "Moderate",
        "action": "Referral to ophthalmology clinic within 4 to 8 weeks for detailed evaluation.",
    },
    3: {
        "severity": "Severe Non-Proliferative DR",
        "risk_level": "High",
        "action": "Urgent ophthalmology referral within 2 to 4 weeks; assess for pan-retinal photocoagulation.",
    },
    4: {
        "severity": "Proliferative DR",
        "risk_level": "Critical",
        "action": "Immediate ophthalmological emergency referral; high risk of severe visual impairment/vitreous hemorrhage.",
    },
}

# Image dimensions
DEFAULT_IMAGE_SIZE: Tuple[int, int] = (384, 384)

# ImageNet normalization statistics
IMAGENET_MEAN: Tuple[float, float, float] = (0.485, 0.456, 0.406)
IMAGENET_STD: Tuple[float, float, float] = (0.229, 0.224, 0.225)

# Primary model architecture
DEFAULT_BACKBONE: str = "resnet50"

# Fallback backbones
SUPPORTED_BACKBONES: List[str] = [
    "tf_efficientnetv2_s.in21k_ft_in1k",
    "convnext_tiny",
    "resnet50",
    "densenet121",
]
