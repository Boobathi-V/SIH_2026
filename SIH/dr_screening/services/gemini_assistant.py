"""Gemini-powered VoiceAI Assistant Service (Buddy) for Diabetic Retinopathy Triage.

Provides context-aware clinical explanations for predicted DR classes, lesion types,
follow-up protocols, and lifestyle guidance in English, Tamil, and other languages.
Includes robust offline fallback if network connectivity is absent.
"""

import os
import re
import json
import urllib.request
from typing import Dict, Any, Optional

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
CANDIDATE_MODELS = [
    "gemini-3.1-flash-lite",
    "gemini-2.5-flash",
    "gemini-flash-latest",
]


def clean_for_speech(text: str) -> str:
    """Strip markdown formatting, bullet symbols, and brackets for clean TTS speech output."""
    # Remove markdown bold/italic asterisks
    cleaned = re.sub(r"\*+", "", text)
    # Remove markdown links [text](url) -> text
    cleaned = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", cleaned)
    # Remove hashtags and headers
    cleaned = re.sub(r"#+\s*", "", cleaned)
    # Remove bullet points
    cleaned = re.sub(r"^[•\-\*]\s*", "", cleaned, flags=re.MULTILINE)
    # Collapse multiple whitespace
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def build_system_prompt(prediction_context: Optional[Dict[str, Any]]) -> str:
    """Build empathetic medical AI assistant prompt with patient screening context."""
    if not prediction_context:
        return (
            "You are Buddy (VoiceAI Assistant), a compassionate and knowledgeable ophthalmic AI triage companion. "
            "Help the patient or healthcare worker understand Diabetic Retinopathy screening, eye health, and diabetes management."
        )

    p_class = prediction_context.get("prediction_class", prediction_context.get("class_index", 0))
    p_name = prediction_context.get("prediction", prediction_context.get("class_name", f"Class {p_class}"))
    conf = prediction_context.get("confidence", 0)
    conf_pct = round(conf * 100) if conf <= 1.0 else round(conf)
    risk = prediction_context.get("risk_level", "Unknown")
    dominant_lesion = prediction_context.get("dominant_lesion", "None")
    dominant_reason = prediction_context.get("dominant_reason", "")
    rec_action = prediction_context.get("recommended_action", "")
    lesion_counts = prediction_context.get("lesion_counts", {})
    if not lesion_counts and "counts" in prediction_context:
        lesion_counts = prediction_context.get("counts", {})

    context_summary = f"""
Current Patient Screening Findings:
- Diagnostic Grade: Class {p_class} - {p_name}
- Calibrated AI Confidence: {conf_pct}%
- Clinical Risk Tier: {risk}
- Primary Pathology Driver: {dominant_lesion}
- Clinical Justification: {dominant_reason}
- Identified Lesions: {json.dumps(lesion_counts)}
- Protocol Recommendation: {rec_action}
"""

    return f"""You are "Buddy (VoiceAI Assistant)", an empathetic, clinical AI triage companion embedded in the VisionX Diabetic Retinopathy Screening System.

{context_summary}

Instructions:
1. Answer the user's question directly, empathetically, and clearly using the specific patient findings above.
2. If asked about the prediction class, explain what it means in simple everyday language, followed by the clinical meaning in parentheses.
3. If asked about lesions (e.g., red dots/microaneurysms, yellow spots/hard exudates, bleeding/hemorrhages), explain why they formed from damaged retinal blood vessels and how to prevent worsening.
4. If the user asks in Tamil, reply in natural, supportive Tamil or clear Tanglish.
5. If the user asks in English, reply in friendly, professional English.
6. For voice inquiries, keep the primary explanation clear, direct, and under 3-4 sentences so it sounds natural when spoken aloud.
7. Always encourage follow-up with an ophthalmologist or physician while offering reassuring, practical lifestyle/dietary guidance.
"""


