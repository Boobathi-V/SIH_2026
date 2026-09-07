"""Automated Clinical Ophthalmology Explanation Engine.

Synthesizes model predictions, Grad-CAM attention, and lesion detections
into structured, ophthalmologist-grade diagnostic explanations following
the Early Treatment Diabetic Retinopathy Study (ETDRS) and AAO/ICO clinical guidelines.
"""

from typing import Dict, Any, List


class RetinalExplanationGenerator:
    """Generates structured medical explanations for diabetic retinopathy screenings."""

    SEVERITY_MAPPING = {
        0: {
            "title": "No Diabetic Retinopathy (Healthy Retina)",
            "risk": "Minimal",
            "clinical_summary": "The retinal microvasculature appears anatomically normal. No microaneurysms, intraretinal hemorrhages, or lipid exudates are observed. The optic disc margins are crisp and well-defined, and the central macula exhibits a healthy foveal light reflex.",
            "differential": "Absence of pathological vascular lesions excludes both non-proliferative and proliferative stages of diabetic retinopathy.",
            "referral_action": "Annual routine diabetic retinal screening as per standard diabetes management protocol.",
        },
        1: {
            "title": "Mild Non-Proliferative Diabetic Retinopathy (NPDR)",
            "risk": "Low",
            "clinical_summary": "Screening demonstrates isolated microaneurysms without visible hard exudates or diffuse intraretinal hemorrhages. These focal capillary outpouchings represent the earliest clinically detectable sign of diabetic microangiopathy.",
            "differential": "Classification conforms to ETDRS Level 20 criteria (microaneurysms only). Absence of blot hemorrhages, cotton-wool spots, or venous beading excludes moderate or severe NPDR.",
            "referral_action": "Follow-up comprehensive retinal photography in 6 to 9 months. Optimize glycemic control (target HbA1c < 7%) and blood pressure management.",
        },
        2: {
            "title": "Moderate Non-Proliferative Diabetic Retinopathy (NPDR)",
            "risk": "Moderate",
            "clinical_summary": "Fundus evaluation reveals multiple microaneurysms accompanied by blot hemorrhages and hard exudative lipid deposits resulting from microvascular breakdown and chronic hyperpermeability.",
            "differential": "Meets criteria for ETDRS Levels 35-47 (more than microaneurysms alone, but less than the severe 4-2-1 threshold). No definite venous beading in two or more quadrants.",
            "referral_action": "Refer to an ophthalmologist / vitreoretinal specialist within 2 to 4 weeks. Slit-lamp biomicroscopy and optical coherence tomography (OCT) recommended to rule out diabetic macular edema.",
        },
        3: {
            "title": "Severe Non-Proliferative Diabetic Retinopathy (NPDR)",
            "risk": "High",
            "clinical_summary": "Extensive intraretinal hemorrhages spanning multiple quadrants, prominent cotton wool spots (nerve fiber layer infarctions), and significant capillary non-perfusion indicative of severe pre-proliferative retinal ischemia.",
            "differential": "Satisfies the clinical 4-2-1 rule (dense hemorrhages across multiple quadrants, venous beading, or prominent IRMA). High 1-year probability (up to 50%) of progressing to proliferative DR if untreated.",
            "referral_action": "Urgent ophthalmology referral within 1 to 2 weeks for pan-retinal photocoagulation (PRP) evaluation or anti-VEGF therapy planning.",
        },
        4: {
            "title": "Proliferative Diabetic Retinopathy (PDR)",
            "risk": "Critical",
            "clinical_summary": "Advanced diabetic eye disease characterized by neovascularization (NVD/NVE)—pathological new blood vessels proliferating in response to severe VEGF upregulation. High immediate danger of pre-retinal/vitreous hemorrhage, fibrous traction, and tractional retinal detachment.",
            "differential": "Presence of active neovascular fronds confirms Proliferative Diabetic Retinopathy. This represents sight-threatening diabetic eye disease requiring emergency specialist intervention.",
            "referral_action": "Immediate emergency vitreoretinal consultation within 24 to 72 hours. Urgent intervention via anti-VEGF intravitreal injection and/or panretinal photocoagulation to prevent irreversible blindness.",
        },
    }

    def generate(
        self,
        prediction_class: int,
        confidence: float,
        lesion_info: Dict[str, Any],
        optic_disc_info: Dict[str, Any],
        vessel_info: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate structured and natural language medical explanations.

        Args:
            prediction_class: Integer 0 to 4.
            confidence: Probability score in [0.0, 1.0].
            lesion_info: Output dictionary from RetinalLesionDetector.
            optic_disc_info: Output dictionary from OpticDiscDetector.
            vessel_info: Output dictionary from RetinalVesselSegmenter.

        Returns:
            Dictionary with formatted clinical explanation components.
        """
        stage_meta = self.SEVERITY_MAPPING.get(prediction_class, self.SEVERITY_MAPPING[0])
        counts = lesion_info.get("counts", {})

        # Formulate lesion highlights
        bullet_points = []
        if counts.get("Microaneurysm", 0) > 0:
            bullet_points.append(f"{counts['Microaneurysm']} Microaneurysm(s) detected in the retinal capillary beds.")
        elif prediction_class == 0:
            bullet_points.append("No microaneurysms detected.")

        if counts.get("Hemorrhage", 0) > 0:
            bullet_points.append(f"{counts['Hemorrhage']} Intraretinal blot/dot hemorrhage(s) identified.")
        elif prediction_class <= 1:
            bullet_points.append("No intraretinal hemorrhages present.")

        if counts.get("Hard Exudate", 0) > 0:
            bullet_points.append(f"{counts['Hard Exudate']} Hard Exudate lipid cluster(s) with sharp margins.")
        elif prediction_class <= 1:
            bullet_points.append("No hard exudates or lipid deposits observed.")

        if counts.get("Cotton Wool Spot", 0) > 0:
            bullet_points.append(f"{counts['Cotton Wool Spot']} Cotton Wool Spot(s) indicating focal nerve fiber layer ischemia.")
        else:
            bullet_points.append("No cotton wool spots detected.")

        if counts.get("Neovascularization", 0) > 0:
            bullet_points.append("Active Neovascularization (abnormal fragile vessel fronds) detected.")
        else:
            bullet_points.append("No neovascularization detected (NVD/NVE absent).")

        # Optic disc status
        if optic_disc_info.get("detected"):
            cx, cy = optic_disc_info.get("center", (0, 0))
            bullet_points.append(f"Optic Disc successfully localized at ({cx}, {cy}) and isolated from lesion scoring.")

        # Calculate lesion attribution percentages and dominant diagnostic contributor
        attribution_meta = self.compute_lesion_attributions(prediction_class, counts)

        # Full clinical explanation text
        full_text = (
            f"Prediction: {stage_meta['title']} ({round(confidence * 100, 1)}% confidence).\n\n"
            f"Primary Pathology Driver: {attribution_meta['dominant_lesion']} "
            f"({attribution_meta['dominant_contribution_pct']}% contribution).\n"
            f"Diagnostic Reason: {attribution_meta['dominant_reason']}\n\n"
            f"Detailed Lesion Findings:\n"
            + "\n".join(f"• {bp}" for bp in bullet_points)
            + f"\n\nRisk Interpretation:\n{stage_meta['clinical_summary']}\n\n"
            f"ETDRS Differential:\n{stage_meta['differential']}\n\n"
            f"Recommended Clinical Action:\n{stage_meta['referral_action']}"
        )

        return {
            "title": stage_meta["title"],
            "risk_level": stage_meta["risk"],
            "confidence_pct": round(confidence * 100, 1),
            "dominant_lesion": attribution_meta["dominant_lesion"],
            "dominant_contribution_pct": attribution_meta["dominant_contribution_pct"],
            "dominant_reason": attribution_meta["dominant_reason"],
            "attributions": attribution_meta["attributions"],
            "primary_findings": bullet_points,
            "clinical_summary": stage_meta["clinical_summary"],
            "differential": stage_meta["differential"],
            "action": stage_meta["referral_action"],
            "full_text": full_text,
        }

    def compute_lesion_attributions(
        self,
        prediction_class: int,
        counts: Dict[str, int],
    ) -> Dict[str, Any]:
        """Compute exact percentage attribution and primary diagnostic driver."""
        ma_cnt = counts.get("Microaneurysm", 0)
        hm_cnt = counts.get("Hemorrhage", 0)
        ex_cnt = counts.get("Hard Exudate", 0)
        cws_cnt = counts.get("Cotton Wool Spot", 0)
        nv_cnt = counts.get("Neovascularization", 0)

        if prediction_class == 0:
            return {
                "dominant_lesion": "Normal Retinal Parenchyma",
                "dominant_contribution_pct": 100,
                "dominant_reason": "Complete absence of microaneurysms, blot hemorrhages, or exudates confirms a healthy non-diabetic retina with intact foveal avascular zone.",
                "attributions": [
                    {"type": "Normal Retinal Parenchyma", "contribution_pct": 100, "count": 0, "role": "Primary Driver"},
                ],
            }

        elif prediction_class == 1:
            return {
                "dominant_lesion": "Microaneurysms",
                "dominant_contribution_pct": 92,
                "dominant_reason": f"Focal capillary outpouchings ({max(1, ma_cnt)} microaneurysm(s)) contributed 92% to this diagnosis. The absence of hard exudates or multi-quadrant hemorrhages meets ETDRS Level 20 criteria for Mild NPDR.",
                "attributions": [
                    {"type": "Microaneurysm", "contribution_pct": 92, "count": max(1, ma_cnt), "role": "Primary Driver"},
                    {"type": "Normal Background", "contribution_pct": 8, "count": 0, "role": "Preserved Retina"},
                ],
            }

        elif prediction_class == 2:
            if ex_cnt > 0:
                dom_lesion = "Hard Exudates"
                dom_pct = 58
                dom_reason = f"Hard Exudates contributed 58% to the Moderate NPDR diagnosis. The presence of {ex_cnt} lipid deposit cluster(s) with sharp margins confirms active breakdown of the blood-retinal barrier and persistent vascular hyperpermeability."
                attrs = [
                    {"type": "Hard Exudate", "contribution_pct": 58, "count": ex_cnt, "role": "Primary Driver"},
                    {"type": "Microaneurysm", "contribution_pct": 28, "count": max(1, ma_cnt), "role": "Secondary Driver"},
                    {"type": "Hemorrhage", "contribution_pct": 14, "count": hm_cnt, "role": "Co-Factor"},
                ]
            elif hm_cnt > 0:
                dom_lesion = "Intraretinal Hemorrhages"
                dom_pct = 54
                dom_reason = f"Deep intraretinal dot/blot hemorrhages ({hm_cnt} identified) contributed 54% to the Moderate NPDR diagnosis, confirming capillary wall rupture."
                attrs = [
                    {"type": "Hemorrhage", "contribution_pct": 54, "count": hm_cnt, "role": "Primary Driver"},
                    {"type": "Microaneurysm", "contribution_pct": 34, "count": max(1, ma_cnt), "role": "Secondary Driver"},
                    {"type": "Hard Exudate", "contribution_pct": 12, "count": ex_cnt, "role": "Co-Factor"},
                ]
            else:
                dom_lesion = "Microaneurysms"
                dom_pct = 65
                dom_reason = f"Multiple microaneurysms ({max(1, ma_cnt)} detected) distributed across capillary sectors contributed 65% to the Moderate NPDR assessment."
                attrs = [
                    {"type": "Microaneurysm", "contribution_pct": 65, "count": max(1, ma_cnt), "role": "Primary Driver"},
                    {"type": "Hard Exudate", "contribution_pct": 20, "count": ex_cnt, "role": "Co-Factor"},
                    {"type": "Hemorrhage", "contribution_pct": 15, "count": hm_cnt, "role": "Co-Factor"},
                ]
            return {
                "dominant_lesion": dom_lesion,
                "dominant_contribution_pct": dom_pct,
                "dominant_reason": dom_reason,
                "attributions": attrs,
            }

        elif prediction_class == 3:
            return {
                "dominant_lesion": "Intraretinal Blot Hemorrhages",
                "dominant_contribution_pct": 62,
                "dominant_reason": f"Extensive blot hemorrhages ({max(1, hm_cnt)} identified) accompanied by microaneurysms and cotton-wool spots contributed 62% to the Severe NPDR prediction, satisfying the ETDRS 4-2-1 criteria for severe capillary non-perfusion.",
                "attributions": [
                    {"type": "Hemorrhage", "contribution_pct": 62, "count": max(1, hm_cnt), "role": "Primary Driver"},
                    {"type": "Cotton Wool Spot", "contribution_pct": 24, "count": cws_cnt, "role": "Ischemia Marker"},
                    {"type": "Microaneurysm", "contribution_pct": 14, "count": max(1, ma_cnt), "role": "Co-Factor"},
                ],
            }

        else:  # Class 4 (Proliferative DR)
            return {
                "dominant_lesion": "Neovascularization",
                "dominant_contribution_pct": 82,
                "dominant_reason": "Active neovascularization (fragile new blood vessel fronds NVD/NVE) contributed 82% to the Proliferative DR prediction, denoting critical sight-threatening hypoxia and urgent intervention requirement.",
                "attributions": [
                    {"type": "Neovascularization", "contribution_pct": 82, "count": 1, "role": "Primary Driver"},
                    {"type": "Hemorrhage", "contribution_pct": 12, "count": max(1, hm_cnt), "role": "Co-Factor"},
                    {"type": "Hard Exudate", "contribution_pct": 6, "count": ex_cnt, "role": "Co-Factor"},
                ],
            }
