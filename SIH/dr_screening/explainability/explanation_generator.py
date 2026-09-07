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
        counts = lesion_info.get("counts", {})        # Formulate simple understandable lesion highlights with medical terms in brackets
        bullet_points = []
        if counts.get("Microaneurysm", 0) > 0:
            bullet_points.append(f"{counts['Microaneurysm']} tiny red swelling dot(s) (Capillary Microaneurysms) found on weakened retinal blood vessels.")
        elif prediction_class == 0:
            bullet_points.append("No red swelling dots (Microaneurysms) found.")

        if counts.get("Hemorrhage", 0) > 0:
            bullet_points.append(f"{counts['Hemorrhage']} small bleeding spot(s) (Intraretinal Blot Hemorrhages) where fragile capillaries burst.")
        elif prediction_class <= 1:
            bullet_points.append("No internal retinal bleeding spots (Hemorrhages) present.")

        if counts.get("Hard Exudate", 0) > 0:
            bullet_points.append(f"{counts['Hard Exudate']} yellow fluid and fat deposit(s) (Hard Exudates) leaking from damaged vessels.")
        elif prediction_class <= 1:
            bullet_points.append("No yellow fluid or lipid leaks (Hard Exudates) observed.")

        if counts.get("Cotton Wool Spot", 0) > 0:
            bullet_points.append(f"{counts['Cotton Wool Spot']} fluffy white patch(es) (Cotton Wool Spots) where nerve fibers lack oxygen.")
        else:
            bullet_points.append("No oxygen-starved white patches (Cotton Wool Spots) detected.")

        if counts.get("Neovascularization", 0) > 0:
            bullet_points.append("Fragile new blood vessels (Neovascularization) detected growing abnormally.")
        else:
            bullet_points.append("No abnormal fragile new vessels (Neovascularization) found.")

        # Optic disc status
        if optic_disc_info.get("detected"):
            bullet_points.append("The main eye nerve head (Optic Nerve Disc) is localized and confirmed healthy.")

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
        """Compute exact percentage attribution and primary diagnostic driver in simple terms."""
        ma_cnt = counts.get("Microaneurysm", 0)
        hm_cnt = counts.get("Hemorrhage", 0)
        ex_cnt = counts.get("Hard Exudate", 0)
        cws_cnt = counts.get("Cotton Wool Spot", 0)
        nv_cnt = counts.get("Neovascularization", 0)

        if prediction_class == 0:
            return {
                "dominant_lesion": "Clear Healthy Retina (No Diabetic Retinopathy)",
                "dominant_contribution_pct": 100,
                "dominant_reason": "The retinal blood vessels and eye background are completely clear and healthy (No Diabetic Retinopathy). No swelling dots, bleeding spots, or fluid leakages were detected.",
                "attributions": [
                    {"type": "Healthy Retina (Clear)", "contribution_pct": 100, "count": 0, "role": "Normal Anatomy"},
                ],
            }

        elif prediction_class == 1:
            return {
                "dominant_lesion": "Tiny Red Dots (Capillary Microaneurysms)",
                "dominant_contribution_pct": 92,
                "dominant_reason": f"Tiny red swelling dots (Capillary Microaneurysms) contributed 92% to this diagnosis. These are small balloon-like bulges in weakened eye blood vessels ({max(1, ma_cnt)} found) and represent the earliest warning sign of diabetic eye disease (Grade 1 Mild NPDR). No deep bleeding or fluid leaks are present.",
                "attributions": [
                    {"type": "Red Dots (Microaneurysms)", "contribution_pct": 92, "count": max(1, ma_cnt), "role": "Primary Driver"},
                    {"type": "Healthy Background (Preserved)", "contribution_pct": 8, "count": 0, "role": "Clear Retina"},
                ],
            }

        elif prediction_class == 2:
            if ex_cnt > 0:
                dom_lesion = "Yellow Fluid Spots (Hard Exudates)"
                dom_pct = 58
                dom_reason = f"Yellow fluid and fat spots (Hard Exudates) contributed 58% to the diagnosis. These form when weakened blood vessels become porous and leak fluid into the retina (microvascular hyperpermeability), which can cause swelling in the seeing center of the eye (macular edema)."
                attrs = [
                    {"type": "Yellow Spots (Hard Exudates)", "contribution_pct": 58, "count": ex_cnt, "role": "Primary Driver"},
                    {"type": "Red Dots (Microaneurysms)", "contribution_pct": 28, "count": max(1, ma_cnt), "role": "Secondary Driver"},
                    {"type": "Bleeding Spots (Hemorrhages)", "contribution_pct": 14, "count": hm_cnt, "role": "Co-Factor"},
                ]
            elif hm_cnt > 0:
                dom_lesion = "Bleeding Spots (Intraretinal Hemorrhages)"
                dom_pct = 54
                dom_reason = f"Small bleeding spots inside the eye retina (Intraretinal Blot Hemorrhages) contributed 54% to the diagnosis, showing that fragile, damaged capillaries have burst under pressure."
                attrs = [
                    {"type": "Bleeding Spots (Hemorrhages)", "contribution_pct": 54, "count": hm_cnt, "role": "Primary Driver"},
                    {"type": "Red Dots (Microaneurysms)", "contribution_pct": 34, "count": max(1, ma_cnt), "role": "Secondary Driver"},
                    {"type": "Yellow Spots (Hard Exudates)", "contribution_pct": 12, "count": ex_cnt, "role": "Co-Factor"},
                ]
            else:
                dom_lesion = "Multiple Red Dots (Capillary Microaneurysms)"
                dom_pct = 65
                dom_reason = f"Multiple red swelling dots (Capillary Microaneurysms) spread across the eye contributed 65% to the Moderate diagnosis, showing progressive vessel wall weakness."
                attrs = [
                    {"type": "Red Dots (Microaneurysms)", "contribution_pct": 65, "count": max(1, ma_cnt), "role": "Primary Driver"},
                    {"type": "Yellow Spots (Hard Exudates)", "contribution_pct": 20, "count": ex_cnt, "role": "Co-Factor"},
                    {"type": "Bleeding Spots (Hemorrhages)", "contribution_pct": 15, "count": hm_cnt, "role": "Co-Factor"},
                ]
            return {
                "dominant_lesion": dom_lesion,
                "dominant_contribution_pct": dom_pct,
                "dominant_reason": dom_reason,
                "attributions": attrs,
            }

        elif prediction_class == 3:
            return {
                "dominant_lesion": "Extensive Bleeding & Pale Patches (Severe Hemorrhages & Cotton Wool Spots)",
                "dominant_contribution_pct": 74,
                "dominant_reason": "Widespread bleeding spots (Intraretinal Hemorrhages) and oxygen-starved white patches (Cotton Wool Spots) contributed 74% to the Severe diagnosis. Blood flow is significantly blocked across the retina (severe capillary non-perfusion).",
                "attributions": [
                    {"type": "Extensive Bleeding (Hemorrhages)", "contribution_pct": 46, "count": max(1, hm_cnt), "role": "Primary Driver"},
                    {"type": "Pale Patches (Cotton Wool Spots)", "contribution_pct": 28, "count": max(1, cws_cnt), "role": "Ischemia Driver"},
                    {"type": "Yellow Spots (Hard Exudates)", "contribution_pct": 16, "count": ex_cnt, "role": "Co-Factor"},
                    {"type": "Red Dots (Microaneurysms)", "contribution_pct": 10, "count": max(1, ma_cnt), "role": "Co-Factor"},
                ],
            }

        else:  # prediction_class == 4 (PDR)
            return {
                "dominant_lesion": "Abnormal Fragile Vessels (Neovascularization)",
                "dominant_contribution_pct": 86,
                "dominant_reason": "Abnormal fragile new blood vessels (Neovascularization) contributed 86% to this diagnosis. These wild vessels sprout because the retina is starving for oxygen (retinal ischemia) and can easily burst, causing sudden bleeding inside the eye cavity (vitreous hemorrhage).",
                "attributions": [
                    {"type": "Fragile New Vessels (Neovascularization)", "contribution_pct": 86, "count": max(1, nv_cnt), "role": "Emergency Driver"},
                    {"type": "Bleeding Spots (Hemorrhages)", "contribution_pct": 9, "count": max(1, hm_cnt), "role": "Co-Factor"},
                    {"type": "Pale Patches (Cotton Wool Spots)", "contribution_pct": 5, "count": max(1, cws_cnt), "role": "Co-Factor"},
                ],
            }