def generate_gemini_response(prompt: str) -> Optional[str]:
    """Call Google Gemini API using candidate models."""
    api_key = os.environ.get("GEMINI_API_KEY", GEMINI_API_KEY)
    if not api_key:
        return None

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.4,
            "maxOutputTokens": 600,
        },
    }
    data = json.dumps(payload).encode("utf-8")

    for model_name in CANDIDATE_MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=12) as resp:
                if resp.status == 200:
                    res_json = json.loads(resp.read().decode("utf-8"))
                    candidates = res_json.get("candidates", [])
                    if candidates and "content" in candidates[0]:
                        parts = candidates[0]["content"].get("parts", [])
                        if parts and "text" in parts[0]:
                            txt = parts[0]["text"].strip()
                            # Clean leading conversational prefixes like "Buddy Response:" or "Buddy:"
                            txt = re.sub(r'^(?:Buddy(?:\s*Response)?\s*:\s*)+', '', txt, flags=re.IGNORECASE)
                            txt = txt.strip(' \t\n\r"')
                            return txt
        except Exception:
            continue
    return None


def generate_offline_fallback(user_message: str, prediction_context: Optional[Dict[str, Any]], is_voice: bool) -> str:
    """Rule-based clinical fallback if internet or Gemini API is temporarily unavailable."""
    msg = (user_message or "").lower()
    p_class = 0
    if prediction_context:
        p_class = prediction_context.get("prediction_class", prediction_context.get("class_index", 0))

    if "tamil" in msg or "தமிழ்" in msg or "enna" in msg or "epadi" in msg:
        if p_class == 0:
            return "உங்கள் கண் விழித்திரை முழுமையாக ஆரோக்கியமாக உள்ளது (No DR). எந்த இரத்தக் கசிவும் அல்லது வீக்கமும் இல்லை. வருடத்திற்கு ஒரு முறை வழக்கமான பரிசோதனை போதுமானது."
        elif p_class == 1:
            return "உங்கள் விழித்திரையில் ஆரம்ப நிலை சிறிய சிவப்பு புள்ளிகள் (Microaneurysms) கண்டறியப்பட்டுள்ளன (Grade 1 Mild DR). இது ஆரம்ப நிலைதான். சர்க்கரை மற்றும் இரத்த அழுத்தத்தை கட்டுப்பாட்டில் வைத்திருங்கள்; 6 மாதங்களில் மருத்துவரை அணுகவும்."
        elif p_class == 2:
            return "உங்கள் விழித்திரையில் இரத்தக் கசிவு அல்லது மஞ்சள் கொழுப்பு படிவுகள் (Hard Exudates) உள்ளன (Grade 2 Moderate DR). கண் பார்வை பாதிக்காமல் இருக்க 4 முதல் 8 வாரங்களுக்குள் கண் மருத்துவரை (Ophthalmologist) அணுகவும்."
        elif p_class >= 3:
            return "உங்கள் விழித்திரையில் தீவிர பாதிப்பு (Severe / Proliferative DR) கண்டறியப்பட்டுள்ளது. பார்வை இழப்பைத் தடுக்க உடனடியாக அவசரமாக கண் மருத்துவரை அணுகி சிகிச்சை பெற வேண்டும்."

    # English Fallback
    if "mean" in msg or "class" in msg or "prediction" in msg or "diagnosis" in msg or "result" in msg:
        if p_class == 0:
            return (
                "Your screening shows **Class 0: No Diabetic Retinopathy**. "
                "Your retinal blood vessels and background are clear and healthy with no microaneurysms or fluid leaks. "
                "Maintain healthy blood sugar levels and schedule your routine annual retinal checkup."
            )
        elif p_class == 1:
            return (
                "Your screening shows **Class 1: Mild Non-Proliferative Diabetic Retinopathy (NPDR)**. "
                "We detected tiny red swelling dots called microaneurysms where fragile capillaries have slightly bulged. "
                "This is the earliest warning sign. With strict blood sugar and blood pressure control, it can be stabilized. "
                "A follow-up retinal examination in 6 to 12 months is recommended."
            )
        elif p_class == 2:
            return (
                "Your screening shows **Class 2: Moderate Non-Proliferative Diabetic Retinopathy (NPDR)**. "
                "There are multiple microvascular changes, including deeper intraretinal hemorrhages or yellow lipid deposits (hard exudates). "
                "You should consult an ophthalmologist within 4 to 8 weeks for a dilated fundus exam and possible macular OCT scan."
            )
        elif p_class == 3:
            return (
                "Your screening shows **Class 3: Severe Non-Proliferative Diabetic Retinopathy (NPDR)**. "
                "Extensive retinal blood flow blockages (ischemia) and bleeding spots are present. "
                "This is a sight-threatening stage requiring prompt ophthalmic consultation within 1 to 2 weeks."
            )
        elif p_class == 4:
            return (
                "Your screening shows **Class 4: Proliferative Diabetic Retinopathy (PDR)**. "
                "Abnormal, fragile new blood vessels (neovascularization) have begun growing across the retina or optic disc, which can bleed into the eye. "
                "Immediate specialist intervention (laser photocoagulation or anti-VEGF therapy) is strongly advised."
            )

    if "red dot" in msg or "microaneurysm" in msg or "aneurysm" in msg:
        return (
            "**Microaneurysms** are tiny, balloon-like bulges in the fragile capillaries of the retina caused by prolonged high blood sugar. "
            "They appear as pinpoint red dots and are the hallmark earliest sign of diabetic retinopathy. Keeping your HbA1c below 7% helps prevent them from leaking."
        )

    if "yellow spot" in msg or "exudate" in msg:
        return (
            "**Hard Exudates** are yellow-white deposits of lipids and proteins that leak out when weakened retinal blood vessels become permeable. "
            "If they accumulate near the central seeing area (macula), they can cause blurred vision (macular edema). Controlling cholesterol and blood pressure is vital."
        )

    if "doctor" in msg or "when" in msg or "referral" in msg or "specialist" in msg:
        if p_class <= 1:
            return "For Class 1 Mild DR, schedule a follow-up with your eye doctor in 6 to 12 months. If you notice any sudden vision changes or floaters, see a doctor sooner."
        else:
            return "Because your scan indicates Moderate or higher severity, you should see an ophthalmologist for a comprehensive dilated eye exam and optical coherence tomography (OCT) as soon as possible."

    # General fallback
    return (
        f"Buddy here! Your current scan was graded as Class {p_class}. "
        "I can help explain what your specific grade means, what the detected lesions represent, diet and lifestyle advice, or how soon you should consult an ophthalmologist. "
        "Feel free to ask by voice or type any question!"
    )


