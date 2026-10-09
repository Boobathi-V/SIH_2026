"""Chat API Route for VoiceAI Assistant (Buddy).

Handles voice and text inquiries concerning diabetic retinopathy prediction grades,
microvascular lesion types, clinical urgency, and lifestyle guidance.
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, Body
from pydantic import BaseModel, Field

from dr_screening.services.gemini_assistant import generate_dr_chat_response

router = APIRouter(prefix="/api/chat", tags=["VoiceAI Assistant (Buddy)"])


class ChatRequest(BaseModel):
    message: str = Field(..., description="User query in text or transcribed voice")
    is_voice: bool = Field(default=False, description="True if query originated from voice mic")
    language: str = Field(default="auto", description="User language preference: auto, en, ta")
    prediction_context: Optional[Dict[str, Any]] = Field(default=None, description="Current patient screening data")


class ChatResponse(BaseModel):
    reply_text: str
    speak_text: str
    is_voice: bool
    provider: str


@router.post("", response_model=ChatResponse)
def chat_with_buddy(req: ChatRequest = Body(...)) -> Dict[str, Any]:
    """Process question about DR prediction grade and return text + speech response."""
    return generate_dr_chat_response(
        user_message=req.message,
        is_voice=req.is_voice,
        prediction_context=req.prediction_context,
        language=req.language,
    )
