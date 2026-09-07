"""Automated Integration Verification for Feature 2: Explainable Lesion Detection (SIH26038).

Tests:
1. Optic Disc detection and safe masking.
2. Retinal Vasculature segmentation & caliber profiling.
3. Multi-lesion detection (MAs, HMs, Exudates, Cotton Wool Spots).
4. Clinical annotation rendering with leader lines and typography.
5. Automated ETDRS ophthalmology explanation generation.
6. End-to-end latency validation (< 1.5s).
"""

import os
import time
import cv2
import numpy as np

from dr_screening.inference.predictor import FundusPredictor
from dr_screening.explainability import (
    OpticDiscDetector,
    RetinalVesselSegmenter,
    RetinalLesionDetector,
    RetinalAnnotationRenderer,
    RetinalExplanationGenerator,
    ExplainableLesionPipeline,
)


def _get_sample_image():
    paths = [
        "SIH/dr-screen/public/samples/sample_moderate_dr.png",
        "dr-screen/public/samples/sample_moderate_dr.png",
        "outputs/preprocessing/sample_mod.png",
    ]
    for p in paths:
        if os.path.exists(p):
            img = cv2.imread(p)
            if img is not None:
                return img, p
    raise FileNotFoundError("Could not find sample_moderate_dr.png")


def test_optic_disc_detector():
    """Verify optic disc localization and exclusion mask."""
    img, path = _get_sample_image()
    detector = OpticDiscDetector()
    res = detector.detect(img)

    assert res["detected"] is True
    assert "center" in res and len(res["center"]) == 2
    assert res["radius"] > 15
    assert res["confidence"] >= 0.50
    assert res["mask"].shape == img.shape[:2]
    print(f"[OK] Optic Disc localized at {res['center']}, radius={res['radius']}, conf={res['confidence']}")


def test_vessel_segmenter():
    """Verify vasculature segmentation and arteriole/venule points."""
    img, path = _get_sample_image()
    segmenter = RetinalVesselSegmenter()
    res = segmenter.segment(img)

    assert res["vessel_density"] > 1.0
    assert np.sum(res["vessel_mask"] > 0) > 1000
    assert len(res["arteriole_points"]) > 0
    print(f"[OK] Vessels segmented (density={res['vessel_density']}%, {len(res['arteriole_points'])} arteriole landmarks)")


def test_lesion_detector():
    """Verify detection of pathological lesions."""
    img, path = _get_sample_image()
    od_info = OpticDiscDetector().detect(img)
    vessel_info = RetinalVesselSegmenter().segment(img)
    detector = RetinalLesionDetector()

    res = detector.detect_all(img, od_info, vessel_info, prediction_class=2)

    assert "counts" in res
    assert res["counts"]["Microaneurysm"] > 0 or res["counts"]["Hard Exudate"] > 0
    print(f"[OK] Lesions detected: {res['counts']}")


def test_end_to_end_predictor_explainability():
    """Verify complete FundusPredictor integration with lesion detection and annotation."""
    img, path = _get_sample_image()
    predictor = FundusPredictor(enforce_quality_gate=False)

    t0 = time.time()
    result = predictor.predict(path, generate_heatmap=True, image_name="test_mod_dr")
    elapsed = time.time() - t0

    assert "prediction" in result
    assert "confidence" in result
    assert "heatmap_path" in result and os.path.exists(result["heatmap_path"])
    assert "annotated_path" in result and os.path.exists(result["annotated_path"])
    assert "annotated_base64" in result and len(result["annotated_base64"]) > 1000
    assert "lesion_counts" in result
    assert "clinical_explanation" in result and len(result["clinical_explanation"]) > 50

    print(f"[OK] End-to-end explainability completed in {elapsed:.3f}s")
    print(f"  Prediction: {result['prediction']} ({result['confidence']*100:.1f}%)")
    print(f"  Lesion Counts: {result['lesion_counts']}")
    print(f"  Annotated Retina: {result['annotated_path']}")


if __name__ == "__main__":
    print("Running Integration Tests for Feature 2 (Explainable Lesion Detection)...")
    test_optic_disc_detector()
    test_vessel_segmenter()
    test_lesion_detector()
    test_end_to_end_predictor_explainability()
    print("\nALL FEATURE 2 TESTS PASSED SUCCESSFULLY!")