def generate_dr_chat_response(
    user_message: str,
    is_voice: bool = False,
    prediction_context: Optional[Dict[str, Any]] = None,
    language: str = "auto",
) -> Dict[str, Any]:
    """Process user message and return both text response and speech-friendly audio text."""
    clean_msg = (user_message or "").strip()
    if not clean_msg:
        return {
            "reply_text": "Hello! I am Buddy, your VoiceAI Assistant. How can I help you understand your retinal screening results today?",
            "speak_text": "Hello! I am Buddy, your Voice AI Assistant. How can I help you understand your retinal screening results today?",
            "is_voice": is_voice,
            "provider": "default",
        }

    system_prompt = build_system_prompt(prediction_context)
    full_prompt = f"{system_prompt}\n\nUser Question ({'Voice input' if is_voice else 'Text input'}): {clean_msg}\nBuddy Response:"

    gemini_reply = generate_gemini_response(full_prompt)
    if gemini_reply:
        reply_text = gemini_reply
        provider = "gemini-3.1-flash"
    else:
        reply_text = generate_offline_fallback(clean_msg, prediction_context, is_voice)
        provider = "clinical-offline-engine"

    speak_text = clean_for_speech(reply_text)

    return {
        "reply_text": reply_text,
        "speak_text": speak_text,
        "is_voice": is_voice,
        "provider": provider,
    }
